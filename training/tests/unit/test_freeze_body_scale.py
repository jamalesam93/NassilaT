"""Unit tests for freeze_body_scale_from_draft.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

TRAINING_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRAINING_ROOT / "scripts"))

from freeze_body_scale_from_draft import DEFAULT_DROP_IDS, freeze_row  # noqa: E402


def test_default_drop_ids_has_seven() -> None:
    assert len(DEFAULT_DROP_IDS) == 7
    assert "bh-scale-072" in DEFAULT_DROP_IDS


def test_freeze_row_renumbers_and_keeps_parent(tmp_path: Path) -> None:
    row = {
        "id": "bh-scale-001",
        "task": "l3_grounding",
        "passage": "x",
        "source_excerpt": "x y",
        "meta": {"scale_source": "frozen_v1"},
        "expect": {"must_parse_json": True},
    }
    out = freeze_row(1, row)
    assert out["id"] == "bh-sv1-001"
    assert out["meta"]["draft_status"] == "scale_frozen_v1"
    assert out["meta"]["parent_scale_id"] == "bh-scale-001"
    assert out["meta"]["scale_source"] == "frozen_v1"
