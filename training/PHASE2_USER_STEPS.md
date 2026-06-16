# Phase 2 — your next steps

**Agent brief:** [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md)

**Current Vast walkthrough:** [PHASE2_8_V1_5_WALKTHROUGH.md](./PHASE2_8_V1_5_WALKTHROUGH.md) (v1.8)  
**Previous:** [PHASE2_7_V1_4_WALKTHROUGH.md](./PHASE2_7_V1_4_WALKTHROUGH.md)

## Ship state (Sanad)

| Version | Combined | Verdict | HF adapter |
|---------|----------|---------|------------|
| **v1.4a** | 90% | **SHIP** | `nassila-grounding-e4b-v1.4a-adapter` |
| v1.4b | 87.1% | NO-GO | `nassila-grounding-e4b-v1.4b-adapter` |

Reports: `reports/v1_4a_*`, `reports/v1_4b_*`, `reports/holdout_failure_matrix.md`

## Your checklist

### v1.8 (next — Vast)

1. PC: `git pull` — train file `l3_grounding_train_v18.jsonl` includes **updated prompt** in chat export
2. Vast: `PHASE=8 bash scripts/run_vast_pipeline.sh`
3. Target: fix h-042 (passage claims), h-043/h-045 (no spurious `supported`), h-032/h-034/eval-012/013
4. v1.4a remains ship until `tier2_gates.model_gates_passed`

### v1.7 (done — zero delta vs v1.6; do not ship)

Identical eval to v1.6. Boost ineffective — archived. `PHASE=7` still in pipeline for reference only.

### v1.6 (done — clean NO-GO, 88.57%)

Trustworthy (contamination 0) but below 90%. Quote validity now genuinely 100%. Misses isolated to compound claims + evidential hedging → addressed in v1.7. `PHASE=6` still works.

### v1.5 (archived — contaminated, NO-GO)

Do not ship. 7 boost rows leaked eval passages. Kept for regression reference only (`PHASE=5` still works in pipeline).

### v1.0–v1.3 (reference)

Historical walkthroughs and model cards removed from tree — see **git history**.
