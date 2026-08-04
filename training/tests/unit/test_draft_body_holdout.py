"""Unit tests for draft_body_holdout_from_oa.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TRAINING_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRAINING_ROOT / "scripts"))

from draft_body_holdout_from_oa import corpus_by_doi, draft_row, sentences  # noqa: E402


def test_sentences_splits_on_period() -> None:
    text = (
        "First sentence here is definitely longer than forty characters. "
        "Second sentence is also longer than forty characters total."
    )
    parts = sentences(text)
    assert len(parts) >= 2


def test_draft_row_requires_min_abstract() -> None:
    paper = {"abstract": "Too short."}
    oa = {"id": "oa-x", "doi": "10.1/example", "url": "https://example.com"}
    assert draft_row(1, paper, oa) is None


def test_draft_row_shape() -> None:
    abstract = (
        "Background: We enrolled adults from three clinics in a prospective cohort. "
        "Participants were followed for twelve months with regular symptom assessments. "
        "Outcomes included symptom scores, hospitalization rates, and mortality endpoints. "
        "Additional secondary outcomes captured quality of life and adverse events."
    )
    paper = {"abstract": abstract}
    oa = {"id": "oa-test", "doi": "10.1/example", "url": "https://example.com/pdf"}
    row = draft_row(1, paper, oa)
    assert row is not None
    assert row["task"] == "l3_grounding"
    assert row["meta"]["excerpt_mode"] == "paragraph"
    assert row["meta"]["draft_status"] == "operator_review"
    assert row["passage"] in abstract


def test_corpus_by_doi_index(tmp_path: Path) -> None:
    path = tmp_path / "corpus.jsonl"
    path.write_text(
        json.dumps({"doi": "10.1/abc", "abstract": "x" * 200}) + "\n",
        encoding="utf-8",
    )
    index = corpus_by_doi(path)
    assert "10.1/abc" in index
