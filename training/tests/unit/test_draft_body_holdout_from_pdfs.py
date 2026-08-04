"""Unit tests for draft_body_holdout_from_pdfs.py."""

from __future__ import annotations

import sys
from pathlib import Path

TRAINING_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRAINING_ROOT / "scripts"))

from draft_body_holdout_from_pdfs import (  # noqa: E402
    build_excerpt_window,
    choose_anchor_pages,
    choose_passage,
    is_acceptable_body_text,
    normalize_page_text,
    noise_penalty,
    page_quality,
    parse_page_hint,
)


def test_parse_page_hint_reads_standard_format() -> None:
    assert parse_page_hint("p. 8") == 8
    assert parse_page_hint("see p. 12 for the letter") == 12
    assert parse_page_hint(None) is None


def test_normalize_page_text_flattens_lines_and_hyphens() -> None:
    text = "Treat-\nment results\nwere significant.\n"
    assert normalize_page_text(text) == "Treatment results were significant."


def test_normalize_page_text_joins_soft_hyphens() -> None:
    text = "can be ne\u00ad\nglected. Pharm\u2014Vol 58"
    assert normalize_page_text(text) == "can be neglected. Pharm-Vol 58"


def test_choose_anchor_pages_prefers_valid_hint() -> None:
    pages = [
        "Short page",
        (
            "Methods section with participants and analysis. " * 20
            + "Results showed a significant reduction in symptoms."
        ),
        ("References bibliography " * 80),
    ]
    assert choose_anchor_pages(pages, 2) == [1]


def test_is_acceptable_body_text_rejects_reference_page() -> None:
    refs = (
        "Review 69 Hahn, W.C., Counter, C.M., Lundberg, A.S., Beijersbgern, R.L. "
        "Markowitz, S., Wang, J., Meyeroff, L., Parsons, R., Sun, L. (1999). "
        "Creation of human tumor cells with defined genetic elements. Nature 400, 464-468."
    )
    assert not is_acceptable_body_text(refs)


def test_is_acceptable_body_text_rejects_cid_and_toc() -> None:
    cid = "/C82/C97/C116/C105/C110/C103 /C83/C99/C97/C108/C101 " * 40
    toc = (
        "11.1 Defining statistical models; formulae..............................................50 "
        "11.1.1 Contrasts....................................................................52 "
        "11.2 Linear models....................................................................53 "
    ) * 4
    assert not is_acceptable_body_text(cid)
    assert not is_acceptable_body_text(toc)


def test_build_excerpt_window_expands_to_neighbor_pages() -> None:
    pages = [
        "Introductory matter " * 28,
        "Results showed significant improvement in the intervention arm. " * 8,
        "Follow-up outcomes remained stable at twelve months. " * 10,
    ]
    excerpt, pages_label = build_excerpt_window(pages, 1, 1)
    assert "significant improvement" in excerpt
    assert pages_label in {"pp. 1-2", "pp. 2-3"}


def test_choose_passage_prefers_results_sentence() -> None:
    excerpt = (
        "Background: We enrolled adults from three clinics for a prospective study. "
        "Results showed a significant reduction in admissions from 24% to 12% over twelve months. "
        "Additional details described follow-up procedures and adverse event monitoring."
    )
    passage = choose_passage(excerpt)
    assert passage is not None
    assert "significant reduction in admissions" in passage


def test_page_quality_penalizes_reference_pages() -> None:
    body = "Results showed improvement in multiple outcomes. " * 20
    refs = "References bibliography " * 120
    assert page_quality(body) > page_quality(refs)
    assert noise_penalty(refs) > noise_penalty(body)


def test_resolve_pdf_path_does_not_steal_other_doi_by_line(tmp_path, monkeypatch) -> None:
    from draft_body_holdout_from_pdfs import resolve_pdf_path
    import draft_body_holdout_from_pdfs as mod

    monkeypatch.setattr(mod, "PDF_DIR", tmp_path)
    (tmp_path / "001_10.1000_other.pdf").write_bytes(b"%PDF-1.4 other")
    (tmp_path / "101_10.1000_target.pdf").write_bytes(b"%PDF-1.4 target")
    # Same line index as pilot, different DOI — must not return other.pdf
    assert resolve_pdf_path(1, {"doi": "10.1000/target", "output": {}}) == (
        tmp_path / "101_10.1000_target.pdf"
    )
    assert resolve_pdf_path(1, {"doi": "10.1000/missing", "output": {}}) is None
