#!/usr/bin/env python3
"""Draft Tier 3 body holdout rows from filed PDFs.

Builds l3_grounding eval rows from PDFs already filed under cache/oa_fulltext/pdfs/.
Unlike draft_body_holdout_from_oa.py, this uses extracted PDF body text rather than
abstract proxies.

Usage (from training/):
  python scripts/draft_body_holdout_from_pdfs.py
  python scripts/draft_body_holdout_from_pdfs.py --limit 1000 --out data/eval_holdout_body_pdf_draft.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from pypdf import PdfReader

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from corpus_utils import CACHE_DIR, DATA_DIR, normalize_doi, read_jsonl  # noqa: E402

OA_PILOT = DATA_DIR / "source_pdf_extract_pilot.jsonl"
DEFAULT_OUT = DATA_DIR / "eval_holdout_body_pdf_draft.jsonl"
PDF_DIR = CACHE_DIR / "oa_fulltext" / "pdfs"
MIN_PAGE_CHARS = 500
MIN_EXCERPT_CHARS = 700
MAX_EXCERPT_CHARS = 2400
MIN_SENTENCE_CHARS = 60
MAX_PAGES_SCAN = 24
MAX_PAGES_AROUND_HINT = 4
PAGE_HINT_RE = re.compile(r"\bp+\.\s*(\d+)\b", re.I)
REFS_RE = re.compile(r"\b(references|bibliography|acknowledg(?:e)?ments?)\b", re.I)
REVIEW_HEADER_RE = re.compile(r"^\s*review\s+\d+\b", re.I)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
ET_AL_RE = re.compile(r"\bet al\.?\b", re.I)
CID_TOKEN_RE = re.compile(r"/(?:C\d{2,}|G[0-9A-Fa-f]{2,})")
TOC_DOTS_RE = re.compile(r"\.{4,}")
RESULTS_RE = re.compile(
    r"\b(results?|found|showed|demonstrat\w*|conclud\w*|significant|increased|decreased)\b",
    re.I,
)
METHODS_RE = re.compile(
    r"\b(methods?|design|setting|participants?|objective|purpose|background)\b",
    re.I,
)
NOISE_REJECT_THRESHOLD = 2000.0


def parse_page_hint(value: Any) -> int | None:
    if not isinstance(value, str) or not value.strip():
        return None
    match = PAGE_HINT_RE.search(value)
    if not match:
        return None
    page = int(match.group(1))
    return page if page > 0 else None


def noise_penalty(text: str) -> float:
    penalty = 0.0
    if REVIEW_HEADER_RE.search(text):
        penalty += 5000.0
    if REFS_RE.search(text):
        penalty += 2500.0
    cid_hits = len(CID_TOKEN_RE.findall(text))
    if cid_hits:
        penalty += cid_hits * 180.0
    toc_dots = len(TOC_DOTS_RE.findall(text))
    if toc_dots:
        penalty += toc_dots * 250.0
    years = len(YEAR_RE.findall(text))
    et_als = len(ET_AL_RE.findall(text))
    if years >= 6:
        penalty += years * 220.0
    if et_als >= 2:
        penalty += et_als * 450.0
    paren = text.count("(")
    if paren >= 10:
        penalty += paren * 35.0
    words = max(len(text.split()), 1)
    if text.count(",") / words > 0.08:
        penalty += 1500.0
    if text.count(";") >= 4 and years >= 3:
        penalty += 900.0
    return penalty


def is_acceptable_body_text(text: str, *, min_chars: int = MIN_PAGE_CHARS) -> bool:
    if len(text.strip()) < min_chars:
        return False
    if noise_penalty(text) >= NOISE_REJECT_THRESHOLD:
        return False
    if REVIEW_HEADER_RE.search(text):
        return False
    if len(YEAR_RE.findall(text)) >= 8 or len(ET_AL_RE.findall(text)) >= 4:
        return False
    cid_hits = len(CID_TOKEN_RE.findall(text))
    if cid_hits >= 6:
        return False
    if text.count("/C") >= 8 or text.count("/G") >= 8:
        return False
    if len(TOC_DOTS_RE.findall(text)) >= 6:
        return False
    letters = sum(ch.isalpha() for ch in text)
    if letters / max(len(text), 1) < 0.40 and cid_hits >= 2:
        return False
    head = text[:120].strip().lower()
    if head.startswith(("references", "bibliography", "acknowledg")):
        return False
    return True


def normalize_page_text(text: str) -> str:
    text = text.replace("\x00", " ")
    # Soft hyphen must join across whitespace/newlines (avoid "ne glected").
    text = re.sub(r"\u00ad\s*", "", text)
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"[\u2010-\u2015\u2212]", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_masthead_or_header_sentence(sentence: str) -> bool:
    if re.search(r"\bVol\.?\s*\d+", sentence, re.I) and re.search(
        r"\b(19|20)\d{2}\b", sentence
    ):
        return True
    if re.search(r"\b(REPORTS?|CONTENTS)\b", sentence) and re.search(
        r"\b(ASHP|Am J|JAMA|N Engl)\b", sentence, re.I
    ):
        return True
    if re.match(r"^\s*(PAGE|pp?\.)\s*\d+", sentence, re.I):
        return True
    return False


def page_quality(text: str) -> float:
    if len(text) < MIN_PAGE_CHARS:
        return -1.0
    if not is_acceptable_body_text(text):
        return -1.0
    letters = sum(ch.isalpha() for ch in text)
    digits = sum(ch.isdigit() for ch in text)
    if letters < 250:
        return -1.0
    score = float(len(text)) - noise_penalty(text)
    score += min(digits, 60) * 2.0
    if RESULTS_RE.search(text):
        score += 120.0
    if METHODS_RE.search(text):
        score += 40.0
    return score


def extract_pdf_pages(path: Path, page_hint: int | None) -> tuple[list[str], int]:
    reader = PdfReader(str(path))
    total_pages = len(reader.pages)
    if page_hint and 1 <= page_hint <= total_pages:
        start = max(0, page_hint - 1)
        end = min(total_pages, start + MAX_PAGES_AROUND_HINT)
    else:
        start = 0
        end = min(total_pages, MAX_PAGES_SCAN)
    pages: list[str] = []
    for page_idx in range(start, end):
        page = reader.pages[page_idx]
        text = normalize_page_text(page.extract_text() or "")
        pages.append(text)
    return pages, start + 1


def choose_anchor_pages(pages: list[str], page_hint: int | None) -> list[int]:
    if not pages:
        return []
    ranked = sorted(
        ((page_quality(text), idx) for idx, text in enumerate(pages)),
        reverse=True,
    )
    anchors: list[int] = []
    if page_hint and 1 <= page_hint <= len(pages):
        idx = page_hint - 1
        if page_quality(pages[idx]) > 0 and is_acceptable_body_text(pages[idx]):
            anchors.append(idx)
    for score, idx in ranked:
        if score <= 0 or idx in anchors:
            continue
        if is_acceptable_body_text(pages[idx]):
            anchors.append(idx)
    return anchors


def build_excerpt_window(pages: list[str], anchor_idx: int, base_page: int) -> tuple[str, str]:
    start = anchor_idx
    end = anchor_idx
    excerpt = pages[anchor_idx]
    while len(excerpt) < MIN_EXCERPT_CHARS:
        left_ok = (
            start > 0
            and page_quality(pages[start - 1]) > 0
            and is_acceptable_body_text(pages[start - 1])
        )
        right_ok = (
            end + 1 < len(pages)
            and page_quality(pages[end + 1]) > 0
            and is_acceptable_body_text(pages[end + 1])
        )
        if not left_ok and not right_ok:
            break
        if right_ok and (not left_ok or len(pages[end + 1]) >= len(pages[start - 1])):
            end += 1
        else:
            start -= 1
        excerpt = " ".join(p for p in pages[start : end + 1] if p)
        if len(excerpt) >= MAX_EXCERPT_CHARS:
            excerpt = excerpt[:MAX_EXCERPT_CHARS].rsplit(" ", 1)[0]
            break
    if len(excerpt) > MAX_EXCERPT_CHARS:
        excerpt = excerpt[:MAX_EXCERPT_CHARS].rsplit(" ", 1)[0]
    start_page = base_page + start
    end_page = base_page + end
    pages_label = f"p. {start_page}" if start_page == end_page else f"pp. {start_page}-{end_page}"
    return excerpt.strip(), pages_label


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) >= MIN_SENTENCE_CHARS]


def choose_passage(excerpt: str) -> str | None:
    sentences = [
        s
        for s in split_sentences(excerpt)
        if is_acceptable_body_text(s, min_chars=MIN_SENTENCE_CHARS)
        and not is_masthead_or_header_sentence(s)
    ]
    if not sentences:
        return None
    scored: list[tuple[int, str]] = []
    for sentence in sentences:
        score = 0
        if RESULTS_RE.search(sentence):
            score += 4
        if re.search(r"\d", sentence):
            score += 3
        if METHODS_RE.search(sentence):
            score -= 1
        if len(ET_AL_RE.findall(sentence)) >= 1:
            score -= 6
        if len(YEAR_RE.findall(sentence)) >= 2:
            score -= 4
        if is_masthead_or_header_sentence(sentence):
            score -= 20
        score += min(len(sentence), 220) // 40
        scored.append((score, sentence))
    scored.sort(key=lambda item: (-item[0], item[1]))
    best = scored[0][1]
    return best if is_acceptable_body_text(best, min_chars=MIN_SENTENCE_CHARS) else None


def doi_safe(doi: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", doi)[:120]


def resolve_pdf_path(line_no: int, oa: dict[str, Any]) -> Path | None:
    """Resolve filed PDF for an OA row.

    Prefer explicit pdf_path, then exact ``{line}_{doi}.pdf``, then any
    ``*_{doi}.pdf``. Do **not** fall back to another DOI's file that only
    shares the line prefix (breaks batch2+ scale drafts).
    """
    output = oa.get("output") or {}
    pdf_path_raw = output.get("pdf_path") or (oa.get("meta") or {}).get("pdf_path")
    if isinstance(pdf_path_raw, str) and pdf_path_raw.strip():
        pdf_path = Path(pdf_path_raw)
        if pdf_path.exists():
            return pdf_path
    doi = normalize_doi(oa.get("doi"))
    if doi:
        safe = doi_safe(doi)
        guessed = PDF_DIR / f"{line_no:03d}_{safe}.pdf"
        if guessed.exists():
            return guessed
        by_doi = sorted(PDF_DIR.glob(f"*_{safe}.pdf"))
        if by_doi:
            return by_doi[0]
        return None
    matches = sorted(PDF_DIR.glob(f"{line_no:03d}_*.pdf"))
    return matches[0] if matches else None


def draft_row(idx: int, line_no: int, oa: dict[str, Any]) -> dict[str, Any] | None:
    output = oa.get("output") or {}
    pdf_path = resolve_pdf_path(line_no, oa)
    if not pdf_path:
        return None
    page_hint = parse_page_hint(output.get("page_hint"))
    pages, base_page = extract_pdf_pages(pdf_path, page_hint)
    if page_hint and not (base_page <= page_hint < base_page + len(pages)):
        page_hint = None
    subset_hint = (page_hint - base_page + 1) if page_hint else None
    for anchor_idx in choose_anchor_pages(pages, subset_hint):
        excerpt, pages_label = build_excerpt_window(pages, anchor_idx, base_page)
        if not is_acceptable_body_text(excerpt):
            continue
        passage = choose_passage(excerpt)
        if not passage:
            continue
        break
    else:
        return None

    doc_id = oa.get("id", f"oa-pdf-{idx:03d}")
    return {
        "id": f"bh-pdf-{idx:03d}",
        "task": "l3_grounding",
        "version": 1,
        "passage": passage,
        "source_excerpt": excerpt,
        "meta": {
            "label": "full text body draft (pdf extract)",
            "excerpt_mode": "page_window",
            "doc_id": doc_id,
            "language": "en",
            "doi": oa.get("doi"),
            "draft_status": "operator_review",
            "draft_provenance": "pdf_body_extract",
            "oa_url": oa.get("url"),
            "pdf_path": str(pdf_path.resolve()),
            "page_hint": output.get("page_hint"),
            "source_pages": pages_label,
        },
        "expect": {
            "must_parse_json": True,
            "any_claim_verdict": ["supported", "weak"],
            "quotes_must_be_substrings": True,
            "min_claims": 1,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oa", type=Path, default=OA_PILOT)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    seen_doi: set[str] = set()
    for line_no, oa in enumerate(read_jsonl(args.oa), start=1):
        if len(rows) >= args.limit:
            break
        doi = normalize_doi(oa.get("doi"))
        if not doi or doi in seen_doi:
            continue
        draft = draft_row(len(rows) + 1, line_no, oa)
        if not draft:
            continue
        seen_doi.add(doi)
        rows.append(draft)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "draft_rows": len(rows),
                "out": str(args.out),
                "note": "Operator review required — PDF body excerpts are draft quality and may need page/window cleanup",
            },
            indent=2,
        )
    )
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
