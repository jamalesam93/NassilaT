#!/usr/bin/env python3
"""Validate Tier 3 body holdout pilot rows and report gate readiness (W6 prep).

Usage (from training/):
  python scripts/score_body_holdout_pilot.py
  python scripts/score_body_holdout_pilot.py --holdout data/eval_holdout_body_pilot.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from corpus_utils import read_jsonl  # noqa: E402

DEFAULT_HOLDOUT = SCRIPT_DIR.parent / "data" / "eval_holdout_body_pilot.jsonl"
REQUIRED_META = ("doc_id", "excerpt_mode", "language")


def validate_row(row: dict, line_no: int) -> list[str]:
    errors: list[str] = []
    if row.get("task") != "l3_grounding":
        errors.append(f"line {line_no}: task must be l3_grounding")
    meta = row.get("meta")
    if not isinstance(meta, dict):
        errors.append(f"line {line_no}: meta must be object")
        return errors
    for key in REQUIRED_META:
        if key not in meta:
            errors.append(f"line {line_no}: meta.{key} required for body holdout")
    if meta.get("excerpt_mode") != "paragraph":
        errors.append(f"line {line_no}: meta.excerpt_mode must be paragraph for pilot")
    if meta.get("language") == "ar" and meta.get("arabic_slice") != "unvalidated_pilot":
        errors.append(f"line {line_no}: Arabic rows must set arabic_slice=unvalidated_pilot")
    if "expect" not in row:
        errors.append(f"line {line_no}: expect block required")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    args = parser.parse_args()

    rows = read_jsonl(args.holdout)
    errors: list[str] = []
    for i, row in enumerate(rows, start=1):
        errors.extend(validate_row(row, i))

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1

    ar_rows = [r for r in rows if r.get("meta", {}).get("language") == "ar"]
    en_rows = [r for r in rows if r.get("meta", {}).get("language") == "en"]
    pilot_min_rows = 5
    print(json.dumps({
        "holdout": str(args.holdout),
        "rows": len(rows),
        "english_rows": len(en_rows),
        "arabic_rows_unvalidated": len(ar_rows),
        "structure_valid": True,
        "pilot_row_gate": {
            "value": len(rows),
            "min": pilot_min_rows,
            "passed": len(rows) >= pilot_min_rows,
        },
        "next": "Run run_l3_eval_batch.py on this holdout when scoring model outputs",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
