#!/usr/bin/env python3
"""
Tier 2 go/no-go gates — canonical source: Nassila docs/OUROBOROS_CONTEXT.md §10.

Used by run_eval_reports.py after scoring predictions.
"""

from __future__ import annotations

from typing import Any

# Minimum gate (Tier 2 ship) vs recommended buffer (operator target)
TIER2_EXPECT_PASS_MIN = 0.90
TIER2_EXPECT_PASS_BUFFER = 0.92
TIER2_JSON_PARSE_MIN = 0.98
TIER2_QUOTE_VALIDITY_MIN = 0.98
TIER2_FALSE_SUPPORTED_MAX = 0.05
TIER2_SUPPORTED_H_MIN = 8
TIER2_CORE_LEGACY_MIN = 5


def _supported_h_pass_count(holdout_per_row: list[dict[str, Any]]) -> int:
    supported_ids = {f"h-{i:03d}" for i in range(1, 11)}
    passed = 0
    for row in holdout_per_row:
        rid = row.get("id", "")
        if rid not in supported_ids:
            continue
        if row.get("checks_passed") and not row.get("skipped"):
            passed += 1
    return passed


def _core_legacy_pass_count(legacy_per_row: list[dict[str, Any]]) -> int:
    passed = 0
    for row in legacy_per_row:
        if row.get("checks_passed") and not row.get("skipped"):
            passed += 1
    return passed


def evaluate_tier2_gates(
    *,
    legacy: dict[str, Any],
    extended: dict[str, Any],
    holdout: dict[str, Any],
    combined_totals: dict[str, Any],
) -> dict[str, Any]:
    """Return Tier 2 model gate results. Product-safety gate is app-side (quote guardrail)."""
    holdout_per = holdout.get("per_row", [])
    legacy_per = legacy.get("per_row", [])

    supported_h = _supported_h_pass_count(holdout_per)
    core_legacy = _core_legacy_pass_count(legacy_per)

    expect_rate = combined_totals.get("expect_checks_pass_rate", 0)
    json_rate = combined_totals.get("json_parse_rate_with_repair", 0)
    quote_holdout = holdout.get("quote_validity_rate")
    false_supported_holdout = holdout.get("false_supported_rate")

    gates = {
        "combined_expect_pass": {
            "value": expect_rate,
            "min": TIER2_EXPECT_PASS_MIN,
            "buffer_target": TIER2_EXPECT_PASS_BUFFER,
            "passed": expect_rate >= TIER2_EXPECT_PASS_MIN,
            "buffer_met": expect_rate >= TIER2_EXPECT_PASS_BUFFER,
        },
        "json_parse_with_repair": {
            "value": json_rate,
            "min": TIER2_JSON_PARSE_MIN,
            "passed": json_rate >= TIER2_JSON_PARSE_MIN,
        },
        "supported_h001_h010": {
            "value": supported_h,
            "min": TIER2_SUPPORTED_H_MIN,
            "passed": supported_h >= TIER2_SUPPORTED_H_MIN,
        },
        "core_legacy_5": {
            "value": core_legacy,
            "min": TIER2_CORE_LEGACY_MIN,
            "passed": core_legacy >= TIER2_CORE_LEGACY_MIN,
        },
        "quote_validity_holdout": {
            "value": quote_holdout,
            "min": TIER2_QUOTE_VALIDITY_MIN,
            "passed": quote_holdout is not None and quote_holdout >= TIER2_QUOTE_VALIDITY_MIN,
        },
        "false_supported_holdout": {
            "value": false_supported_holdout,
            "max": TIER2_FALSE_SUPPORTED_MAX,
            "passed": false_supported_holdout is not None
            and false_supported_holdout <= TIER2_FALSE_SUPPORTED_MAX,
            "note": "Gated on holdout slice only; monitor extended_core false_supported separately.",
        },
    }

    slice_metrics = {
        "legacy_core": {
            "expect_checks_pass_rate": legacy.get("expect_checks_pass_rate"),
            "quote_validity_rate": legacy.get("quote_validity_rate"),
            "false_supported_rate": legacy.get("false_supported_rate"),
        },
        "extended_core": {
            "expect_checks_pass_rate": extended.get("expect_checks_pass_rate"),
            "quote_validity_rate": extended.get("quote_validity_rate"),
            "false_supported_rate": extended.get("false_supported_rate"),
        },
        "holdout": {
            "expect_checks_pass_rate": holdout.get("expect_checks_pass_rate"),
            "quote_validity_rate": holdout.get("quote_validity_rate"),
            "false_supported_rate": holdout.get("false_supported_rate"),
        },
    }

    all_passed = all(g["passed"] for g in gates.values())
    return {
        "tier": 2,
        "canonical_doc": "Nassila docs/OUROBOROS_CONTEXT.md §10",
        "model_gates_passed": all_passed,
        "gates": gates,
        "slice_metrics": slice_metrics,
        "product_safety_gate": {
            "description": "0 false pass after engine quote-substring guardrail (Nassila grounding-llm.ts)",
            "evaluated_in_app": True,
            "not_scored_here": True,
        },
    }
