# Model cards — Nassila grounding (One Ring v1)

| Version | Card | HF adapter | Eval |
|---------|------|------------|------|
| **v1** | [MODEL_CARD_v1.md](./MODEL_CARD_v1.md) | `QinEmPeRoR93/nassila-grounding-e4b-v1-adapter` | NO-GO |
| **v1.1** | [MODEL_CARD_v1_1.md](./MODEL_CARD_v1_1.md) | `QinEmPeRoR93/nassila-grounding-e4b-v1.1-adapter` | NO-GO |
| **v1.2** | (planned) | `nassila-grounding-e4b-v1.2-adapter` | — |

**Next work:** [PHASE2_3_V1_2_PLAN.md](./PHASE2_3_V1_2_PLAN.md)

## Identity (all E4B variants)

| Field | Value |
|-------|-------|
| Task | `l3_grounding` only |
| Base model | `google/gemma-4-E4B-it` |
| Export quant | Q6_K GGUF (after merge + llama.cpp) |
| Excerpt type | **Abstract only** |

## Eval targets

| Metric | Target |
|--------|--------|
| JSON parse (repair) | ≥95% |
| Expect pass | ≥90% |
| Quote validity (holdout) | ≥98% |
| False supported | ≤5% |
