---
license: apache-2.0
base_model: google/gemma-4-31B-it
tags:
  - gguf
  - gemma
  - gemma4
  - nassila
  - sanad
  - l3-grounding
  - ouroboros
  - premium
  - academic
  - text-generation
language:
  - en
  - ar
library_name: llama.cpp
---

# Nassila Sanad 31B (premium tier)

*Train checkpoint **v1.12** · Tier 2 quality target*

Premium Sanad GGUF — Gemma 4 31B dense (~30.7B params). Same v1.12 grounding data and prompt as E4B recovery. Targets **full Tier 2** gates on the 115-row harness.

## Operator train

```bash
ARM=31b PHASE=12 MULTI_SEED=1 bash training/scripts/run_ab_pilot_pipeline.sh
```

Walkthrough: [`PHASE2_12_31B_PREMIUM_WALKTHROUGH.md`](https://github.com/jamalesam93/NassilaT/blob/main/training/PHASE2_12_31B_PREMIUM_WALKTHROUGH.md).

## Hardware

- QLoRA train: **A100 80GB** (or equivalent) on Vast
- GGUF: Q4_K_M / Q6_K eval in pipeline

## Tier ladder

| Tier | Model | Gate |
|------|-------|------|
| Default | `nassila-sanad-e4b` | E4B default-tier |
| Quality | `nassila-sanad-12b` | Tier 2 (v1.10) |
| **Premium** | **`nassila-sanad-31b`** | **Tier 2 (v1.12)** |

Publish to `QinEmPeRoR93/nassila-sanad-31b` (private) when `tier2_gates.model_gates_passed` is true.
