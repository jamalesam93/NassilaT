#!/usr/bin/env python3
"""Export full l3_grounding_train.jsonl to a review CSV (all rows, stable order)."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
DATA_DIR = TRAINING_DIR / "data"
sys.path.insert(0, str(SCRIPT_DIR))

from corpus_utils import read_jsonl  # noqa: E402
from generate_l3_from_corpus import VISIBLE_CLAIM_CHARS, excerpt_preview  # noqa: E402


def export_all(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    preview_len = max(VISIBLE_CLAIM_CHARS + 80, 320)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "row",
                "id",
                "passage",
                "claim",
                "verdict",
                "source_quote",
                "source_excerpt_preview",
                "approve",
            ],
        )
        w.writeheader()
        for i, r in enumerate(rows, start=1):
            claim_obj = r["output"]["claims"][0]
            quotes = claim_obj.get("sourceQuotes") or []
            quote = quotes[0] if quotes and isinstance(quotes[0], str) else ""
            anchor = quote or str(claim_obj.get("claim", ""))
            claim_text = str(claim_obj.get("claim", ""))
            w.writerow(
                {
                    "row": i,
                    "id": r["id"],
                    "passage": r["passage"][:preview_len],
                    "claim": claim_text[:preview_len],
                    "verdict": claim_obj.get("verdict", ""),
                    "source_quote": quote[:preview_len],
                    "source_excerpt_preview": excerpt_preview(r["source_excerpt"], anchor),
                    "approve": "",
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Export l3 train JSONL to review CSV")
    parser.add_argument(
        "--train",
        type=Path,
        default=DATA_DIR / "l3_grounding_train.jsonl",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DATA_DIR / "l3_review_full_400.csv",
    )
    args = parser.parse_args()
    rows = read_jsonl(args.train)
    if not rows:
        print(f"No rows in {args.train}", file=sys.stderr)
        return 1
    export_all(rows, args.out)
    print(f"Wrote {len(rows)} row(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
