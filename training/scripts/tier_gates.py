#!/usr/bin/env python3
"""
Sanad ship gates — canonical policy: Nassila docs/OUROBOROS_CONTEXT.md §10.

Tier 2 (quality): 12B / 31B premium — full abstract Sanad bar.
E4B default: achievable bar for nassila-sanad-e4b (v1.10-class capacity).
"""

from __future__ import annotations

from typing import Any

# --- Tier 2 (quality tier: 12B, 31B premium) ---
TIER2_EXPECT_PASS_MIN = 0.90
TIER2_EXPECT_PASS_BUFFER = 0.92
TIER2_JSON_PARSE_MIN = 0.98
TIER2_QUOTE_VALIDITY_MIN = 0.98
TIER2_FALSE_SUPPORTED_MAX = 0.05
TIER2_SUPPORTED_H_MIN = 8
TIER2_CORE_LEGACY_MIN = 5

# --- E4B default tier (ship nassila-sanad-e4b) — anchored to v1.10 multi-seed mean ---
E4B_DEFAULT_EXPECT_MIN = 0.88
E4B_DEFAULT_QUOTE_VALIDITY_MIN = 0.88
E4B_DEFAULT_FALSE_SUPPORTED_MAX = 0.07
E4B_DEFAULT_JSON_PARSE_MIN = 0.98
E4B_DEFAULT_SUPPORTED_H_MIN = 8
E4B_DEFAULT_CORE_LEGACY_MIN = 5

# v1.10 E4B Q6_K reference (beat bar for v1.12 recovery runs)
V110_E4B_BASELINE = {
    "combined_expect": 0.8812,
    "quote_validity_holdout": 0.8947,
    "false_supported_holdout": 0.0657,
}


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


