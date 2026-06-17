#!/usr/bin/env python3
"""
Evaluate model predictions against eval JSONL (especially l3_grounding).

Usage:
  python scripts/evaluate_outputs.py \\
    --eval data/eval_samples.jsonl \\
    --predictions outputs/predictions.jsonl \\
    --report outputs/eval_report.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from json_repair import parse_strict_json, try_parse_with_repair  # noqa: E402

L3_VERDICTS = frozenset(
    {"supported", "weak", "contradicted", "not_in_source", "insufficient_evidence"}
)


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def parse_grounding_json(
    raw: str, allow_repair: bool = False
) -> tuple[bool, dict[str, Any] | None, str | None, bool]:
    """Mirror parseGroundingJson in grounding-llm.ts (simplified).

    Returns (ok, parsed, error, repaired_used).
    When allow_repair is False, only strict JSON counts as success.
    """
    if allow_repair:
        ok, parsed, err, repaired = try_parse_with_repair(raw)
        if not ok:
            return False, None, err, repaired
    else:
        ok, parsed, err = parse_strict_json(raw)
        if not ok:
            return False, None, err, False
        repaired = False
    if not isinstance(parsed, dict):
        return False, None, "JSON root not an object", repaired
    claims = parsed.get("claims")
    if not isinstance(claims, list):
        return False, None, "Missing claims array", repaired
    clean_claims = []
    for item in claims:
        if not isinstance(item, dict):
            continue
        verdict = item.get("verdict")
        claim = item.get("claim", "")
        if not isinstance(claim, str) or not claim.strip():
            continue
        if verdict not in L3_VERDICTS:
            continue
        clean_claims.append(item)
    parsed["claims"] = clean_claims
    return True, parsed, None, repaired


def is_substring_quote(quote: str, excerpt: str) -> bool:
    if quote in excerpt:
        return True
    return normalize_ws(quote) in normalize_ws(excerpt)


def load_jsonl_by_id(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            rid = row.get("id")
            if not rid:
                raise ValueError(f"{path}:{line_no} missing id")
            out[str(rid)] = row
    return out


def classify_failure_mode(
    eval_row: dict[str, Any],
    row_result: dict[str, Any],
    parsed: dict[str, Any] | None,
) -> str:
    """Per-row failure taxonomy for holdout matrix and debugging."""
    if row_result.get("error") == "missing_prediction":
        return "missing_prediction"
    expect = eval_row.get("expect", {})
    if expect.get("must_parse_json") and not row_result.get("parsed_strict"):
        if not row_result.get("parsed"):
            return "parse_json"
    if not row_result.get("parsed") or parsed is None:
        return "parse_json"

    claims = parsed.get("claims", [])
    verdicts = [c.get("verdict") for c in claims if isinstance(c, dict)]
    failures = row_result.get("failures") or []

    if row_result.get("checks_passed"):
        return "pass"

    for f in failures:
        if f == "must_parse_json":
            return "parse_json"
        if f.startswith("min_claims"):
            return "min_claims"
        if f.startswith("any_claim_verdict"):
            return "wrong_verdict"
        if f.startswith("forbidden"):
            return "forbidden_verdict"
        if "invalid quote" in f:
            return "quote_invalid"

    forbidden = expect.get("forbidden_claim_verdict", [])
    if "supported" in forbidden and "supported" in verdicts:
        return "forbidden_verdict"

    return "wrong_verdict"


def evaluate_l3_row(
    eval_row: dict[str, Any],
    raw_output: str,
    allow_repair: bool = False,
) -> dict[str, Any]:
    expect = eval_row.get("expect", {})
    excerpt = eval_row.get("source_excerpt", "")
    ok_strict, parsed_strict, err_strict, _ = parse_grounding_json(raw_output, allow_repair=False)
    if ok_strict:
        ok, parsed, err, repaired = ok_strict, parsed_strict, err_strict, False
    elif allow_repair:
        ok, parsed, err, repaired = parse_grounding_json(raw_output, allow_repair=True)
    else:
        ok, parsed, err, repaired = ok_strict, parsed_strict, err_strict, False

    result: dict[str, Any] = {
        "id": eval_row["id"],
        "parsed": ok,
        "parsed_strict": ok_strict,
        "repaired_used": bool(repaired),
        "parse_error": err,
        "checks_passed": True,
        "failures": [],
    }

    if expect.get("must_parse_json") and not ok:
        result["checks_passed"] = False
        result["failures"].append("must_parse_json")

    if not ok or parsed is None:
        result["failure_mode"] = classify_failure_mode(eval_row, result, None)
        return result

    claims = parsed.get("claims", [])
    verdicts = [c.get("verdict") for c in claims if isinstance(c, dict)]

    if "min_claims" in expect:
        min_c = expect["min_claims"]
        if len(claims) < min_c:
            result["checks_passed"] = False
            result["failures"].append(f"min_claims:{len(claims)}<{min_c}")

    any_expected = expect.get("any_claim_verdict")
    if any_expected:
        if not any(v in any_expected for v in verdicts):
            result["checks_passed"] = False
            result["failures"].append(f"any_claim_verdict missing {any_expected}")

    forbidden = expect.get("forbidden_claim_verdict", [])
    if any(v in forbidden for v in verdicts):
        result["checks_passed"] = False
        result["failures"].append(f"forbidden verdict present: {forbidden}")

    allowed = expect.get("all_claim_verdicts_in")
    if allowed and any(v not in allowed for v in verdicts):
        result["checks_passed"] = False
        result["failures"].append(f"verdict not in {allowed}")

    if expect.get("quotes_must_be_substrings"):
        for c in claims:
            if c.get("verdict") != "supported":
                continue
            for q in c.get("sourceQuotes") or []:
                if isinstance(q, str) and not is_substring_quote(q, excerpt):
                    result["checks_passed"] = False
                    result["failures"].append(f"invalid quote substring: {q[:40]!r}")

    result["failure_mode"] = classify_failure_mode(eval_row, result, parsed)
    return result


def holdout_category(row_id: str, eval_row: dict[str, Any] | None = None) -> str | None:
    """Infer eval category from meta.eval_category or holdout id ranges (h-001..h-090)."""
    if eval_row:
        cat = eval_row.get("meta", {}).get("eval_category")
        if isinstance(cat, str) and cat:
            return cat
    if not row_id.startswith("h-"):
        return None
    try:
        n = int(row_id.split("-", 1)[1])
    except ValueError:
        return None
    if 1 <= n <= 10 or 46 <= n <= 53:
        return "supported"
    if 11 <= n <= 19 or 54 <= n <= 59:
        return "contradicted"
    if 20 <= n <= 28 or 60 <= n <= 65:
        return "not_in_source"
    if 29 <= n <= 34 or 66 <= n <= 75:
        return "weak"
    if 35 <= n <= 39 or 76 <= n <= 83:
        return "insufficient_evidence"
    if 40 <= n <= 45 or 84 <= n <= 90:
        return "multi_claim"
    return None


def evaluate_dataset(
    eval_path: Path,
    predictions_path: Path,
    allow_repair: bool = False,
) -> dict[str, Any]:
    eval_rows = load_jsonl_by_id(eval_path)
    pred_rows = load_jsonl_by_id(predictions_path)

    missing = set(eval_rows) - set(pred_rows)
    if missing:
        print(f"Warning ({eval_path.name}): missing predictions for {sorted(missing)}")

    per_row: list[dict[str, Any]] = []
    parse_ok_strict = 0
    parse_ok_any = 0
    repaired_used = 0
    checks_ok = 0
    quote_checks = 0
    quote_ok = 0
    false_supported = 0
    false_supported_denom = 0
    l3_total = 0
    by_category: dict[str, dict[str, int]] = {}

    for rid, eval_row in eval_rows.items():
        pred = pred_rows.get(rid)
        if not pred:
            per_row.append({"id": rid, "error": "missing_prediction"})
            continue

        raw = pred.get("raw_output", "")
        if eval_row.get("task") != "l3_grounding":
            per_row.append({"id": rid, "skipped": True, "task": eval_row.get("task")})
            continue

        l3_total += 1
        row_result = evaluate_l3_row(eval_row, raw, allow_repair=allow_repair)
        cat = holdout_category(rid, eval_row)
        if cat:
            row_result["category"] = cat
            bucket = by_category.setdefault(cat, {"total": 0, "checks_passed": 0})
            bucket["total"] += 1
            if row_result.get("checks_passed"):
                bucket["checks_passed"] += 1

        per_row.append(row_result)
        if row_result.get("parsed_strict"):
            parse_ok_strict += 1
        if row_result.get("parsed"):
            parse_ok_any += 1
        if row_result.get("repaired_used"):
            repaired_used += 1
        if row_result.get("checks_passed"):
            checks_ok += 1

        expect = eval_row.get("expect", {})
        if expect.get("quotes_must_be_substrings"):
            quote_checks += 1
            if row_result.get("checks_passed") and "invalid quote" not in str(
                row_result.get("failures")
            ):
                quote_ok += 1

        forbidden = expect.get("forbidden_claim_verdict", [])
        if "supported" in forbidden:
            false_supported_denom += 1
            ok, parsed, _, _ = parse_grounding_json(raw, allow_repair=allow_repair)
            if ok and parsed:
                verdicts = [
                    c.get("verdict")
                    for c in parsed.get("claims", [])
                    if isinstance(c, dict)
                ]
                if "supported" in verdicts:
                    false_supported += 1

    total = l3_total
    category_rates = {
        cat: round(v["checks_passed"] / v["total"], 4) if v["total"] else 0
        for cat, v in by_category.items()
    }
    return {
        "eval_file": str(eval_path),
        "total_l3_rows": total,
        "json_parse_rate_strict": round(parse_ok_strict / total, 4) if total else 0,
        "json_parse_rate_with_repair": round(parse_ok_any / total, 4) if total else 0,
        "repair_used_count": repaired_used,
        "expect_checks_pass_rate": round(checks_ok / total, 4) if total else 0,
        "quote_validity_rate": round(quote_ok / quote_checks, 4) if quote_checks else None,
        "false_supported_rate": (
            round(false_supported / false_supported_denom, 4)
            if false_supported_denom
            else None
        ),
        "category_pass_rates": category_rates,
        "per_row": per_row,
    }


def print_summary(summary: dict[str, Any], label: str) -> None:
    print(f"\n=== {label} ===")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("per_row", "eval_file")}, indent=2))
    for row in summary.get("per_row", []):
        if not row.get("checks_passed", True) and not row.get("skipped") and not row.get("error"):
            print(f"  FAIL {row['id']}: {row.get('failures')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Nassila model predictions")
    parser.add_argument("--eval", type=Path, required=True, help="Eval JSONL with expect blocks")
    parser.add_argument(
        "--predictions",
        type=Path,
        required=True,
        help="JSONL with {id, raw_output} per eval row",
    )
    parser.add_argument("--report", type=Path, help="Write JSON summary report")
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Allow lightweight JSON repair (trailing commas, ?: keys, fences)",
    )
    args = parser.parse_args()

    summary = evaluate_dataset(args.eval, args.predictions, allow_repair=args.repair)
    print_summary(summary, args.eval.name)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Wrote report: {args.report}")

    total = summary["total_l3_rows"]
    checks_ok = round(summary["expect_checks_pass_rate"] * total) if total else 0
    return 0 if checks_ok == total and total > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
