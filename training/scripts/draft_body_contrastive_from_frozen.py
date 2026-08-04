#!/usr/bin/env python3
"""Draft contrastive (false-supported) body holdout from frozen_v1 support rows.

Each output row keeps a real PDF body excerpt but pairs it with a passage that
must NOT be labeled supported (overclaim, polarity flip, or cross-doc mismatch).

Usage (from training/):
  python scripts/draft_body_contrastive_from_frozen.py
  python scripts/draft_body_contrastive_from_frozen.py --limit 42
"""

from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from corpus_utils import DATA_DIR, read_jsonl

DEFAULT_IN = DATA_DIR / "eval_holdout_body_scale_frozen_v4.jsonl"
DEFAULT_OUT = DATA_DIR / "eval_holdout_body_contrastive_draft_v2.jsonl"

# Only mutate claim-salient numbers — bare citation indices (e.g. "PBE 27")
# are too weak and still leave a supportable claim.
PERCENT_RE = re.compile(
    r"(?<![A-Za-z0-9./-])(\d+(?:\.\d+)?)(\s*%)(?![A-Za-z0-9./-])"
)
SAMPLE_N_RE = re.compile(
    r"\b([Nn]\s*=\s*|K\s*=\s*|n\s+)(\d+)(?!\d)"
)
YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")

# Applied in order; first successful substitution wins for polarity family.
POLARITY_SWAPS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bincreased\b", re.I), "decreased"),
    (re.compile(r"\bdecreased\b", re.I), "increased"),
    (re.compile(r"\bhigher\b", re.I), "lower"),
    (re.compile(r"\blower\b", re.I), "higher"),
    (re.compile(r"\bimproved\b", re.I), "worsened"),
    (re.compile(r"\bworsened\b", re.I), "improved"),
    (re.compile(r"\bsignificant\b", re.I), "nonsignificant"),
    (re.compile(r"\bnonsignificant\b", re.I), "significant"),
    (re.compile(r"\bcan be neglected\b", re.I), "cannot be neglected"),
    (re.compile(r"\bcannot be neglected\b", re.I), "can be neglected"),
    (re.compile(r"\bis important\b", re.I), "is unimportant"),
    (re.compile(r"\bwas observed\b", re.I), "was not observed"),
    (re.compile(r"\bshowed that\b", re.I), "failed to show that"),
    (re.compile(r"\bhighly consistent\b", re.I), "highly inconsistent"),
    (re.compile(r"\bagreement with experiment\b", re.I), "disagreement with experiment"),
]


def mutate_number(passage: str, *, factor: float = 10.0) -> str | None:
    """Inflate a claim-salient number (%, n=/K=, or year); else None."""
    m = PERCENT_RE.search(passage)
    if m:
        raw = m.group(1)
        try:
            val = float(raw)
        except ValueError:
            val = 0.0
        if val > 0:
            new_val = min(val * factor, 99.0) if val < 50 else max(val / factor, 0.1)
            rendered = f"{new_val:.4g}" if "." in raw else str(int(round(new_val)))
            return passage[: m.start(1)] + rendered + passage[m.end(1) :]

    m = SAMPLE_N_RE.search(passage)
    if m:
        raw = m.group(2)
        try:
            val = int(raw)
        except ValueError:
            val = 0
        if val > 0:
            new_val = max(val * int(factor), val + 50)
            return passage[: m.start(2)] + str(new_val) + passage[m.end(2) :]

    m = YEAR_RE.search(passage)
    if m:
        year = int(m.group(1))
        # Shift far enough that chronological claims clearly diverge.
        new_year = year + 20 if year < 2010 else year - 20
        return passage[: m.start(1)] + str(new_year) + passage[m.end(1) :]

    return None


def flip_polarity(passage: str) -> str | None:
    for pat, repl in POLARITY_SWAPS:
        if pat.search(passage):
            return pat.sub(repl, passage, count=1)
    return None


