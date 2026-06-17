#!/usr/bin/env python3
"""
A/B pilot decision gates: compare E4B baseline vs 12B quant-ladder arms.

Reads multi_seed_aggregate.json (or single combined reports) and applies plan gates:
  - Adopt 12B optional tier if 12B beats E4B-Q6 by >=3 pts combined expect,
    multi_claim pass >=0.8, and quote validity >= E4B baseline.

Usage:
  python scripts/compare_ab_pilot.py \\
    --baseline reports/ab_e4b_v110/multi_seed_aggregate.json \\
    --candidate reports/ab_12b_q6_v110/multi_seed_aggregate.json \\
    --label "12B Q6_K"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent

COMBINED_DELTA_MIN = 0.03
MULTI_CLAIM_MIN = 0.80
HARD_ROWS = ("h-043", "h-045", "h-084", "h-085", "h-088")


def load_aggregate(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "mean_metrics" not in data and "combined_totals" in data:
        return {
            "mean_metrics": {
                "combined_expect": data["combined_totals"].get("expect_checks_pass_rate"),
                "quote_validity_holdout": data.get("holdout_eval", {}).get("quote_validity_rate")
                or data.get("holdout", {}).get("quote_validity_rate"),
                "false_supported_holdout": data.get("holdout_eval", {}).get("false_supported_rate")
                or data.get("holdout", {}).get("false_supported_rate"),
                "multi_claim_pass": (
                    data.get("holdout_eval", {}).get("category_pass_rates", {}).get("multi_claim")
                    or data.get("holdout", {}).get("category_pass_rates", {}).get("multi_claim")
                ),
            }
        }
    return data


def hard_row_pass_rate(predictions_path: Path, holdout_path: Path) -> dict[str, bool]:
    sys.path.insert(0, str(SCRIPT_DIR))
    from evaluate_outputs import evaluate_dataset, load_jsonl_by_id  # noqa: E402

    holdout = load_jsonl_by_id(holdout_path)
    scored = evaluate_dataset(holdout_path, predictions_path, allow_repair=True)
    by_id = {r["id"]: r.get("checks_passed", False) for r in scored.get("per_row", [])}
    return {rid: bool(by_id.get(rid)) for rid in HARD_ROWS if rid in holdout}


def evaluate_gates(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    label: str,
    hard_rows: dict[str, bool] | None = None,
) -> dict[str, Any]:
    b = baseline["mean_metrics"]
    c = candidate["mean_metrics"]
    combined_delta = (c.get("combined_expect") or 0) - (b.get("combined_expect") or 0)
    gates = {
        "combined_expect_delta": {
            "value": round(combined_delta, 4),
            "min": COMBINED_DELTA_MIN,
            "passed": combined_delta >= COMBINED_DELTA_MIN,
        },
        "multi_claim_pass": {
            "value": c.get("multi_claim_pass"),
            "min": MULTI_CLAIM_MIN,
            "passed": (c.get("multi_claim_pass") or 0) >= MULTI_CLAIM_MIN,
        },
        "quote_validity_vs_baseline": {
            "candidate": c.get("quote_validity_holdout"),
            "baseline": b.get("quote_validity_holdout"),
            "passed": (c.get("quote_validity_holdout") or 0)
            >= (b.get("quote_validity_holdout") or 0),
        },
    }
    if hard_rows:
        passed_hard = sum(1 for v in hard_rows.values() if v)
        gates["hard_rows"] = {
            "rows": hard_rows,
            "passed_count": passed_hard,
            "total": len(hard_rows),
            "passed": passed_hard == len(hard_rows),
        }
    all_passed = all(g["passed"] for g in gates.values())
    recommendation = "adopt_12b_optional_tier" if all_passed else "defer_12b_to_shahid_only"
    return {
        "label": label,
        "recommendation": recommendation,
        "all_gates_passed": all_passed,
        "gates": gates,
        "baseline_mean": b,
        "candidate_mean": c,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="A/B pilot decision gates (E4B vs 12B)")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--label", default="12B candidate")
    parser.add_argument(
        "--predictions",
        type=Path,
        help="Optional single-seed predictions for hard-row check",
    )
    parser.add_argument(
        "--holdout",
        type=Path,
        default=TRAINING_DIR / "data" / "eval_holdout_90.jsonl",
    )
    parser.add_argument("--out", type=Path, help="Write JSON decision report")
    args = parser.parse_args()

    baseline = load_aggregate(args.baseline)
    candidate = load_aggregate(args.candidate)
    hard_rows = None
    if args.predictions and args.predictions.exists():
        hard_rows = hard_row_pass_rate(args.predictions, args.holdout)

    result = evaluate_gates(baseline, candidate, label=args.label, hard_rows=hard_rows)
    print(json.dumps(result, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Wrote {args.out}")
    return 0 if result["all_gates_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
