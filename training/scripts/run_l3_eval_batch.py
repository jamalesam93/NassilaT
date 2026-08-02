#!/usr/bin/env python3
"""
Run all L3 grounding rows in one or more JSONL files against an LM Studio
(or any OpenAI-compatible) local server, then write predictions and a
parse-rate summary.

Usage:
  python scripts/run_l3_eval_batch.py --model "google/gemma-4-e4b"
  python scripts/run_l3_eval_batch.py --model "google/gemma-4-e4b" \\
      --data data/eval_samples.jsonl data/eval_holdout_45.jsonl \\
      --retry 1 --repair --out outputs/predictions.jsonl

Then score (eval rows that have `expect` blocks):
  python scripts/evaluate_outputs.py --eval data/eval_samples.jsonl \\
      --predictions outputs/predictions.jsonl --report outputs/eval_report.json --repair
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from validate_dataset import (  # noqa: E402
    GROUNDING_SYSTEM_MESSAGE,
    build_grounding_chat_messages,
    load_jsonl,
)
from lmstudio_smoke_test import chat_completion  # noqa: E402
from json_repair import parse_strict_json, try_parse_with_repair  # noqa: E402


def fold_system_into_user(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """LM Studio peg-gemma4 workaround: some 12B loads reject system+user (HTTP 400)."""
    system_parts: list[str] = []
    user_parts: list[str] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content") or ""
        if role == "system":
            system_parts.append(content)
        elif role == "user":
            user_parts.append(content)
        else:
            user_parts.append(content)
    prefix = "\n\n".join(p for p in system_parts if p.strip())
    body = "\n\n".join(p for p in user_parts if p.strip())
    content = f"{prefix}\n\n{body}".strip() if prefix else body
    return [{"role": "user", "content": content or GROUNDING_SYSTEM_MESSAGE}]


def parse_status(raw: str, allow_repair: bool) -> tuple[str, bool]:
    """Returns (status, repaired_used). status is ok | ok_repaired | parse_fail:* | error:*"""
    ok, parsed, err = parse_strict_json(raw)
    if ok:
        return "ok", False
    if not allow_repair:
        return f"parse_fail:{err or 'invalid'}", False
    ok, parsed, err, repaired = try_parse_with_repair(raw)
    if ok and isinstance(parsed, dict) and isinstance(parsed.get("claims"), list):
        return ("ok_repaired" if repaired else "ok"), repaired
    return f"parse_fail:{err or 'invalid'}", repaired


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch L3 eval against LM Studio")
    parser.add_argument("--base-url", default="http://localhost:1234")
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key", default="lm-studio")
    parser.add_argument(
        "--data",
        nargs="+",
        type=Path,
        default=[
            TRAINING_DIR / "data" / "eval_samples.jsonl",
            TRAINING_DIR / "data" / "l3_grounding_samples.jsonl",
        ],
        help="One or more JSONL files; only l3_grounding rows are used",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=TRAINING_DIR / "outputs" / "predictions.jsonl",
        help="Where to write per-row predictions",
    )
    parser.add_argument(
        "--id",
        nargs="+",
        help="Optional list of row ids to include (default: all)",
    )
    parser.add_argument(
        "--retry",
        type=int,
        default=0,
        help="Retries per row on parse failure (default 0)",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Allow lightweight JSON repair (trailing commas, ?: keys, fences)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.5,
        help="Seconds to sleep between requests (default 0.5)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Per-request HTTP timeout seconds (default 300)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional decode seed (OpenAI-compatible servers)",
    )
    parser.add_argument(
        "--chat-template",
        action="store_true",
        help="Deprecated compatibility flag; production system+user messages are always used",
    )
    parser.add_argument(
        "--fold-system",
        action="store_true",
        help=(
            "Fold system message into the user turn (laptop LM Studio workaround for "
            "peg-gemma4 HTTP 400 on some 12B loads). Not production message shape."
        ),
    )
    parser.add_argument(
        "--disable-thinking",
        action="store_true",
        help="Pass chat_template_kwargs enable_thinking=false (Nanbeige / reasoning models)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of concurrent request threads (default 1)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Max completion tokens per request (caps thinking + JSON output)",
    )
    args = parser.parse_args()

    template_kwargs = {"enable_thinking": False} if args.disable_thinking else None

    rows: list[dict] = []
    seen: set[str] = set()
    id_filter = set(args.id) if args.id else None
    for path in args.data:
        if not path.exists():
            print(f"Warning: missing data file {path}", file=sys.stderr)
            continue
        for _, r in load_jsonl(path):
            if r.get("task") != "l3_grounding":
                continue
            rid = r.get("id")
            if not rid or rid in seen:
                continue
            if id_filter and rid not in id_filter:
                continue
            seen.add(rid)
            rows.append(r)

    if not rows:
        print("No l3_grounding rows matched.", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fold_note = ", fold-system" if args.fold_system else ""
    think_note = ", disable-thinking" if args.disable_thinking else ""
    print(
        f"Running {len(rows)} L3 row(s) against {args.model!r} "
        f"(retry={args.retry}, repair={args.repair}{fold_note}{think_note})"
    )

    parse_strict = 0
    parse_after_repair = 0
    repair_needed = 0
    parse_after_retry = 0
    total_seconds = 0.0

    def process_sample(sample: dict) -> dict:
        rid = sample["id"]
        messages = build_grounding_chat_messages(
            sample["passage"],
            sample["source_excerpt"],
            sample.get("meta", {}),
            chat_template=args.chat_template,
        )
        if args.fold_system:
            messages = fold_system_into_user(messages)
        # Qwen3/3.5: append /no_think to last user message to reliably
        # suppress reasoning tokens on llama.cpp (chat_template_kwargs
        # enable_thinking=false only works in LM Studio).
        if args.disable_thinking:
            for m in reversed(messages):
                if m.get("role") == "user":
                    m["content"] = m["content"].rstrip() + "\n/no_think"
                    break
        else:
            for m in reversed(messages):
                if m.get("role") == "user":
                    m["content"] = (
                        m["content"].rstrip()
                        + "\n\nNote: Keep your reasoning process concise (< 150 words) before writing the JSON output."
                    )
                    break
        attempts = args.retry + 1
        last_raw = ""
        last_status = ""
        last_repaired = False
        retry_count = 0
        t0 = time.time()
        for attempt in range(1, attempts + 1):
            try:
                last_raw = chat_completion(
                    args.base_url,
                    args.model,
                    messages,
                    args.api_key,
                    temperature=args.temperature,
                    seed=args.seed,
                    timeout=args.timeout,
                    chat_template_kwargs=template_kwargs,
                    max_tokens=args.max_tokens,
                )
            except Exception as e:
                last_raw = ""
                last_status = f"error:{e}"
                err_l = str(e).lower()
                if attempt < attempts and ("timed out" in err_l or "timeout" in err_l):
                    continue
                break
            status, repaired = parse_status(last_raw, args.repair)
            last_status, last_repaired = status, repaired
            if status.startswith("ok"):
                if attempt > 1:
                    retry_count = 1
                break
        elapsed = round(time.time() - t0, 1)
        return {
            "id": rid,
            "raw_output": last_raw,
            "status": last_status,
            "repaired_used": last_repaired,
            "seconds": elapsed,
            "retry_count": retry_count,
        }

    with args.out.open("w", encoding="utf-8") as f:
        if args.concurrency > 1:
            with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
                future_to_idx = {executor.submit(process_sample, sample): idx for idx, sample in enumerate(rows, 1)}
                completed = 0
                for future in as_completed(future_to_idx):
                    completed += 1
                    idx = future_to_idx[future]
                    res = future.result()
                    last_status = res["status"]
                    elapsed = res["seconds"]
                    if last_status == "ok":
                        parse_strict += 1
                    if last_status in ("ok", "ok_repaired"):
                        parse_after_repair += 1
                    if last_status == "ok_repaired":
                        repair_needed += 1
                    if res["retry_count"] > 0:
                        parse_after_retry += 1
                    total_seconds += elapsed

                    record = {
                        "id": res["id"],
                        "raw_output": res["raw_output"],
                        "status": res["status"],
                        "repaired_used": res["repaired_used"],
                        "seconds": res["seconds"],
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    f.flush()
                    print(f"[{completed}/{len(rows)}] {res['id']} {last_status} ({elapsed}s)")
        else:
            for i, sample in enumerate(rows, 1):
                res = process_sample(sample)
                last_status = res["status"]
                elapsed = res["seconds"]
                if last_status == "ok":
                    parse_strict += 1
                if last_status in ("ok", "ok_repaired"):
                    parse_after_repair += 1
                if last_status == "ok_repaired":
                    repair_needed += 1
                if res["retry_count"] > 0:
                    parse_after_retry += 1
                total_seconds += elapsed

                record = {
                    "id": res["id"],
                    "raw_output": res["raw_output"],
                    "status": res["status"],
                    "repaired_used": res["repaired_used"],
                    "seconds": res["seconds"],
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                f.flush()
                print(f"[{i}/{len(rows)}] {res['id']} {last_status} ({elapsed}s)")
                if args.sleep:
                    time.sleep(args.sleep)

    n = len(rows)
    print()
    print("Batch summary")
    print(f"  Rows:                     {n}")
    print(f"  Parse OK (strict):        {parse_strict}/{n} = {parse_strict / n:.1%}")
    print(f"  Parse OK (with repair):   {parse_after_repair}/{n} = {parse_after_repair / n:.1%}")
    if args.repair:
        print(f"  Needed JSON repair:       {repair_needed}/{n} = {repair_needed / n:.1%}")
    if args.retry > 0:
        print(f"  Recovered by retry:       {parse_after_retry}")
    print()
    print("Next: score predictions against eval sets:")
    print("  python scripts/run_eval_reports.py --predictions outputs/predictions.jsonl --repair")
    print(f"  Total time:               {total_seconds:.1f}s (avg {total_seconds / n:.1f}s/row)")
    print(f"  Predictions:              {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
