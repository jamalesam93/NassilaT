#!/usr/bin/env python3
"""Batch L3 eval via HuggingFace Transformers (Nanbeige fallback when vLLM fails)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from json_repair import parse_strict_json, try_parse_with_repair  # noqa: E402
from run_l3_eval_batch import fold_system_into_user  # noqa: E402
from validate_dataset import build_grounding_chat_messages, load_jsonl  # noqa: E402


def parse_status(raw: str, allow_repair: bool) -> tuple[str, bool]:
    ok, parsed, err = parse_strict_json(raw)
    if ok:
        return "ok", False
    if not allow_repair:
        return f"parse_fail:{err or 'invalid'}", False
    ok, parsed, err, repaired = try_parse_with_repair(raw)
    if ok and isinstance(parsed, dict) and isinstance(parsed.get("claims"), list):
        return ("ok_repaired" if repaired else "ok"), repaired
    return f"parse_fail:{err or 'invalid'}", repaired


def generate_one(
    model,
    tokenizer,
    messages: list[dict[str, str]],
    temperature: float,
    max_new_tokens: int,
) -> str:
    prompt = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=False,
        enable_thinking=False,
    )
    inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    gen_kwargs: dict = {
        "max_new_tokens": max_new_tokens,
        "do_sample": temperature > 0,
        "pad_token_id": tokenizer.eos_token_id,
    }
    if temperature > 0:
        gen_kwargs.update({"temperature": temperature, "top_p": 0.95, "top_k": 20})
    with torch.inference_mode():
        out = model.generate(**inputs, **gen_kwargs)
    new_tokens = out[0][inputs["input_ids"].shape[1] :]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Nanbeige/Nanbeige4.2-3B")
    parser.add_argument("--data", nargs="+", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--retry", type=int, default=1)
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument("--fold-system", action="store_true")
    args = parser.parse_args()

    rows: list[dict] = []
    seen: set[str] = set()
    for path in args.data:
        for _, r in load_jsonl(path):
            if r.get("task") != "l3_grounding":
                continue
            rid = r.get("id")
            if not rid or rid in seen:
                continue
            seen.add(rid)
            rows.append(r)

    if not rows:
        print("No rows", file=sys.stderr)
        return 1

    print(f"Loading {args.model}...")
    tokenizer = AutoTokenizer.from_pretrained(
        args.model, trust_remote_code=True, use_fast=False
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()
    print(f"Running {len(rows)} rows on {model.device}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    parse_strict = 0
    parse_after_repair = 0

    with args.out.open("w", encoding="utf-8") as f:
        for i, sample in enumerate(rows, 1):
            rid = sample["id"]
            messages = build_grounding_chat_messages(
                sample["passage"],
                sample["source_excerpt"],
                sample.get("meta", {}),
            )
            if args.fold_system:
                messages = fold_system_into_user(messages)

            last_raw = ""
            last_status = ""
            last_repaired = False
            t0 = time.time()
            for attempt in range(1, args.retry + 2):
                try:
                    last_raw = generate_one(
                        model,
                        tokenizer,
                        messages,
                        args.temperature,
                        args.max_new_tokens,
                    )
                except Exception as e:
                    last_status = f"error:{e}"
                    break
                last_status, last_repaired = parse_status(last_raw, args.repair)
                if last_status.startswith("ok"):
                    break
            elapsed = round(time.time() - t0, 1)

            if last_status == "ok":
                parse_strict += 1
            if last_status in ("ok", "ok_repaired"):
                parse_after_repair += 1

            f.write(
                json.dumps(
                    {
                        "id": rid,
                        "raw_output": last_raw,
                        "status": last_status,
                        "repaired_used": last_repaired,
                        "seconds": elapsed,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            f.flush()
            print(f"[{i}/{len(rows)}] {rid} {last_status} ({elapsed}s)")

    n = len(rows)
    print(f"Parse strict: {parse_strict}/{n}")
    print(f"Parse repair: {parse_after_repair}/{n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
