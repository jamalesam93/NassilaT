"""Unit tests for freeze_body_scale_v5_from_v4_multiclaim.py."""

from __future__ import annotations

import sys
from pathlib import Path

TRAINING_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRAINING_ROOT / "scripts"))

from freeze_body_scale_v5_from_v4_multiclaim import (  # noqa: E402
    build_v5,
    freeze_multiclaim_row,
    min_claim_floor,
)


def test_freeze_multiclaim_row_sets_v5_meta() -> None:
    row = {
        "id": "bh-mc-001",
        "meta": {"eval_category": "multi_claim", "parent_id": "bh-sv4-001"},
        "expect": {"min_claims": 2},
    }
    out = freeze_multiclaim_row(row)
    assert out["id"] == "bh-mc-001"
    assert out["meta"]["draft_status"] == "scale_frozen_v5_multiclaim"
    assert out["meta"]["scale_freeze"] == "v5"
    assert out["meta"]["parent_multiclaim_id"] == "bh-mc-001"


def test_build_v5_merges_and_claim_floor() -> None:
    v4 = [{"id": "bh-sv4-001", "expect": {"min_claims": 1}}]
    mc = [
        {
            "id": "bh-mc-001",
            "meta": {"eval_category": "multi_claim"},
            "expect": {"min_claims": 2},
        }
    ]
    merged = build_v5(v4, mc)
    assert len(merged) == 2
    assert merged[0]["id"] == "bh-sv4-001"
    assert merged[1]["meta"]["draft_status"] == "scale_frozen_v5_multiclaim"
    assert min_claim_floor(merged) == 3