def _slice_metrics(
    legacy: dict[str, Any],
    extended: dict[str, Any],
    holdout: dict[str, Any],
) -> dict[str, Any]:
    return {
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


def _evaluate_gates(
    *,
    legacy: dict[str, Any],
    extended: dict[str, Any],
    holdout: dict[str, Any],
    combined_totals: dict[str, Any],
    tier: int,
    tier_label: str,
    canonical_doc: str,
    expect_min: float,
    json_min: float,
    supported_h_min: int,
    core_legacy_min: int,
    quote_min: float,
    false_supported_max: float,
    expect_buffer: float | None = None,
) -> dict[str, Any]:
    holdout_per = holdout.get("per_row", [])
    legacy_per = legacy.get("per_row", [])

    supported_h = _supported_h_pass_count(holdout_per)
    core_legacy = _core_legacy_pass_count(legacy_per)

    expect_rate = combined_totals.get("expect_checks_pass_rate", 0)
    json_rate = combined_totals.get("json_parse_rate_with_repair", 0)
    quote_holdout = holdout.get("quote_validity_rate")
    false_supported_holdout = holdout.get("false_supported_rate")

    combined_gate: dict[str, Any] = {
        "value": expect_rate,
        "min": expect_min,
        "passed": expect_rate >= expect_min,
    }
    if expect_buffer is not None:
        combined_gate["buffer_target"] = expect_buffer
        combined_gate["buffer_met"] = expect_rate >= expect_buffer

    gates = {
        "combined_expect_pass": combined_gate,
        "json_parse_with_repair": {
            "value": json_rate,
            "min": json_min,
            "passed": json_rate >= json_min,
        },
        "supported_h001_h010": {
            "value": supported_h,
            "min": supported_h_min,
            "passed": supported_h >= supported_h_min,
        },
        "core_legacy_5": {
            "value": core_legacy,
            "min": core_legacy_min,
            "passed": core_legacy >= core_legacy_min,
        },
        "quote_validity_holdout": {
            "value": quote_holdout,
            "min": quote_min,
            "passed": quote_holdout is not None and quote_holdout >= quote_min,
        },
        "false_supported_holdout": {
            "value": false_supported_holdout,
            "max": false_supported_max,
            "passed": false_supported_holdout is not None
            and false_supported_holdout <= false_supported_max,
            "note": "Gated on holdout slice only; monitor extended_core false_supported separately.",
        },
    }

    return {
        "tier": tier,
        "tier_label": tier_label,
        "canonical_doc": canonical_doc,
        "model_gates_passed": all(g["passed"] for g in gates.values()),
        "gates": gates,
        "slice_metrics": _slice_metrics(legacy, extended, holdout),
        "product_safety_gate": {
            "description": "0 false pass after engine quote-substring guardrail (Nassila grounding-llm.ts)",
            "evaluated_in_app": True,
            "not_scored_here": True,
        },
    }


def evaluate_tier2_gates(
    *,
    legacy: dict[str, Any],
    extended: dict[str, Any],
    holdout: dict[str, Any],
    combined_totals: dict[str, Any],
) -> dict[str, Any]:
    """Tier 2 quality bar — 12B / 31B premium Sanad."""
    return _evaluate_gates(
        legacy=legacy,
        extended=extended,
        holdout=holdout,
        combined_totals=combined_totals,
        tier=2,
        tier_label="quality_tier",
        canonical_doc="Nassila docs/OUROBOROS_CONTEXT.md §10 (12B / 31B premium)",
        expect_min=TIER2_EXPECT_PASS_MIN,
        expect_buffer=TIER2_EXPECT_PASS_BUFFER,
        json_min=TIER2_JSON_PARSE_MIN,
        supported_h_min=TIER2_SUPPORTED_H_MIN,
        core_legacy_min=TIER2_CORE_LEGACY_MIN,
        quote_min=TIER2_QUOTE_VALIDITY_MIN,
        false_supported_max=TIER2_FALSE_SUPPORTED_MAX,
    )


def evaluate_e4b_default_gates(
    *,
    legacy: dict[str, Any],
    extended: dict[str, Any],
    holdout: dict[str, Any],
    combined_totals: dict[str, Any],
) -> dict[str, Any]:
    """E4B default-tier ship bar — nassila-sanad-e4b (v1.10-class)."""
    result = _evaluate_gates(
        legacy=legacy,
        extended=extended,
        holdout=holdout,
        combined_totals=combined_totals,
        tier=1,
        tier_label="e4b_default",
        canonical_doc="NassilaT docs/DUAL_TIER_POLICY.md (E4B default tier)",
        expect_min=E4B_DEFAULT_EXPECT_MIN,
        expect_buffer=None,
        json_min=E4B_DEFAULT_JSON_PARSE_MIN,
        supported_h_min=E4B_DEFAULT_SUPPORTED_H_MIN,
        core_legacy_min=E4B_DEFAULT_CORE_LEGACY_MIN,
        quote_min=E4B_DEFAULT_QUOTE_VALIDITY_MIN,
        false_supported_max=E4B_DEFAULT_FALSE_SUPPORTED_MAX,
    )
    holdout_quote = holdout.get("quote_validity_rate")
    false_sup = holdout.get("false_supported_rate")
    result["v110_baseline_beat"] = {
        "reference": "E4B v1.10 Q6_K multi-seed mean",
        "baseline": V110_E4B_BASELINE,
        "combined_expect_met": combined_totals.get("expect_checks_pass_rate", 0)
        >= V110_E4B_BASELINE["combined_expect"],
        "quote_validity_met": holdout_quote is not None
        and holdout_quote >= V110_E4B_BASELINE["quote_validity_holdout"],
        "false_supported_met": false_sup is not None
        and false_sup <= V110_E4B_BASELINE["false_supported_holdout"],
        "all_met": (
            combined_totals.get("expect_checks_pass_rate", 0)
            >= V110_E4B_BASELINE["combined_expect"]
            and holdout_quote is not None
            and holdout_quote >= V110_E4B_BASELINE["quote_validity_holdout"]
            and false_sup is not None
            and false_sup <= V110_E4B_BASELINE["false_supported_holdout"]
        ),
    }
    return result
