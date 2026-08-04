#!/usr/bin/env python3
"""Pilot OA full-text fetch for Tier 3 source_pdf_extract rows (W4).

Usage (from training/):
  python scripts/fetch_oa_fulltext.py --limit 100 --mailto you@example.com
  python scripts/fetch_oa_fulltext.py --limit 100 --skip-existing --out data/source_pdf_extract_batch2.jsonl --mailto you@example.com
  python scripts/fetch_oa_fulltext.py --doi 10.1371/journal.pone.0123456 --mailto you@example.com
  python scripts/fetch_oa_fulltext.py --apply-overrides
  python scripts/fetch_oa_fulltext.py --reprobe-pilot --mailto you@example.com

Writes JSONL rows with task=source_pdf_extract and a manifest under cache/oa_fulltext/.
Probes candidate URLs (HEAD/GET) and records honest fetch_status + meta.access_tier.

Operator overrides: cache/oa_fulltext/url_overrides.json
Operator-filed PDFs (e.g. training corpus): scripts/file_operator_pdf.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from corpus_utils import DATA_DIR, normalize_doi, read_jsonl  # noqa: E402
from oa_pdf_probe import (  # noqa: E402
    ACCESS_TIER_OA_URL_ONLY,
    ACCESS_TIER_OPERATOR_OVERRIDE,
    FETCH_STATUS_PDF_FILED,
    FETCH_STATUS_PDF_VERIFIED,
    FETCH_STATUS_URL_ONLY,
    access_tier_for_selection,
    is_pmc_url,
    probe_url,
    sha256_bytes,
)

USER_AGENT = "NassilaT/1.0 (Nassila Tier3 OA pilot; mailto:nassila-corpus@users.noreply.github.com)"
UNPAYWALL = "https://api.unpaywall.org/v2/{doi}"
CACHE_DIR = SCRIPT_DIR.parent / "cache" / "oa_fulltext"
MANIFEST = CACHE_DIR / "manifest.jsonl"
OVERRIDES = CACHE_DIR / "url_overrides.json"
OUT_JSONL = DATA_DIR / "source_pdf_extract_pilot.jsonl"

TRUSTED_REPO_MARKERS = (
    "ncbi.nlm.nih.gov/pmc",
    "europepmc.org",
    "pubmed.ncbi.nlm.nih.gov",
    "arxiv.org",
    "biorxiv.org",
    "medrxiv.org",
    "zenodo.org",
    "figshare.com",
    "scielo.br",
    "plos.org",
    "frontiersin.org",
    "mdpi.com",
    "biomedcentral.com",
    "bmj.com",
    "cran.r-project.org",
    "deepblue.lib.umich.edu",
    "pure.eur.nl",
)

EXCERPT_DEFERRED = (
    "Excerpt text deferred — run PDF extract in app/Masdar-lite before training rows"
)


def load_manifest(path: Path = MANIFEST) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        doi = normalize_doi(entry.get("doi"))
        if doi:
            entry["doi"] = doi
            entries[doi] = entry
    return entries


def write_manifest(entries: dict[str, dict[str, Any]], path: Path = MANIFEST) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for doi in sorted(entries):
            f.write(json.dumps(entries[doi], ensure_ascii=False) + "\n")


def upsert_manifest(entries: dict[str, dict[str, Any]], entry: dict[str, Any]) -> None:
    doi = normalize_doi(entry.get("doi"))
    if not doi:
        return
    entries[doi] = {**entry, "doi": doi}


def load_url_overrides(path: Path = OVERRIDES) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        if key.startswith("_") or not isinstance(value, dict):
            continue
        doi = normalize_doi(key)
        url = value.get("url")
        if doi and isinstance(url, str) and url.strip():
            out[doi] = {**value, "url": url.strip()}
    return out


def doi_url_variants(doi: str) -> list[str]:
    d = doi.lower()
    variants = {d, d.replace("/", "%2f"), unquote(d), re.sub(r"[^\w]+", "", d)}
    variants.add(
        d.replace("(", "%28")
        .replace(")", "%29")
        .replace("<", "%3c")
        .replace(">", "%3e")
        .replace(":", "%3a")
        .replace(";", "%3b")
    )
    return [v for v in variants if v]


def url_embeds_doi(url: str, doi: str) -> bool:
    hay = unquote(url).lower()
    return any(v in hay for v in doi_url_variants(doi))


def is_trusted_repo_url(url: str) -> bool:
    low = url.lower()
    return any(marker in low for marker in TRUSTED_REPO_MARKERS)


def pick_location_url(loc: dict[str, Any]) -> str | None:
    for key in ("url_for_pdf", "url", "url_for_landing_page"):
        value = loc.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def score_oa_location(loc: dict[str, Any], doi: str) -> tuple[int, str] | None:
    url = pick_location_url(loc)
    if not url:
        return None

    host_type = (loc.get("host_type") or "").lower()
    embeds = url_embeds_doi(url, doi)
    has_pdf = bool(loc.get("url_for_pdf"))
    trusted = is_trusted_repo_url(url)

    if host_type == "repository" and not embeds and not trusted:
        return None

    score = 0
    if embeds:
        score += 100
    if is_pmc_url(url):
        score += 95
    elif host_type == "repository":
        score += 75
    elif host_type == "publisher":
        score += 35
    if has_pdf:
        score += 25
    if trusted:
        score += 15
    if url.lower().endswith(".pdf") or "/pdf" in url.lower():
        score += 10
    return score, url


def collect_oa_locations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    locs: list[dict[str, Any]] = []
    best = payload.get("best_oa_location")
    if isinstance(best, dict):
        locs.append(best)
    for loc in payload.get("oa_locations") or []:
        if isinstance(loc, dict):
            locs.append(loc)
    return locs


def rank_oa_candidates(
    payload: dict[str, Any],
    doi: str,
    overrides: dict[str, dict[str, Any]] | None = None,
) -> list[tuple[int, str, dict[str, Any]]]:
    doi_n = normalize_doi(doi)
    if not doi_n:
        return []

    if overrides and doi_n in overrides:
        ov = overrides[doi_n]
        return [
            (
                10_000,
                ov["url"],
                {
                    "host_type": ov.get("host_type") or "override",
                    "is_oa": ov.get("is_oa"),
                    "selection": "operator_override",
                    "override_reason": ov.get("reason"),
                },
            )
        ]

    scored: list[tuple[int, str, dict[str, Any]]] = []
    rejected = 0
    seen_urls: set[str] = set()
    for loc in collect_oa_locations(payload):
        result = score_oa_location(loc, doi_n)
        if result is None:
            rejected += 1
            continue
        score, url = result
        if url in seen_urls:
            continue
        seen_urls.add(url)
        scored.append(
            (
                score,
                url,
                {
                    "host_type": loc.get("host_type"),
                    "is_oa": bool(payload.get("is_oa")),
                    "selection": "scored_oa_location",
                    "score": score,
                    "rejected_mismatch_locations": rejected,
                },
            )
        )

    scored.sort(key=lambda t: t[0], reverse=True)
    return scored


def best_oa_url(
    payload: dict[str, Any],
    doi: str,
    overrides: dict[str, dict[str, Any]] | None = None,
) -> tuple[str, dict[str, Any]] | None:
    ranked = rank_oa_candidates(payload, doi, overrides)
    if not ranked:
        return None
    score, url, meta = ranked[0]
    return url, meta


def select_verified_url(
    session: requests.Session,
    candidates: list[tuple[int, str, dict[str, Any]]],
    *,
    probe: bool,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Return (url, selection_meta, probe_output_fields)."""
    if not candidates:
        raise ValueError("no candidates")

    if not probe:
        _, url, meta = candidates[0]
        selection = meta.get("selection") or "scored_oa_location"
        return url, meta, {
            "fetch_status": FETCH_STATUS_URL_ONLY,
            "access_tier": access_tier_for_selection(selection, FETCH_STATUS_URL_ONLY),
        }

    for _, url, meta in candidates:
        result = probe_url(session, url)
        selection = meta.get("selection") or "scored_oa_location"
        tier = access_tier_for_selection(selection, result.fetch_status)
        if result.fetch_status == FETCH_STATUS_PDF_VERIFIED:
            return url, {**meta, "verified_url": result.final_url or url}, {
                "fetch_status": result.fetch_status,
                "access_tier": tier,
                "pdf_sha256": result.pdf_sha256,
                "pdf_bytes": result.pdf_bytes,
                "probe_final_url": result.final_url,
                "probe_http_status": result.http_status,
                "probe_content_type": result.content_type,
                "probe_attempts": len(result.attempts),
            }
        time.sleep(0.12)

    _, url, meta = candidates[0]
    selection = meta.get("selection") or "scored_oa_location"
    last = probe_url(session, url)
    return url, meta, {
        "fetch_status": last.fetch_status,
        "access_tier": access_tier_for_selection(selection, last.fetch_status),
        "probe_final_url": last.final_url,
        "probe_http_status": last.http_status,
        "probe_content_type": last.content_type,
        "probe_error": last.error,
        "probe_attempts": len(last.attempts),
    }


