#!/usr/bin/env python3
"""
Upload Nassila fine-tuned Qwen3.5-4B LoRA adapter and GGUF to Hugging Face Hub (separate repos).

Usage:
  python scripts/upload_to_hf.py \
    --hf-token "YOUR_HF_TOKEN" \
    --org "QinEmPeRoR93" \
    --adapter-dir outputs/nassila-sanad-qwen35-4b-v1/lora_adapter \
    --gguf-file outputs/nassila-sanad-qwen35-4b-s16.gguf
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from huggingface_hub import HfApi
except ImportError:
    print("Install huggingface_hub: pip install huggingface_hub", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload Nassila Sanad Qwen 3.5 4B to Hugging Face")
    parser.add_argument("--hf-token", required=True, help="Hugging Face User Access Token (write permission)")
    parser.add_argument("--org", default="QinEmPeRoR93", help="HF Username or Org (e.g. QinEmPeRoR93 or jamalesam93)")
    parser.add_argument(
        "--adapter-dir",
        type=Path,
        default=Path("outputs/nassila-sanad-qwen35-4b-v1/lora_adapter"),
        help="Path to lora_adapter directory",
    )
    parser.add_argument(
        "--gguf-file",
        type=Path,
        default=Path("outputs/nassila-sanad-qwen35-4b-s16.gguf"),
        help="Path to fine-tuned GGUF file",
    )
    args = parser.parse_args()

    api = HfApi(token=args.hf_token)

    adapter_repo = f"{args.org}/nassila-sanad-4b-lora"
    gguf_repo = f"{args.org}/nassila-sanad-4b"

    # 1. Upload LoRA Adapter
    if args.adapter_dir.exists():
        print(f"\n[1/2] Creating repo: https://huggingface.co/{adapter_repo}")
        api.create_repo(repo_id=adapter_repo, repo_type="model", exist_ok=True)
        print(f"Uploading LoRA adapter folder from {args.adapter_dir}...")
        api.upload_folder(
            folder_path=str(args.adapter_dir),
            repo_id=adapter_repo,
            repo_type="model",
            commit_message="Upload Nassila Sanad Qwen3.5 4B S16 LoRA adapter",
        )
        print(f"✅ Adapter uploaded successfully to https://huggingface.co/{adapter_repo}")
    else:
        print(f"Warning: Adapter dir not found at {args.adapter_dir}", file=sys.stderr)

    # 2. Upload GGUF Model
    if args.gguf_file.exists():
        print(f"\n[2/2] Creating repo: https://huggingface.co/{gguf_repo}")
        api.create_repo(repo_id=gguf_repo, repo_type="model", exist_ok=True)
        print(f"Uploading GGUF file from {args.gguf_file}...")
        api.upload_file(
            path_or_fileobj=str(args.gguf_file),
            path_in_repo="nassila-sanad-4b-q6_k.gguf",
            repo_id=gguf_repo,
            repo_type="model",
            commit_message="Upload Nassila Sanad Qwen3.5 4B S16 GGUF (Q6_K)",
        )
        print(f"✅ GGUF uploaded successfully to https://huggingface.co/{gguf_repo}")
    else:
        print(f"Warning: GGUF file not found at {args.gguf_file}", file=sys.stderr)

    print("\n🎉 Hugging Face Upload Complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
