#!/usr/bin/env python3
"""Export human-adjudicated masdar-lite field notes to boost JSONL.

Usage (from training/):
  python scripts/apply_masdar_lite_top_labels.py   # if labels pending in script
  python scripts/export_field_note_boost_jsonl.py

Never exports rows without expected_overall_verdict. Never writes to holdout files.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING = SCRIPT_DIR.parent
FIELD_DIR = TRAINING / "field-notes" / "masdar-lite-jul13-2026-07-13"
CALLS = FIELD_DIR / "grounding-calls.csv"
NOTES = FIELD_DIR / "grounding-field-notes.jsonl"
DEFAULT_OUT = TRAINING / "data" / "l3_grounding_masdar_lite_boost.jsonl"

VERDICT_MAP = {
    "support": "support",
    "weak": "weak",
    "unrelated": "unrelated",
    "insufficient_evidence": "insufficient_evidence",
    "insufficient": "insufficient_evidence",
    "parse_error": "insufficient_evidence",
}

OVERALL_TO_CLAIM = {
    "support": "weak",  # overall support; claim quotes deferred (field-note echo lesson)
    "weak": "weak",
    "unrelated": "not_in_source",
    "insufficient_evidence": "insufficient_evidence",
}


def boost_output(passage: str, overall: str, notes: str) -> dict:
    """Synthetic claim row — human label is overallVerdict; do not ship model echo quotes."""
    passage_snip = (passage or "").strip()[:240] or "field note passage"
    claim_verdict = OVERALL_TO_CLAIM.get(overall, "insufficient_evidence")
    claim = {
        "claim": passage_snip,
        "verdict": claim_verdict,
        "sourceQuotes": [],
        "rationale": [notes or "human-adjudicated field note"],
    }
    return {"claims": [claim], "overallVerdict": overall}


def load_labels() -> dict[str, tuple[str, str]]:
    labels: dict[str, tuple[str, str]] = {}
    with CALLS.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            verdict = (row.get("expected_overall_verdict") or "").strip()
            if not verdict:
                continue
            labels[row["id"]] = (verdict, (row.get("reviewer_notes") or "").strip())
    return labels


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    labels = load_labels()
    if not labels:
        print("No human labels found in grounding-calls.csv", file=sys.stderr)
        return 1

    exported = 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with NOTES.open(encoding="utf-8") as src, args.out.open("w", encoding="utf-8") as dst:
        for line in src:
            row = json.loads(line)
            row_id = row.get("id")
            if row_id not in labels:
                continue
            verdict, notes = labels[row_id]
            mapped = VERDICT_MAP.get(verdict.lower(), verdict)
            boost = {
                "id": f"boost-{row_id}",
                "task": "l3_grounding",
                "version": 1,
                "passage": row.get("passage", ""),
                "source_excerpt": row.get("source_excerpt", ""),
                "meta": {
                    **(row.get("meta") or {}),
                    "label_provenance": "human-adjudicated",
                    "prompt_contract": "sanad-grounding-v1",
                    "field_note_id": row_id,
                    "reviewer_notes": notes or None,
                },
                "output": boost_output(row.get("passage", ""), mapped, notes),
            }
            dst.write(json.dumps(boost, ensure_ascii=False) + "\n")
            exported += 1

    print(f"exported={exported} labels={len(labels)} out={args.out}")
    return 0 if exported else 1


if __name__ == "__main__":
    raise SystemExit(main())
