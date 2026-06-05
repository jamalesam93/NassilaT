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
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from validate_dataset import build_grounding_user_prompt, load_jsonl  # noqa: E402
from lmstudio_smoke_test import chat_completion  # noqa: E402
from json_repair import parse_strict_json, try_parse_with_repair  # noqa: E402


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
        "--temperature",
        type=float,
        default=0.2,
    )
    args = parser.parse_args()

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
    print(f"Running {len(rows)} L3 row(s) against {args.model!r} (retry={args.retry}, repair={args.repair})")

    parse_strict = 0
    parse_after_repair = 0
    repair_needed = 0
    parse_after_retry = 0
    total_seconds = 0.0

    with args.out.open("w", encoding="utf-8") as f:
        for i, sample in enumerate(rows, 1):
            rid = sample["id"]
            prompt = build_grounding_user_prompt(
                sample["passage"],
                sample["source_excerpt"],
                sample.get("meta", {}),
            )
            attempts = args.retry + 1
            last_raw = ""
            last_status = ""
            last_repaired = False
            t0 = time.time()
            for attempt in range(1, attempts + 1):
                try:
                    last_raw = chat_completion(
                        args.base_url,
                        args.model,
                        [{"role": "user", "content": prompt}],
                        args.api_key,
                        temperature=args.temperature,
                    )
                except Exception as e:
                    last_raw = ""
                    last_status = f"error:{e}"
                    break
                status, repaired = parse_status(last_raw, args.repair)
                last_status, last_repaired = status, repaired
                if status.startswith("ok"):
                    if attempt > 1:
                        parse_after_retry += 1
                    break
            elapsed = round(time.time() - t0, 1)
            total_seconds += elapsed

            if last_status == "ok":
                parse_strict += 1
            if last_status in ("ok", "ok_repaired"):
                parse_after_repair += 1
            if last_status == "ok_repaired":
                repair_needed += 1

            f.write(
                json.dumps(
                    {
                        "id": rid,
                        "raw_output": last_raw,
                        "status": last_status,
                        "repaired_used": last_repaired,
                        "seconds": elapsed,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            f.flush()
            print(f"[{i}/{len(rows)}] {rid} {last_status} ({elapsed}s)")
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
