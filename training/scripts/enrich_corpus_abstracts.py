#!/usr/bin/env python3
"""
Backfill missing abstracts via OpenAlex and Crossref APIs (Phase 1.5).

Usage:
  python scripts/enrich_corpus_abstracts.py
  python scripts/enrich_corpus_abstracts.py --limit 100
  python scripts/enrich_corpus_abstracts.py --mailto you@example.com
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from corpus_utils import (  # noqa: E402
    CACHE_DIR,
    DATA_DIR,
    crossref_abstract,
    doi_cache_path,
    read_jsonl,
    reconstruct_openalex_abstract,
    write_jsonl,
)

USER_AGENT = "NassilaT/1.0 (Nassila training corpus; mailto:nassila-corpus@users.noreply.github.com)"
OPENALEX_WORKS = "https://api.openalex.org/works/https://doi.org/{doi}"
CROSSREF_WORKS = "https://api.crossref.org/works/{doi}"
S2_WORKS = "https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=abstract"


def fetch_openalex(doi: str, mailto: str | None, session: requests.Session) -> str | None:
    url = OPENALEX_WORKS.format(doi=doi)
    params = {"mailto": mailto} if mailto else {}
    resp = session.get(url, params=params, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()
    inv = data.get("abstract_inverted_index")
    if isinstance(inv, dict):
        return reconstruct_openalex_abstract(inv)
    return None


def fetch_crossref(doi: str, session: requests.Session) -> str | None:
    url = CROSSREF_WORKS.format(doi=doi)
    resp = session.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    msg = resp.json().get("message", {})
    if isinstance(msg, dict):
        return crossref_abstract(msg)
    return None


def fetch_semantic_scholar(doi: str, api_key: str | None, session: requests.Session) -> str | None:
    headers = {"User-Agent": USER_AGENT}
    if api_key:
        headers["x-api-key"] = api_key
    url = S2_WORKS.format(doi=doi)
    resp = session.get(url, headers=headers, timeout=30)
    if resp.status_code == 404:
        return None
    if resp.status_code == 429:
        time.sleep(5)
        return fetch_semantic_scholar(doi, api_key, session)
    resp.raise_for_status()
    data = resp.json()
    ab = data.get("abstract")
    return ab.strip() if isinstance(ab, str) and ab.strip() else None


def load_cached(doi: str) -> dict[str, Any] | None:
    path = doi_cache_path(doi)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def save_cached(doi: str, payload: dict[str, Any]) -> None:
    path = doi_cache_path(doi)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def enrich_one(
    doi: str,
    mailto: str | None,
    s2_key: str | None,
    session: requests.Session,
    use_cache: bool,
) -> tuple[str | None, str]:
    if use_cache:
        cached = load_cached(doi)
        if cached and "abstract" in cached:
            return cached.get("abstract"), cached.get("source", "cache")

    abstract: str | None = None
    source = "none"

    try:
        abstract = fetch_openalex(doi, mailto, session)
        if abstract:
            source = "openalex_api"
    except requests.RequestException as e:
        save_cached(doi, {"abstract": None, "source": "openalex_error", "error": str(e)})

    if not abstract:
        try:
            abstract = fetch_crossref(doi, session)
            if abstract:
                source = "crossref"
        except requests.RequestException:
            pass

    if not abstract and s2_key:
        try:
            abstract = fetch_semantic_scholar(doi, s2_key, session)
            if abstract:
                source = "semantic_scholar_api"
        except requests.RequestException:
            pass

    save_cached(doi, {"abstract": abstract, "source": source})
    return abstract, source


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich paper corpus with API abstracts")
    parser.add_argument(
        "--in",
        dest="in_path",
        type=Path,
        default=DATA_DIR / "paper_corpus.jsonl",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DATA_DIR / "paper_corpus_enriched.jsonl",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=CACHE_DIR / "enrich_manifest.jsonl",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max API lookups (0=all missing)")
    parser.add_argument("--mailto", default=os.environ.get("OPENALEX_MAILTO", ""))
    parser.add_argument("--sleep", type=float, default=0.12, help="Seconds between API calls")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    rows = read_jsonl(args.in_path)
    if not rows:
        print(f"No rows in {args.in_path}", file=sys.stderr)
        return 1

    s2_key = os.environ.get("S2_API_KEY", "").strip() or None
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest_mode = "a" if args.manifest.exists() else "w"
    looked_up = 0
    enriched_count = 0

    with args.manifest.open(manifest_mode, encoding="utf-8") as manifest:
        for rec in rows:
            if rec.get("abstract"):
                continue
            doi = rec.get("doi")
            if not doi:
                continue
            if args.limit and looked_up >= args.limit:
                break

            abstract, source = enrich_one(
                doi,
                args.mailto or None,
                s2_key,
                session,
                use_cache=not args.no_cache,
            )
            looked_up += 1
            if abstract:
                rec["abstract"] = abstract
                rec["abstract_source"] = source
                enriched_count += 1

            manifest.write(
                json.dumps(
                    {
                        "doi": doi,
                        "corpus_id": rec.get("corpus_id"),
                        "status": "ok" if abstract else "miss",
                        "source": source,
                        "chars": len(abstract) if abstract else 0,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            manifest.flush()
            if looked_up % 50 == 0:
                write_jsonl(args.out, rows)
            time.sleep(args.sleep)

    write_jsonl(args.out, rows)

    stats = {
        "total": len(rows),
        "with_abstract": sum(1 for r in rows if r.get("abstract")),
        "abstract_ge_120": sum(
            1 for r in rows if r.get("abstract") and len(r["abstract"]) >= 120
        ),
        "api_lookups_this_run": looked_up,
        "newly_enriched_this_run": enriched_count,
    }
    stats_path = DATA_DIR / "paper_corpus_enriched_stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print(f"Wrote {args.out}")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
