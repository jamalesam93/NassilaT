#!/usr/bin/env python3
"""
Audit chat JSONL token lengths against a max sequence budget (v1.4: 2048 on A6000).

Usage:
  python scripts/audit_chat_seq_lengths.py data/l3_grounding_chat.jsonl --max-length 2048
  python scripts/audit_chat_seq_lengths.py data/l3_grounding_chat.jsonl --max-length 2048 --json outputs/seq_audit.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from corpus_utils import read_jsonl  # noqa: E402


def count_tokens(messages: list[dict], tokenizer) -> int:
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=False
    )
    return len(tokenizer.encode(text, add_special_tokens=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit chat JSONL sequence lengths")
    parser.add_argument("chat_file", type=Path)
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument(
        "--model",
        default="google/gemma-4-E4B-it",
        help="Tokenizer model id (must match training base)",
    )
    parser.add_argument("--json", type=Path, default=None, dest="json_out")
    args = parser.parse_args()

    try:
        from transformers import AutoTokenizer  # type: ignore
    except ImportError as e:
        print(f"transformers required: {e}", file=sys.stderr)
        return 1

    rows = read_jsonl(args.chat_file)
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)

    overflows: list[dict] = []
    lengths: list[int] = []
    for row in rows:
        messages = row.get("messages", [])
        if not messages:
            continue
        n = count_tokens(messages, tokenizer)
        lengths.append(n)
        if n > args.max_length:
            overflows.append({"id": row.get("id", "?"), "tokens": n})

    report = {
        "file": str(args.chat_file),
        "rows": len(lengths),
        "max_length": args.max_length,
        "overflow_count": len(overflows),
        "max_tokens_seen": max(lengths) if lengths else 0,
        "p95_tokens": sorted(lengths)[int(len(lengths) * 0.95)] if lengths else 0,
        "overflows": overflows,
    }

    print(f"Audited {len(lengths)} chat row(s), max budget {args.max_length}")
    print(f"Max tokens: {report['max_tokens_seen']}, p95: {report['p95_tokens']}")
    if overflows:
        print(f"FAIL: {len(overflows)} overflow(s)")
        for item in overflows[:20]:
            print(f"  - {item['id']}: {item['tokens']} tokens")
    else:
        print("PASS: no overflows")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {args.json_out}")

    return 1 if overflows else 0


if __name__ == "__main__":
    raise SystemExit(main())
