---
license: apache-2.0
base_model: google/gemma-4-12B-it
tags:
  - gguf
  - gemma
  - gemma4
  - nassila
  - sanad
  - l3-grounding
  - ouroboros
  - academic
  - text-generation
language:
  - en
  - ar
library_name: llama.cpp
---

# Nassila Sanad 12B

*Ship checkpoint: **v1.12** Tier 2 PASS · v1.13 **NO-GO** · v1.14+ in progress*

**Quality tier** — Gemma 4 12B Q6_K (~9 GB). Default fast tier: [`nassila-sanad-e4b`](https://huggingface.co/QinEmPeRoR93/nassila-sanad-e4b) (**v1.12**).

## v1.12 eval (115-row harness, multi-seed mean — 2026-06-19)

| Gate | Result | Target |
|------|--------|--------|
| Combined expect pass | **94.20%** | ≥90% |
| Quote validity (holdout) | **100%** | ≥98% |
| False supported (holdout) | **2.86%** | ≤5% |
| multi_claim (holdout) | **69.23%** | (not Tier 2 gate) |
| **Tier 2** | **PASS** (3/3 seeds) | all six |

Reports: `training/reports/ab_12b_q6_k_v112/`. h-043 pass; h-045 / h-088 still fail (bundled single claim).

## v1.13 — NO-GO (do not publish)

| Metric | v1.12 | v1.13 mean |
|--------|-------|------------|
| Combined expect | 94.20% | **88.99%** |
| Quote (holdout) | 100% | **94.74%** |
| Tier 2 pass | 3/3 | **0/3** |

Reports: `training/reports/ab_12b_q6_k_v113/`. h-045/h-088 → JSON parse failures. See [`EVAL_GONOGO.md`](https://github.com/jamalesam93/NassilaT/blob/main/training/EVAL_GONOGO.md).

## v1.14+ (operator)

Iterate until Tier 2 holds **and** h-045/h-088 pass. Map: [`POST_V113_MAP.md`](https://github.com/jamalesam93/NassilaT/blob/main/training/POST_V113_MAP.md). Walkthrough: [`PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md`](https://github.com/jamalesam93/NassilaT/blob/main/training/PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md).

## Dual-tier policy

| Tier | Model | Role |
|------|-------|------|
| Default | `nassila-sanad-e4b` Q6_K v1.12 | ~8 GB |
| **Quality** | **`nassila-sanad-12b` Q6_K v1.12** | Tier 2 ship |
