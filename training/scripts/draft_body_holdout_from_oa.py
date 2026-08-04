#!/usr/bin/env python3
"""Draft Tier 3 body holdout rows from OA pilot + enriched corpus abstracts (W6).

Proxy rows use abstract paragraphs until app PDF extract fills real body excerpts.
Operator must review before promoting to frozen holdout.

Usage (from training/):
  python scripts/draft_body_holdout_from_oa.py
  python scripts/draft_body_holdout_from_oa.py --limit 25 --out data/eval_holdout_body_draft.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from corpus_utils import DATA_DIR, normalize_doi, read_jsonl  # noqa: E402

OA_PILOT = DATA_DIR / "source_pdf_extract_pilot.jsonl"
CORPUS = DATA_DIR / "paper_corpus_enriched.jsonl"
DEFAULT_OUT = DATA_DIR / "eval_holdout_body_draft.jsonl"
MIN_ABSTRACT = 180


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) >= 40]


def corpus_by_doi(path: Path) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for row in read_jsonl(path):
        doi = normalize_doi(row.get("doi"))
        if doi:
            index[doi] = row
    return index


def draft_row(idx: int, paper: dict, oa: dict) -> dict | None:
    abstract = (paper.get("abstract") or "").strip()
    if len(abstract) < MIN_ABSTRACT:
        return None
    sents = sentences(abstract)
    if len(sents) < 2:
        return None
    passage = sents[1]
    if len(passage) > 520:
        passage = passage[:517] + "..."
    doc_id = oa.get("id", f"oa-draft-{idx:03d}")
    return {
        "id": f"bh-draft-{idx:03d}",
        "task": "l3_grounding",
        "version": 1,
        "passage": passage,
        "source_excerpt": abstract,
        "meta": {
            "label": "full text body draft (abstract proxy)",
            "excerpt_mode": "paragraph",
            "doc_id": doc_id,
            "language": "en",
            "doi": oa.get("doi"),
            "draft_status": "operator_review",
            "draft_provenance": "abstract_proxy_until_pdf_extract",
            "oa_url": oa.get("url"),
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
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    by_doi = corpus_by_doi(args.corpus)
    rows: list[dict] = []
    for oa in read_jsonl(args.oa):
        if len(rows) >= args.limit:
            break
        doi = normalize_doi(oa.get("doi"))
        if not doi or doi not in by_doi:
            continue
        row = draft_row(len(rows) + 1, by_doi[doi], oa)
        if row:
            rows.append(row)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps({
        "draft_rows": len(rows),
        "out": str(args.out),
        "note": "Operator review required — replace abstract proxy with PDF body excerpts before freezing holdout",
    }, indent=2))
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
