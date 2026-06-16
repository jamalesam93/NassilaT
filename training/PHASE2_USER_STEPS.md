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

### v1.9 (next — Vast)

1. `git pull` → `PHASE=9 bash scripts/run_vast_pipeline.sh`
2. Target: quote holdout ≥98% (fix h-009 over-hedge), close last 6 failures
3. v1.8 already passes combined ≥90%; v1.9 is calibration not a reset

### v1.8 (done — 91.43% combined, quote gate miss)

### v1.7 (done — zero delta vs v1.6; do not ship)

Identical eval to v1.6. Boost ineffective — archived. `PHASE=7` still in pipeline for reference only.

### v1.6 (done — clean NO-GO, 88.57%)

Trustworthy (contamination 0) but below 90%. Quote validity now genuinely 100%. Misses isolated to compound claims + evidential hedging → addressed in v1.7. `PHASE=6` still works.

### v1.5 (archived — contaminated, NO-GO)

Do not ship. 7 boost rows leaked eval passages. Kept for regression reference only (`PHASE=5` still works in pipeline).

### v1.0–v1.3 (reference)

Historical walkthroughs and model cards removed from tree — see **git history**.
