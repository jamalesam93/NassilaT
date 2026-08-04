#!/usr/bin/env python3
"""Freeze PDF-body draft holdout after operator quality filters.

Usage (from training/):
  python scripts/freeze_body_holdout_from_pdf_draft.py
  python scripts/freeze_body_holdout_from_pdf_draft.py --in data/eval_holdout_body_pdf_draft_skip98.jsonl --out data/eval_holdout_body_frozen_v1.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

from corpus_utils import DATA_DIR, read_jsonl

DEFAULT_IN = DATA_DIR / "eval_holdout_body_pdf_draft_skip98.jsonl"
DEFAULT_OUT = DATA_DIR / "eval_holdout_body_frozen_v1.jsonl"
MASTHEAD_RE = re.compile(r"\bVol\.?\s*\d+.*\b(19|20)\d{2}\b", re.I)


def looks_broken(row: dict) -> bool:
    passage = row.get("passage") or ""
    excerpt = row.get("source_excerpt") or ""
    if MASTHEAD_RE.search(passage[:160]):
        return True
    if "/C" in excerpt[:300] or "/G" in excerpt[:300]:
        return True
    # Soft hyphen left as U+00AD (should already be stripped at extract).
    if "\u00ad" in passage or "\u00ad" in excerpt:
        return True
    return False


def freeze_row(idx: int, row: dict) -> dict:
    meta = dict(row.get("meta") or {})
    meta["draft_status"] = "frozen_v1"
    meta["label"] = "full text body holdout (pdf extract)"
    meta["frozen_date"] = date.today().isoformat()
    return {
        **row,
        "id": f"bh-v1-{idx:03d}",
        "meta": meta,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="infile", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    kept: list[dict] = []
    dropped = 0
    for row in read_jsonl(args.infile):
        if looks_broken(row):
            dropped += 1
            continue
        kept.append(freeze_row(len(kept) + 1, row))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in kept:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "in": str(args.infile),
                "out": str(args.out),
                "kept": len(kept),
                "dropped": dropped,
            },
            indent=2,
        )
    )
    return 0 if kept else 1


if __name__ == "__main__":
    raise SystemExit(main())
