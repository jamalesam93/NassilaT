#!/usr/bin/env python3
"""
Score predictions against all eval sets and write combined reports.

Usage:
  python scripts/run_eval_reports.py --predictions outputs/predictions.jsonl --repair

Writes:
  outputs/eval_report.json          (5 core eval rows)
  outputs/eval_holdout_report.json  (45 holdout rows)
  outputs/eval_combined_report.json (merged summary)
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
        "--repair",
        action="store_true",
        help="Allow lightweight JSON repair when scoring",
    )
    args = parser.parse_args()

    if not args.predictions.exists():
        print(f"Predictions not found: {args.predictions}", file=sys.stderr)
        print("Run batch first:", file=sys.stderr)
        print(
            '  python scripts/run_l3_eval_batch.py --model "YOUR_MODEL_ID" '
            "--data data/eval_samples.jsonl data/eval_holdout_45.jsonl "
            "--retry 1 --repair",
            file=sys.stderr,
        )
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    core_path = TRAINING_DIR / "data" / "eval_samples.jsonl"
    holdout_path = TRAINING_DIR / "data" / "eval_holdout_45.jsonl"

    core = evaluate_dataset(core_path, args.predictions, allow_repair=args.repair)
    holdout = evaluate_dataset(holdout_path, args.predictions, allow_repair=args.repair)

    print_summary(core, "eval_samples.jsonl (5 core)")
    print_summary(holdout, "eval_holdout_45.jsonl (45 holdout)")

    core_report = args.out_dir / "eval_report.json"
    holdout_report = args.out_dir / "eval_holdout_report.json"
    combined_report = args.out_dir / "eval_combined_report.json"

    core_report.write_text(json.dumps(core, indent=2), encoding="utf-8")
    holdout_report.write_text(json.dumps(holdout, indent=2), encoding="utf-8")

    combined = {
        "predictions_file": str(args.predictions),
        "repair_allowed": args.repair,
        "core_eval": {k: v for k, v in core.items() if k != "per_row"},
        "holdout_eval": {k: v for k, v in holdout.items() if k != "per_row"},
        "combined_totals": {
            "total_l3_rows": core["total_l3_rows"] + holdout["total_l3_rows"],
            "expect_checks_pass_rate": round(
                (
                    core["expect_checks_pass_rate"] * core["total_l3_rows"]
                    + holdout["expect_checks_pass_rate"] * holdout["total_l3_rows"]
                )
                / max(1, core["total_l3_rows"] + holdout["total_l3_rows"]),
                4,
            ),
            "json_parse_rate_strict": round(
                (
                    core["json_parse_rate_strict"] * core["total_l3_rows"]
                    + holdout["json_parse_rate_strict"] * holdout["total_l3_rows"]
                )
                / max(1, core["total_l3_rows"] + holdout["total_l3_rows"]),
                4,
            ),
            "json_parse_rate_with_repair": round(
                (
                    core["json_parse_rate_with_repair"] * core["total_l3_rows"]
                    + holdout["json_parse_rate_with_repair"] * holdout["total_l3_rows"]
                )
                / max(1, core["total_l3_rows"] + holdout["total_l3_rows"]),
                4,
            ),
        },
    }
    combined_report.write_text(json.dumps(combined, indent=2), encoding="utf-8")

    print("\n=== Combined (50 eval rows) ===")
    print(json.dumps(combined["combined_totals"], indent=2))
    print(f"\nWrote {core_report}")
    print(f"Wrote {holdout_report}")
    print(f"Wrote {combined_report}")

    total = core["total_l3_rows"] + holdout["total_l3_rows"]
    passed = sum(
        1
        for row in core["per_row"] + holdout["per_row"]
        if row.get("checks_passed") and not row.get("skipped")
    )
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
