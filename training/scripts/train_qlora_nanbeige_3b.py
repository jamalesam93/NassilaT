#!/usr/bin/env python3
"""
QLoRA fine-tuning for Nassila L3 grounding on Nanbeige4.2-3B.

Base model: Nanbeige/Nanbeige4.2-3B
Fine-tunes the 3B parameter model with ChatML jinja template for Sanad grounding.

Usage:
  python scripts/train_qlora_nanbeige_3b.py \
    --train-file data/l3_grounding_train_v114.jsonl \
    --output-dir outputs/nassila-sanad-nanbeige-3b-v1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from corpus_utils import read_jsonl  # noqa: E402
from validate_dataset import (  # noqa: E402
    GROUNDING_SYSTEM_MESSAGE,
    build_grounding_user_prompt,
)

BASE_MODEL = "Nanbeige/Nanbeige4.2-3B"
MAX_SEQ_LENGTH = 2048
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
BATCH_SIZE = 1
GRAD_ACCUM = 8

DEFAULT_TRAIN_FILE = TRAINING_DIR / "data" / "l3_grounding_train_v114.jsonl"
DEFAULT_OUTPUT_DIR = TRAINING_DIR / "outputs" / "nassila-sanad-nanbeige-3b-v1"


def records_to_chat_jsonl(input_file: Path, output_file: Path) -> int:
    records = read_jsonl(input_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_file.open("w", encoding="utf-8") as f:
        for r in records:
            p = r["passage"]
            ex = r["source_excerpt"]
            m = r.get("meta", {})
            out = r.get("output")
            if not out:
                continue
            user_text = build_grounding_user_prompt(p, ex, m)
            assistant_text = json.dumps(out, ensure_ascii=False)
            messages = [
                {"role": "system", "content": GROUNDING_SYSTEM_MESSAGE},
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": assistant_text},
            ]
            f.write(json.dumps({"messages": messages}, ensure_ascii=False) + "\n")
            count += 1
    return count


def train_nanbeige_peft(
    chat_file: Path,
    output_dir: Path,
    num_epochs: int = 2,
    learning_rate: float = 1e-4,
) -> None:
    import torch
    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
    from trl import SFTTrainer

    print(f"Loading tokenizer: {BASE_MODEL}")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"Loading 4-bit model: {BASE_MODEL}")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)

    peft_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, peft_config)

    dataset = load_dataset("json", data_files=str(chat_file), split="train")

    def formatting_func(examples):
        texts = []
        for messages in examples["messages"]:
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
            texts.append(text)
        return {"text": texts}

    dataset = dataset.map(formatting_func, batched=True)

    try:
        from trl import SFTConfig
        sft_config = SFTConfig(
            output_dir=str(output_dir),
            num_train_epochs=num_epochs,
            per_device_train_batch_size=BATCH_SIZE,
            gradient_accumulation_steps=GRAD_ACCUM,
            learning_rate=learning_rate,
            logging_steps=5,
            warmup_ratio=0.05,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            report_to="none",
            save_strategy="no",
            dataset_text_field="text",
            max_length=MAX_SEQ_LENGTH,
        )
        trainer = SFTTrainer(
            model=model,
            args=sft_config,
            train_dataset=dataset,
            processing_class=tokenizer,
        )
    except (ImportError, TypeError):
        training_args = TrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=num_epochs,
            per_device_train_batch_size=BATCH_SIZE,
            gradient_accumulation_steps=GRAD_ACCUM,
            learning_rate=learning_rate,
            logging_steps=5,
            warmup_ratio=0.05,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            report_to="none",
            save_strategy="no",
        )
        trainer = SFTTrainer(
            model=model,
            args=training_args,
            train_dataset=dataset,
            processing_class=tokenizer,
        )

    print("Starting PyTorch/PEFT QLoRA training...")
    trainer.train()

    adapter_path = output_dir / "lora_adapter"
    model.save_pretrained(str(adapter_path))
    tokenizer.save_pretrained(str(adapter_path))
    print(f"Saved LoRA adapter to {adapter_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="QLoRA for Nassila grounding on Nanbeige4.2-3B")
    parser.add_argument("--train-file", type=Path, default=DEFAULT_TRAIN_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--chat-file", type=Path)
    parser.add_argument("--num-epochs", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    args = parser.parse_args()

    if not args.train_file.exists():
        print(f"Train file not found: {args.train_file}", file=sys.stderr)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    full_chat = args.chat_file or (args.output_dir / "chat_full.jsonl")

    if not args.chat_file:
        n = records_to_chat_jsonl(args.train_file, full_chat)
        print(f"Built chat file: {full_chat} ({n} rows)")

    print(f"Starting Nanbeige 3B QLoRA fine-tuning (Base: {BASE_MODEL})")
    print(f"Epochs: {args.num_epochs}, Learning rate: {args.learning_rate}")

    train_nanbeige_peft(
        chat_file=full_chat,
        output_dir=args.output_dir,
        num_epochs=args.num_epochs,
        learning_rate=args.learning_rate,
    )

    print(f"Training finished. Checkpoint saved to: {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
