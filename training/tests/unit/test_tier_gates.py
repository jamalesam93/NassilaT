"""Unit tests for Sanad dual-tier gate thresholds."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TRAINING_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRAINING_ROOT / "scripts"))

from tier_gates import (  # noqa: E402
    E4B_DEFAULT_EXPECT_MIN,
    TIER2_EXPECT_PASS_MIN,
    TIER2_QUOTE_VALIDITY_MIN,
    evaluate_e4b_default_gates,
    evaluate_tier2_gates,
)


def _mock_slices(*, combined: float, quote: float, false_sup: float) -> tuple[dict, dict, dict, dict]:
    legacy = {
        "per_row": [{"checks_passed": True}] * 5,
        "expect_checks_pass_rate": 1.0,
        "quote_validity_rate": 1.0,
        "false_supported_rate": 0.0,
    }
    extended = {
        "per_row": [],
        "expect_checks_pass_rate": 0.8,
        "quote_validity_rate": 0.9,
        "false_supported_rate": 0.1,
    }
    holdout = {
        "per_row": [{"id": f"h-{i:03d}", "checks_passed": True} for i in range(1, 11)],
        "expect_checks_pass_rate": quote,
        "quote_validity_rate": quote,
        "false_supported_rate": false_sup,
    }
    combined_totals = {
        "expect_checks_pass_rate": combined,
        "json_parse_rate_with_repair": 1.0,
    }
    return legacy, extended, holdout, combined_totals


def test_v110_e4b_passes_default_tier_not_tier2() -> None:
    legacy, extended, holdout, combined_totals = _mock_slices(
        combined=0.8812, quote=0.8947, false_sup=0.0657
    )
    tier2 = evaluate_tier2_gates(
        legacy=legacy, extended=extended, holdout=holdout, combined_totals=combined_totals
    )
    e4b = evaluate_e4b_default_gates(
        legacy=legacy, extended=extended, holdout=holdout, combined_totals=combined_totals
    )
    assert tier2["model_gates_passed"] is False
    assert e4b["model_gates_passed"] is True
    assert e4b["v110_baseline_beat"]["all_met"] is True


def test_tier2_stricter_than_e4b_default() -> None:
    assert TIER2_EXPECT_PASS_MIN > E4B_DEFAULT_EXPECT_MIN
    assert TIER2_QUOTE_VALIDITY_MIN > 0.88
