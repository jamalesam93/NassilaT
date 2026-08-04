#!/usr/bin/env python3
"""Audit source_pdf_extract_pilot.jsonl for high-risk Unpaywall URLs.

Usage (from training/):
  python scripts/audit_oa_urls.py
  python scripts/audit_oa_urls.py --jsonl data/source_pdf_extract_pilot.jsonl --out cache/oa_fulltext/url_audit.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from corpus_utils import DATA_DIR, normalize_doi, read_jsonl  # noqa: E402
from fetch_oa_fulltext import (  # noqa: E402
    CACHE_DIR,
    TRUSTED_REPO_MARKERS,
    url_embeds_doi,
)

OUT_DEFAULT = CACHE_DIR / "url_audit.jsonl"
PILOT_DEFAULT = DATA_DIR / "source_pdf_extract_pilot.jsonl"

# Hosts that have already produced DOI-mismatched Unpaywall hits in this pilot.
HIGH_RISK_HOST_MARKERS = (
    "hdl.handle.net",
    "zotero.org",
    "worktribe.com",
    "hal.science",
    "ine.es/",
    "repositorio.",
    "infoscience.",
    "durham-repository.",
    "dspace.",
)


def flag_reasons(row: dict[str, Any]) -> list[str]:
    meta = row.get("meta") or {}
    if meta.get("url_selection") == "operator_override":
        return []

    doi = normalize_doi(row.get("doi"))
    url = (row.get("url") or "").strip()
    if not doi or not url:
        return ["missing_doi_or_url"]

    host_type = (meta.get("host_type") or "").lower()
    low = url.lower()
    embeds = url_embeds_doi(url, doi)
    trusted = any(m in low for m in TRUSTED_REPO_MARKERS)
    reasons: list[str] = []

    for marker in HIGH_RISK_HOST_MARKERS:
        if marker in low:
            reasons.append(f"high_risk_host:{marker.rstrip('/')}")

    if host_type == "repository" and not embeds and not trusted:
        reasons.append("untrusted_repo_no_doi")

    if not embeds and not trusted and host_type not in {"publisher"}:
        if "no_doi_untrusted" not in reasons and not any(r.startswith("high_risk_host") for r in reasons):
            reasons.append("no_doi_untrusted")

    # doi.org-only landing with no PDF path — identity ok, extract may need operator PDF
    if low.startswith("https://doi.org/") or low.startswith("http://doi.org/"):
        reasons.append("doi_resolver_only")

    return reasons


def audit_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows, start=1):
        reasons = flag_reasons(row)
        if not reasons:
            continue
        out.append(
            {
                "line": i,
                "doi": normalize_doi(row.get("doi")),
                "title": row.get("title"),
                "url": row.get("url"),
                "host_type": (row.get("meta") or {}).get("host_type"),
                "reasons": reasons,
                "suggested_identity_url": (
                    f"https://doi.org/{normalize_doi(row.get('doi'))}"
                    if normalize_doi(row.get("doi"))
                    else None
                ),
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl", type=Path, default=PILOT_DEFAULT)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args()

    rows = read_jsonl(args.jsonl)
    findings = audit_rows(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for item in findings:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"audited={len(rows)} flagged={len(findings)} out={args.out}")
    for item in findings:
        print(
            f"  L{item['line']:03d} {item['doi']} :: {','.join(item['reasons'])}\n"
            f"       {item['url']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
