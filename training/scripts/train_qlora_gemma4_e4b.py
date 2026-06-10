#!/usr/bin/env python3
"""
QLoRA fine-tuning template for Nassila L3 grounding on Gemma 4 E4B.

IMPORTANT:
  - Run on a GPU machine (Linux/WSL/cloud). Not on the LM Studio GGUF file.
  - BASE_MODEL: google/gemma-4-E4B-it (Apache 2.0 on Hugging Face).
  - Install optional deps from requirements.txt (uncomment torch/peft/trl lines).

Usage:
  python scripts/train_qlora_gemma4_e4b.py \\
    --train-file data/l3_grounding_samples.jsonl \\
    --output-dir outputs/nassila-grounding-v1

  # Export chat JSONL first:
  python scripts/validate_dataset.py data/l3_grounding_samples.jsonl \\
    --export-chat data/l3_grounding_chat.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from validate_dataset import build_grounding_user_prompt, load_jsonl  # noqa: E402

# --- Configuration (edit before running) ---
BASE_MODEL = "google/gemma-4-E4B-it"
MAX_SEQ_LENGTH = 4096
LORA_R = 32
LORA_ALPHA = 64
LORA_DROPOUT = 0.05
LEARNING_RATE = 2e-4
NUM_EPOCHS = 2
BATCH_SIZE = 1
GRAD_ACCUM = 8


def records_to_chat_jsonl(input_path: Path, output_path: Path) -> int:
    rows = load_jsonl(input_path)
    count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as out:
        for _, record in rows:
            if record.get("task") != "l3_grounding":
                continue
            user = build_grounding_user_prompt(
                record["passage"],
                record["source_excerpt"],
                record.get("meta", {}),
            )
            assistant = json.dumps(record["output"], ensure_ascii=False)
            chat = {
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
            out.write(json.dumps(chat, ensure_ascii=False) + "\n")
            count += 1
    return count


def train_with_unsloth(chat_file: Path, output_dir: Path) -> None:
    """
    Unsloth path (recommended). See https://unsloth.ai/docs/models/gemma-4/train
    """
    try:
        from unsloth import FastLanguageModel  # type: ignore
        from trl import SFTTrainer  # type: ignore
        from transformers import TrainingArguments  # type: ignore
        from datasets import load_dataset  # type: ignore
    except ImportError as e:
        raise SystemExit(
            "Missing training deps. Install Unsloth + trl + transformers + datasets on a GPU machine.\n"
            f"Original error: {e}"
        ) from e

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=MAX_SEQ_LENGTH,
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )

    dataset = load_dataset("json", data_files=str(chat_file), split="train")

    def formatting_func(examples):
        texts = []
        for messages in examples["messages"]:
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False,
            )
            texts.append(text)
        return {"text": texts}

    dataset = dataset.map(formatting_func, batched=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LEARNING_RATE,
        logging_steps=5,
        save_steps=50,
        warmup_ratio=0.05,
        fp16=False,
        bf16=True,
        report_to="none",
        save_strategy="no",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        args=training_args,
    )

    trainer.train()
    model.save_pretrained(str(output_dir / "lora_adapter"))
    tokenizer.save_pretrained(str(output_dir / "lora_adapter"))

    print(f"Saved LoRA adapter to {output_dir / 'lora_adapter'}")
    print("Export GGUF for LM Studio, e.g.:")
    print("  model.save_pretrained_gguf('exports/nassila-q6_k', tokenizer, quantization_method='q6_k')")


def train_with_peft(chat_file: Path, output_dir: Path) -> None:
    """
    Standard Hugging Face + PEFT QLoRA fallback (more manual than Unsloth).
    """
    try:
        import torch  # type: ignore
        from datasets import load_dataset  # type: ignore
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training  # type: ignore
        from transformers import (  # type: ignore
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            TrainingArguments,
        )
        from trl import SFTTrainer  # type: ignore
    except ImportError as e:
        raise SystemExit(
            "Missing torch/peft/transformers/trl/datasets. Install on GPU machine.\n"
            f"Original error: {e}"
        ) from e

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb,
        device_map="auto",
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )
    model = get_peft_model(model, lora_config)

    dataset = load_dataset("json", data_files=str(chat_file), split="train")

    def formatting_func(examples):
        texts = []
        for messages in examples["messages"]:
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False,
            )
            texts.append(text)
        return {"text": texts}

    dataset = dataset.map(formatting_func, batched=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LEARNING_RATE,
        logging_steps=5,
        save_steps=50,
        bf16=True,
        report_to="none",
        save_strategy="no",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        args=training_args,
    )

    trainer.train()
    model.save_pretrained(str(output_dir / "lora_adapter"))
    tokenizer.save_pretrained(str(output_dir / "lora_adapter"))
    print(f"Saved LoRA adapter to {output_dir / 'lora_adapter'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="QLoRA template for Nassila grounding")
    parser.add_argument("--train-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=TRAINING_DIR / "outputs" / "nassila-grounding-v1")
    parser.add_argument(
        "--backend",
        choices=("unsloth", "peft"),
        default="unsloth",
        help="Training backend (unsloth recommended if available)",
    )
    parser.add_argument(
        "--chat-file",
        type=Path,
        help="Pre-built chat JSONL; if omitted, generated from train-file",
    )
    args = parser.parse_args()

    if not args.train_file.exists():
        print(f"Train file not found: {args.train_file}", file=sys.stderr)
        return 1

    chat_file = args.chat_file or (args.output_dir / "chat_train.jsonl")
    if not args.chat_file:
        n = records_to_chat_jsonl(args.train_file, chat_file)
        print(f"Built chat file: {chat_file} ({n} rows)")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.backend == "unsloth":
        train_with_unsloth(chat_file, args.output_dir)
    else:
        train_with_peft(chat_file, args.output_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
