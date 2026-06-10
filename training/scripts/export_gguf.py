#!/usr/bin/env python3
"""
Export Nassila LoRA adapter to GGUF Q6_K for LM Studio (Phase 2).

Run on a GPU machine after train_qlora_gemma4_e4b.py.

Usage:
  python scripts/export_gguf.py \\
    --adapter-dir outputs/nassila-grounding-e4b-v1/lora_adapter \\
    --out-dir exports/nassila-grounding-e4b-v1-q6_k
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent

BASE_MODEL = "google/gemma-4-E4B-it"
MAX_SEQ_LENGTH = 4096


def export_unsloth(adapter_dir: Path, out_dir: Path, quant: str) -> None:
    try:
        from unsloth import FastLanguageModel  # type: ignore
    except ImportError as e:
        raise SystemExit(
            "Unsloth required on GPU machine. See PHASE2_VAST_WALKTHROUGH.md.\n"
            f"{e}"
        ) from e

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=MAX_SEQ_LENGTH,
        load_in_4bit=True,
    )
    model.load_adapter(str(adapter_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained_gguf(str(out_dir), tokenizer, quantization_method=quant)
    print(f"Exported GGUF ({quant}) to {out_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export LoRA to GGUF for LM Studio")
    parser.add_argument(
        "--adapter-dir",
        type=Path,
        default=TRAINING_DIR / "outputs" / "nassila-grounding-e4b-v1" / "lora_adapter",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=TRAINING_DIR / "exports" / "nassila-grounding-e4b-v1-q6_k",
    )
    parser.add_argument(
        "--quant",
        default="q6_k",
        help="GGUF quant method for Unsloth save_pretrained_gguf",
    )
    args = parser.parse_args()

    if not args.adapter_dir.exists():
        print(f"Adapter not found: {args.adapter_dir}", file=sys.stderr)
        return 1

    export_unsloth(args.adapter_dir, args.out_dir, args.quant)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
