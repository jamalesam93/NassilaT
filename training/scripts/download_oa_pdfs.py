#!/usr/bin/env python3
"""Download OA pilot PDFs for Tier 3 source_pdf_extract rows.

Usage (from training/):
  python scripts/download_oa_pdfs.py --from-line 51 --to-line 100
  python scripts/download_oa_pdfs.py --from-line 1 --to-line 100 --skip-existing

Writes files to cache/oa_fulltext/pdfs/ and a download log JSONL.
Uses shared oa_pdf_probe for URL expansion and PDF detection.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from corpus_utils import DATA_DIR, normalize_doi, read_jsonl  # noqa: E402
from fetch_oa_fulltext import CACHE_DIR  # noqa: E402
from oa_pdf_probe import (  # noqa: E402
    expand_candidate_urls,
    is_pdf_bytes,
    probe_url,
)

USER_AGENT = (
    "Mozilla/5.0 (compatible; NassilaT/1.0; OA pilot PDF fetch; "
    "+https://github.com/jamalesam93/NassilaT)"
)
PDF_DIR = CACHE_DIR / "pdfs"
LOG_PATH = CACHE_DIR / "pdf_download_log.jsonl"
PILOT_DEFAULT = DATA_DIR / "source_pdf_extract_pilot.jsonl"


def doi_safe(doi: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", doi)[:120]


def eid_pdf_urls(doi: str) -> list[str]:
    """CDC Emerging Infectious Diseases free PDF patterns."""
    m = re.match(r"10\.3201/eid(\d{2})(\d{2})\.(\d+)", doi.lower())
    if not m:
        return []
    yy, issue_raw, art = m.group(1), m.group(2), m.group(3)
    vol = int(yy)
    issue = int(issue_raw)
    art_slug = f"{art[:2]}-{art[2:]}" if len(art) == 6 else art
    return [
        f"https://wwwnc.cdc.gov/eid/article/{vol}/{issue}/pdfs/{art_slug}-article.pdf",
        f"https://wwwnc.cdc.gov/eid/article/{vol}/{issue}/pdfs/{art_slug}.pdf",
    ]


def unpaywall_pdf_urls(doi: str, mailto: str, session: requests.Session) -> list[str]:
    """Collect url_for_pdf / OA URLs from Unpaywall."""
    try:
        resp = session.get(
            f"https://api.unpaywall.org/v2/{doi}",
            params={"email": mailto},
            timeout=30,
            headers={"User-Agent": USER_AGENT},
        )
        if resp.status_code != 200:
            return []
        payload = resp.json()
    except requests.RequestException:
        return []

    urls: list[str] = []
    locs: list[dict[str, Any]] = []
    best = payload.get("best_oa_location")
    if isinstance(best, dict):
        locs.append(best)
    for loc in payload.get("oa_locations") or []:
        if isinstance(loc, dict):
            locs.append(loc)
    for loc in locs:
        for key in ("url_for_pdf", "url", "url_for_landing_page"):
            value = loc.get(key)
            if isinstance(value, str) and value.strip():
                urls.append(value.strip())
    urls.sort(key=lambda u: (0 if "pdf" in u.lower() else 1, u))
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def candidate_urls(url: str, extra: list[str] | None = None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for u in (extra or []) + expand_candidate_urls(url):
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def download_row(
    session: requests.Session,
    row: dict[str, Any],
    line: int,
    out_dir: Path,
    skip_existing: bool,
    mailto: str | None,
) -> dict[str, Any]:
    doi = normalize_doi(row.get("doi")) or f"line-{line}"
    dest = out_dir / f"{line:03d}_{doi_safe(doi)}.pdf"
    entry: dict[str, Any] = {
        "line": line,
        "doi": doi,
        "title": row.get("title"),
        "source_url": row.get("url"),
        "path": str(dest),
        "status": "pending",
    }

    if skip_existing and dest.exists() and dest.stat().st_size > 1000:
        entry["status"] = "skipped_existing"
        entry["bytes"] = dest.stat().st_size
        return entry

    extras: list[str] = []
    extras.extend(eid_pdf_urls(doi))
    if mailto:
        extras.extend(unpaywall_pdf_urls(doi, mailto, session))

    attempts: list[dict[str, Any]] = []
    queue = candidate_urls(str(row.get("url") or ""), extras)
    seen_urls: set[str] = set(queue)
    idx = 0
    while idx < len(queue):
        url = queue[idx]
        idx += 1
        result = probe_url(session, url)
        attempts.extend(result.attempts)
        if result.fetch_status == "pdf_verified" and result.pdf_bytes:
            # Re-fetch once to write file (probe already validated bytes)
            resp = session.get(
                result.final_url or url,
                timeout=60,
                allow_redirects=True,
                headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*"},
            )
            data = resp.content
            if is_pdf_bytes(data):
                dest.write_bytes(data)
                entry["status"] = "ok"
                entry["bytes"] = len(data)
                entry["final_url"] = result.final_url
                entry["attempts"] = attempts
                return entry
        time.sleep(0.15)

    entry["status"] = "failed"
    entry["attempts"] = attempts
    return entry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl", type=Path, default=PILOT_DEFAULT)
    parser.add_argument("--out-dir", type=Path, default=PDF_DIR)
    parser.add_argument("--log", type=Path, default=LOG_PATH)
    parser.add_argument("--from-line", type=int, default=1)
    parser.add_argument("--to-line", type=int, default=100)
    parser.add_argument(
        "--line-offset",
        type=int,
        default=0,
        help="Add to JSONL line index for PDF filenames (batch2: --line-offset 100 → 101_*.pdf)",
    )
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.35)
    parser.add_argument(
        "--mailto",
        default="nassila-corpus@users.noreply.github.com",
        help="Unpaywall contact email for alternate OA PDF URLs",
    )
    args = parser.parse_args()

    rows = read_jsonl(args.jsonl)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    results: list[dict[str, Any]] = []
    ok = fail = skip = 0

    for i, row in enumerate(rows, start=1):
        if i < args.from_line or i > args.to_line:
            continue
        file_line = args.line_offset + i
        entry = download_row(
            session, row, file_line, args.out_dir, args.skip_existing, args.mailto
        )
        results.append(entry)
        status = entry["status"]
        if status == "ok":
            ok += 1
            print(f"OK   L{file_line:03d} {entry['bytes']}B  {entry['doi']}")
        elif status == "skipped_existing":
            skip += 1
            print(f"SKIP L{file_line:03d} {entry['doi']}")
        else:
            fail += 1
            err = ""
            if entry.get("attempts"):
                last = entry["attempts"][-1]
                err = (
                    f" status={last.get('status')} "
                    f"err={last.get('error') or last.get('content_type')}"
                )
            print(f"FAIL L{file_line:03d} {entry['doi']}{err}")
        time.sleep(args.sleep)

    existing: list[dict[str, Any]] = []
    if args.log.exists():
        for line in args.log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            prev = json.loads(line)
            if not (args.from_line <= int(prev.get("line", 0)) <= args.to_line):
                existing.append(prev)
    with args.log.open("w", encoding="utf-8") as f:
        for item in existing + results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(
        f"done ok={ok} failed={fail} skipped={skip} "
        f"out={args.out_dir} log={args.log}"
    )
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
