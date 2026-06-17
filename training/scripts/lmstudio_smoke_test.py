#!/usr/bin/env python3
"""
Smoke-test LM Studio (or any OpenAI-compatible local server).

Usage:
  python scripts/lmstudio_smoke_test.py --base-url http://localhost:1234 --model google/gemma-4-e4b
  python scripts/lmstudio_smoke_test.py --base-url http://localhost:1234 --model google/gemma-4-e4b --task l3_grounding
  python scripts/lmstudio_smoke_test.py --model google/gemma-4-e4b --task l3_grounding --id eval-002
  python scripts/lmstudio_smoke_test.py --model google/gemma-4-e4b --task l3_grounding --retry 1 --repair
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install requests: pip install -r requirements.txt", file=sys.stderr)
    raise SystemExit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from validate_dataset import build_grounding_chat_messages, load_jsonl  # noqa: E402
from json_repair import try_parse_with_repair  # noqa: E402


def chat_completion(
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    api_key: str = "lm-studio",
    temperature: float = 0.2,
    timeout: int = 180,
    seed: int | None = None,
) -> str:
    base = base_url.rstrip("/")
    url = f"{base}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if seed is not None:
        payload["seed"] = seed
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content")
    if not content:
        raise RuntimeError("Empty response content")
    return content


def parse_grounding(raw: str, allow_repair: bool) -> tuple[bool, str | None, bool]:
    if allow_repair:
        ok, parsed, err, repaired = try_parse_with_repair(raw)
    else:
        ok, parsed, err, repaired = try_parse_with_repair(raw)
        if repaired:
            ok = False
            err = err or "Required repair (strict mode)"
    if ok and (not isinstance(parsed, dict) or not isinstance(parsed.get("claims"), list)):
        return False, "Missing claims array", repaired
    return ok, err, repaired


def main() -> int:
    parser = argparse.ArgumentParser(description="LM Studio smoke test for Nassila")
    parser.add_argument("--base-url", default="http://localhost:1234")
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key", default="lm-studio")
    parser.add_argument(
        "--task",
        choices=("ping", "l3_grounding"),
        default="ping",
        help="ping = single word ok; l3_grounding = sample eval prompt",
    )
    parser.add_argument(
        "--sample",
        type=Path,
        default=TRAINING_DIR / "data" / "eval_samples.jsonl",
        help="JSONL file containing l3_grounding rows",
    )
    parser.add_argument(
        "--id",
        help="Specific row id to use (defaults to first l3_grounding row)",
    )
    parser.add_argument(
        "--retry",
        type=int,
        default=0,
        help="Number of retries on parse failure (default 0)",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Allow lightweight JSON repair (trailing commas, ?: keys, fences)",
    )
    parser.add_argument(
        "--chat-template",
        action="store_true",
        help="Send system+user messages matching QLoRA train layout",
    )
    args = parser.parse_args()

    if args.task == "ping":
        messages = [{"role": "user", "content": "Reply with the single word: ok"}]
        print(f"POST {args.base_url}/v1/chat/completions model={args.model!r}")
        content = chat_completion(args.base_url, args.model, messages, args.api_key)
        print("Response:", content.strip()[:200])
        return 0 if "ok" in content.lower() else 1

    rows = load_jsonl(args.sample)
    l3_rows = [r for _, r in rows if r.get("task") == "l3_grounding"]
    if args.id:
        sample = next((r for r in l3_rows if r.get("id") == args.id), None)
        if not sample:
            print(f"No l3_grounding row with id {args.id} in {args.sample}", file=sys.stderr)
            return 1
    else:
        sample = l3_rows[0] if l3_rows else None
    if not sample:
        print(f"No l3_grounding row in {args.sample}", file=sys.stderr)
        return 1

    messages = build_grounding_chat_messages(
        sample["passage"],
        sample["source_excerpt"],
        sample.get("meta", {}),
        chat_template=args.chat_template,
    )
    print(
        f"POST {args.base_url}/v1/chat/completions model={args.model!r} "
        f"task=l3_grounding id={sample['id']} retry={args.retry} repair={args.repair} "
        f"chat_template={args.chat_template}"
    )

    attempts = args.retry + 1
    last_raw = ""
    last_err: str | None = None
    last_repaired = False
    for attempt in range(1, attempts + 1):
        last_raw = chat_completion(args.base_url, args.model, messages, args.api_key)
        ok, err, repaired = parse_grounding(last_raw, args.repair)
        last_err, last_repaired = err, repaired
        suffix = " (after repair)" if repaired and ok else ""
        print(f"Attempt {attempt}/{attempts}: {'OK' if ok else f'FAIL ({err})'}{suffix}")
        if ok:
            print("Raw output (first 800 chars):")
            print(last_raw[:800])
            return 0

    print("Raw output (first 800 chars):")
    print(last_raw[:800])
    print(f"Parse check: FAILED ({last_err}; repaired_attempted={last_repaired})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
