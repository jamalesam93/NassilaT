# Model card — nassila-grounding-e4b-v1.2 (Sanad / Ouroboros)

**Hugging Face:** `QinEmPeRoR93/nassila-grounding-e4b-v1.2-adapter`  
**Status:** evaluation **NO-GO** — adapter archived; GGUF not published.

## Evaluation summary (Vast, `--chat-template`)

| Metric | Stock baseline | v1.2 | Target |
|--------|----------------|------|--------|
| Combined expect | 86% | **86%** | ≥90% |
| Holdout expect | 84.4% | **91.1%** | — |
| Core eval (5 rows) | 100% | **40%** | — |
| Quote validity (holdout) | 100% | **90.9%** | ≥98% |
| False supported (holdout) | 11.8% | **0%** | ≤5% |
| Supported h-001–h-010 | 10/10 | **9/10** | ≥8/10 |

Reports: [reports/v1_2_eval_combined_report.json](./reports/v1_2_eval_combined_report.json)

**Next:** [PHASE2_5_V1_3_PLAN.md](./PHASE2_5_V1_3_PLAN.md)
