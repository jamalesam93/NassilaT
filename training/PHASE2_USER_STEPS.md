# Phase 2 — your next steps

**Full walkthrough:** [PHASE2_TRAINING_GUIDE.md](./PHASE2_TRAINING_GUIDE.md)

## Current repo state

- [x] **v1.2** trained/eval on Vast — **NO-GO** (86% combined; holdout 91.1%, supported 9/10)
- [x] v1.2 adapter on HF: `QinEmPeRoR93/nassila-grounding-e4b-v1.2-adapter`
- [x] Eval reports: [reports/v1_2_eval_combined_report.json](./reports/v1_2_eval_combined_report.json)
- [x] **v1.3** trained/eval on Vast — **NO-GO** (80% combined; core 5/5; supported 3/10; JSON parse 86%)
- [x] v1.3 adapter on HF: `QinEmPeRoR93/nassila-grounding-e4b-v1.3-adapter`
- [x] Eval reports: [reports/v1_3_eval_combined_report.json](./reports/v1_3_eval_combined_report.json)
- [ ] **v1.4** — JSON stability + holdout supported (next)

## Your checklist

### v1.4 (next)

1. Diagnose v1.3 JSON parse failures on supported holdout (h-002–h-010 cluster)
2. Dataset / train tweaks without losing core 5/5 gains
3. See [MODEL_CARD_v1_3.md](./MODEL_CARD_v1_3.md) for failure summary

### Done — v1.3 (reference)

**Plan:** [PHASE2_5_V1_3_PLAN.md](./PHASE2_5_V1_3_PLAN.md)  
**Walkthrough:** [PHASE2_6_V1_3_WALKTHROUGH.md](./PHASE2_6_V1_3_WALKTHROUGH.md)  
**llama.cpp:** [LLAMA_CPP_VAST.md](./LLAMA_CPP_VAST.md) (tag **b9608**)

### Done (reference)

| Version | Combined expect | Supported holdout | Verdict |
|---------|-----------------|-------------------|---------|
| v1.1 | 66% | 1/10 | NO-GO |
| v1.2 | 86% | 9/10 | NO-GO — [MODEL_CARD_v1_2.md](./MODEL_CARD_v1_2.md) |
