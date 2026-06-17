#!/usr/bin/env python3
"""Check train/eval contamination: train rows vs eval sets (passage/excerpt overlap).

Importable: `contaminating_rows(rows)` returns [(id, passage_match, excerpt_match), ...].
CLI: `python scripts/check_contamination.py data/l3_grounding_train_v16.jsonl`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
EVAL_FILES = (
    "eval_holdout_90.jsonl",
    "eval_holdout_45.jsonl",
    "eval_holdout_extension_45.jsonl",
    "eval_samples_extended.jsonl",
    "eval_samples.jsonl",
)


def norm(s: str) -> str:
    return " ".join(str(s).split()).lower()


def load(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.open(encoding="utf-8") if line.strip()]


def _eval_index() -> tuple[dict[str, str], dict[str, str]]:
    eval_rows: list[dict] = []
    for name in EVAL_FILES:
        f = DATA / name
        if f.exists():
            eval_rows.extend(load(f))
    eval_pass = {norm(r["passage"]): r["id"] for r in eval_rows if r.get("passage")}
    eval_exc = {norm(r["source_excerpt"]): r["id"] for r in eval_rows if r.get("source_excerpt")}
    return eval_pass, eval_exc


def contaminating_rows(rows: list[dict]) -> list[tuple[str, str | None, str | None]]:
    """Return train rows that reuse an eval passage or excerpt (verbatim, ws-normalized)."""
    eval_pass, eval_exc = _eval_index()
    hits: list[tuple[str, str | None, str | None]] = []
    for b in rows:
        pm = eval_pass.get(norm(b.get("passage", "")))
        em = eval_exc.get(norm(b.get("source_excerpt", "")))
        if pm or em:
            hits.append((str(b.get("id", "?")), pm, em))
    return hits


def main() -> int:
    train_file = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA / "l3_grounding_v16_boost.jsonl"
    rows = load(train_file)
    eval_count = sum(len(load(DATA / n)) for n in EVAL_FILES if (DATA / n).exists())
    print(f"Checking {len(rows)} train rows vs {eval_count} eval rows")
    hits = contaminating_rows(rows)
    for rid, pm, em in hits:
        print(f"  CONTAM {rid}: passage~{pm}  excerpt~{em}")
    print(f"Total contaminated rows: {len(hits)}")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
