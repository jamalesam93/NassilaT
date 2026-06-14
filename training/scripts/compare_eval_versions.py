#!/usr/bin/env python3
"""
Cross-version holdout failure matrix (v1.0–v1.4).

Loads reports/v1_*_eval_holdout_report.json and emits a row × version matrix
of pass | failure_mode for regression tracking.

Usage:
  python scripts/compare_eval_versions.py
  python scripts/compare_eval_versions.py --out reports/holdout_failure_matrix.md
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
REPORTS_DIR = TRAINING_DIR / "reports"


def infer_failure_mode(row: dict) -> str:
    if row.get("error") == "missing_prediction":
        return "missing_prediction"
    if row.get("failure_mode"):
        return str(row["failure_mode"])
    if not row.get("parsed_strict") and not row.get("parsed"):
        return "parse_json"
    failures = row.get("failures") or []
    if not failures:
        return "pass" if row.get("checks_passed") else "unknown"
    first = failures[0]
    if first == "must_parse_json":
        return "parse_json"
    if first.startswith("min_claims"):
        return "min_claims"
    if first.startswith("any_claim_verdict"):
        return "wrong_verdict"
    if first.startswith("forbidden"):
        return "forbidden_verdict"
    if "invalid quote" in first:
        return "quote_invalid"
    return first.split(":")[0] if ":" in first else first


def load_version_reports(reports_dir: Path) -> dict[str, dict[str, dict]]:
    """version_label -> row_id -> per_row result dict."""
    out: dict[str, dict[str, dict]] = {}
    patterns = [
        ("v1.0", "v1_0_eval_holdout_report.json"),
        ("v1.1", "v1_1_eval_holdout_report.json"),
        ("v1.2", "v1_2_eval_holdout_report.json"),
        ("v1.3", "v1_3_eval_holdout_report.json"),
        ("v1.4a", "v1_4a_eval_holdout_report.json"),
        ("v1.4b", "v1_4_eval_holdout_report.json"),
        ("v1.4", "v1_4_eval_holdout_report.json"),
    ]
    for label, name in patterns:
        path = reports_dir / name
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        by_id = {r["id"]: r for r in data.get("per_row", []) if "id" in r}
        out[label] = by_id
    # Also pick up generic eval_holdout_report.json as v1.0 fallback
    generic = reports_dir / "eval_holdout_report.json"
    if "v1.0" not in out and generic.exists():
        data = json.loads(generic.read_text(encoding="utf-8"))
        out["v1.0"] = {r["id"]: r for r in data.get("per_row", []) if "id" in r}
    return out


def holdout_row_ids(by_version: dict[str, dict[str, dict]]) -> list[str]:
    ids: set[str] = set()
    for rows in by_version.values():
        ids.update(rows.keys())
    return sorted(ids, key=lambda x: (not x.startswith("h-"), x))


def render_markdown(
    versions: list[str], row_ids: list[str], matrix: dict[str, dict[str, str]]
) -> str:
    lines = [
        "# Holdout failure matrix",
        "",
        "Row × version: `pass` or failure mode (`parse_json`, `wrong_verdict`, etc.).",
        "",
        "| row | " + " | ".join(versions) + " |",
        "| --- | " + " | ".join(["---"] * len(versions)) + " |",
    ]
    for rid in row_ids:
        cells = [matrix.get(rid, {}).get(v, "—") for v in versions]
        lines.append("| " + rid + " | " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare holdout eval across model versions")
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=REPORTS_DIR,
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPORTS_DIR / "holdout_failure_matrix.md",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Optional CSV export",
    )
    args = parser.parse_args()

    by_version = load_version_reports(args.reports_dir)
    if not by_version:
        print("No holdout reports found under", args.reports_dir, file=sys.stderr)
        return 1

    versions = sorted(by_version.keys(), key=lambda v: [int(x) if x.isdigit() else x for x in re.findall(r"\d+|\D+", v)])
    row_ids = holdout_row_ids(by_version)
    matrix: dict[str, dict[str, str]] = {}
    for rid in row_ids:
        matrix[rid] = {}
        for ver in versions:
            row = by_version[ver].get(rid)
            if row is None:
                matrix[rid][ver] = "—"
            else:
                matrix[rid][ver] = infer_failure_mode(row)

    md = render_markdown(versions, row_ids, matrix)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")
    print(f"Wrote {args.out} ({len(row_ids)} rows × {len(versions)} versions)")

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["row_id", *versions])
            for rid in row_ids:
                w.writerow([rid, *[matrix[rid].get(v, "—") for v in versions]])
        print(f"Wrote {args.csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
