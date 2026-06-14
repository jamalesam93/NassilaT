---
license: apache-2.0
base_model: google/gemma-4-E4B-it
tags:
  - lora
  - gemma
  - gemma4
  - nassila
  - l3-grounding
  - sanad
  - ouroboros
  - academic
  - peft
library_name: peft
pipeline_tag: text-generation
---

# Nassila grounding E4B v1.4a — LoRA adapter (SHIP)

Fourth QLoRA iteration (**Sanad** worker, Nassila Ouroboros). **Recommended production adapter** for `l3_grounding` as of v1.4.

Fixes v1.3 JSON schema drift (`hasNumericClaim` last), priority-balanced train rows, prompt dedup, and seq-safe excerpts (2048 tokens).

## Status

**Evaluation GATE PASS — use this adapter for merge/GGUF/LM Studio.**

Sibling experiment [v1.4b-adapter](https://huggingface.co/QinEmPeRoR93/nassila-grounding-e4b-v1.4b-adapter) scored lower on combined expect; archived for comparison only.

## Training

| Field | Value |
|-------|--------|
| Task | `l3_grounding` (abstract-only excerpts) |
| Worker | **Sanad** (`l3_grounding`) |
| Base model | [`google/gemma-4-E4B-it`](https://huggingface.co/google/gemma-4-E4B-it) |
| Method | QLoRA (Unsloth), Vast RTX A6000 |
| Train file | `l3_grounding_train_v14a.jsonl` (850 rows, capped excerpts) |
| Seq length | 2048 |
| LoRA r / α | 16 / 32 |
| Epochs | **2** |
| Learning rate | **1e-4** (v1.3 recipe) |
| `save_strategy` | `no` (Unsloth/Gemma4 checkpoint pickle workaround) |
| Export | `merge_adapter_gemma4.py` → llama.cpp **b9608** → Q6_K |
| Code | [NassilaT](https://github.com/jamalesam93/NassilaT) — `training/PHASE2_7_V1_4_WALKTHROUGH.md` |

## Evaluation (Vast, llama-server + Q6_K, 70 rows)

| Metric | v1.2 | v1.3 | v1.4a | Target |
|--------|------|------|-------|--------|
| Combined expect pass | 86% | 80% | **90%** | ≥90% |
| JSON parse (repair) | 100% | 86% | **100%** | ≥98% |
| Supported h-001–h-010 | 9/10 | 3/10 | **8/10** | ≥8/10 |
| Core eval (legacy 5) | 2/5 | 5/5 | **5/5** | 5/5 |
| Quote validity (holdout) | 90.9% | 36.4% | **81.8%** | ≥98% |
| False supported (holdout) | 0% | 2.9% | **2.9%** | ≤5% |

### What improved vs v1.3

- **JSON parse** on supported holdout: `parse_json` cluster → **pass** (schema fix)
- **Combined expect**: 80% → **90%**
- **Core legacy 5/5** retained

### Known gaps (v1.5 targets)

- Quote validity still **81.8%** (target ≥98%)
- Paraphrase supported: **h-006**, **h-010**
- Multi-claim edge cases: **h-043**, **h-045**

## Usage

1. Merge adapter with base Gemma 4 E4B IT (see NassilaT `merge_adapter_gemma4.py`).
2. Convert to GGUF (llama.cpp b9608) and quantize Q6_K.
3. Load in LM Studio; local server `http://127.0.0.1:1234`.
4. Point Nassila manuscript-audit preset at the server (when UI is enabled).

## Limitations

- Trained on **abstract excerpts**, not full PDF text
- Advisory only — pair with Nassila deterministic guardrails
- Not bundled in Nassila installer — bring your own GGUF

## Related

- [v1.4b adapter (NO-GO)](https://huggingface.co/QinEmPeRoR93/nassila-grounding-e4b-v1.4b-adapter)
- [MODEL_CARD_v1_4.md](https://github.com/jamalesam93/NassilaT/blob/main/training/MODEL_CARD_v1_4.md)
