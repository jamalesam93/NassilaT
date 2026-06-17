#!/usr/bin/env python3
"""
Score predictions against all eval sets and write combined reports.

Usage:
  python scripts/run_eval_reports.py --predictions outputs/predictions.jsonl --repair

Writes:
  outputs/eval_report.json              (5 legacy core rows)
  outputs/eval_core_extended_report.json (20 extended core rows)
  outputs/eval_holdout_report.json      (90 hardened holdout rows by default)
  outputs/eval_combined_report.json     (merged summary)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_outputs import evaluate_dataset, print_summary  # noqa: E402
from tier_gates import evaluate_tier2_gates  # noqa: E402


def merge_rate(a: dict, b: dict, key: str) -> float:
    total = a["total_l3_rows"] + b["total_l3_rows"]
    if total == 0:
        return 0.0
    return round(
        (a[key] * a["total_l3_rows"] + b[key] * b["total_l3_rows"]) / total,
        4,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all Nassila L3 eval reports")
    parser.add_argument(
        "--predictions",
        type=Path,
        default=TRAINING_DIR / "outputs" / "predictions.jsonl",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=TRAINING_DIR / "outputs",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="",
        help="Report filename prefix, e.g. v1_4a_ -> v1_4a_eval_holdout_report.json",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Allow lightweight JSON repair when scoring",
    )
    parser.add_argument(
        "--holdout",
        type=Path,
        default=TRAINING_DIR / "data" / "eval_holdout_90.jsonl",
        help="Holdout eval file (default: hardened 90-row harness)",
    )
    args = parser.parse_args()

    if not args.predictions.exists():
        print(f"Predictions not found: {args.predictions}", file=sys.stderr)
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    legacy_core_path = TRAINING_DIR / "data" / "eval_samples.jsonl"
    extended_core_path = TRAINING_DIR / "data" / "eval_samples_extended.jsonl"
    holdout_path = args.holdout

    legacy = evaluate_dataset(legacy_core_path, args.predictions, allow_repair=args.repair)
    extended = evaluate_dataset(extended_core_path, args.predictions, allow_repair=args.repair)
    holdout = evaluate_dataset(holdout_path, args.predictions, allow_repair=args.repair)

    print_summary(legacy, "eval_samples.jsonl (5 legacy core)")
    print_summary(extended, "eval_samples_extended.jsonl (20 extended core)")
    print_summary(holdout, f"{holdout_path.name} (holdout)")

    p = args.prefix
    legacy_report = args.out_dir / f"{p}eval_report.json"
    extended_report = args.out_dir / f"{p}eval_core_extended_report.json"
    holdout_report = args.out_dir / f"{p}eval_holdout_report.json"
    combined_report = args.out_dir / f"{p}eval_combined_report.json"

    legacy_report.write_text(json.dumps(legacy, indent=2), encoding="utf-8")
    extended_report.write_text(json.dumps(extended, indent=2), encoding="utf-8")
    holdout_report.write_text(json.dumps(holdout, indent=2), encoding="utf-8")

    core_total = legacy["total_l3_rows"] + extended["total_l3_rows"]
    all_total = core_total + holdout["total_l3_rows"]
    combined_expect = merge_rate(
        {
            "total_l3_rows": all_total,
            "expect_checks_pass_rate": (
                legacy["expect_checks_pass_rate"] * legacy["total_l3_rows"]
                + extended["expect_checks_pass_rate"] * extended["total_l3_rows"]
                + holdout["expect_checks_pass_rate"] * holdout["total_l3_rows"]
            )
            / max(1, all_total),
        },
        {"total_l3_rows": 0, "expect_checks_pass_rate": 0},
        "expect_checks_pass_rate",
    )
    combined = {
        "predictions_file": str(args.predictions),
        "repair_allowed": args.repair,
        "legacy_core_eval": {k: v for k, v in legacy.items() if k != "per_row"},
        "extended_core_eval": {k: v for k, v in extended.items() if k != "per_row"},
        "holdout_eval": {k: v for k, v in holdout.items() if k != "per_row"},
        "combined_totals": {
            "total_l3_rows": all_total,
            "legacy_core_rows": legacy["total_l3_rows"],
            "extended_core_rows": extended["total_l3_rows"],
            "holdout_rows": holdout["total_l3_rows"],
            "expect_checks_pass_rate": combined_expect,
            "json_parse_rate_strict": round(
                (
                    legacy["json_parse_rate_strict"] * legacy["total_l3_rows"]
                    + extended["json_parse_rate_strict"] * extended["total_l3_rows"]
                    + holdout["json_parse_rate_strict"] * holdout["total_l3_rows"]
                )
                / max(1, all_total),
                4,
            ),
            "json_parse_rate_with_repair": round(
                (
                    legacy["json_parse_rate_with_repair"] * legacy["total_l3_rows"]
                    + extended["json_parse_rate_with_repair"] * extended["total_l3_rows"]
                    + holdout["json_parse_rate_with_repair"] * holdout["total_l3_rows"]
                )
                / max(1, all_total),
                4,
            ),
            "quote_validity_by_slice": {
                "legacy_core": legacy.get("quote_validity_rate"),
                "extended_core": extended.get("quote_validity_rate"),
                "holdout": holdout.get("quote_validity_rate"),
            },
            "false_supported_by_slice": {
                "legacy_core": legacy.get("false_supported_rate"),
                "extended_core": extended.get("false_supported_rate"),
                "holdout": holdout.get("false_supported_rate"),
            },
        },
    }
    combined["tier2_gates"] = evaluate_tier2_gates(
        legacy=legacy,
        extended=extended,
        holdout=holdout,
        combined_totals=combined["combined_totals"],
    )
    combined_report.write_text(json.dumps(combined, indent=2), encoding="utf-8")

    print(f"\n=== Combined ({all_total} eval rows) ===")
    print(json.dumps(combined["combined_totals"], indent=2))
    print("\n=== Tier 2 gates (canonical: Nassila docs/OUROBOROS_CONTEXT.md §10) ===")
    print(json.dumps(combined["tier2_gates"], indent=2))
    print(f"\nWrote {legacy_report}")
    print(f"Wrote {extended_report}")
    print(f"Wrote {holdout_report}")
    print(f"Wrote {combined_report}")

    passed = sum(
        1
        for row in legacy["per_row"] + extended["per_row"] + holdout["per_row"]
        if row.get("checks_passed") and not row.get("skipped")
    )
    return 0 if passed == all_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
