"""Audit helpers for OA pilot URL risk flags."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from audit_oa_urls import audit_rows, flag_reasons  # noqa: E402


def test_flag_handle_without_override() -> None:
    row = {
        "doi": "10.1007/978-3-642-85829-1",
        "url": "http://hdl.handle.net/2060/20050031105",
        "meta": {"host_type": "repository"},
    }
    reasons = flag_reasons(row)
    assert any(r.startswith("high_risk_host:hdl.handle.net") for r in reasons)


def test_override_skips_flag() -> None:
    row = {
        "doi": "10.1007/978-3-642-85829-1",
        "url": "https://link.springer.com/book/10.1007/978-3-642-85829-1",
        "meta": {"host_type": "publisher", "url_selection": "operator_override"},
    }
    assert flag_reasons(row) == []


def test_trusted_pmc_not_flagged() -> None:
    row = {
        "doi": "10.1038/75556",
        "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/3037419",
        "meta": {"host_type": "repository"},
    }
    assert flag_reasons(row) == []


def test_audit_rows_emits_line_numbers() -> None:
    rows = [
        {
            "doi": "10.1038/35002501",
            "title": "Biodiversity hotspots",
            "url": "https://zotero.org/groups/1/items/ABC",
            "meta": {"host_type": "repository"},
        }
    ]
    findings = audit_rows(rows)
    assert len(findings) == 1
    assert findings[0]["line"] == 1
    assert findings[0]["suggested_identity_url"] == "https://doi.org/10.1038/35002501"
