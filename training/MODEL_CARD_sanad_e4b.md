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

*Ship checkpoint: **v1.12** (2026-06-19)*

Default Sanad GGUF — Gemma 4 E4B Q6_K (~8 GB). Ships on **E4B default-tier gates**, not full Tier 2. See [`docs/DUAL_TIER_POLICY.md`](https://github.com/jamalesam93/NassilaT/blob/main/docs/DUAL_TIER_POLICY.md).

## v1.12 ship metrics (115-row harness, multi-seed mean, seeds 42/43/44)

| Metric | Value |
|--------|--------|
| Combined expect | **89.27%** |
| Quote validity (holdout) | **92.98%** |
| False supported (holdout) | **3.81%** |
| E4B default-tier | **PASS** (3/3 seeds) |
| v1.10 baseline beat | **PASS** (3/3 seeds) |
| Tier 2 (quality bar) | FAIL (expected for E4B) |

Reports: `training/reports/ab_e4b_q6_k_v112/`. Walkthrough (archive): [`archive/PHASE2_11_V112_WALKTHROUGH.md`](https://github.com/jamalesam93/NassilaT/blob/main/training/archive/PHASE2_11_V112_WALKTHROUGH.md).

**Known gaps (non-blocking):** h-045 still fails (same class as v1.10); eval-010 residual `supported` spam on extended core.

## v1.10 reference (superseded)

| Metric | Value |
|--------|--------|
| Combined expect | 88.12% |
| Quote validity (holdout) | 89.47% |
| False supported (holdout) | 6.57% |

## Do not publish

- **v1.11** — regressed to 80.58% combined (supported epidemic).

## Train recipe (v1.12)

```bash
ARM=e4b PHASE=12 MULTI_SEED=1 bash training/scripts/run_ab_pilot_pipeline.sh
```

Data: `l3_grounding_train_v112.jsonl` (850 rows). Prompt v1.12 synced in Nassila `grounding-llm.ts`.

## Quality tiers (optional)

- [`nassila-sanad-12b`](https://huggingface.co/QinEmPeRoR93/nassila-sanad-12b) — Tier 2 PASS (v1.10 fallback; v1.12 train pending)
- `nassila-sanad-31b` — premium, Tier 2 target (v1.12 train)

## Usage

Load `nassila-sanad-e4b-q6_k.gguf` in LM Studio. Point Nassila Sanad preset at `http://localhost:1234` with model id from server UI.

## Limitations

- Trained on **abstracts**, not full PDF text
- Advisory only — use with Nassila deterministic guardrails (Tier 2b quote substring checks)
