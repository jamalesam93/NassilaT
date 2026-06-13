# Model card — nassila-grounding-e4b-v1.3 (Sanad / Ouroboros)

**Status:** Template — fill after Vast train + eval.

| Field | Value |
|-------|--------|
| Worker | **Sanad** (`l3_grounding`) |
| Base | `google/gemma-4-E4B-it` |
| Method | QLoRA (Unsloth), 2 epochs, LR 1e-4 |
| Train rows | 850 (seed 45) |
| HF adapter | `QinEmPeRoR93/nassila-grounding-e4b-v1.3-adapter` |

## v1.3 focus

Multi-claim decomposition, polarity contradicted, semantic Sanad, overclaim contradicted — targeting v1.2 core eval collapse and quote validity gap.

## Eval (fill in)

| Metric | v1.2 | v1.3 | Target |
|--------|------|------|--------|
| Combined expect | 86% | | ≥90% |
| Core eval | 40% | | 100% |
| Quote validity (holdout) | 90.9% | | ≥98% |
| Supported holdout | 9/10 | | ≥8/10 |

## Related

- [PHASE2_5_V1_3_PLAN.md](./PHASE2_5_V1_3_PLAN.md)
- [MODEL_CARD_v1_2.md](./MODEL_CARD_v1_2.md)
