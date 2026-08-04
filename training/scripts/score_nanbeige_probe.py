#!/usr/bin/env python3
"""Write Nanbeige zero-shot probe memo from eval reports.

Usage:
  python scripts/score_nanbeige_probe.py \\
    --predictions outputs/nanbeige_zeroshot_predictions.jsonl \\
    --combined-report outputs/nanbeige_zeroshot_eval_combined_report.json \\
    --holdout-report outputs/nanbeige_zeroshot_eval_holdout_report.json \\
    --out reports/nanbeige_zeroshot_probe_2026-07.md
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent

# S12/S14 single-seed baselines from PROMPT_CONTRACT_REEVAL.md
BASELINES = {
    "s12": {
        "parse_strict": 1.0,
        "combined_expect": 0.9368,
        "holdout_expect": 0.9444,
        "quote_validity_holdout": 1.0,
        "false_supported_holdout": 0.0143,
    },
    "s14": {
        "parse_strict": 1.0,
        "combined_expect": 0.9368,
        "holdout_expect": 0.9333,
        "quote_validity_holdout": 0.9474,
        "false_supported_holdout": 0.0286,
    },
}

THRESHOLDS = {
    "parse_strict_min": 0.90,
    "combined_expect_promising": 0.70,
    "combined_expect_strong": 0.75,
    "quote_validity_min": 0.85,
    "quote_validity_strong": 0.90,
    "false_supported_max": 0.10,
    "parse_strict_strong": 0.95,
}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def pct(x: float | None) -> str:
    if x is None:
        return "n/a"
    return f"{x * 100:.2f}%"


def verdict(metrics: dict) -> tuple[str, str]:
    parse_ok = metrics.get("parse_strict_rate", 0) or 0
    combined = metrics.get("combined_expect_rate", 0) or 0
    quote = metrics.get("quote_validity_rate", 0) or 0
    false_sup = metrics.get("false_supported_rate", 0) or 0

    if parse_ok < THRESHOLDS["parse_strict_min"] or combined < 0.60:
        return (
            "WAIT",
            "Parse or combined expect below probe floor — not a drop-in S15 base; "
            "wait for official GGUF/Ollama or better tooling before QLoRA.",
        )
    if (
        parse_ok >= THRESHOLDS["parse_strict_strong"]
        and combined >= THRESHOLDS["combined_expect_strong"]
        and quote >= THRESHOLDS["quote_validity_strong"]
    ):
        return (
            "GO (later)",
            "Strong zero-shot signal — schedule QLoRA on Nanbeige when S15 un-parks "
            "(after S15_UNPARK_CRITERIA data gates).",
        )
    if parse_ok >= 0.85 and combined >= THRESHOLDS["combined_expect_promising"]:
        return (
            "AMBIGUOUS",
            "Model follows JSON shape but Sanad verdict logic needs work — fine-tuning "
            "might help; only after S15 data gates pass.",
        )
    return (
        "WEAK",
        "Marginal zero-shot — do not prioritize Nanbeige over Gemma4 for S15 until "
        "a repeat probe or official serving improves.",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Nanbeige probe memo writer")
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--combined-report", type=Path, required=True)
    parser.add_argument("--holdout-report", type=Path, required=True)
    parser.add_argument(
        "--legacy-report",
        type=Path,
        default=None,
        help="Legacy 5-row report (default: sibling of combined report)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=TRAINING_DIR / "reports" / "nanbeige_zeroshot_probe_2026-07.md",
    )
    args = parser.parse_args()

    for p in (args.predictions, args.combined_report, args.holdout_report):
        if not p.exists():
            print(f"Missing: {p}", file=sys.stderr)
            return 1

    legacy_report_path = args.legacy_report
    if legacy_report_path is None:
        legacy_report_path = args.combined_report.with_name(
            args.combined_report.name.replace("eval_combined_report", "eval_report")
        )

    combined = load_json(args.combined_report)
    holdout = load_json(args.holdout_report)
    legacy_detail = load_json(legacy_report_path) if legacy_report_path.exists() else {}

    totals = combined.get("combined_totals") or {}
    metrics = {
        "parse_strict_rate": totals.get("json_parse_rate_strict"),
        "parse_with_repair_rate": totals.get("json_parse_rate_with_repair"),
        "combined_expect_rate": totals.get("expect_checks_pass_rate"),
        "holdout_expect_rate": holdout.get("expect_checks_pass_rate"),
        "quote_validity_rate": holdout.get("quote_validity_rate"),
        "false_supported_rate": holdout.get("false_supported_rate"),
        "legacy_core_pass": None,
        "total_rows": totals.get("total_l3_rows"),
    }
    if legacy_detail.get("total_l3_rows"):
        passed = sum(
            1
            for row in legacy_detail.get("per_row", [])
            if row.get("checks_passed") and not row.get("skipped")
        )
        metrics["legacy_core_pass"] = f"{passed}/{legacy_detail['total_l3_rows']}"

    label, rationale = verdict(metrics)
    today = date.today().isoformat()

    lines = [
        f"# Nanbeige4.2-3B zero-shot probe ({today})",
        "",
        "**Model:** [Nanbeige/Nanbeige4.2-3B](https://huggingface.co/Nanbeige/Nanbeige4.2-3B)  ",
        "**Harness:** `sanad-grounding-v1` · 95 rows (`eval_samples` + `eval_holdout_90`)  ",
        "**Runner:** Vast + Nanbeige vLLM fork (`nanbeige42`) · `enable_thinking: false`",
        "",
        "## Verdict",
        "",
        f"**{label}** — {rationale}",
        "",
        "## Metrics (this run)",
        "",
        "| Metric | Nanbeige | S12 | S14 | Probe target |",
        "|--------|----------|-----|-----|--------------|",
        f"| JSON parse (strict) | {pct(metrics['parse_strict_rate'])} | "
        f"{pct(BASELINES['s12']['parse_strict'])} | "
        f"{pct(BASELINES['s14']['parse_strict'])} | ≥90% |",
        f"| Combined expect | {pct(metrics['combined_expect_rate'])} | "
        f"{pct(BASELINES['s12']['combined_expect'])} | "
        f"{pct(BASELINES['s14']['combined_expect'])} | ≥70% promising |",
        f"| Holdout expect | {pct(metrics['holdout_expect_rate'])} | "
        f"{pct(BASELINES['s12']['holdout_expect'])} | "
        f"{pct(BASELINES['s14']['holdout_expect'])} | — |",
        f"| Quote validity (holdout) | {pct(metrics['quote_validity_rate'])} | "
        f"{pct(BASELINES['s12']['quote_validity_holdout'])} | "
        f"{pct(BASELINES['s14']['quote_validity_holdout'])} | ≥85% |",
        f"| False supported (holdout) | {pct(metrics['false_supported_rate'])} | "
        f"{pct(BASELINES['s12']['false_supported_holdout'])} | "
        f"{pct(BASELINES['s14']['false_supported_holdout'])} | ≤10% |",
        f"| Legacy core 5/5 | {metrics.get('legacy_core_pass', 'n/a')} | 4/5 | 5/5 | info |",
        "",
        "## Artifacts",
        "",
        f"- Predictions: `{args.predictions.as_posix()}`",
        f"- Combined report: `{args.combined_report.as_posix()}`",
        f"- Holdout report: `{args.holdout_report.as_posix()}`",
        "",
        "## Notes",
        "",
        "- Zero-shot base model — not comparable to fine-tuned Sanad S12/S14 on combined expect alone.",
        "- Do not start S15 QLoRA from this probe alone; see `S15_UNPARK_CRITERIA.md`.",
        "- Body holdout deferred until abstract probe passes strong/ambiguous bar.",
        "",
    ]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.out}")
    print(f"Verdict: {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