def meta_label_for_tier(access_tier: str, is_oa: bool | None) -> str:
    if access_tier in ("oa_unpaywall_verified", "operator_override_verified"):
        return "full_text_oa_verified"
    if access_tier in ("operator_attached_pdf", "operator_grey_mirror"):
        return "full_text_operator_attached"
    if is_oa:
        return "full_text_oa_unpaywall"
    return "full_text_url_unverified"


def build_row(
    *,
    doi: str,
    title: str | None,
    url: str,
    selection: dict[str, Any],
    probe_fields: dict[str, Any],
    is_oa: bool | None,
) -> dict[str, Any]:
    source_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    notes = EXCERPT_DEFERRED
    if selection.get("selection") == "operator_override":
        reason = selection.get("override_reason") or "operator override"
        notes = f"Operator URL override: {reason} {notes}"

    access_tier = probe_fields.get("access_tier") or ACCESS_TIER_OA_URL_ONLY
    fetch_status = probe_fields.get("fetch_status") or FETCH_STATUS_URL_ONLY

    meta: dict[str, Any] = {
        "label": meta_label_for_tier(access_tier, is_oa),
        "access_tier": access_tier,
        "is_oa": is_oa,
        "host_type": selection.get("host_type"),
        "label_provenance": (
            "oa_fetch_pilot_override"
            if selection.get("selection") == "operator_override"
            else "oa_fetch_pilot"
        ),
        "url_selection": selection.get("selection"),
        "url_selection_score": selection.get("score"),
        "rejected_mismatch_locations": selection.get("rejected_mismatch_locations"),
        "override_reason": selection.get("override_reason"),
        "unpaywall_bibliographic_oa": is_oa,
    }
    if probe_fields.get("probe_final_url"):
        meta["probe_final_url"] = probe_fields["probe_final_url"]
    if probe_fields.get("pdf_sha256"):
        meta["pdf_sha256"] = probe_fields["pdf_sha256"]

    output: dict[str, Any] = {
        "excerpt": "",
        "page_hint": None,
        "fetch_status": fetch_status,
        "notes": notes,
    }
    if probe_fields.get("pdf_bytes"):
        output["pdf_bytes"] = probe_fields["pdf_bytes"]
    if probe_fields.get("probe_error"):
        output["probe_error"] = probe_fields["probe_error"]

    return {
        "id": f"oa-{source_hash}",
        "task": "source_pdf_extract",
        "version": 1,
        "url": url,
        "doi": doi,
        "title": title,
        "meta": meta,
        "output": output,
    }


