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

# Nassila grounding E4B v1.4b — LoRA adapter (NO-GO)

Fifth QLoRA experiment in the v1.4 line (**Sanad** worker). Same train data as v1.4a with **v1.2 hyperparams** (3 epochs @ 1.5e-4) to test quote-validity and semantic-supported gains.

**Status: evaluation NO-GO — not recommended for production.**

Use [**v1.4a-adapter**](https://huggingface.co/QinEmPeRoR93/nassila-grounding-e4b-v1.4a-adapter) instead. This repo is archived for A/B comparison and training history.

## Why v1.4b

v1.4a passed the JSON/supported gate (90% combined) but quote validity remained **81.8%** (target ≥98%). v1.4b isolated the hyperparameter change from v1.4a to see if longer training improved paraphrase-supported and multi-claim rows.

**Result:** combined expect **regressed** (90% → 87.1%); quote validity **unchanged**; new regressions on h-008 and h-034.

## Training

| Field | Value |
|-------|--------|
| Task | `l3_grounding` (abstract-only excerpts) |
| Base model | [`google/gemma-4-E4B-it`](https://huggingface.co/google/gemma-4-E4B-it) |
| Method | QLoRA (Unsloth), Vast RTX A6000 |
| Train file | `l3_grounding_train_v14a.jsonl` (850 rows, same as 4a) |
| Seq length | 2048 |
| LoRA r / α | 16 / 32 |
| Epochs | **3** |
| Learning rate | **1.5e-4** (v1.2 recipe) |
| `save_strategy` | `no` |
| Export | `merge_adapter_gemma4.py` → llama.cpp **b9608** → Q6_K |
| Code | [NassilaT](https://github.com/jamalesam93/NassilaT) |

## Evaluation (Vast, llama-server + Q6_K, 70 rows)

| Metric | v1.4a | v1.4b | Target |
|--------|-------|-------|--------|
| Combined expect pass | **90%** | 87.1% | ≥90% |
| JSON parse (repair) | 100% | **100%** | ≥98% |
| Supported h-001–h-010 | 8/10 | **8/10** | ≥8/10 |
| Core eval (legacy 5) | 5/5 | **5/5** | 5/5 |
| Extended core (20) | **85%** | 80% | — |
| Holdout expect | **91.1%** | 88.9% | — |
| Quote validity (holdout) | 81.8% | **81.8%** | ≥98% |
| False supported (holdout) | 2.9% | **0%** | ≤5% |

### vs v1.4a on holdout

| Row | v1.4a | v1.4b |
|-----|-------|-------|
| h-006 | fail | **pass** |
| h-008 | pass | **fail** |
| h-010 | fail | fail |
| h-034 | pass | **fail** |
| h-043 | forbidden_verdict | wrong_verdict |
| h-045 | fail | fail |

## Usage

Research / comparison only. For deployment, merge and export **v1.4a** instead.

## Limitations

- Same abstract-only training scope as v1.4a
- Extra epochs did not fix quote validity — likely needs v1.5 data or loss changes, not more LR/epochs

## Related

- [**v1.4a adapter (SHIP)**](https://huggingface.co/QinEmPeRoR93/nassila-grounding-e4b-v1.4a-adapter)
- [MODEL_CARD_v1_4.md](https://github.com/jamalesam93/NassilaT/blob/main/training/MODEL_CARD_v1_4.md)
