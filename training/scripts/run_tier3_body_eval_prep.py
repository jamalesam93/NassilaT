#!/usr/bin/env python3
"""Tier 3 body holdout eval prep — validate files and print scoring commands (W6).

Usage (from training/):
  python scripts/run_tier3_body_eval_prep.py
  python scripts/run_tier3_body_eval_prep.py --merge-out data/eval_holdout_body_combined_draft.jsonl
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING = SCRIPT_DIR.parent
DATA = TRAINING / "data"
PILOT = DATA / "eval_holdout_body_pilot.jsonl"
DRAFT = DATA / "eval_holdout_body_draft.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", type=Path, default=PILOT)
    parser.add_argument("--draft", type=Path, default=DRAFT)
    parser.add_argument("--merge-out", type=Path, default=None)
    args = parser.parse_args()

    missing = [p for p in (args.pilot, args.draft) if not p.exists()]
    if missing:
        for p in missing:
            print(f"missing: {p}", file=sys.stderr)
        return 1

    for path in (args.pilot, args.draft):
        rc = subprocess.call(
            [sys.executable, str(SCRIPT_DIR / "validate_dataset.py"), str(path)],
            cwd=TRAINING,
        )
        if rc != 0:
            return rc

    pilot = load_jsonl(args.pilot)
    draft = load_jsonl(args.draft)
    doc_ids = {r.get("meta", {}).get("doc_id") for r in pilot + draft}
    proxy_draft = sum(
        1 for r in draft if r.get("meta", {}).get("draft_provenance") == "abstract_proxy_until_pdf_extract"
    )

    if args.merge_out:
        args.merge_out.parent.mkdir(parents=True, exist_ok=True)
        with args.merge_out.open("w", encoding="utf-8") as f:
            for row in pilot + draft:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps({
        "pilot_rows": len(pilot),
        "draft_rows": len(draft),
        "unique_doc_ids": len(doc_ids),
        "draft_abstract_proxy_rows": proxy_draft,
        "merged_out": str(args.merge_out) if args.merge_out else None,
        "score_commands": [
            "python scripts/run_l3_eval_batch.py --model nassila-sanad-12b "
            f"--data {args.pilot} {args.draft} --repair --out reports/tier3_body_pilot_predictions.jsonl",
            "python scripts/run_eval_reports.py --predictions reports/tier3_body_pilot_predictions.jsonl "
            f"--holdout {args.pilot}",
        ],
        "note": "Replace abstract-proxy draft excerpts with PDF body text before freezing product holdout.",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
