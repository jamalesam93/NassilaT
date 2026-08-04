#!/usr/bin/env python3
"""Freeze scale body holdout: drop residual quote-fail rows, renumber.

Default drop set = union of S12/S14 quote fails on eval_holdout_body_scale_draft.jsonl
(2026-07-24). Does not re-score models.

Usage (from training/):
  python scripts/freeze_body_scale_from_draft.py
  python scripts/freeze_body_scale_from_draft.py --drop-ids bh-scale-072,bh-scale-088
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from corpus_utils import DATA_DIR, read_jsonl

DEFAULT_IN = DATA_DIR / "eval_holdout_body_scale_draft.jsonl"
DEFAULT_OUT = DATA_DIR / "eval_holdout_body_scale_frozen_v1.jsonl"
DEFAULT_DROPPED = DATA_DIR / "eval_holdout_body_scale_dropped_quote_fails.jsonl"

# Union of S12 + S14 invalid-quote fails on the 166-row scale draft (2026-07-24).
DEFAULT_DROP_IDS = frozenset(
    {
        "bh-scale-072",
        "bh-scale-088",
        "bh-scale-096",
        "bh-scale-118",
        "bh-scale-121",
        "bh-scale-123",
        "bh-scale-158",
    }
)


def freeze_row(idx: int, row: dict) -> dict:
    meta = dict(row.get("meta") or {})
    meta["draft_status"] = "scale_frozen_v1"
    meta["label"] = "full text body holdout (scale freeze)"
    meta["frozen_date"] = date.today().isoformat()
    meta["parent_scale_id"] = row.get("id")
    return {
        **row,
        "id": f"bh-sv1-{idx:03d}",
        "meta": meta,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="infile", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dropped-out", type=Path, default=DEFAULT_DROPPED)
    parser.add_argument(
        "--drop-ids",
        default=",".join(sorted(DEFAULT_DROP_IDS)),
        help="Comma-separated scale draft ids to exclude",
    )
    args = parser.parse_args()

    drop_ids = {x.strip() for x in args.drop_ids.split(",") if x.strip()}
    kept: list[dict] = []
    dropped: list[dict] = []
    for row in read_jsonl(args.infile):
        rid = row.get("id")
        if rid in drop_ids:
            meta = dict(row.get("meta") or {})
            meta["dropped_reason"] = "quote_fail_s12_or_s14_scale_draft"
            dropped.append({**row, "meta": meta})
            continue
        kept.append(freeze_row(len(kept) + 1, row))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in kept:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with args.dropped_out.open("w", encoding="utf-8") as f:
        for row in dropped:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    by_src: dict[str, int] = {}
    for row in kept:
        src = (row.get("meta") or {}).get("scale_source", "?")
        by_src[src] = by_src.get(src, 0) + 1

    print(
        json.dumps(
            {
                "in": str(args.infile),
                "out": str(args.out),
                "dropped_out": str(args.dropped_out),
                "kept": len(kept),
                "dropped": len(dropped),
                "drop_ids": sorted(drop_ids),
                "kept_by_scale_source": by_src,
            },
            indent=2,
        )
    )
    return 0 if kept else 1


if __name__ == "__main__":
    raise SystemExit(main())
