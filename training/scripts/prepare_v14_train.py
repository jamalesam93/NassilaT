#!/usr/bin/env python3
"""
Build data/l3_grounding_train_v14a.jsonl for Vast training (seq <= 2048 tokens).

1. Cap long source_excerpt fields (chunked like inference).
2. Drop rows that fail quote validation after cap.
3. Drop rows that still exceed --max-tokens in chat template.

Usage:
  python scripts/prepare_v14_train.py
  python scripts/prepare_v14_train.py --in data/l3_grounding_train.jsonl --max-tokens 2048
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from corpus_utils import read_jsonl, write_jsonl  # noqa: E402
from generate_l3_from_corpus import capped_abstract_excerpt  # noqa: E402
from validate_dataset import build_grounding_user_prompt, validate_l3_record  # noqa: E402

DEFAULT_IN = TRAINING_DIR / "data" / "l3_grounding_train.jsonl"
DEFAULT_OUT = TRAINING_DIR / "data" / "l3_grounding_train_v14a.jsonl"
MAX_TOKENS = 2048


def cap_row_excerpt(row: dict) -> dict:
    out = dict(row)
    passage = str(row.get("passage", ""))
    excerpt = str(row.get("source_excerpt", ""))
    out["source_excerpt"] = capped_abstract_excerpt(passage, excerpt)
    return out


def row_still_valid(row: dict, line_no: int) -> list[str]:
    errors: list[str] = []
    validate_l3_record(row, line_no, errors)
    return errors


def chat_token_count(row: dict, tokenizer) -> int:
    user = build_grounding_user_prompt(
        row["passage"], row["source_excerpt"], row.get("meta", {})
    )
    assistant = json.dumps(row["output"], ensure_ascii=False)
    messages = [
        {"role": "system", "content": "You are a strict academic citation grounding assistant."},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    return len(tokenizer.encode(text, add_special_tokens=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare v1.4 train JSONL (seq-safe)")
    parser.add_argument("--in", dest="in_path", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out", dest="out_path", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    args = parser.parse_args()

    if not args.in_path.exists():
        print(f"Input not found: {args.in_path}", file=sys.stderr)
        return 1

    try:
        from transformers import AutoTokenizer  # type: ignore
    except ImportError as e:
        print(f"transformers required: {e}", file=sys.stderr)
        return 1

    rows = read_jsonl(args.in_path)
    tokenizer = AutoTokenizer.from_pretrained("google/gemma-4-E4B-it", trust_remote_code=True)

    kept: list[dict] = []
    dropped_cap: list[str] = []
    dropped_tokens: list[tuple[str, int]] = []

    for i, row in enumerate(rows, start=1):
        capped = cap_row_excerpt(row)
        errs = row_still_valid(capped, i)
        if errs:
            dropped_cap.append(f"{row.get('id', '?')}: {errs[0]}")
            continue
        n_tok = chat_token_count(capped, tokenizer)
        if n_tok > args.max_tokens:
            dropped_tokens.append((str(row.get("id", "?")), n_tok))
            continue
        kept.append(capped)

    write_jsonl(args.out_path, kept)

    print(f"Input rows: {len(rows)}")
    print(f"Output rows: {len(kept)} -> {args.out_path}")
    if dropped_cap:
        print(f"Dropped after excerpt cap / validation: {len(dropped_cap)}")
        for msg in dropped_cap[:10]:
            print(f"  - {msg}")
    if dropped_tokens:
        print(f"Dropped over {args.max_tokens} tokens: {len(dropped_tokens)}")
        for rid, n in dropped_tokens:
            print(f"  - {rid}: {n} tokens")

    return 0 if kept else 1


if __name__ == "__main__":
    raise SystemExit(main())
