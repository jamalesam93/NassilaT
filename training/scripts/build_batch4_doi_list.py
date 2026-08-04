#!/usr/bin/env python3
"""Build batch4 DOI list (100) for operator PDF fetch."""

from __future__ import annotations

import csv
import hashlib
import html
import json
from pathlib import Path

from corpus_utils import normalize_doi, read_jsonl
from fetch_oa_fulltext import load_manifest

DATA = Path(__file__).resolve().parents[1] / "data"
LINE_OFFSET = 300
LIMIT = 100

KNOWN_FILES = [
    "source_pdf_extract_pilot.jsonl",
    "source_pdf_extract_pilot_skip98.jsonl",
    "source_pdf_extract_batch2.jsonl",
    "source_pdf_extract_batch3.jsonl",
    "source_pdf_extract_batch2_dropped.jsonl",
    "source_pdf_extract_batch3_dropped.jsonl",
]


def main() -> int:
    manifest = load_manifest()
    seen: set[str] = set(manifest)
    for name in KNOWN_FILES:
        path = DATA / name
        if not path.exists():
            continue
        for row in read_jsonl(path):
            doi = normalize_doi(row.get("doi"))
            if doi:
                seen.add(doi)

    candidates: list[dict[str, str]] = []
    for paper in read_jsonl(DATA / "paper_corpus_enriched.jsonl"):
        doi = normalize_doi(paper.get("doi"))
        if not doi or doi in seen:
            continue
        title = html.unescape((paper.get("title") or "").strip())
        candidates.append({"doi": doi, "title": title[:200]})
        seen.add(doi)
        if len(candidates) >= LIMIT:
            break

    jl = DATA / "source_pdf_extract_batch4_doi_list.jsonl"
    with jl.open("w", encoding="utf-8") as f:
        for i, c in enumerate(candidates, 1):
            f.write(
                json.dumps(
                    {
                        "line": i,
                        "line_offset_filename": f"{LINE_OFFSET + i:03d}",
                        "doi": c["doi"],
                        "title": c["title"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    (DATA / "source_pdf_extract_batch4_dois.txt").write_text(
        "\n".join(c["doi"] for c in candidates) + "\n",
        encoding="utf-8",
    )

    with (DATA / "source_pdf_extract_batch4_dois.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        w = csv.writer(f)
        w.writerow(["line", "file_prefix", "suggested_filename", "doi", "title"])
        for i, c in enumerate(candidates, 1):
            pref = f"{LINE_OFFSET + i:03d}"
            fname = f"{pref}_{c['doi'].replace('/', '_')}.pdf"
            w.writerow([i, pref, fname, c["doi"], c["title"][:120]])

    stub = DATA / "source_pdf_extract_batch4.jsonl"
    with stub.open("w", encoding="utf-8") as f:
        for i, c in enumerate(candidates, 1):
            doi = c["doi"]
            oid = "oa-" + hashlib.sha256(doi.encode()).hexdigest()[:16]
            f.write(
                json.dumps(
                    {
                        "id": oid,
                        "task": "source_pdf_extract",
                        "version": 1,
                        "url": f"https://doi.org/{doi}",
                        "doi": doi,
                        "title": c["title"] or doi,
                        "meta": {
                            "label": "batch4_doi_list",
                            "access_tier": "pending_operator_pdf",
                            "label_provenance": "batch4_operator_list",
                            "batch": 4,
                            "list_line": i,
                            "line_offset_filename": f"{LINE_OFFSET + i:03d}",
                        },
                        "output": {
                            "excerpt": "",
                            "page_hint": None,
                            "fetch_status": "url_resolved",
                            "notes": "Batch4 DOI list stub — awaiting operator PDF",
                        },
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(
        json.dumps(
            {
                "candidates": len(candidates),
                "manifest": len(manifest),
                "filename_prefix": f"{LINE_OFFSET + 1:03d}..{LINE_OFFSET + LIMIT:03d}",
                "first5": [c["doi"] for c in candidates[:5]],
                "out": str(jl),
            },
            indent=2,
        )
    )
    return 0 if candidates else 1


if __name__ == "__main__":
    raise SystemExit(main())
