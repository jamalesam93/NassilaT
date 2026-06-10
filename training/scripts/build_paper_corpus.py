#!/usr/bin/env python3
"""
Merge Publish-or-Perish-style JSON exports into paper_corpus.jsonl (Phase 1.5).

Usage:
  python scripts/build_paper_corpus.py
  python scripts/build_paper_corpus.py --glob "data/*_papers_*.json"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from corpus_utils import (  # noqa: E402
    DATA_DIR,
    TRAINING_DIR,
    corpus_id_from_uid,
    load_json_array,
    normalize_authors,
    normalize_doi,
    write_jsonl,
)


def detect_source_export(path: Path) -> str:
    name = path.name.lower()
    if "openalex" in name:
        return "openalex"
    if "semantic" in name:
        return "semantic"
    return "export"


def raw_to_record(raw: dict[str, Any], source_export: str) -> dict[str, Any] | None:
    doi = normalize_doi(raw.get("doi"))
    uid = raw.get("uid")
    if isinstance(uid, str):
        uid = uid.strip()
    else:
        uid = None

    abstract = raw.get("abstract")
    if isinstance(abstract, str):
        abstract = abstract.strip() or None
    else:
        abstract = None

    title = raw.get("title")
    if not isinstance(title, str) or not title.strip():
        title = None

    if not doi and not abstract and not uid:
        return None

    authors = normalize_authors(raw.get("authors"))
    year = raw.get("year")
    if isinstance(year, str) and year.isdigit():
        year = int(year)
    elif not isinstance(year, int):
        year = None

    fulltext_url = raw.get("fulltext_url")
    if not isinstance(fulltext_url, str) or not fulltext_url.strip():
        fulltext_url = None

    article_url = raw.get("article_url")
    if not isinstance(article_url, str) or not article_url.strip():
        article_url = None
    if not article_url and doi:
        article_url = f"https://doi.org/{doi}"

    cid = corpus_id_from_uid(uid, doi, source_export)
    return {
        "corpus_id": cid,
        "source_export": source_export,
        "uid": uid,
        "doi": doi,
        "title": title,
        "year": year,
        "authors": authors,
        "abstract": abstract,
        "abstract_source": "export" if abstract else "none",
        "fulltext_url": fulltext_url,
        "article_url": article_url,
        "meta_label": "abstract",
    }


def merge_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick best record per doi or corpus_id."""
    by_key: dict[str, dict[str, Any]] = {}
    for rec in records:
        key = rec.get("doi") or rec["corpus_id"]
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = rec
            continue
        ex_abs = existing.get("abstract") or ""
        new_abs = rec.get("abstract") or ""
        if len(new_abs) > len(ex_abs):
            by_key[key] = rec
        elif len(new_abs) == len(ex_abs) and rec.get("source_export") == "openalex":
            by_key[key] = rec
    return by_key


def compute_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    abs_lens = [len(r["abstract"]) for r in rows if r.get("abstract")]
    abs_lens.sort()
    year_hist: Counter[int] = Counter()
    for r in rows:
        y = r.get("year")
        if isinstance(y, int):
            year_hist[y] += 1
    return {
        "total_records": len(rows),
        "with_abstract": sum(1 for r in rows if r.get("abstract")),
        "with_doi": sum(1 for r in rows if r.get("doi")),
        "with_fulltext_url": sum(1 for r in rows if r.get("fulltext_url")),
        "abstract_ge_120_chars": sum(
            1 for r in rows if r.get("abstract") and len(r["abstract"]) >= 120
        ),
        "median_abstract_chars": abs_lens[len(abs_lens) // 2] if abs_lens else 0,
        "by_source_export": dict(Counter(r.get("source_export", "?") for r in rows)),
        "year_histogram": dict(sorted(year_hist.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build unified paper corpus JSONL")
    parser.add_argument(
        "--glob",
        default="*_papers_*.json",
        help="Glob under data/ for input JSON arrays",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DATA_DIR / "paper_corpus.jsonl",
    )
    parser.add_argument(
        "--stats",
        type=Path,
        default=DATA_DIR / "paper_corpus_stats.json",
    )
    args = parser.parse_args()

    paths = sorted(DATA_DIR.glob(args.glob))
    if not paths:
        print(f"No files match data/{args.glob}", file=sys.stderr)
        return 1

    all_raw: list[dict[str, Any]] = []
    for path in paths:
        source = detect_source_export(path)
        rows = load_json_array(path)
        print(f"Loaded {len(rows)} from {path.name} ({source})")
        for raw in rows:
            rec = raw_to_record(raw, source)
            if rec:
                all_raw.append(rec)

    merged = list(merge_records(all_raw).values())
    merged.sort(key=lambda r: (r.get("year") or 0, r.get("corpus_id", "")))

    write_jsonl(args.out, merged)
    stats = compute_stats(merged)
    args.stats.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print(f"Wrote {len(merged)} records -> {args.out}")
    print(f"Stats -> {args.stats}")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
