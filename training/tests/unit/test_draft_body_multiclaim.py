"""Unit tests for draft_body_multiclaim_from_freeze.py."""

from __future__ import annotations

import sys
from pathlib import Path

TRAINING_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRAINING_ROOT / "scripts"))

from draft_body_multiclaim_from_freeze import (  # noqa: E402
    build_multi_passage,
    candidate_sentences,
    draft_multiclaim_row,
    is_junk_claim_sentence,
)


def test_rejects_xx_introduction_lead() -> None:
    assert is_junk_claim_sentence(
        "XX Introduction showed that the flow past a body can be divided into two regions."
    )


def test_candidate_sentences_needs_two_long_sentences() -> None:
    excerpt = (
        "Results showed a significant reduction in admissions from 24% to 12% over twelve months. "
        "Follow-up outcomes remained stable at twelve months across both study arms in the cohort. "
        "Short."
    )
    cands = candidate_sentences(excerpt)
    assert len(cands) >= 2


def test_build_multi_passage_joins_two() -> None:
    a = "Results showed a significant reduction in admissions from 24% to 12% over twelve months."
    b = "Follow-up outcomes remained stable at twelve months across both study arms in the cohort."
    out = build_multi_passage([a, b])
    assert out is not None
    assert "significant reduction" in out
    assert "Follow-up outcomes" in out


def test_draft_multiclaim_row_sets_min_claims_two() -> None:
    row = {
        "id": "bh-sv4-001",
        "passage": "x",
        "source_excerpt": (
            "Results showed a significant reduction in admissions from 24% to 12% over twelve months. "
            "Follow-up outcomes remained stable at twelve months across both study arms in the cohort. "
            "Adverse events were uncommon and similar between groups during the follow-up window."
        ),
        "meta": {"doi": "10.example/a", "scale_source": "batch2"},
    }
    out = draft_multiclaim_row(1, row)
    assert out is not None
    assert out["id"] == "bh-mc-001"
    assert out["expect"]["min_claims"] == 2
    assert out["meta"]["eval_category"] == "multi_claim"
    assert out["meta"]["parent_id"] == "bh-sv4-001"
