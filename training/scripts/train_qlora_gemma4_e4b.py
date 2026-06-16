#!/usr/bin/env python3
"""
QLoRA fine-tuning for Nassila L3 grounding on Gemma 4 E4B (v1.4 / v1.5).

v1.4a: schema/balance fixes, v1.3 hyperparams (2 ep, 1e-4)
v1.4b: same data, v1.2 hyperparams (3 ep, 1.5e-4)
v1.5:  v1.4a data + boost rows, v1.4a hyperparams (2 ep, 1e-4)
v1.6:  decontaminated boost + weak/insufficient rows, v1.4a hyperparams (2 ep, 1e-4)
v1.7:  v1.6 + compound/evidential boost — **no eval delta vs v1.6** (dropped for v1.8)
v1.8:  v1.6 boost + passage-claim prompt + v18 boost (no v17); v1.4a hyperparams (2 ep, 1e-4)

Default train file: data/l3_grounding_train_v14a.jsonl (seq-safe, 850 rows).
v1.5: data/l3_grounding_train_v15.jsonl via prepare_v15_train.py.

Unsloth + Gemma4: save_strategy="no" (mid-training checkpoints pickle-fail on Vast).

Usage:
  python scripts/prepare_v14_train.py
  python scripts/validate_dataset.py data/l3_grounding_train_v14a.jsonl \\
    --export-chat data/l3_grounding_chat.jsonl --strict-length 2048

  python scripts/train_qlora_gemma4_e4b.py --phase 4b \\
    --train-file data/l3_grounding_train_v14a.jsonl \\
    --chat-file data/l3_grounding_chat.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from validate_dataset import build_grounding_user_prompt, load_jsonl  # noqa: E402

# --- Configuration ---
BASE_MODEL = "google/gemma-4-E4B-it"
MAX_SEQ_LENGTH = 2048
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
BATCH_SIZE = 1
GRAD_ACCUM = 8
EVAL_HOLDOUT_FRACTION = 0.05

DEFAULT_TRAIN_FILE = TRAINING_DIR / "data" / "l3_grounding_train_v14a.jsonl"

PHASE_CONFIG = {
    "4a": {
        "num_epochs": 2,
        "learning_rate": 1e-4,
        "output_name": "nassila-grounding-e4b-v1.4a",
    },
    "4b": {
        "num_epochs": 3,
        "learning_rate": 1.5e-4,
        "output_name": "nassila-grounding-e4b-v1.4b",
    },
    "5": {
        "num_epochs": 2,
        "learning_rate": 1e-4,
        "output_name": "nassila-grounding-e4b-v1.5",
    },
    "6": {
        "num_epochs": 2,
        "learning_rate": 1e-4,
        "output_name": "nassila-grounding-e4b-v1.6",
    },
    "7": {
        "num_epochs": 2,
        "learning_rate": 1e-4,
        "output_name": "nassila-grounding-e4b-v1.7",
    },
    "8": {
        "num_epochs": 2,
        "learning_rate": 1e-4,
        "output_name": "nassila-grounding-e4b-v1.8",
    },
}


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


def split_train_eval(
    chat_file: Path, train_out: Path, eval_out: Path, seed: int = 46
) -> tuple[int, int]:
    """Hold out ~5% of chat rows for eval loss during training."""
    lines = [ln.strip() for ln in chat_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    rng = random.Random(seed)
    indices = list(range(len(lines)))
    rng.shuffle(indices)
    n_eval = max(1, int(len(lines) * EVAL_HOLDOUT_FRACTION))
    eval_idx = set(indices[:n_eval])
    train_out.parent.mkdir(parents=True, exist_ok=True)
    n_train = n_eval_rows = 0
    with train_out.open("w", encoding="utf-8") as tf, eval_out.open("w", encoding="utf-8") as ef:
        for i, line in enumerate(lines):
            if i in eval_idx:
                ef.write(line + "\n")
                n_eval_rows += 1
            else:
                tf.write(line + "\n")
                n_train += 1
    return n_train, n_eval_rows


def train_with_unsloth(
    chat_file: Path,
    output_dir: Path,
    *,
    num_epochs: int,
    learning_rate: float,
) -> None:
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
        use_gradient_checkpointing="unsloth",
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

    # save_strategy="no": Unsloth/Gemma4 pickles SFTConfig on checkpoint save (Vast crash).
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=num_epochs,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=learning_rate,
        logging_steps=5,
        warmup_ratio=0.05,
        fp16=False,
        bf16=True,
        report_to="none",
        save_strategy="no",
        eval_strategy="no",
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


def train_with_peft(
    chat_file: Path,
    output_dir: Path,
    *,
    num_epochs: int,
    learning_rate: float,
) -> None:
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
        raise SystemExit(f"Missing torch/peft/transformers/trl/datasets.\nOriginal error: {e}") from e

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
        num_train_epochs=num_epochs,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=learning_rate,
        logging_steps=5,
        bf16=True,
        report_to="none",
        save_strategy="no",
        eval_strategy="no",
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
    parser = argparse.ArgumentParser(description="QLoRA for Nassila grounding v1.4 / v1.5")
    parser.add_argument(
        "--train-file",
        type=Path,
        default=DEFAULT_TRAIN_FILE,
        help="Train JSONL (default: data/l3_grounding_train_v14a.jsonl)",
    )
    parser.add_argument(
        "--phase",
        choices=tuple(PHASE_CONFIG.keys()),
        default="5",
        help="4a–7 = prior phases; 8 = v1.8 passage-claim prompt + v18 boost (v1.4a hyperparams)",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--backend", choices=("unsloth", "peft"), default="unsloth")
    parser.add_argument("--chat-file", type=Path, help="Pre-built chat JSONL")
    parser.add_argument("--seed", type=int, default=46)
    parser.add_argument(
        "--eval-split",
        action="store_true",
        help="Split 5%% eval holdout (not recommended: no checkpoint save with Unsloth)",
    )
    args = parser.parse_args()

    if not args.train_file.exists():
        print(f"Train file not found: {args.train_file}", file=sys.stderr)
        print("Run: python scripts/prepare_v14_train.py", file=sys.stderr)
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
        f"Phase {args.phase}: epochs={phase['num_epochs']}, lr={phase['learning_rate']}, "
        f"max_seq={MAX_SEQ_LENGTH}, save_strategy=no, out={output_dir}"
    )

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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
