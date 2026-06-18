---
license: apache-2.0
base_model: google/gemma-4-E4B-it
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

# Nassila Sanad E4B (default tier)

*Ship checkpoint: **v1.10** (reference) · target **v1.12** recovery*

Default Sanad GGUF — Gemma 4 E4B Q6_K (~8 GB). Ships on **E4B default-tier gates**, not full Tier 2. See [`docs/DUAL_TIER_POLICY.md`](https://github.com/jamalesam93/NassilaT/blob/main/docs/DUAL_TIER_POLICY.md).

## v1.10 reference metrics (115-row harness, multi-seed mean)

| Metric | Value |
|--------|--------|
| Combined expect | **88.12%** |
| Quote validity (holdout) | **89.47%** |
| False supported (holdout) | **6.57%** |
| E4B default-tier | **PASS** |
| Tier 2 (quality bar) | FAIL (expected for E4B) |

**Do not publish v1.11** (regressed to 80.58% combined).

## v1.12 recovery train

```bash
ARM=e4b PHASE=12 MULTI_SEED=1 bash training/scripts/run_ab_pilot_pipeline.sh
```

Publish when `e4b_default_gates` pass **and** `v110_baseline_beat` is met: [`PHASE2_11_V112_WALKTHROUGH.md`](https://github.com/jamalesam93/NassilaT/blob/main/training/PHASE2_11_V112_WALKTHROUGH.md).

## Quality tiers (optional)

- [`nassila-sanad-12b`](https://huggingface.co/QinEmPeRoR93/nassila-sanad-12b) — Tier 2 PASS (v1.10)
- `nassila-sanad-31b` — premium, Tier 2 target (v1.12 train)
