#!/usr/bin/env python3
"""
Merge Nassila LoRA adapter into full Qwen 3.5 4B weights (safetensors).

Usage (GPU machine, after train):
  python scripts/merge_adapter_qwen.py \
    --adapter-dir outputs/nassila-sanad-qwen35-4b-v1/lora_adapter \
    --out-dir outputs/nassila-sanad-qwen35-4b-v1-merged
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_MODEL = "Qwen/Qwen3.5-4B"


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge Qwen 3.5 4B LoRA adapter into bf16 HF weights")
    parser.add_argument("--adapter-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--base-model", default=BASE_MODEL)
    args = parser.parse_args()

    if not args.adapter_dir.exists():
        print(f"Adapter not found: {args.adapter_dir}", file=sys.stderr)
        return 1

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"Loading base model: {args.base_model}")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )

    print(f"Merging LoRA adapter from: {args.adapter_dir}")
    model = PeftModel.from_pretrained(model, str(args.adapter_dir))
    model = model.merge_and_unload()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Saving merged model to: {args.out_dir}")
    model.save_pretrained(str(args.out_dir), safe_serialization=True)
    tokenizer.save_pretrained(str(args.out_dir))
    print(f"Merged bf16 HF weights saved to {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
