"""Tests for oa_pdf_probe.py."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from oa_pdf_probe import (  # noqa: E402
    ACCESS_TIER_OA_VERIFIED,
    ACCESS_TIER_OPERATOR_OVERRIDE,
    ACCESS_TIER_OPERATOR_OVERRIDE_VERIFIED,
    FETCH_STATUS_PDF_VERIFIED,
    access_tier_for_selection,
    expand_candidate_urls,
    is_pdf_bytes,
    is_pmc_url,
)


def test_is_pdf_bytes() -> None:
    assert is_pdf_bytes(b"%PDF-1.4\n")
    assert not is_pdf_bytes(b"<html>")


def test_is_pmc_url() -> None:
    assert is_pmc_url("https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3037419/")
    assert not is_pmc_url("https://example.com/paper.pdf")


def test_expand_pmc_candidates() -> None:
    url = "https://www.ncbi.nlm.nih.gov/pmc/articles/3037419"
    expanded = expand_candidate_urls(url)
    assert any("europepmc.org" in u for u in expanded)
    assert any("/pdf/" in u for u in expanded)


def test_access_tier_for_selection() -> None:
    assert access_tier_for_selection("scored_oa_location", FETCH_STATUS_PDF_VERIFIED) == ACCESS_TIER_OA_VERIFIED
    assert (
        access_tier_for_selection("operator_override", FETCH_STATUS_PDF_VERIFIED)
        == ACCESS_TIER_OPERATOR_OVERRIDE_VERIFIED
    )
    assert access_tier_for_selection("operator_override", "paywall_or_auth") == ACCESS_TIER_OPERATOR_OVERRIDE
