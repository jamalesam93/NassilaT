"""Operator PDF filing for source_pdf_extract pilot rows."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from file_operator_pdf import apply_filing  # noqa: E402
from oa_pdf_probe import ACCESS_TIER_OPERATOR_GREY, FETCH_STATUS_PDF_FILED  # noqa: E402


def test_apply_filing_grey_mirror(tmp_path: Path) -> None:
    pdf = tmp_path / "051_10.1063_1.1316015.pdf"
    pdf.write_bytes(b"%PDF-1.4 test content for filing\n")

    row = {
        "doi": "10.1063/1.1316015",
        "url": "https://aip.scitation.org/doi/pdf/10.1063/1.1316015",
        "meta": {"is_oa": True},
        "output": {"fetch_status": "paywall_or_auth", "notes": "old"},
    }
    updated = apply_filing(row, pdf, grey=True, reason="operator Sci-Hub filing")
    assert updated["output"]["fetch_status"] == FETCH_STATUS_PDF_FILED
    assert updated["meta"]["access_tier"] == ACCESS_TIER_OPERATOR_GREY
    assert updated["meta"]["operator_grey_mirror"] is True
    assert "grey mirror" in updated["output"]["notes"]
    assert updated["output"]["pdf_path"] == str(pdf.resolve())
