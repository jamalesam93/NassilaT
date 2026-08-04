#!/usr/bin/env python3
"""Summarize body product holdout scores without re-scoring support rows.

Combines frozen v4 support evals + multiclaim slice evals into one report.

Usage (from training/):
  python scripts/summarize_body_product_holdout.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
DATA_DIR = TRAINING_DIR / "data"
REPORTS_DIR = TRAINING_DIR / "reports"

DEFAULT_SUPPORT_S12 = REPORTS_DIR / "tier3_body_scale_frozen_v4_s12_eval.json"
DEFAULT_SUPPORT_S14 = REPORTS_DIR / "tier3_body_scale_frozen_v4_s14_eval.json"
DEFAULT_MC_S12 = REPORTS_DIR / "tier3_body_multiclaim_s12_eval.json"
DEFAULT_MC_S14 = REPORTS_DIR / "tier3_body_multiclaim_s14_eval.json"
DEFAULT_OUT = REPORTS_DIR / "tier3_body_product_holdout_summary.json"


def load_report(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def slice_summary(report: dict, *, label: str) -> dict:
    return {
        "label": label,
        "rows": report.get("total_l3_rows"),
        "parse": report.get("json_parse_rate_with_repair"),
        "expect": report.get("expect_checks_pass_rate"),
        "quote": report.get("quote_validity_rate"),
        "false_supported": report.get("false_supported_rate"),
        "category_pass_rates": report.get("category_pass_rates") or {},
        "fail_ids": [r["id"] for r in report.get("per_row", []) if not r.get("checks_passed")],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--support-s12", type=Path, default=DEFAULT_SUPPORT_S12)
    parser.add_argument("--support-s14", type=Path, default=DEFAULT_SUPPORT_S14)
    parser.add_argument("--multiclaim-s12", type=Path, default=DEFAULT_MC_S12)
    parser.add_argument("--multiclaim-s14", type=Path, default=DEFAULT_MC_S14)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    support_s12 = load_report(args.support_s12)
    support_s14 = load_report(args.support_s14)
    mc_s12 = load_report(args.multiclaim_s12)
    mc_s14 = load_report(args.multiclaim_s14)

    support_rows = support_s12["total_l3_rows"]
    mc_rows = mc_s12["total_l3_rows"]
    total_rows = support_rows + mc_rows
    support_floor = support_rows * 1
    mc_floor = mc_rows * 2

    summary = {
        "note": "Support scores from frozen v4; multiclaim from bh-mc slice (same rows in v5). No support re-score.",
        "freeze_v5_rows": total_rows,
        "min_claim_floor": support_floor + mc_floor,
        "support_v4": {
            "eval": "data/eval_holdout_body_scale_frozen_v4.jsonl",
            "s12": slice_summary(support_s12, label="S12 support"),
            "s14": slice_summary(support_s14, label="S14 support"),
        },
        "multiclaim": {
            "eval": "data/eval_holdout_body_multiclaim_frozen_v1.jsonl",
            "s12": slice_summary(mc_s12, label="S12 multiclaim"),
            "s14": slice_summary(mc_s14, label="S14 multiclaim"),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
