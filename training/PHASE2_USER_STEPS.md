# Phase 2 — your next steps

**Full walkthrough:** [PHASE2_TRAINING_GUIDE.md](./PHASE2_TRAINING_GUIDE.md)

## Current repo state

- [x] **v1.2** trained/eval on Vast — **NO-GO** (86% combined; holdout 91.1%, supported 9/10)
- [x] v1.2 adapter on HF: `QinEmPeRoR93/nassila-grounding-e4b-v1.2-adapter`
- [x] Eval reports: [reports/v1_2_eval_combined_report.json](./reports/v1_2_eval_combined_report.json)
- [ ] **v1.3** — dataset + train (next)

## Your checklist

### v1.3 — Phase 2.5–2.6 (next)

**Plan:** [PHASE2_5_V1_3_PLAN.md](./PHASE2_5_V1_3_PLAN.md)  
**Walkthrough:** [PHASE2_6_V1_3_WALKTHROUGH.md](./PHASE2_6_V1_3_WALKTHROUGH.md)

1. Regenerate `l3_grounding_train.jsonl` (850 rows, seed 45) — multi-claim, polarity, semantic Sanad
2. Spot-check `data/l3_review_queue_v1_3.csv`
3. Vast train `nassila-grounding-e4b-v1.3` (2 epochs)
4. Eval `--chat-template` + `run_eval_reports.py`
5. GO → GGUF download · NO-GO → adapter only to HF

### Done (reference)

| Version | Combined expect | Supported holdout | Verdict |
|---------|-----------------|-------------------|---------|
| v1.1 | 66% | 1/10 | NO-GO |
| v1.2 | 86% | 9/10 | NO-GO — [MODEL_CARD_v1_2.md](./MODEL_CARD_v1_2.md) |
