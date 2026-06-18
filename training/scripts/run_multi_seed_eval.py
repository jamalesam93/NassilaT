#!/usr/bin/env python3
"""
Run L3 eval multiple times with different decode seeds and aggregate metrics.

Reduces single-row gate flips on small holdouts. Requires >=3 seeds for A/B pilot.

Usage:
  python scripts/run_multi_seed_eval.py \\
    --model nassila-grounding --base-url http://127.0.0.1:1234 \\
    --seeds 42 43 44 --out-dir reports/ab_e4b_v110

Then score each seed:
  python scripts/run_eval_reports.py --predictions reports/ab_e4b_v110/seed_42_predictions.jsonl --repair
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_outputs import evaluate_dataset  # noqa: E402
from run_eval_reports import merge_rate  # noqa: E402
from tier_gates import evaluate_e4b_default_gates, evaluate_tier2_gates  # noqa: E402

DEFAULT_DATA = [
    TRAINING_DIR / "data" / "eval_samples.jsonl",
    TRAINING_DIR / "data" / "eval_samples_extended.jsonl",
    TRAINING_DIR / "data" / "eval_holdout_90.jsonl",
]
DEFAULT_SEEDS = (42, 43, 44)


def run_batch(
    *,
    model: str,
    base_url: str,
    data: list[Path],
    out: Path,
    seed: int,
    repair: bool,
    temperature: float,
) -> int:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "run_l3_eval_batch.py"),
        "--model",
        model,
        "--base-url",
        base_url,
        "--out",
        str(out),
        "--seed",
        str(seed),
        "--temperature",
        str(temperature),
        "--retry",
        "1",
        "--chat-template",
        "--data",
        *[str(p) for p in data],
    ]
    if repair:
        cmd.append("--repair")
    print(f"--- seed={seed} -> {out.name} ---")
    return subprocess.call(cmd)


def score_all_slices(predictions: Path, holdout: Path, repair: bool) -> dict:
    legacy = evaluate_dataset(
        TRAINING_DIR / "data" / "eval_samples.jsonl", predictions, allow_repair=repair
    )
    extended = evaluate_dataset(
        TRAINING_DIR / "data" / "eval_samples_extended.jsonl", predictions, allow_repair=repair
    )
    holdout_eval = evaluate_dataset(holdout, predictions, allow_repair=repair)
    all_total = (
        legacy["total_l3_rows"]
        + extended["total_l3_rows"]
        + holdout_eval["total_l3_rows"]
    )
    combined_expect = merge_rate(
        {
            "total_l3_rows": all_total,
            "expect_checks_pass_rate": (
                legacy["expect_checks_pass_rate"] * legacy["total_l3_rows"]
                + extended["expect_checks_pass_rate"] * extended["total_l3_rows"]
                + holdout_eval["expect_checks_pass_rate"] * holdout_eval["total_l3_rows"]
            )
            / max(1, all_total),
        },
        {"total_l3_rows": 0, "expect_checks_pass_rate": 0},
        "expect_checks_pass_rate",
    )
    combined_totals = {
        "total_l3_rows": all_total,
        "expect_checks_pass_rate": combined_expect,
        "json_parse_rate_with_repair": round(
            (
                legacy["json_parse_rate_with_repair"] * legacy["total_l3_rows"]
                + extended["json_parse_rate_with_repair"] * extended["total_l3_rows"]
                + holdout_eval["json_parse_rate_with_repair"] * holdout_eval["total_l3_rows"]
            )
            / max(1, all_total),
            4,
        ),
    }
    tier2 = evaluate_tier2_gates(
        legacy=legacy,
        extended=extended,
        holdout=holdout_eval,
        combined_totals=combined_totals,
    )
    e4b_default = evaluate_e4b_default_gates(
        legacy=legacy,
        extended=extended,
        holdout=holdout_eval,
        combined_totals=combined_totals,
    )
    return {
        "legacy": legacy,
        "extended": extended,
        "holdout": holdout_eval,
        "combined_totals": combined_totals,
        "tier2_gates": tier2,
        "e4b_default_gates": e4b_default,
    }


def mean_metric(seed_reports: list[dict], path: list[str]) -> float | None:
    vals: list[float] = []
    for rep in seed_reports:
        cur: object = rep
        for key in path:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(key)
        if isinstance(cur, (int, float)):
            vals.append(float(cur))
    if not vals:
        return None
    return round(sum(vals) / len(vals), 4)


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-seed L3 eval aggregation")
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:1234")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--holdout", type=Path, default=TRAINING_DIR / "data" / "eval_holdout_90.jsonl")
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--skip-batch", action="store_true", help="Only aggregate existing prediction files")
    args = parser.parse_args()

    if len(args.seeds) < 3:
        print("Warning: plan recommends >=3 seeds for stable gates", file=sys.stderr)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    data = DEFAULT_DATA

    if not args.skip_batch:
        for seed in args.seeds:
            pred_out = args.out_dir / f"seed_{seed}_predictions.jsonl"
            rc = run_batch(
                model=args.model,
                base_url=args.base_url,
                data=data,
                out=pred_out,
                seed=seed,
                repair=args.repair,
                temperature=args.temperature,
            )
            if rc != 0:
                return rc

    seed_reports: list[dict] = []
    for seed in args.seeds:
        pred_out = args.out_dir / f"seed_{seed}_predictions.jsonl"
        if not pred_out.exists():
            print(f"Missing {pred_out}", file=sys.stderr)
            return 1
        scored = score_all_slices(pred_out, args.holdout, args.repair)
        scored["seed"] = seed
        seed_reports.append(scored)
        seed_report_path = args.out_dir / f"seed_{seed}_combined_report.json"
        seed_report_path.write_text(json.dumps(scored, indent=2), encoding="utf-8")

    aggregate = {
        "model": args.model,
        "seeds": args.seeds,
        "holdout_file": str(args.holdout),
        "per_seed": [
            {
                "seed": r["seed"],
                "combined_expect": r["combined_totals"]["expect_checks_pass_rate"],
                "quote_validity_holdout": r["holdout"].get("quote_validity_rate"),
                "false_supported_holdout": r["holdout"].get("false_supported_rate"),
                "multi_claim_pass": r["holdout"].get("category_pass_rates", {}).get("multi_claim"),
                "tier2_passed": r["tier2_gates"]["model_gates_passed"],
                "e4b_default_passed": r["e4b_default_gates"]["model_gates_passed"],
                "beats_v110_baseline": r["e4b_default_gates"]["v110_baseline_beat"]["all_met"],
            }
            for r in seed_reports
        ],
        "mean_metrics": {
            "combined_expect": mean_metric(seed_reports, ["combined_totals", "expect_checks_pass_rate"]),
            "quote_validity_holdout": mean_metric(seed_reports, ["holdout", "quote_validity_rate"]),
            "false_supported_holdout": mean_metric(seed_reports, ["holdout", "false_supported_rate"]),
            "multi_claim_pass": mean_metric(
                seed_reports, ["holdout", "category_pass_rates", "multi_claim"]
            ),
            "tier2_pass_rate": mean_metric(
                seed_reports, ["tier2_gates", "model_gates_passed"]
            ),
            "e4b_default_pass_rate": mean_metric(
                seed_reports, ["e4b_default_gates", "model_gates_passed"]
            ),
            "beats_v110_baseline_rate": mean_metric(
                seed_reports, ["e4b_default_gates", "v110_baseline_beat", "all_met"]
            ),
        },
    }
    agg_path = args.out_dir / "multi_seed_aggregate.json"
    agg_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    print(json.dumps(aggregate, indent=2))
    print(f"Wrote {agg_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