def fetch_unpaywall(doi: str, mailto: str, session: requests.Session) -> dict[str, Any] | None:
    resp = session.get(
        UNPAYWALL.format(doi=doi),
        params={"email": mailto},
        timeout=30,
        headers={"User-Agent": USER_AGENT},
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def row_from_paper(
    paper: dict[str, Any],
    mailto: str,
    session: requests.Session,
    overrides: dict[str, dict[str, Any]],
    *,
    probe: bool,
) -> dict[str, Any] | None:
    doi = normalize_doi(paper.get("doi"))
    if not doi:
        return None

    payload: dict[str, Any] | None = None
    try:
        payload = fetch_unpaywall(doi, mailto, session)
    except Exception:
        payload = None

    if doi in overrides:
        candidates = rank_oa_candidates(payload or {"is_oa": False, "oa_locations": []}, doi, overrides)
    else:
        if not payload:
            return None
        candidates = rank_oa_candidates(payload, doi, overrides=None)
        if not candidates:
            return None

    url, selection, probe_fields = select_verified_url(session, candidates, probe=probe)

    is_oa = selection.get("is_oa")
    if is_oa is None and payload is not None:
        is_oa = bool(payload.get("is_oa"))

    return build_row(
        doi=doi,
        title=paper.get("title"),
        url=url,
        selection=selection,
        probe_fields=probe_fields,
        is_oa=is_oa,
    )


def reprobe_pilot_row(
    row: dict[str, Any],
    session: requests.Session,
    overrides: dict[str, dict[str, Any]],
    *,
    probe: bool,
) -> dict[str, Any]:
    """Re-run URL probe on an existing pilot row; preserve pdf_filed / operator attach."""
    output = dict(row.get("output") or {})
    meta = dict(row.get("meta") or {})
    if output.get("fetch_status") == FETCH_STATUS_PDF_FILED:
        return row

    doi = normalize_doi(row.get("doi"))
    if not doi:
        return row

    if doi in overrides:
        candidates = rank_oa_candidates({"is_oa": meta.get("is_oa"), "oa_locations": []}, doi, overrides)
    else:
        url = str(row.get("url") or "")
        candidates = [
            (
                100,
                url,
                {
                    "host_type": meta.get("host_type"),
                    "is_oa": meta.get("is_oa"),
                    "selection": meta.get("url_selection") or "scored_oa_location",
                    "score": meta.get("url_selection_score"),
                    "override_reason": meta.get("override_reason"),
                },
            )
        ]
        payload = None
        try:
            payload = fetch_unpaywall(doi, "", session)
        except Exception:
            pass
        if payload:
            extra = rank_oa_candidates(payload, doi, overrides=None)
            seen = {c[1] for c in candidates}
            for item in extra:
                if item[1] not in seen:
                    candidates.append(item)
                    seen.add(item[1])
            candidates.sort(key=lambda t: t[0], reverse=True)

    url, selection, probe_fields = select_verified_url(session, candidates, probe=probe)
    is_oa = meta.get("is_oa")
    if is_oa is None:
        is_oa = meta.get("unpaywall_bibliographic_oa")

    updated = build_row(
        doi=doi,
        title=row.get("title"),
        url=url,
        selection=selection,
        probe_fields=probe_fields,
        is_oa=is_oa,
    )
    if output.get("page_hint"):
        updated["output"]["page_hint"] = output["page_hint"]
    if output.get("excerpt"):
        updated["output"]["excerpt"] = output["excerpt"]
    return updated


def apply_overrides_to_jsonl(
    path: Path,
    overrides: dict[str, dict[str, Any]],
    manifest: dict[str, dict[str, Any]],
    session: requests.Session | None = None,
    *,
    probe: bool = True,
) -> int:
    if not path.exists() or not overrides:
        return 0
    rows = read_jsonl(path)
    updated = 0
    for i, row in enumerate(rows):
        doi = normalize_doi(row.get("doi"))
        if not doi or doi not in overrides:
            continue
        ov = overrides[doi]
        new_url = ov["url"]
        if row.get("url") == new_url and not probe:
            continue
        if session is not None and probe:
            row = reprobe_pilot_row(row, session, overrides, probe=True)
        else:
            row["url"] = new_url
            row["id"] = f"oa-{hashlib.sha256(new_url.encode()).hexdigest()[:16]}"
            meta = dict(row.get("meta") or {})
            meta["host_type"] = ov.get("host_type") or "override"
            if "is_oa" in ov:
                meta["is_oa"] = ov["is_oa"]
            meta["label_provenance"] = "oa_fetch_pilot_override"
            meta["url_selection"] = "operator_override"
            meta["override_reason"] = ov.get("reason")
            meta["access_tier"] = ACCESS_TIER_OPERATOR_OVERRIDE
            meta["label"] = meta_label_for_tier(ACCESS_TIER_OPERATOR_OVERRIDE, meta.get("is_oa"))
            row["meta"] = meta
            output = dict(row.get("output") or {})
            reason = ov.get("reason") or "operator override"
            output["notes"] = f"Operator URL override: {reason} {EXCERPT_DEFERRED}"
            output["fetch_status"] = FETCH_STATUS_URL_ONLY
            row["output"] = output
        rows[i] = row
        upsert_manifest(
            manifest,
            {
                "doi": doi,
                "status": row.get("output", {}).get("fetch_status", "resolved"),
                "url": row["url"],
                "selection": (row.get("meta") or {}).get("url_selection"),
                "access_tier": (row.get("meta") or {}).get("access_tier"),
            },
        )
        updated += 1

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return updated


def reprobe_pilot_jsonl(
    path: Path,
    mailto: str,
    session: requests.Session,
    overrides: dict[str, dict[str, Any]],
    manifest: dict[str, dict[str, Any]],
    *,
    probe: bool,
) -> dict[str, int]:
    rows = read_jsonl(path)
    counts = {"pdf_verified": 0, "paywall_or_auth": 0, "html_only": 0, "url_resolved": 0, "pdf_filed": 0, "other": 0}
    for i, row in enumerate(rows):
        new_row = reprobe_pilot_row(row, session, overrides, probe=probe)
        rows[i] = new_row
        status = (new_row.get("output") or {}).get("fetch_status") or "other"
        counts[status] = counts.get(status, 0) + 1
        doi = normalize_doi(new_row.get("doi"))
        if doi:
            upsert_manifest(
                manifest,
                {
                    "doi": doi,
                    "status": status,
                    "url": new_row.get("url"),
                    "access_tier": (new_row.get("meta") or {}).get("access_tier"),
                },
            )
        time.sleep(0.15)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--mailto", help="Required for Unpaywall API (not needed with --dedupe-manifest)")
    parser.add_argument("--doi", help="Single DOI pilot")
    parser.add_argument("--corpus", type=Path, default=DATA_DIR / "paper_corpus_enriched.jsonl")
    parser.add_argument("--out", type=Path, default=OUT_JSONL)
    parser.add_argument("--dedupe-manifest", action="store_true")
    parser.add_argument("--apply-overrides", action="store_true")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip DOIs already present in cache/oa_fulltext/manifest.jsonl (for batch2+ scale)",
    )
    parser.add_argument(
        "--reprobe-pilot",
        action="store_true",
        help="Re-probe URLs in existing pilot JSONL (honest fetch_status); needs --mailto for extra Unpaywall candidates",
    )
    parser.add_argument(
        "--no-probe",
        action="store_true",
        help="Skip live PDF probe (legacy url_resolved only)",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    overrides = load_url_overrides()
    probe = not args.no_probe

    if args.dedupe_manifest:
        write_manifest(manifest)
        print(f"manifest_deduped={len(manifest)} path={MANIFEST}")
        return 0

    if args.apply_overrides:
        session = requests.Session() if probe else None
        n = apply_overrides_to_jsonl(args.out, overrides, manifest, session, probe=probe)
        write_manifest(manifest)
        print(f"overrides_applied={n} overrides_file={OVERRIDES} out={args.out}")
        return 0

    if args.reprobe_pilot:
        if not args.mailto:
            parser.error("--mailto is required for --reprobe-pilot")
        session = requests.Session()
        counts = reprobe_pilot_jsonl(
            args.out, args.mailto, session, overrides, manifest, probe=probe
        )
        write_manifest(manifest)
        print(f"reprobe_counts={json.dumps(counts)} out={args.out}")
        return 0

    if not args.mailto:
        parser.error("--mailto is required unless using --dedupe-manifest or --apply-overrides")

    session = requests.Session()
    rows: list[dict[str, Any]] = []
    skipped_existing = 0

    if args.doi:
        paper = {"doi": args.doi, "title": args.doi}
        row = row_from_paper(paper, args.mailto, session, overrides, probe=probe)
        if row:
            rows.append(row)
            upsert_manifest(
                manifest,
                {
                    "doi": args.doi,
                    "status": row["output"]["fetch_status"],
                    "url": row["url"],
                    "access_tier": row["meta"]["access_tier"],
                },
            )
        else:
            upsert_manifest(manifest, {"doi": args.doi, "status": "unresolved"})
    else:
        papers = read_jsonl(args.corpus)
        for paper in papers:
            if len(rows) >= args.limit:
                break
            doi = normalize_doi(paper.get("doi"))
            if args.skip_existing and doi and doi in manifest:
                skipped_existing += 1
                continue
            row = row_from_paper(paper, args.mailto, session, overrides, probe=probe)
            if not row:
                continue
            rows.append(row)
            upsert_manifest(
                manifest,
                {
                    "doi": row["doi"],
                    "status": row["output"]["fetch_status"],
                    "url": row["url"],
                    "access_tier": row["meta"]["access_tier"],
                },
            )
            time.sleep(0.2)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    write_manifest(manifest)
    verified = sum(1 for r in rows if r["output"]["fetch_status"] == FETCH_STATUS_PDF_VERIFIED)
    skip_note = f" skipped_existing={skipped_existing}" if args.skip_existing else ""
    print(
        f"resolved={len(rows)} pdf_verified={verified} manifest={len(manifest)} "
        f"path={MANIFEST} out={args.out}{skip_note}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
