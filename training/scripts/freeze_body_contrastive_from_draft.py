#!/usr/bin/env python3
"""Freeze contrastive body holdout after operator review.

Keeps residual hard numeric overclaims (intentional false-supported signal).

Usage (from training/):
  python scripts/freeze_body_contrastive_from_draft.py
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from corpus_utils import DATA_DIR, read_jsonl

DEFAULT_IN = DATA_DIR / "eval_holdout_body_contrastive_draft_v2.jsonl"
DEFAULT_OUT = DATA_DIR / "eval_holdout_body_contrastive_frozen_v2.jsonl"


def freeze_row(row: dict, *, freeze_tag: str = "frozen_v2") -> dict:
    meta = dict(row.get("meta") or {})
    meta["draft_status"] = freeze_tag
    meta["frozen_date"] = date.today().isoformat()
    meta["label"] = "full text body holdout (contrastive false-supported)"
    return {**row, "meta": meta}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="infile", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--freeze-tag", default="frozen_v2")
    args = parser.parse_args()

    rows = [freeze_row(r, freeze_tag=args.freeze_tag) for r in read_jsonl(args.infile)]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    kinds: dict[str, int] = {}
    for row in rows:
        k = (row.get("meta") or {}).get("contrastive_kind", "?")
        kinds[k] = kinds.get(k, 0) + 1

    print(
        json.dumps(
            {"in": str(args.infile), "out": str(args.out), "rows": len(rows), "kinds": kinds},
            indent=2,
        )
    )
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
