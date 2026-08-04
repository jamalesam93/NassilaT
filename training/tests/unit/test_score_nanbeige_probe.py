"""Unit tests for Nanbeige probe memo scoring."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from score_nanbeige_probe import verdict  # noqa: E402


def test_verdict_wait_low_parse() -> None:
    label, _ = verdict({"parse_strict_rate": 0.5, "combined_expect_rate": 0.8})
    assert label == "WAIT"


def test_verdict_go_later_strong() -> None:
    label, _ = verdict(
        {
            "parse_strict_rate": 0.98,
            "combined_expect_rate": 0.80,
            "quote_validity_rate": 0.92,
            "false_supported_rate": 0.05,
        }
    )
    assert label == "GO (later)"


def test_verdict_ambiguous() -> None:
    label, _ = verdict(
        {
            "parse_strict_rate": 0.92,
            "combined_expect_rate": 0.72,
            "quote_validity_rate": 0.80,
        }
    )
    assert label == "AMBIGUOUS"
