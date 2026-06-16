#!/usr/bin/env python3
"""
Build the v1.x Sanad QLoRA train file (default: v1.6).

Merges the v1.4a base rows with a targeted, decontaminated boost set
(paraphrase-supported, quote-fidelity, contrastive not_in_source, weak,
insufficient_evidence, multi-claim partial). Keeps the ~850 row budget
(OUROBOROS_CONTEXT §11) and HARD-FAILS on train/eval contamination.

Usage:
  python scripts/prepare_v15_train.py --base data/l3_grounding_train_v14a.jsonl
  python scripts/prepare_v15_train.py --boost data/l3_grounding_v16_boost.jsonl \
      --out data/l3_grounding_train_v16.jsonl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from check_contamination import contaminating_rows  # noqa: E402
from corpus_utils import read_jsonl, write_jsonl  # noqa: E402
from validate_dataset import validate_l3_record  # noqa: E402

DEFAULT_BASE = TRAINING_DIR / "data" / "l3_grounding_train_v14a.jsonl"
FALLBACK_BASE = TRAINING_DIR / "data" / "l3_grounding_train.jsonl"
BOOST_FILE = TRAINING_DIR / "data" / "l3_grounding_v16_boost.jsonl"
DEFAULT_OUT = TRAINING_DIR / "data" / "l3_grounding_train_v16.jsonl"
MAX_ROWS = 850

# Any base row whose id starts with a boost-version prefix is replaced by the boost set.
BOOST_REPLACE_PREFIXES = ("l3-v15-", "l3-v16-", "l3-v17-", "l3-v18-", "l3-v19-")


def row_valid(row: dict, line_no: int) -> bool:
    errors: list[str] = []
    validate_l3_record(row, line_no, errors)
    return len(errors) == 0


def _first_verdict(row: dict) -> str:
    claims = row.get("output", {}).get("claims", [])
    if claims and isinstance(claims[0], dict):
        return claims[0].get("verdict", "?")
    return "?"


def _trim_overrepresented(rows: list[dict], trim: int) -> list[dict]:
    """Drop `trim` rows from the most over-represented first-claim verdict.

    Preserves order otherwise. Avoids discarding scarce verdicts
    (contradicted, insufficient_evidence) that the model still needs.
    """
    if trim <= 0:
        return rows
    counts: dict[str, int] = {}
    for r in rows:
        counts[_first_verdict(r)] = counts.get(_first_verdict(r), 0) + 1
    dropped = 0
    out: list[dict] = []
    # Trim from the single largest bucket only, from the tail of that bucket.
    target = max(counts, key=lambda k: counts[k]) if counts else None
    # Walk from the end so we drop the most recently added rows of the target.
    keep_flags = [True] * len(rows)
    for i in range(len(rows) - 1, -1, -1):
        if dropped >= trim:
            break
        if _first_verdict(rows[i]) == target:
            keep_flags[i] = False
            dropped += 1
    out = [r for r, keep in zip(rows, keep_flags) if keep]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare v1.5 Sanad train JSONL")
    parser.add_argument("--base", type=Path, default=None, help="v14a or full train JSONL")
    parser.add_argument(
        "--boost",
        type=Path,
        nargs="+",
        default=[BOOST_FILE],
        help="One or more boost JSONL files (merged in order)",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-rows", type=int, default=MAX_ROWS)
    args = parser.parse_args()

    base_path = args.base
    if base_path is None:
        base_path = DEFAULT_BASE if DEFAULT_BASE.exists() else FALLBACK_BASE

    if not base_path.exists():
        print(
            f"Base train file not found: {base_path}\n"
            "Generate with generate_l3_from_corpus.py + prepare_v14_train.py first, "
            "or pass --base explicitly.",
            file=sys.stderr,
        )
        return 1

    missing = [p for p in args.boost if not p.exists()]
    if missing:
        print(f"Boost file(s) not found: {', '.join(map(str, missing))}", file=sys.stderr)
        return 1

    base_rows = read_jsonl(base_path)
    boost_rows: list[dict] = []
    for boost_path in args.boost:
        boost_rows.extend(read_jsonl(boost_path))

    boost_ids = {r.get("id") for r in boost_rows}
    kept_base = [
        r
        for r in base_rows
        if not any(str(r.get("id", "")).startswith(p) for p in BOOST_REPLACE_PREFIXES)
        and r.get("id") not in boost_ids
    ]

    merged = kept_base + boost_rows
    if len(merged) > args.max_rows:
        # Keep all boost rows. Trim from the most over-represented base verdict
        # (usually `supported`) so we hold budget without losing scarce verdict
        # signal (contradicted / not_in_source) or worsening supported skew.
        trim = len(merged) - args.max_rows
        kept_base = _trim_overrepresented(kept_base, trim)
        merged = kept_base + boost_rows

    valid: list[dict] = []
    for i, row in enumerate(merged, start=1):
        if row_valid(row, i):
            valid.append(row)

    # HARD GATE: never ship a train file that reuses eval passages/excerpts.
    contam = contaminating_rows(valid)
    if contam:
        print(
            f"ABORT: {len(contam)} train row(s) overlap the eval harness "
            "(train/eval contamination). Fix the boost set before building:",
            file=sys.stderr,
        )
        for rid, pm, em in contam:
            print(f"  CONTAM {rid}: passage~{pm}  excerpt~{em}", file=sys.stderr)
        return 2

    write_jsonl(args.out, valid)

    from collections import Counter

    verdicts = Counter(_first_verdict(r) for r in valid)
    boost_types = Counter(str(r.get("meta", {}).get("row_type", "base")) for r in boost_rows)

    print(f"Base: {base_path} ({len(base_rows)} rows)")
    boost_names = ", ".join(p.name for p in args.boost)
    print(f"Boost: {boost_names} ({len(boost_rows)} rows: {dict(boost_types)})")
    print(f"Output: {args.out} ({len(valid)} rows, max {args.max_rows})")
    print(f"First-claim verdict mix: {dict(verdicts)}")
    print("Contamination: 0 (gate passed)")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
