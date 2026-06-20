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

*Ship: **v1.12** Tier 2 PASS · **v1.13** pending (h-045 / h-088 boost)*

**Main quality tier** — Gemma 4 12B Q6_K (~9 GB). Same v1.12 data + prompt as E4B recovery. Default fast tier: [`nassila-sanad-e4b`](https://huggingface.co/QinEmPeRoR93/nassila-sanad-e4b) (**v1.12 ship**).

## v1.12 eval (115-row harness, multi-seed mean — 2026-06-19)

| Gate | Result | Target |
|------|--------|--------|
| Combined expect pass | **94.20%** | ≥90% |
| Quote validity (holdout) | **100%** | ≥98% |
| False supported (holdout) | **2.86%** | ≤5% |
| multi_claim (holdout) | **69.23%** | (not ship gate) |
| **Tier 2** | **PASS** (3/3 seeds) | all six |

Reports: `training/reports/ab_12b_q6_k_v112/`. h-043 pass; h-045 / h-088 still fail (bundled single claim).

## v1.13 train (operator — 12B only, multi_claim boost)

```bash
ARM=12b PHASE=13 MULTI_SEED=1 bash training/scripts/run_ab_pilot_pipeline.sh
```

Walkthrough: [`PHASE2_13_12B_MULTI_CLAIM_WALKTHROUGH.md`](https://github.com/jamalesam93/NassilaT/blob/main/training/PHASE2_13_12B_MULTI_CLAIM_WALKTHROUGH.md). Target: h-045 + h-088 pass; `multi_claim` ≥80%.

## v1.10 reference (pre-gold-fix harness)

| Gate | Result | Target |
|------|--------|--------|
| Combined expect pass | **94.79%** | ≥90% |
| Quote validity (holdout) | **100%** | ≥98% |
| False supported (holdout) | **2.82%** | ≤5% |
| **Tier 2** | **PASS** | all six |

*Scored on pre–h-043-fix gold; regrade on corrected gold expected ~96% without retrain. v1.12 train targets h-045 / multi_claim fixes.*

## Dual-tier policy

| Tier | Model | Role |
|------|-------|------|
| Default | `nassila-sanad-e4b` Q6_K | ~8 GB |
| **Quality (main)** | **`nassila-sanad-12b` Q6_K** | Tier 2 ship target |
