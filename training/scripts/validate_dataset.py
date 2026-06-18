#!/usr/bin/env python3
"""
Validate Nassila training JSONL files.

Usage:
  python scripts/validate_dataset.py data/l3_grounding_samples.jsonl
  python scripts/validate_dataset.py data/webpage_citation_samples.jsonl
  python scripts/validate_dataset.py data/eval_samples.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

L3_VERDICTS = frozenset(
    {"supported", "weak", "contradicted", "not_in_source", "insufficient_evidence"}
)
OVERALL_VERDICTS = frozenset({"support", "weak", "unrelated", "insufficient_evidence"})
# Ouroboros task ids — see docs/OUROBOROS.md and src/shared/nassila-agent-tasks.ts
TASKS = frozenset({
    "l3_grounding",
    "doc_extract",
    "source_pdf_extract",
    "table_figure_grounding",
    "webpage_metadata",
    "webpage_classify",
    "issue_explain",
})


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def is_substring_quote(quote: str, excerpt: str) -> bool:
    if quote in excerpt:
        return True
    return normalize_ws(quote) in normalize_ws(excerpt)


GROUNDING_SYSTEM_MESSAGE = "You are a strict academic citation grounding assistant."


def build_grounding_user_prompt(passage: str, source_excerpt: str, meta: dict[str, Any]) -> str:
    """Mirror src/engine/manuscript/grounding-llm.ts buildGroundingUserPrompt."""
    label = meta.get("label", "source")
    url = meta.get("url")
    url_part = f" {url}" if url else ""
    return "\n".join(
        [
            "You are a strict academic citation grounding assistant.",
            "Break the manuscript passage into short factual claims (atomic where possible).",
            "Each claim string MUST restate an assertion from the PASSAGE — do NOT copy source sentences as claim text unless that exact assertion also appears in the passage. When the passage states a number, use that number, not a different number from the source.",
            "For each claim, compare ONLY to SOURCE_EXCERPT (verbatim text from the cited work).",
            "Verdict per claim:",
            "- supported: SOURCE_EXCERPT contains clear support; you MUST copy 1–3 verbatim sourceQuotes from SOURCE_EXCERPT.",
            "- weak: partial or vague alignment, OR the source hedges (may/might/suggest/preliminary/unclear). Do NOT use weak when the excerpt clearly supports a single passage claim (including paraphrase and 'associated with' / 'significantly' wording).",
            "- not_in_source: not found in excerpt (excerpt may be incomplete).",
            "- contradicted: excerpt clearly conflicts.",
            "- insufficient_evidence: cannot tell from excerpt.",
            'Compound passages: when the passage bundles multiple claims (e.g., joined by "and"), split into one claim per conjunct and evaluate each independently. A conjunct may be supported if SOURCE_EXCERPT directly supports it with matching meaning and numbers — but NOT if the passage asserts a specific number that differs from the source. On compound passages where the passage asserts parity or equality across subgroups (e.g., "equally well in adults and children") and the source addresses only one subgroup, the studied subgroup receives weak (not supported), and the unstudied subgroup receives not_in_source.',
            "Scope-silence rule: if the passage asserts a claim about specific subgroups (e.g., adults and children, men and women) and SOURCE_EXCERPT addresses one subgroup but states or implies the other was not studied / not collected / not enrolled, split into one claim per subgroup. The unstudied subgroup receives not_in_source, never contradicted. The studied subgroup receives weak (not supported) when the passage asserts parity or equality across those subgroups.",
            'Respond with a single JSON object ONLY, no markdown fencing, keys:',
            '{ "claims": [ { "claim": string, "verdict": "supported"|"weak"|"not_in_source"|"contradicted"|"insufficient_evidence", "hasNumericClaim"?: boolean, "sourceQuotes"?: string[], "rationale"?: string[] } ], "overallVerdict"?: "support"|"weak"|"unrelated"|"insufficient_evidence", "overallRationale"?: string[] }',
            "",
            f"PASSAGE:\n{passage}",
            "",
            f"SOURCE_EXCERPT ({label}{url_part}):\n{source_excerpt}",
        ]
    )


def build_grounding_chat_messages(
    passage: str,
    source_excerpt: str,
    meta: dict[str, Any],
    *,
    chat_template: bool = False,
) -> list[dict[str, str]]:
    """Messages for eval/inference; chat_template matches train_qlora system+user layout."""
    user = build_grounding_user_prompt(passage, source_excerpt, meta)
    if chat_template:
        return [
            {"role": "system", "content": GROUNDING_SYSTEM_MESSAGE},
            {"role": "user", "content": user},
        ]
    return [{"role": "user", "content": user}]


def validate_l3_record(record: dict[str, Any], line_no: int, errors: list[str]) -> None:
    for field in ("passage", "source_excerpt", "meta"):
        if field not in record:
            errors.append(f"Line {line_no}: missing '{field}'")

    if "output" not in record and "expect" not in record:
        errors.append(f"Line {line_no}: l3_grounding rows need either 'output' (gold) or 'expect' (eval)")
        return

    output = record.get("output")
    if output is None:
        return
    if not isinstance(output, dict):
        errors.append(f"Line {line_no}: output must be an object")
        return

    claims = output.get("claims")
    if not isinstance(claims, list):
        errors.append(f"Line {line_no}: output.claims must be an array")
        return

    excerpt = record.get("source_excerpt", "")
    if not isinstance(excerpt, str):
        excerpt = ""

    overall = output.get("overallVerdict")
    if overall is not None and overall not in OVERALL_VERDICTS:
        errors.append(f"Line {line_no}: invalid overallVerdict '{overall}'")

    for i, claim in enumerate(claims):
        if not isinstance(claim, dict):
            errors.append(f"Line {line_no}: claims[{i}] must be an object")
            continue
        verdict = claim.get("verdict")
        if verdict not in L3_VERDICTS:
            errors.append(f"Line {line_no}: claims[{i}] invalid verdict '{verdict}'")
            continue
        text = claim.get("claim", "")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"Line {line_no}: claims[{i}] missing claim text")

        quotes = claim.get("sourceQuotes", [])
        if verdict == "supported":
            if not isinstance(quotes, list) or len(quotes) == 0:
                errors.append(
                    f"Line {line_no}: claims[{i}] supported requires sourceQuotes"
                )
            else:
                for q in quotes:
                    if not isinstance(q, str):
                        errors.append(f"Line {line_no}: claims[{i}] quote must be string")
                    elif not is_substring_quote(q, excerpt):
                        errors.append(
                            f"Line {line_no}: claims[{i}] quote not substring of source_excerpt: {q[:60]!r}..."
                        )


def validate_webpage_metadata(record: dict[str, Any], line_no: int, errors: list[str]) -> None:
    for field in ("url", "page_signals", "output"):
        if field not in record:
            errors.append(f"Line {line_no}: missing '{field}'")
    output = record.get("output")
    if isinstance(output, dict):
        if "suggested_type" not in output:
            errors.append(f"Line {line_no}: output.suggested_type required")


def validate_webpage_classify(record: dict[str, Any], line_no: int, errors: list[str]) -> None:
    output = record.get("output")
    if not isinstance(output, dict):
        errors.append(f"Line {line_no}: output must be object")
        return
    if "recommended_csl_type" not in output:
        errors.append(f"Line {line_no}: output.recommended_csl_type required")


def validate_issue_explain(record: dict[str, Any], line_no: int, errors: list[str]) -> None:
    for field in ("issue_code", "issue_context", "output"):
        if field not in record:
            errors.append(f"Line {line_no}: missing '{field}'")
    output = record.get("output")
    if isinstance(output, dict) and "explanation" not in output:
        errors.append(f"Line {line_no}: output.explanation required")


def validate_record(record: dict[str, Any], line_no: int) -> list[str]:
    errors: list[str] = []
    if "id" not in record:
        errors.append(f"Line {line_no}: missing 'id'")
    task = record.get("task")
    if task not in TASKS:
        errors.append(f"Line {line_no}: invalid or missing task '{task}'")
        return errors

    if task == "l3_grounding":
        validate_l3_record(record, line_no, errors)
    elif task == "webpage_metadata":
        validate_webpage_metadata(record, line_no, errors)
    elif task == "webpage_classify":
        validate_webpage_classify(record, line_no, errors)
    elif task == "issue_explain":
        validate_issue_explain(record, line_no, errors)

    if task == "l3_grounding" and "expect" in record:
        expect = record["expect"]
        if not isinstance(expect, dict):
            errors.append(f"Line {line_no}: expect must be object")

    return errors


def load_jsonl(path: Path) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rows.append((line_no, json.loads(stripped)))
            except json.JSONDecodeError as e:
                raise ValueError(f"Line {line_no}: invalid JSON: {e}") from e
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Nassila training JSONL")
    parser.add_argument("path", type=Path, help="Path to .jsonl file")
    parser.add_argument(
        "--export-chat",
        type=Path,
        help="Optional: write chat-format JSONL for SFT training (l3_grounding only)",
    )
    parser.add_argument(
        "--strict-length",
        type=int,
        metavar="MAX_TOKENS",
        help="When exporting chat JSONL, fail if any row exceeds this token count (requires transformers)",
    )
    args = parser.parse_args()

    if not args.path.exists():
        print(f"File not found: {args.path}", file=sys.stderr)
        return 1

    rows = load_jsonl(args.path)
    all_errors: list[str] = []
    chat_rows: list[dict[str, Any]] = []

    for line_no, record in rows:
        if not isinstance(record, dict):
            all_errors.append(f"Line {line_no}: record must be JSON object")
            continue
        all_errors.extend(validate_record(record, line_no))

        if args.export_chat and record.get("task") == "l3_grounding":
            user = build_grounding_user_prompt(
                record["passage"],
                record["source_excerpt"],
                record.get("meta", {}),
            )
            assistant = json.dumps(record["output"], ensure_ascii=False)
            chat_rows.append(
                {
                    "id": record["id"],
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a strict academic citation grounding assistant.",
                        },
                        {"role": "user", "content": user},
                        {"role": "assistant", "content": assistant},
                    ],
                }
            )

    if all_errors:
        print(f"FAILED: {len(all_errors)} error(s) in {args.path}")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print(f"OK: {len(rows)} record(s) in {args.path}")

    if args.export_chat:
        args.export_chat.parent.mkdir(parents=True, exist_ok=True)
        tokenizer = None
        if args.strict_length:
            try:
                from transformers import AutoTokenizer  # type: ignore

                tokenizer = AutoTokenizer.from_pretrained(
                    "google/gemma-4-E4B-it", trust_remote_code=True
                )
            except ImportError:
                print(
                    "strict-length requires transformers; install on export machine",
                    file=sys.stderr,
                )
                return 1

        length_errors: list[str] = []
        with args.export_chat.open("w", encoding="utf-8") as out:
            for row in chat_rows:
                if tokenizer is not None:
                    text = tokenizer.apply_chat_template(
                        row["messages"], tokenize=False, add_generation_prompt=False
                    )
                    n_tok = len(tokenizer.encode(text, add_special_tokens=False))
                    if n_tok > args.strict_length:
                        length_errors.append(
                            f"{row['id']}: {n_tok} tokens > {args.strict_length}"
                        )
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
        if length_errors:
            print(f"FAILED strict-length: {len(length_errors)} overflow(s)")
            for err in length_errors[:20]:
                print(f"  - {err}")
            return 1
        print(f"Wrote chat export: {args.export_chat} ({len(chat_rows)} rows)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
