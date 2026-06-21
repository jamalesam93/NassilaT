#!/usr/bin/env python3
"""Score the 4-row laptop smoke set from batch predictions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_outputs import evaluate_l3_row, load_jsonl_by_id  # noqa: E402
from validate_dataset import load_jsonl  # noqa: E402

SMOKE_IDS = ("h-001", "eval-004", "h-045", "h-088")
EVAL_FILES = (
    TRAINING_DIR / "data" / "eval_samples.jsonl",
    TRAINING_DIR / "data" / "eval_holdout_90.jsonl",
)


def load_eval_rows() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for path in EVAL_FILES:
        for _, row in load_jsonl(path):
            rid = row.get("id")
            if rid in SMOKE_IDS:
                rows[rid] = row
    missing = [rid for rid in SMOKE_IDS if rid not in rows]
    if missing:
        raise SystemExit(f"Missing smoke eval rows: {missing}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Score laptop smoke predictions")
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--no-repair",
        action="store_true",
        help="Disable JSON repair when scoring (default: repair on)",
    )
    args = parser.parse_args()
    allow_repair = not args.no_repair

    eval_rows = load_eval_rows()
    preds = load_jsonl_by_id(args.predictions)

    per_row: list[dict] = []
    passed = 0
    for rid in SMOKE_IDS:
        eval_row = eval_rows[rid]
        pred = preds.get(rid)
        if not pred:
            per_row.append({"id": rid, "error": "missing_prediction", "checks_passed": False})
            continue
        raw = pred.get("raw_output", "")
        result = evaluate_l3_row(eval_row, raw, allow_repair=allow_repair)
        result["id"] = rid
        result["status"] = pred.get("status")
        result["seconds"] = pred.get("seconds")
        if result.get("checks_passed"):
            passed += 1
        per_row.append(result)

    report = {
        "smoke_ids": list(SMOKE_IDS),
        "predictions_file": str(args.predictions),
        "rows_scored": len(SMOKE_IDS),
        "checks_passed": passed,
        "all_passed": passed == len(SMOKE_IDS),
        "per_row": per_row,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Smoke score: {passed}/{len(SMOKE_IDS)} expect checks passed")
    for row in per_row:
        rid = row["id"]
        ok = row.get("checks_passed", False)
        mark = "PASS" if ok else "FAIL"
        detail = "" if ok else f" — {row.get('failures') or row.get('error')}"
        print(f"  {rid}: {mark}{detail}")
    print(f"Report: {args.report}")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
