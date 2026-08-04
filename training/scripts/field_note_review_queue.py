#!/usr/bin/env python3
"""Emit a prioritized human-review queue from masdar-lite field notes.

Usage (from training/):
  python scripts/field_note_review_queue.py
  python scripts/field_note_review_queue.py --write

Does not invent labels — only ranks rows for operator adjudication.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

TRAINING = Path(__file__).resolve().parents[1]
DEFAULT_CSV = TRAINING / "field-notes" / "masdar-lite-jul13-2026-07-13" / "grounding-calls.csv"
OUT_CSV = TRAINING / "field-notes" / "masdar-lite-jul13-2026-07-13" / "review-queue.csv"


def priority(row: dict[str, str]) -> tuple[int, str]:
    flags = row.get("review_flags") or ""
    actual = (row.get("actual_overall_verdict") or "").strip()
    if "parse_error" in flags or actual == "PARSE_ERROR":
        return (0, "parse_error")
    if "echo_false_positive" in flags and actual == "support":
        return (1, "echo_support")
    if "echo_false_positive" in flags:
        return (2, "echo_other")
    if actual == "support":
        return (3, "support_review")
    if "truncated_passage" in flags:
        return (4, "truncated")
    return (5, "other")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--write", action="store_true", help=f"Write {OUT_CSV.name}")
    args = parser.parse_args()

    rows = list(csv.DictReader(args.csv.open(encoding="utf-8")))
    labeled = sum(1 for r in rows if (r.get("expected_overall_verdict") or "").strip())
    ranked = sorted(rows, key=lambda r: (priority(r)[0], r.get("id") or ""))

    print(f"calls={len(rows)} human_labels={labeled}")
    print("priority_buckets:")
    buckets: dict[str, int] = {}
    for r in ranked:
        _, name = priority(r)
        buckets[name] = buckets.get(name, 0) + 1
    for k, v in sorted(buckets.items(), key=lambda kv: kv[0]):
        print(f"  {k}: {v}")

    print("\nTop 15 review ids:")
    for r in ranked[:15]:
        _, bucket = priority(r)
        print(
            f"  {r.get('id')}\tactual={r.get('actual_overall_verdict')}\t"
            f"bucket={bucket}\tflags={r.get('review_flags')}"
        )

    if args.write:
        fieldnames = list(ranked[0].keys()) + ["review_priority", "review_bucket"]
        # dedupe if already present
        fieldnames = list(dict.fromkeys(fieldnames))
        with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in ranked:
                rank, bucket = priority(r)
                out = dict(r)
                out["review_priority"] = str(rank)
                out["review_bucket"] = bucket
                w.writerow(out)
        print(f"\nWrote {OUT_CSV}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
