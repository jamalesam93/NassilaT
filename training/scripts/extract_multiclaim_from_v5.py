#!/usr/bin/env python3
"""Extract multiclaim rows from freeze v5 into a standalone frozen slice."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from corpus_utils import DATA_DIR, read_jsonl

DEFAULT_IN = DATA_DIR / "eval_holdout_body_scale_frozen_v5.jsonl"
DEFAULT_OUT = DATA_DIR / "eval_holdout_body_multiclaim_frozen_v1.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="infile", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    rows = [r for r in read_jsonl(args.infile) if str(r.get("id", "")).startswith("bh-mc-")]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps({"in": str(args.infile), "out": str(args.out), "rows": len(rows)}, indent=2))
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
