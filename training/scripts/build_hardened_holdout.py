#!/usr/bin/env python3
"""
Build hardened holdout: merge legacy 45-row holdout + extension rows.

Writes data/eval_holdout_90.jsonl (canonical Tier 2 holdout for A/B pilot).

Usage:
  python scripts/build_hardened_holdout.py
  python scripts/build_hardened_holdout.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA = SCRIPT_DIR.parent / "data"

LEGACY = DATA / "eval_holdout_45.jsonl"
EXTENSION = DATA / "eval_holdout_extension_45.jsonl"
OUT = DATA / "eval_holdout_90.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not row.get("id"):
                raise ValueError(f"{path}:{line_no} missing id")
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Build eval_holdout_90.jsonl")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate inputs and print stats without writing",
    )
    args = parser.parse_args()

    if not LEGACY.exists():
        print(f"Missing {LEGACY}", file=sys.stderr)
        return 1
    if not EXTENSION.exists():
        print(f"Missing {EXTENSION}", file=sys.stderr)
        return 1

    legacy = load_jsonl(LEGACY)
    extension = load_jsonl(EXTENSION)
    seen: set[str] = set()
    merged: list[dict] = []

    for row in legacy + extension:
        rid = row["id"]
        if rid in seen:
            print(f"Duplicate id: {rid}", file=sys.stderr)
            return 1
        seen.add(rid)
        merged.append(row)

    by_cat: dict[str, int] = {}
    for row in merged:
        cat = row.get("meta", {}).get("eval_category", "unknown")
        by_cat[cat] = by_cat.get(cat, 0) + 1

    print(f"Legacy rows:    {len(legacy)}")
    print(f"Extension rows: {len(extension)}")
    print(f"Merged total:   {len(merged)}")
    print("Category mix:")
    for cat, n in sorted(by_cat.items()):
        print(f"  {cat}: {n}")

    if args.check:
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for row in merged:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
