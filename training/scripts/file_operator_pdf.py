#!/usr/bin/env python3
"""Register operator-filed PDFs against source_pdf_extract pilot rows.

Use when OA/Unpaywall URLs are paywalled but you have a local PDF (e.g. filed
manually for Sanad training). Does not fetch from grey mirrors — you place the
file in cache/oa_fulltext/pdfs/ first.

Usage (from training/):
  python scripts/file_operator_pdf.py --line 51 --pdf cache/oa_fulltext/pdfs/051_10.1234_example.pdf
  python scripts/file_operator_pdf.py --doi 10.1234/example --pdf path/to/file.pdf --grey
  python scripts/file_operator_pdf.py --scan-dir cache/oa_fulltext/pdfs --grey
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from corpus_utils import DATA_DIR, normalize_doi, read_jsonl  # noqa: E402
from fetch_oa_fulltext import CACHE_DIR, load_manifest, upsert_manifest, write_manifest  # noqa: E402
from oa_pdf_probe import (  # noqa: E402
    ACCESS_TIER_OPERATOR_ATTACHED,
    ACCESS_TIER_OPERATOR_GREY,
    FETCH_STATUS_PDF_FILED,
    is_pdf_bytes,
    sha256_bytes,
)

PILOT_DEFAULT = DATA_DIR / "source_pdf_extract_pilot.jsonl"
PDF_DIR = CACHE_DIR / "pdfs"
LINE_PREFIX = re.compile(r"^(\d{3})_")

EXCERPT_DEFERRED = (
    "Excerpt text deferred — run PDF extract in app/Masdar-lite before training rows"
)


def pdf_meta(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if not is_pdf_bytes(data):
        raise ValueError(f"not a PDF: {path}")
    return {
        "pdf_path": str(path.resolve()),
        "pdf_bytes": len(data),
        "pdf_sha256": sha256_bytes(data),
    }


def line_from_filename(name: str) -> int | None:
    m = LINE_PREFIX.match(name)
    return int(m.group(1)) if m else None


def doi_from_filename(name: str) -> str | None:
    stem = Path(name).stem
    m = LINE_PREFIX.match(stem)
    rest = stem[m.end() :] if m else stem
    doi = rest.replace("_", "/")
    return normalize_doi(doi) if doi else None


def apply_filing(
    row: dict[str, Any],
    path: Path,
    *,
    grey: bool,
    reason: str | None,
) -> dict[str, Any]:
    meta_fields = pdf_meta(path)
    access_tier = ACCESS_TIER_OPERATOR_GREY if grey else ACCESS_TIER_OPERATOR_ATTACHED
    meta = dict(row.get("meta") or {})
    meta["access_tier"] = access_tier
    meta["label"] = "full_text_operator_attached"
    meta["label_provenance"] = "operator_pdf_filed"
    meta["operator_filed"] = True
    meta["operator_grey_mirror"] = grey
    if reason:
        meta["operator_filing_reason"] = reason
    meta["pdf_sha256"] = meta_fields["pdf_sha256"]
    meta["pdf_path"] = meta_fields["pdf_path"]

    output = dict(row.get("output") or {})
    output["fetch_status"] = FETCH_STATUS_PDF_FILED
    output["pdf_bytes"] = meta_fields["pdf_bytes"]
    output["pdf_path"] = meta_fields["pdf_path"]
    note = "Operator-filed PDF"
    if grey:
        note += " (grey mirror — training corpus only, not product path)"
    if reason:
        note += f": {reason}"
    prior = (output.get("notes") or "").strip()
    if prior and EXCERPT_DEFERRED not in prior:
        output["notes"] = f"{note}. {prior}"
    else:
        output["notes"] = f"{note}. {EXCERPT_DEFERRED}"

    return {**row, "meta": meta, "output": output}


def file_by_line(
    pilot: Path,
    line: int,
    pdf: Path,
    manifest: dict[str, dict[str, Any]],
    *,
    grey: bool,
    reason: str | None,
) -> bool:
    rows = read_jsonl(pilot)
    if line < 1 or line > len(rows):
        raise SystemExit(f"line {line} out of range (1..{len(rows)})")
    row = rows[line - 1]
    rows[line - 1] = apply_filing(row, pdf, grey=grey, reason=reason)
    with pilot.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    doi = normalize_doi(row.get("doi"))
    if doi:
        upsert_manifest(
            manifest,
            {
                "doi": doi,
                "status": FETCH_STATUS_PDF_FILED,
                "url": row.get("url"),
                "access_tier": ACCESS_TIER_OPERATOR_GREY if grey else ACCESS_TIER_OPERATOR_ATTACHED,
                "pdf_path": str(pdf.resolve()),
            },
        )
    return True


def file_by_doi(
    pilot: Path,
    doi: str,
    pdf: Path,
    manifest: dict[str, dict[str, Any]],
    *,
    grey: bool,
    reason: str | None,
) -> bool:
    doi_n = normalize_doi(doi)
    rows = read_jsonl(pilot)
    for i, row in enumerate(rows):
        if normalize_doi(row.get("doi")) == doi_n:
            rows[i] = apply_filing(row, pdf, grey=grey, reason=reason)
            with pilot.open("w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            upsert_manifest(
                manifest,
                {
                    "doi": doi_n,
                    "status": FETCH_STATUS_PDF_FILED,
                    "url": row.get("url"),
                    "access_tier": ACCESS_TIER_OPERATOR_GREY if grey else ACCESS_TIER_OPERATOR_ATTACHED,
                    "pdf_path": str(pdf.resolve()),
                },
            )
            return True
    raise SystemExit(f"DOI not found in pilot: {doi_n}")


def scan_dir(
    pilot: Path,
    directory: Path,
    manifest: dict[str, dict[str, Any]],
    *,
    grey: bool,
    line_offset: int = 0,
) -> int:
    rows = read_jsonl(pilot)
    by_line = {i + 1: row for i, row in enumerate(rows)}
    by_doi = {normalize_doi(r.get("doi")): (i + 1, r) for i, r in enumerate(rows) if normalize_doi(r.get("doi"))}
    filed = 0
    for pdf in sorted(directory.glob("*.pdf")):
        line = line_from_filename(pdf.name)
        doi = doi_from_filename(pdf.name)
        target_line: int | None = None
        # Prefer DOI — line prefixes may use --line-offset (batch2: 101 → row 1).
        if doi and doi in by_doi:
            target_line = by_doi[doi][0]
        elif line is not None:
            jsonl_line = line - line_offset if line_offset else line
            if jsonl_line in by_line:
                target_line = jsonl_line
        if not target_line:
            continue
        row = by_line[target_line]
        if (row.get("output") or {}).get("fetch_status") == FETCH_STATUS_PDF_FILED:
            # Still refresh path if a better file appeared for this DOI.
            existing = Path(str((row.get("output") or {}).get("pdf_path") or ""))
            if existing.exists() and existing.resolve() == pdf.resolve():
                continue
        by_line[target_line] = apply_filing(row, pdf, grey=grey, reason="scan-dir match")
        filed += 1
        doi_n = normalize_doi(row.get("doi"))
        if doi_n:
            upsert_manifest(
                manifest,
                {
                    "doi": doi_n,
                    "status": FETCH_STATUS_PDF_FILED,
                    "url": row.get("url"),
                    "access_tier": ACCESS_TIER_OPERATOR_GREY if grey else ACCESS_TIER_OPERATOR_ATTACHED,
                    "pdf_path": str(pdf.resolve()),
                },
            )
    with pilot.open("w", encoding="utf-8") as f:
        for i in range(1, len(rows) + 1):
            f.write(json.dumps(by_line[i], ensure_ascii=False) + "\n")
    return filed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", type=Path, default=PILOT_DEFAULT)
    parser.add_argument("--line", type=int)
    parser.add_argument("--doi")
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--scan-dir", type=Path, dest="scan_directory")
    parser.add_argument(
        "--line-offset",
        type=int,
        default=0,
        help="Filename line prefix minus this = JSONL row (batch2 PDFs: --line-offset 100)",
    )
    parser.add_argument(
        "--grey",
        action="store_true",
        help="Mark access_tier=operator_grey_mirror (training-only provenance)",
    )
    parser.add_argument("--reason", help="Optional operator note")
    args = parser.parse_args()

    manifest = load_manifest()

    if args.scan_directory:
        n = scan_dir(
            args.pilot,
            args.scan_directory,
            manifest,
            grey=args.grey,
            line_offset=args.line_offset,
        )
        write_manifest(manifest)
        print(f"filed={n} pilot={args.pilot}")
        return 0

    if not args.pdf or not args.pdf.exists():
        parser.error("--pdf is required (existing file) unless using --scan-dir")

    if args.line:
        file_by_line(args.pilot, args.line, args.pdf, manifest, grey=args.grey, reason=args.reason)
    elif args.doi:
        file_by_doi(args.pilot, args.doi, args.pdf, manifest, grey=args.grey, reason=args.reason)
    else:
        parser.error("one of --line, --doi, or --scan-dir is required")

    write_manifest(manifest)
    print(f"filed pdf={args.pdf} grey={args.grey} pilot={args.pilot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
