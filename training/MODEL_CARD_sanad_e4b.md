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

# Nassila Sanad E4B

*Train checkpoint v1.11 (target) · default tier*

Placeholder card for the **default** Sanad GGUF — Gemma 4 E4B Q6_K (~8 GB). Ships when v1.11 passes all Tier 2 gates on the 115-row harness.

Until published, use the optional quality tier [`nassila-sanad-12b`](https://huggingface.co/QinEmPeRoR93/nassila-sanad-12b) (checkpoint v1.10, Tier 2 PASS).

## Train v1.11 on Vast

```bash
ARM=e4b PHASE=11 MULTI_SEED=1 bash training/scripts/run_ab_pilot_pipeline.sh
```

Publish `exports/nassila-sanad-e4b-q6_k.gguf` to this repo when gates pass. Full operator steps: [PHASE2_9_AB_PILOT_WALKTHROUGH.md](https://github.com/jamalesam93/NassilaT/blob/main/training/PHASE2_9_AB_PILOT_WALKTHROUGH.md).
