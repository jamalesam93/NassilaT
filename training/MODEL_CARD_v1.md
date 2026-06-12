# Model card — `nassila-grounding-e4b-v1-adapter` (NO-GO)

**Hugging Face:** `QinEmPeRoR93/nassila-grounding-e4b-v1-adapter`  
**Status:** evaluation **NO-GO** — not for production. Kept for baseline comparison.

Copy the body below into the HF repo README if not already published.

---

```markdown
---
license: apache-2.0
base_model: google/gemma-4-E4B-it
tags:
  - lora
  - gemma
  - gemma4
  - nassila
  - l3-grounding
  - academic
  - peft
library_name: peft
pipeline_tag: text-generation
---

# Nassila grounding E4B v1 — LoRA adapter (NO-GO)

QLoRA adapter for **l3_grounding**: manuscript passage vs **abstract** excerpt → structured JSON claims.

**Status: evaluation NO-GO — not recommended for production use.**

## Training

| Field | Value |
|-------|--------|
| Task | `l3_grounding` (abstract-only excerpts) |
| Base model | `google/gemma-4-E4B-it` |
| Method | QLoRA (Unsloth) on Vast RTX A6000 |
| Train rows | 400 |
| Seq length | 1536 |
| LoRA r / α | 16 / 32 |
| Epochs | 2 |
| Effective batch | 8 |
| Code / data | [NassilaT](https://github.com/jamalesam93/NassilaT) |

## Evaluation (50 rows, JSON repair allowed)

| Metric | Baseline (stock E4B Q6_K) | Tuned v1 | Target |
|--------|---------------------------|----------|--------|
| JSON parse (with repair) | ~100% | **100%** | ≥95% |
| Expect pass rate | ~82% | **~62%** | ≥90% |
| Quote validity (holdout) | — | **~0%** | ≥98% |
| False supported | ~11.8% | **0%** | ≤5% |

### Failure mode

Holdout **supported** paraphrase (e.g. h-001): model returns **`weak`** instead of **`supported`** when passage paraphrases the abstract with matching numbers.

## Usage

LoRA weights only. Merge with base via `scripts/merge_adapter_gemma4.py`, export GGUF with llama.cpp.

## Related

- Successor experiment: `nassila-grounding-e4b-v1.1-adapter`
- Full card in repo: `training/MODEL_CARD_v1.md`
```
