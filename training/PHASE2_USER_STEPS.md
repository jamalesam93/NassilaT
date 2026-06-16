# Phase 2 — your next steps

**Agent brief:** [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md)

**Current Vast walkthrough:** [PHASE2_8_V1_5_WALKTHROUGH.md](./PHASE2_8_V1_5_WALKTHROUGH.md)  
**Previous:** [PHASE2_7_V1_4_WALKTHROUGH.md](./PHASE2_7_V1_4_WALKTHROUGH.md)

## Ship state (Sanad)

| Version | Combined | Verdict | HF adapter |
|---------|----------|---------|------------|
| **v1.4a** | 90% | **SHIP** | `nassila-grounding-e4b-v1.4a-adapter` |
| v1.4b | 87.1% | NO-GO | `nassila-grounding-e4b-v1.4b-adapter` |

Reports: `reports/v1_4a_*`, `reports/v1_4b_*`, `reports/holdout_failure_matrix.md`

## Your checklist

### v1.5 (next — Vast)

1. PC: `prepare_v15_train.py` + validate + `git push`
2. Vast: `PHASE=5 bash scripts/run_vast_pipeline.sh`
3. Quote validity ≥98% (currently 81.8% at v1.4a)
4. Persistent holdout: h-010, h-043, h-045
5. See [PHASE2_8_V1_5_WALKTHROUGH.md](./PHASE2_8_V1_5_WALKTHROUGH.md), [MODEL_CARD_v1_4.md](./MODEL_CARD_v1_4.md), `nassila_training_diagnosis.md` §6.2

### v1.0–v1.3 (reference)

Historical walkthroughs and model cards removed from tree — see **git history**.