def build_contrastive_row(
    *,
    idx: int,
    base: dict[str, Any],
    kind: str,
    passage: str,
    source_excerpt: str,
    eval_category: str,
    any_verdicts: list[str],
    id_prefix: str = "bh-fs-v2",
    draft_provenance: str = "freeze_v4_contrastive",
) -> dict[str, Any]:
    meta = deepcopy(base.get("meta") or {})
    meta["draft_status"] = "contrastive_draft"
    meta["draft_provenance"] = draft_provenance
    meta["contrastive_kind"] = kind
    meta["eval_category"] = eval_category
    meta["parent_id"] = base.get("id")
    meta["label"] = "full text body holdout (contrastive false-supported)"
    return {
        "id": f"{id_prefix}-{idx:03d}",
        "task": "l3_grounding",
        "version": 1,
        "passage": passage,
        "source_excerpt": source_excerpt,
        "meta": meta,
        "expect": {
            "must_parse_json": True,
            "min_claims": 1,
            "forbidden_claim_verdict": ["supported"],
            "any_claim_verdict": any_verdicts,
        },
    }


def choose_contrastive(
    *,
    idx: int,
    base: dict[str, Any],
    all_rows: list[dict[str, Any]],
    id_prefix: str = "bh-fs-v2",
    draft_provenance: str = "freeze_v4_contrastive",
) -> dict[str, Any]:
    passage = str(base.get("passage") or "")
    excerpt = str(base.get("source_excerpt") or "")

    numeric = mutate_number(passage)
    if numeric:
        return build_contrastive_row(
            idx=idx,
            base=base,
            kind="numeric_overclaim",
            passage=numeric,
            source_excerpt=excerpt,
            eval_category="contradicted",
            any_verdicts=["contradicted", "weak", "not_in_source"],
            id_prefix=id_prefix,
            draft_provenance=draft_provenance,
        )

    flipped = flip_polarity(passage)
    if flipped:
        return build_contrastive_row(
            idx=idx,
            base=base,
            kind="polarity_flip",
            passage=flipped,
            source_excerpt=excerpt,
            eval_category="contradicted",
            any_verdicts=["contradicted", "weak", "not_in_source"],
            id_prefix=id_prefix,
            draft_provenance=draft_provenance,
        )

    partner = all_rows[(idx - 1 + max(1, len(all_rows) // 2)) % len(all_rows)]
    return build_contrastive_row(
        idx=idx,
        base=base,
        kind="cross_doc",
        passage=passage,
        source_excerpt=str(partner.get("source_excerpt") or ""),
        eval_category="not_in_source",
        any_verdicts=["not_in_source", "insufficient_evidence", "weak", "contradicted"],
        id_prefix=id_prefix,
        draft_provenance=draft_provenance,
    )


def draft_contrastive(
    rows: list[dict[str, Any]],
    *,
    limit: int | None = None,
    id_prefix: str = "bh-fs-v2",
    draft_provenance: str = "freeze_v4_contrastive",
) -> list[dict[str, Any]]:
    selected = rows[:limit] if limit is not None else rows
    out: list[dict[str, Any]] = []
    for i, base in enumerate(selected, start=1):
        out.append(
            choose_contrastive(
                idx=i,
                base=base,
                all_rows=rows,
                id_prefix=id_prefix,
                draft_provenance=draft_provenance,
            )
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="infile", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--id-prefix", default="bh-fs-v2")
    parser.add_argument("--provenance", default="freeze_v4_contrastive")
    args = parser.parse_args()

    rows = read_jsonl(args.infile)
    drafted = draft_contrastive(
        rows,
        limit=args.limit,
        id_prefix=args.id_prefix,
        draft_provenance=args.provenance,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in drafted:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    kinds: dict[str, int] = {}
    for row in drafted:
        k = (row.get("meta") or {}).get("contrastive_kind", "?")
        kinds[k] = kinds.get(k, 0) + 1

    print(
        json.dumps(
            {
                "in": str(args.infile),
                "out": str(args.out),
                "rows": len(drafted),
                "kinds": kinds,
            },
            indent=2,
        )
    )
    return 0 if drafted else 1


if __name__ == "__main__":
    raise SystemExit(main())
