# Gemma 4 E4B Fine-Tuning Guide for Nassila

This is the main step-by-step guide. Read it once end-to-end, then execute phase by phase.

**Ouroboros context:** Nassila [`docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md). This guide covers **Phase 1–2** — forge worker **Sanad** (`l3_grounding`) → **`nassila-grounding-e4b-v1.4a`**. Later workers reuse the same JSONL discipline before merging into **`nassila-agent-*`**.

---

## Table of contents

1. [Concepts in plain language](#1-concepts-in-plain-language)
2. [Baseline with your LM Studio model](#2-baseline-with-your-lm-studio-model)
3. [Phase 1 — Prepare your environment](#3-phase-1--prepare-your-environment)
4. [Phase 2 — Build your dataset](#4-phase-2--build-your-dataset)
5. [Phase 3 — QLoRA fine-tuning](#5-phase-3--qlora-fine-tuning)
6. [Phase 4 — Export for LM Studio](#6-phase-4--export-for-lm-studio)
7. [Phase 5 — Evaluate before shipping](#7-phase-5--evaluate-before-shipping)
8. [Phase 6 — Connect to Nassila](#8-phase-6--connect-to-nassila)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Concepts in plain language

### Base model vs instruct model

- **Base model** — raw text completion; not ideal for chat/JSON tasks.
- **Instruct model (IT)** — trained to follow instructions; use **`google/gemma-4-E4B-it`** on Hugging Face for QLoRA.

### GGUF vs safetensors

| Format | Used for |
|--------|----------|
| **safetensors** | Training, merging adapters on GPU |
| **GGUF (Q4/Q6/Q8)** | Local inference in LM Studio, llama.cpp, Ollama |

Your **Q6_K download in LM Studio is GGUF** → inference only.

### LoRA and QLoRA

Fine-tuning all 8B+ parameters needs lots of VRAM. **LoRA** trains small adapter matrices instead.

- **LoRA** — adapter weights in higher precision; more VRAM.
- **QLoRA** — base model in 4-bit; adapter in higher precision; **recommended for E4B on one GPU**.

You are not “rebuilding Gemma”; you are teaching it **one specialist behavior** for Nassila.

### What “training” means for this app

The model learns to map:

```
(passage + source_excerpt + instructions)  →  JSON with claims and verdicts
```

That JSON must match what [`parseGroundingJson`](../src/engine/manuscript/grounding-llm.ts) expects.

---

## 2. Baseline with your LM Studio model

**Goal:** Measure stock Gemma 4 E4B Q6_K *before* fine-tuning.

### 2.1 Start LM Studio local server

1. Load **Gemma 4 E4B Instruct Q6_K** in LM Studio.
2. Open the **Local Server** tab.
3. Start server (default port often **1234**).
4. Note the **model identifier** shown in the server UI (you will pass it to API calls).

### 2.2 Run smoke test

```bash
cd training
pip install -r requirements.txt
python scripts/lmstudio_smoke_test.py ^
  --base-url http://localhost:1234 ^
  --model "google/gemma-4-e4b" ^
  --task l3_grounding
```

On PowerShell, use backticks or single line:

```powershell
python scripts/lmstudio_smoke_test.py --base-url http://localhost:1234 --model "google/gemma-4-e4b" --task l3_grounding
```

Save the output. You will compare parse rate and quote validity after fine-tuning.

### 2.3 Record baseline metrics

Run evaluation on a few rows from [`data/eval_samples.jsonl`](./data/eval_samples.jsonl) manually or with your own script. Track:

- JSON parse success rate
- Valid `sourceQuotes` (substring of excerpt)
- Obvious false `supported` cases

See [EVALUATION_GUIDE.md](./EVALUATION_GUIDE.md) for thresholds.

---

## 3. Phase 1 — Prepare your environment

### Option A — Unsloth (recommended for beginners)

Unsloth documents Gemma 4 E4B training with lower VRAM use and GGUF export helpers.

1. Use **Linux, WSL2, or a cloud GPU** (training on Windows native is possible but WSL/cloud is smoother).
2. Install Python 3.10+ and CUDA-matched PyTorch.
3. Follow [Unsloth Gemma 4 docs](https://unsloth.ai/docs/models/gemma-4/train).

```bash
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install --no-deps trl peft accelerate bitsandbytes
```

### Option B — Hugging Face + PEFT (more manual)

Use the template script [`scripts/train_qlora_gemma4_e4b.py`](./scripts/train_qlora_gemma4_e4b.py). Adjust `BASE_MODEL` to the exact Hugging Face repo name available when you train.

### Hugging Face access

Training uses **`google/gemma-4-E4B-it`** (Apache 2.0). Confirm **Files and versions** on https://huggingface.co/google/gemma-4-E4B-it — no separate gated-access button for this release.

1. Create a **Read** token at https://huggingface.co/settings/tokens
2. Install the modern HF CLI and login:

```bash
pip install -U "huggingface_hub[cli]"
hf auth login
hf auth whoami
```

3. Optional access test (small file; do this **before** renting a cloud GPU):

```bash
hf download google/gemma-4-E4B-it config.json --local-dir ./hf_test
```

### Python deps (validation/eval only on your PC)

```bash
cd training
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 4. Phase 2 — Build your dataset

### 4.1 Start from samples

Copy and expand:

- [`data/l3_grounding_samples.jsonl`](./data/l3_grounding_samples.jsonl) — primary task
- [`data/webpage_citation_samples.jsonl`](./data/webpage_citation_samples.jsonl) — phase 2 task

Full field definitions: [DATASET_SCHEMA.md](./DATASET_SCHEMA.md).

### 4.2 Validate before training

```bash
python scripts/validate_dataset.py data/l3_grounding_samples.jsonl
python scripts/validate_dataset.py data/webpage_citation_samples.jsonl
```

Fix all errors. Common failures:

- `sourceQuotes` not literally contained in `source_excerpt`
- Invalid verdict enum
- Missing `task` field

### 4.3 Dataset size targets

| Stage | L3 grounding rows | Notes |
|-------|-------------------|-------|
| Prototype | 50–100 | Enough to test pipeline |
| Useful v1 | 300–800 | Mix all verdict types |
| Strong v1 | 1,000+ | Include hard negatives |

**Balance matters.** Include many `weak`, `not_in_source`, and `contradicted` examples — not only easy `supported` cases.

### 4.4 Convert to chat format

Each JSONL row becomes a multi-turn example:

- **System:** short role (optional; can match app prompt opening lines)
- **User:** same text as `buildGroundingUserPrompt` in the app
- **Assistant:** the gold JSON string (no markdown fences)

Example conversion logic (conceptual):

```python
def to_chat_row(record):
    user = build_user_prompt(record["passage"], record["source_excerpt"], record["meta"])
    assistant = json.dumps(record["output"], ensure_ascii=False)
    return {
        "messages": [
            {"role": "system", "content": "You are a strict academic citation grounding assistant."},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ]
    }
```

Keep prompts **identical** to production ([`grounding-llm.ts`](../src/engine/manuscript/grounding-llm.ts)) so the model learns the real task.

### 4.5 Hold out eval data

Move 10–20% to `eval_private.jsonl` (do **not** commit private eval if it contains real manuscript text). Use [`data/eval_samples.jsonl`](./data/eval_samples.jsonl) as a public synthetic eval template.

---

## 5. Phase 3 — QLoRA fine-tuning

### 5.1 Recommended starting hyperparameters (E4B)

These are starting points — tune with your eval set:

| Parameter | Starting value | Why |
|-----------|----------------|-----|
| LoRA rank `r` | 16–32 | Structured JSON task; 64 if underfitting |
| LoRA alpha | 2× rank | Common PEFT rule of thumb |
| LoRA dropout | 0.05 | Mild regularization |
| Learning rate | 1e-4 to 2e-4 | Standard for LoRA |
| Epochs | 1–3 | Stop if eval JSON parse rate drops |
| Max seq length | 2048–4096 | Passage + excerpt ~4k chars fits |
| Batch size | As large as VRAM allows | Use gradient accumulation if needed |

Target modules (text-only L3): attention + MLP projections (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`). Disable vision/audio modules for text-only grounding.

### 5.2 Using the template script

Edit paths at the top of [`scripts/train_qlora_gemma4_e4b.py`](./scripts/train_qlora_gemma4_e4b.py), then:

```bash
python scripts/train_qlora_gemma4_e4b.py \
  --train-file data/l3_grounding_samples.jsonl \
  --output-dir outputs/nassila-grounding-v1
```

The script is a **template**. Verify the exact `BASE_MODEL` name on Hugging Face before running.

### 5.3 Unsloth notebook-style flow (alternative)

```python
from unsloth import FastLanguageModel
import torch

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="google/gemma-4-E4B-it",
    max_seq_length=4096,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=32,
    lora_alpha=64,
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
)

# Load JSONL → Dataset with "text" or "messages" column
# Train with SFTTrainer (trl) ...
```

Monitor:

- Training loss decreasing
- Eval JSON parse rate **increasing**
- False `supported` rate **not** increasing

### 5.4 What not to do

- Do not train on eval rows.
- Do not strip the JSON schema from assistant answers.
- Do not add markdown ```json fences in training labels (production parser expects raw JSON).
- Do not optimize for fluent prose — optimize for **valid structured output**.

---

## 6. Phase 4 — Export for LM Studio

After training you have an **adapter folder** (LoRA weights). For LM Studio you need **GGUF**.

### Path A — Unsloth export (easiest)

```python
model.save_pretrained_gguf(
    "exports/nassila-grounding-q6_k",
    tokenizer,
    quantization_method="q6_k",  # match your preference
)
```

### Path B — Merge adapter then convert

1. Merge LoRA into base weights (safetensors) via `scripts/merge_adapter_gemma4.py`.
2. Convert to GGUF with llama.cpp — **Vast:** [LLAMA_CPP_VAST.md](./LLAMA_CPP_VAST.md) (pinned tag `b9608`, UI off).
3. Quantize to **Q6_K** if that is your target runtime.

### Load in LM Studio

1. **Import** the new GGUF file (or place in LM Studio models folder).
2. Update llama.cpp runtime if load fails (Gemma 4 needs recent runtime).
3. Name it clearly: `nassila-grounding-e4b-q6_k-v1.gguf`.
4. Start local server and re-run smoke test.

---

## 7. Phase 5 — Evaluate before shipping

### 7.1 Generate predictions

For each row in `eval_samples.jsonl`, call your model with the user prompt and save raw text to `predictions.jsonl`:

```json
{"id": "eval-001", "raw_output": "{ \"claims\": [...] }"}
```

### 7.2 Run evaluator

```bash
python scripts/evaluate_outputs.py \
  --eval data/eval_samples.jsonl \
  --predictions outputs/predictions.jsonl
```

### 7.3 Acceptance (v1 targets)

See [EVALUATION_GUIDE.md](./EVALUATION_GUIDE.md). Minimum bar before calling it “Nassila grounding v1”:

- JSON parse rate ≥ **95%**
- Supported claims with valid quotes ≥ **98%**
- False supported on contradicted/numeric-mismatch eval ≤ **5%**

Compare against the stock-model baseline. Fine-tuning should improve these, not just training loss.

---

## 8. Phase 6 — Connect to Nassila

Full wiring: [LM_STUDIO_INTEGRATION.md](./LM_STUDIO_INTEGRATION.md).

Summary:

1. LM Studio server at `http://localhost:1234`
2. In manuscript audit settings (when UI returns): preset **vLLM / LM Studio**
3. Base URL: `http://localhost:1234` (no `/v1` suffix — app appends it)
4. Model: exact id from LM Studio server
5. API key: any placeholder for local (app allows short key for localhost)

The app calls [`llm:chat`](../src/main/ipc-llm.ts) → `{baseUrl}/v1/chat/completions` with `temperature: 0.2`.

---

## 9. Troubleshooting

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| Model returns markdown fences | Training labels had fences | Retrain with raw JSON only; add retry in app |
| Empty responses in LM Studio | Old llama.cpp runtime | Update LM Studio runtime to 2.10.1+ |
| OOM during training | Full fine-tune or seq too long | Use QLoRA; reduce seq length; cloud GPU |
| Good loss, bad eval | Overfit or prompt mismatch | Match production prompt; add hard negatives |
| Quotes not in excerpt | Bad labels or model hallucination | Fix dataset; penalize in eval; keep app guardrails |
| “Failed to load model” | GGUF/arch mismatch | Re-export; verify Gemma 4 GGUF build |

---

## Version naming

Use clear version tags:

- `nassila-grounding-e4b-v1` — L3 JSON grounding
- `nassila-webcite-e4b-v1` — webpage metadata (later)
- Document dataset version + eval scores in a local `MODEL_CARD.md` (not required in repo)

---

## Related files

- [DATASET_SCHEMA.md](./DATASET_SCHEMA.md)
- [EVALUATION_GUIDE.md](./EVALUATION_GUIDE.md)
- [LM_STUDIO_INTEGRATION.md](./LM_STUDIO_INTEGRATION.md)
- [ROADMAP.md](./ROADMAP.md)
- App prompt source: [`src/engine/manuscript/grounding-llm.ts`](../src/engine/manuscript/grounding-llm.ts)
