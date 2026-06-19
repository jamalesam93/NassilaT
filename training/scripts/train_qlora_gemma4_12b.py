#!/usr/bin/env python3
"""
QLoRA fine-tuning for Nassila L3 grounding on Gemma 4 12B (A/B pilot arm).

Same recipe as E4B (2 ep, 1e-4, LoRA r=16). v1.12 uses shared v1.12 data + prompt.
Requires ~24GB+ GPU for QLoRA (Vast A6000/A100).

Usage:
  python scripts/train_qlora_gemma4_12b.py --phase 10 \\
    --train-file data/l3_grounding_train_v110.jsonl \\
    --chat-file data/l3_grounding_chat_v110.jsonl

  python scripts/train_qlora_gemma4_12b.py --phase 12 \\
    --train-file data/l3_grounding_train_v112.jsonl \\
    --chat-file data/l3_grounding_chat_v112.jsonl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from train_qlora_gemma4_e4b import (  # noqa: E402
    DEFAULT_TRAIN_FILE,
    records_to_chat_jsonl,
    split_train_eval,
    train_with_peft,
    train_with_unsloth,
)

BASE_MODEL = "google/gemma-4-12B-it"

PHASE_CONFIG = {
    "10": {
        "num_epochs": 2,
        "learning_rate": 1e-4,
        "output_name": "nassila-sanad-12b-v1.10",
    },
    "10ab": {
        "num_epochs": 2,
        "learning_rate": 1e-4,
        "output_name": "nassila-sanad-12b-v1.10-ab",
    },
    "12": {
        "num_epochs": 2,
        "learning_rate": 1e-4,
        "output_name": "nassila-sanad-12b-v1.12",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="QLoRA for Nassila grounding on Gemma 4 12B")
    parser.add_argument(
        "--train-file",
        type=Path,
        default=TRAINING_DIR / "data" / "l3_grounding_train_v110.jsonl",
    )
    parser.add_argument("--phase", choices=tuple(PHASE_CONFIG.keys()), default="10")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--backend", choices=("unsloth", "peft"), default="unsloth")
    parser.add_argument("--chat-file", type=Path)
    parser.add_argument("--seed", type=int, default=46)
    parser.add_argument("--eval-split", action="store_true")
    args = parser.parse_args()

    if not args.train_file.exists():
        print(f"Train file not found: {args.train_file}", file=sys.stderr)
        return 1

    phase = PHASE_CONFIG[args.phase]
    output_dir = args.output_dir or (TRAINING_DIR / "outputs" / phase["output_name"])
    output_dir.mkdir(parents=True, exist_ok=True)

    full_chat = args.chat_file or (output_dir / "chat_full.jsonl")
    if not args.chat_file:
        n = records_to_chat_jsonl(args.train_file, full_chat)
        print(f"Built chat file: {full_chat} ({n} rows)")

    train_chat = full_chat
    if args.eval_split:
        train_chat = output_dir / "chat_train.jsonl"
        eval_chat = output_dir / "eval_chat.jsonl"
        n_train, n_eval = split_train_eval(full_chat, train_chat, eval_chat, seed=args.seed)
        print(f"Split chat: train={n_train}, eval={n_eval}")

    print(
        f"12B phase {args.phase}: base={BASE_MODEL}, epochs={phase['num_epochs']}, "
        f"lr={phase['learning_rate']}, out={output_dir}"
    )

    # Patch BASE_MODEL in train helpers via closure — call with explicit model name
    import train_qlora_gemma4_e4b as e4b_mod  # noqa: E402

    original_base = e4b_mod.BASE_MODEL
    e4b_mod.BASE_MODEL = BASE_MODEL
    try:
        if args.backend == "unsloth":
            train_with_unsloth(
                train_chat,
                output_dir,
                num_epochs=phase["num_epochs"],
                learning_rate=phase["learning_rate"],
            )
        else:
            train_with_peft(
                train_chat,
                output_dir,
                num_epochs=phase["num_epochs"],
                learning_rate=phase["learning_rate"],
            )
    finally:
        e4b_mod.BASE_MODEL = original_base

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
