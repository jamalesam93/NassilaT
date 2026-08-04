"""Unit tests for draft_body_contrastive_from_frozen.py."""

from __future__ import annotations

import sys
from pathlib import Path

TRAINING_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRAINING_ROOT / "scripts"))

from draft_body_contrastive_from_frozen import (  # noqa: E402
    choose_contrastive,
    draft_contrastive,
    flip_polarity,
    mutate_number,
)


def test_mutate_number_inflates_first_value() -> None:
    assert mutate_number("Mortality fell by 12% in the arm.") == "Mortality fell by 99% in the arm."
    assert mutate_number("No digits here.") is None
    assert mutate_number("Functionals like GGA or PBE 27 which have") is None
    assert mutate_number("Enrolled n=40 patients.") == "Enrolled n=400 patients."
    assert mutate_number("Approved in 2001 by regulators.") == "Approved in 2021 by regulators."


def test_flip_polarity_swaps_first_match() -> None:
    out = flip_polarity("Scores increased after treatment.")
    assert out == "Scores decreased after treatment."
    assert flip_polarity("No polarity cue present.") is None


def test_choose_prefers_numeric_then_polarity_then_cross_doc() -> None:
    rows = [
        {
            "id": "bh-v1-001",
            "passage": "Mortality fell by 12% after treatment.",
            "source_excerpt": "Mortality fell by 12% after treatment in the cohort.",
            "meta": {"doi": "10.example/a"},
        },
        {
            "id": "bh-v1-002",
            "passage": "Scores increased after treatment.",
            "source_excerpt": "Scores increased after treatment in both arms.",
            "meta": {"doi": "10.example/b"},
        },
        {
            "id": "bh-v1-003",
            "passage": "The method clusters individuals by ancestry.",
            "source_excerpt": "The method clusters individuals by ancestry across sites.",
            "meta": {"doi": "10.example/c"},
        },
    ]
    n = choose_contrastive(idx=1, base=rows[0], all_rows=rows)
    assert n["meta"]["contrastive_kind"] == "numeric_overclaim"
    assert "99" in n["passage"]
    assert "supported" in n["expect"]["forbidden_claim_verdict"]

    p = choose_contrastive(idx=2, base=rows[1], all_rows=rows)
    assert p["meta"]["contrastive_kind"] == "polarity_flip"
    assert "decreased" in p["passage"]

    c = choose_contrastive(idx=3, base=rows[2], all_rows=rows)
    assert c["meta"]["contrastive_kind"] == "cross_doc"
    assert c["source_excerpt"] != rows[2]["source_excerpt"]
    assert c["passage"] == rows[2]["passage"]


def test_draft_contrastive_ids_and_limit() -> None:
    rows = [
        {
            "id": f"bh-v1-{i:03d}",
            "passage": f"Value was {i} units.",
            "source_excerpt": f"Value was {i} units in the study.",
            "meta": {},
        }
        for i in range(1, 6)
    ]
    out = draft_contrastive(rows, limit=3, id_prefix="bh-fs-v1", draft_provenance="frozen_v1_contrastive")
    assert [r["id"] for r in out] == ["bh-fs-v1-001", "bh-fs-v1-002", "bh-fs-v1-003"]
    assert all(r["expect"]["forbidden_claim_verdict"] == ["supported"] for r in out)
