#!/usr/bin/env python3
"""Match Downloads/*.pdf to pilot lines 1-50 and move into cache/oa_fulltext/pdfs/."""

from __future__ import annotations

import json
import re
import shutil
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from corpus_utils import normalize_doi  # noqa: E402
from download_oa_pdfs import doi_safe  # noqa: E402
from fetch_oa_fulltext import CACHE_DIR  # noqa: E402

PILOT = Path(__file__).resolve().parents[1] / "data" / "source_pdf_extract_pilot.jsonl"
PDF_DIR = CACHE_DIR / "pdfs"
DOWNLOADS = Path.home() / "Downloads"
LOG = CACHE_DIR / "pdf_move_from_downloads.jsonl"
MIN_SCORE = 0.55


def norm(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def score(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    # prefer containment / prefix for truncated download names
    if a in b or b in a:
        shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
        return max(0.75, len(shorter) / max(len(longer), 1))
    return SequenceMatcher(None, a, b).ratio()


def main() -> int:
    rows = []
    for i, line in enumerate(PILOT.open(encoding="utf-8"), start=1):
        if i > 50:
            break
        row = json.loads(line)
        rows.append(
            {
                "line": i,
                "doi": normalize_doi(row.get("doi")) or f"line-{i}",
                "title": row.get("title") or "",
                "title_n": norm(row.get("title")),
            }
        )

    pdfs = [p for p in DOWNLOADS.glob("*.pdf") if p.is_file()]
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    # greedy best unique match
    candidates: list[tuple[float, int, Path]] = []
    for row in rows:
        for pdf in pdfs:
            sc = score(row["title_n"], norm(pdf.stem))
            if sc >= MIN_SCORE:
                candidates.append((sc, row["line"], pdf))
    candidates.sort(reverse=True)

    used_lines: set[int] = set()
    used_pdfs: set[Path] = set()
    moves: list[dict] = []

    for sc, line, pdf in candidates:
        if line in used_lines or pdf in used_pdfs:
            continue
        row = next(r for r in rows if r["line"] == line)
        dest = PDF_DIR / f"{line:03d}_{doi_safe(row['doi'])}.pdf"
        action = "moved"
        if dest.exists() and dest.stat().st_size > 1000:
            action = "skipped_dest_exists"
        else:
            shutil.move(str(pdf), str(dest))
        used_lines.add(line)
        used_pdfs.add(pdf)
        moves.append(
            {
                "line": line,
                "doi": row["doi"],
                "title": row["title"],
                "from": str(pdf),
                "to": str(dest),
                "score": round(sc, 3),
                "action": action,
            }
        )
        print(f"{action.upper():20s} L{line:03d} score={sc:.2f} <- {pdf.name}")

    unmatched = [r for r in rows if r["line"] not in used_lines]
    leftover = [p for p in pdfs if p not in used_pdfs and p.exists()]

    with LOG.open("w", encoding="utf-8") as f:
        for item in moves:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        for r in unmatched:
            f.write(
                json.dumps(
                    {
                        "line": r["line"],
                        "doi": r["doi"],
                        "title": r["title"],
                        "action": "unmatched",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(
        f"moved_or_matched={len(moves)} unmatched={len(unmatched)} "
        f"leftover_downloads={len(leftover)} log={LOG}"
    )
    if unmatched:
        print("UNMATCHED:")
        for r in unmatched:
            print(f"  L{r['line']:03d} {r['title'][:70]}")
    if leftover:
        print("LEFTOVER IN DOWNLOADS (not moved):")
        for p in leftover[:20]:
            print(f"  {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
