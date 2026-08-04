#!/usr/bin/env python3
"""Draft multi-claim body holdout rows from an existing freeze.

For each freeze row whose excerpt has ≥2 acceptable sentences, emit a companion
row whose passage joins the two best sentences and expect.min_claims=2.

Usage (from training/):
  python scripts/draft_body_multiclaim_from_freeze.py
  python scripts/draft_body_multiclaim_from_freeze.py --limit 120 --out data/eval_holdout_body_multiclaim_draft.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from corpus_utils import DATA_DIR, read_jsonl
from draft_body_holdout_from_pdfs import (
    MIN_SENTENCE_CHARS,
    RESULTS_RE,
    METHODS_RE,
    ET_AL_RE,
    YEAR_RE,
    is_acceptable_body_text,
    is_masthead_or_header_sentence,
    split_sentences,
)

DEFAULT_IN = DATA_DIR / "eval_holdout_body_scale_frozen_v4.jsonl"
DEFAULT_OUT = DATA_DIR / "eval_holdout_body_multiclaim_draft.jsonl"
MAX_PASSAGE_CHARS = 520
MIN_SENTENCE_SCORE = 2

# Leading OCR / citation / section-header glue that makes bad claim seeds.
JUNK_LEAD_RE = re.compile(
    r"^(?:"
    r"XX\b|"
    r"[A-Z]{1,3}\s+(?:Introduction|Results|Methods|Discussion|Background)\b|"
    r"(?:Introduction|Background|Methods?|Discussion)\s+(?:showed|found|that)\b|"
    r"\d+(?:\s*[,;]\s*\d+)*(?:\s*[-–]\s*\d+)?\s+[A-Z]"
    r")",
    re.I,
)
GENOTYPE_NOISE_RE = re.compile(
    r"\b(?:lacIq|hsdR|Dlac|Drha|BW\d{4,}|K\s*5\s*=\s*\d)\b",
    re.I,
)
SECTION_ONLY_RE = re.compile(
    r"^\s*(?:results?|methods?|introduction|discussion|background)\s*$",
    re.I,
)


def clean_sentence(sentence: str) -> str:
    s = sentence.strip()
    s = re.sub(r"^\s*(?:RESULTS?|METHODS?)\s+", "", s, flags=re.I)
    return s.strip()


def is_junk_claim_sentence(sentence: str) -> bool:
    if is_masthead_or_header_sentence(sentence):
        return True
    if SECTION_ONLY_RE.match(sentence):
        return True
    if JUNK_LEAD_RE.match(sentence):
        return True
    if GENOTYPE_NOISE_RE.search(sentence):
        return True
    letters = sum(ch.isalpha() for ch in sentence)
    if letters / max(len(sentence), 1) < 0.55:
        return True
    # Citation-heavy openers like "3,14-24 However..."
    if re.match(r"^\d", sentence) and not re.match(r"^\d{4}\b", sentence):
        return True
    return False


def score_sentence(sentence: str) -> int:
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
    if is_junk_claim_sentence(sentence):
        score -= 40
    score += min(len(sentence), 220) // 40
    return score


def candidate_sentences(excerpt: str) -> list[str]:
    scored: list[tuple[int, str]] = []
    for raw in split_sentences(excerpt):
        sentence = clean_sentence(raw)
        if len(sentence) < MIN_SENTENCE_CHARS:
            continue
        if not is_acceptable_body_text(sentence, min_chars=MIN_SENTENCE_CHARS):
            continue
        # Reject OCR-glued leads on the raw split; genotype/letter checks on cleaned.
        if JUNK_LEAD_RE.match(raw.strip()) or is_junk_claim_sentence(sentence):
            continue
        score = score_sentence(sentence)
        if score < MIN_SENTENCE_SCORE:
            continue
        scored.append((score, sentence))
    scored.sort(key=lambda item: (-item[0], item[1]))
    # Deduplicate near-identical starts
    out: list[str] = []
    seen: set[str] = set()
    for _, sentence in scored:
        key = sentence[:80].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(sentence)
    return out


def pick_sentence_pair(sentences: list[str]) -> tuple[str, str] | None:
    """Pick two distinct sentences; prefer at least one results-like."""
    if len(sentences) < 2:
        return None
    for i, a in enumerate(sentences):
        for b in sentences[i + 1 :]:
            if a == b:
                continue
            if a in b or b in a:
                continue
            if RESULTS_RE.search(a) or RESULTS_RE.search(b):
                return a, b
    # Fallback: top two if both scored into the candidate list
    a, b = sentences[0], sentences[1]
    if a != b and a not in b and b not in a:
        return a, b
    return None


def build_multi_passage(sentences: list[str]) -> str | None:
    pair = pick_sentence_pair(sentences)
    if not pair:
        return None
    a, b = pair

    def clip(s: str, n: int = 240) -> str:
        s = s.strip()
        if len(s) <= n:
            return s
        cut = s[:n].rsplit(" ", 1)[0]
        return cut.rstrip(",;:") + "…"

    passage = f"{clip(a)} {clip(b)}"
    if len(passage) > MAX_PASSAGE_CHARS:
        passage = passage[:MAX_PASSAGE_CHARS].rsplit(" ", 1)[0] + "…"
    if not is_acceptable_body_text(passage, min_chars=MIN_SENTENCE_CHARS * 2):
        return None
    # Both clips must remain quoteable from the joined passage's parent excerpt
    # (full sentences are taken from excerpt; clips may end with ellipsis).
    return passage


def draft_multiclaim_row(idx: int, base: dict[str, Any]) -> dict[str, Any] | None:
    excerpt = str(base.get("source_excerpt") or "")
    sentences = candidate_sentences(excerpt)
    passage = build_multi_passage(sentences)
    if not passage:
        return None
    parent_passage = str(base.get("passage") or "").strip()
    if parent_passage and passage == parent_passage:
        return None

    meta = deepcopy(base.get("meta") or {})
    meta["draft_status"] = "multiclaim_draft"
    meta["draft_provenance"] = "freeze_v4_multiclaim"
    meta["eval_category"] = "multi_claim"
    meta["row_type"] = "multi_claim"
    meta["parent_id"] = base.get("id")
    meta["label"] = "full text body holdout (multi-claim draft)"
    # Keep scale_source from parent for rollups.
    return {
        "id": f"bh-mc-{idx:03d}",
        "task": "l3_grounding",
        "version": 1,
        "passage": passage,
        "source_excerpt": excerpt,
        "meta": meta,
        "expect": {
            "must_parse_json": True,
            "any_claim_verdict": ["supported", "weak"],
            "quotes_must_be_substrings": True,
            "min_claims": 2,
        },
    }


def draft_multiclaim(
    rows: list[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for base in rows:
        if limit is not None and len(out) >= limit:
            break
        row = draft_multiclaim_row(len(out) + 1, base)
        if row:
            out.append(row)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="infile", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    bases = read_jsonl(args.infile)
    drafted = draft_multiclaim(bases, limit=args.limit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in drafted:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    claim_floor = sum(int((r.get("expect") or {}).get("min_claims") or 1) for r in drafted)
    base_floor = sum(int((r.get("expect") or {}).get("min_claims") or 1) for r in bases)
    print(
        json.dumps(
            {
                "in": str(args.infile),
                "out": str(args.out),
                "base_rows": len(bases),
                "multiclaim_rows": len(drafted),
                "base_min_claim_floor": base_floor,
                "multiclaim_min_claim_floor": claim_floor,
                "combined_min_claim_floor": base_floor + claim_floor,
            },
            indent=2,
        )
    )
    return 0 if drafted else 1


if __name__ == "__main__":
    raise SystemExit(main())
