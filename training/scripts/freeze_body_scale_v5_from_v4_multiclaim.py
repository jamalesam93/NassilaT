#!/usr/bin/env python3
"""Freeze scale body holdout v5: v4 support rows + multi-claim companions.

Does not re-score models. Operator scores after freeze.

Usage (from training/):
  python scripts/freeze_body_scale_v5_from_v4_multiclaim.py
  python scripts/freeze_body_scale_v5_from_v4_multiclaim.py \\
      --multiclaim data/eval_holdout_body_multiclaim_draft.jsonl
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from corpus_utils import DATA_DIR, read_jsonl

DEFAULT_V4 = DATA_DIR / "eval_holdout_body_scale_frozen_v4.jsonl"
DEFAULT_MULTICLAIM = DATA_DIR / "eval_holdout_body_multiclaim_draft.jsonl"
DEFAULT_OUT = DATA_DIR / "eval_holdout_body_scale_frozen_v5.jsonl"


def freeze_multiclaim_row(row: dict) -> dict:
    meta = dict(row.get("meta") or {})
    meta["draft_status"] = "scale_frozen_v5_multiclaim"
    meta["label"] = "full text body holdout (multi-claim freeze v5)"
    meta["frozen_date"] = date.today().isoformat()
    meta["parent_multiclaim_id"] = row.get("id")
    meta["scale_freeze"] = "v5"
    return {**row, "meta": meta}


def build_v5(
    v4_rows: list[dict],
    multiclaim_rows: list[dict],
) -> list[dict]:
    out = [dict(r) for r in v4_rows]
    seen = {r.get("id") for r in out if r.get("id")}
    for row in multiclaim_rows:
        rid = row.get("id")
        if not rid or rid in seen:
            raise ValueError(f"duplicate or missing multiclaim id: {rid!r}")
        out.append(freeze_multiclaim_row(row))
        seen.add(rid)
    return out


def min_claim_floor(rows: list[dict]) -> int:
    return sum(int((r.get("expect") or {}).get("min_claims") or 1) for r in rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v4", type=Path, default=DEFAULT_V4)
    parser.add_argument("--multiclaim", type=Path, default=DEFAULT_MULTICLAIM)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    v4_rows = read_jsonl(args.v4)
    multiclaim_rows = read_jsonl(args.multiclaim)
    merged = build_v5(v4_rows, multiclaim_rows)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in merged:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    mc = sum(1 for r in merged if (r.get("meta") or {}).get("eval_category") == "multi_claim")
    print(
        json.dumps(
            {
                "v4_in": str(args.v4),
                "multiclaim_in": str(args.multiclaim),
                "out": str(args.out),
                "v4_rows": len(v4_rows),
                "multiclaim_rows": len(multiclaim_rows),
                "total_rows": len(merged),
                "multi_claim_rows": mc,
                "min_claim_floor": min_claim_floor(merged),
            },
            indent=2,
        )
    )
    return 0 if merged else 1


if __name__ == "__main__":
    raise SystemExit(main())
