#!/usr/bin/env python3
"""
Deterministic structural audit for l3_grounding training rows.

Catches truncation collisions, missing quotes, and prefix-template regressions
before human review or Vast training.

Usage:
  python scripts/audit_l3_labels.py data/l3_grounding_train.jsonl
  python scripts/audit_l3_labels.py data/l3_grounding_train.jsonl --json outputs/l3_audit_report.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from corpus_utils import read_jsonl  # noqa: E402
from generate_l3_from_corpus import (  # noqa: E402
    CANONICAL_CLAIM_KEYS,
    HEDGE_RE,
    VISIBLE_CLAIM_CHARS,
    flip_number_in_text,
    numeric_alignment_ok,
    semantic_overlap_ok,
    strip_hedges,
)
from validate_dataset import is_substring_quote, normalize_ws  # noqa: E402

BAD_PREFIXES = (
    "This study reports that",
    "This definitively proves that",
    "The evidence shows that",
    "lunar phases and stock market returns",
)


def audit_row(record: dict) -> list[str]:
    issues: list[str] = []
    rid = record.get("id", "?")
    passage = record.get("passage", "")
    excerpt = record.get("source_excerpt", "")
    claims = record.get("output", {}).get("claims", [])
    if not claims:
        return [f"{rid}: no claims"]
    excerpt_mode = record.get("meta", {}).get("excerpt_mode", "full")

    if "-multi" in rid or len(claims) >= 2:
        if len(claims) < 2:
            issues.append(f"{rid}: multi row needs at least 2 claims")

    for ci, claim_obj in enumerate(claims):
        verdict = claim_obj.get("verdict", "")
        claim = str(claim_obj.get("claim", ""))
        quotes = claim_obj.get("sourceQuotes") or []
        rationale = claim_obj.get("rationale") or []
        suffix = f" claims[{ci}]" if len(claims) > 1 else ""

        for bad in BAD_PREFIXES:
            if bad.lower() in passage.lower() and verdict != "not_in_source":
                issues.append(f"{rid}{suffix}: forbidden template prefix in passage ({bad!r})")

        if verdict == "supported":
            if not quotes:
                issues.append(f"{rid}{suffix}: supported missing sourceQuotes")
            else:
                q = quotes[0]
                if not is_substring_quote(q, excerpt):
                    issues.append(f"{rid}{suffix}: supported quote not in source_excerpt")
                if excerpt_mode == "sentence" and len(claims) == 1:
                    if normalize_ws(q) != normalize_ws(excerpt) and not is_substring_quote(q, excerpt):
                        issues.append(f"{rid}{suffix}: sentence excerpt_mode but quote != excerpt")
                if claim[:VISIBLE_CLAIM_CHARS] != q[:VISIBLE_CLAIM_CHARS] and claim not in q:
                    if not numeric_alignment_ok(claim, q) and not semantic_overlap_ok(claim, q):
                        issues.append(f"{rid}{suffix}: supported claim diverges from quote without alignment")
            if ("-sanad-" in rid or "-sanadsem-" in rid) and not rationale:
                issues.append(f"{rid}{suffix}: sanad supported missing rationale")

        if verdict == "contradicted":
            if not quotes:
                issues.append(f"{rid}{suffix}: contradicted missing sourceQuotes")
            elif quotes:
                q = quotes[0]
                if claim[:VISIBLE_CLAIM_CHARS] == q[:VISIBLE_CLAIM_CHARS]:
                    issues.append(
                        f"{rid}{suffix}: contradicted claim/quote identical in first {VISIBLE_CLAIM_CHARS} chars"
                    )
                flip = flip_number_in_text(q, max_offset=len(q))
                if flip and flip[1][:VISIBLE_CLAIM_CHARS] == q[:VISIBLE_CLAIM_CHARS]:
                    issues.append(f"{rid}{suffix}: numeric flip not visible in claim prefix")

        if verdict == "weak":
            if not quotes:
                issues.append(f"{rid}{suffix}: weak missing sourceQuotes")
            else:
                q = quotes[0]
                if claim[:VISIBLE_CLAIM_CHARS] == q[:VISIBLE_CLAIM_CHARS]:
                    issues.append(
                        f"{rid}{suffix}: weak claim/quote identical in first {VISIBLE_CLAIM_CHARS} chars"
                    )
                if not HEDGE_RE.search(q):
                    issues.append(f"{rid}{suffix}: weak source quote has no hedge words")
                strengthened = strip_hedges(q)
                if strengthened[:VISIBLE_CLAIM_CHARS] == q[:VISIBLE_CLAIM_CHARS]:
                    issues.append(f"{rid}{suffix}: hedge removal not visible in claim prefix")
                if numeric_alignment_ok(claim, q):
                    issues.append(f"{rid}{suffix}: weak row has numeric alignment (should be supported)")

        if verdict == "not_in_source":
            if quotes:
                for q in quotes:
                    if is_substring_quote(str(q), excerpt):
                        issues.append(f"{rid}{suffix}: not_in_source but quote found in excerpt")

        if not claim.strip():
            issues.append(f"{rid}{suffix}: empty claim text")

        keys = list(claim_obj.keys())
        if keys != list(CANONICAL_CLAIM_KEYS):
            issues.append(
                f"{rid}{suffix}: claim keys out of order (expected {CANONICAL_CLAIM_KEYS}, got {tuple(keys)})"
            )
        elif keys[-1] != "hasNumericClaim":
            issues.append(f"{rid}{suffix}: hasNumericClaim must be last claim key")

    return issues


def RESULTS_IN_METHODS_OK(q: str, excerpt: str) -> bool:
    return False  # unused; kept for future expansion


def main() -> int:
    parser = argparse.ArgumentParser(description="Structural audit of l3_grounding train JSONL")
    parser.add_argument("train_file", type=Path)
    parser.add_argument("--json", type=Path, default=None, help="Write machine-readable report")
    args = parser.parse_args()

    rows = read_jsonl(args.train_file)
    all_issues: list[str] = []
    by_verdict: dict[str, int] = {}
    for r in rows:
        v = r.get("output", {}).get("claims", [{}])[0].get("verdict", "?")
        by_verdict[v] = by_verdict.get(v, 0) + 1
        all_issues.extend(audit_row(r))

    report = {
        "file": str(args.train_file),
        "rows": len(rows),
        "verdict_counts": by_verdict,
        "issue_count": len(all_issues),
        "issues": all_issues,
    }

    print(f"Audited {len(rows)} row(s)")
    print(f"Verdict mix: {by_verdict}")
    if all_issues:
        print(f"\nFAIL: {len(all_issues)} structural issue(s):")
        for issue in all_issues[:50]:
            print(f"  - {issue}")
        if len(all_issues) > 50:
            print(f"  ... and {len(all_issues) - 50} more")
    else:
        print("PASS: no structural issues detected")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {args.json}")

    return 1 if all_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
