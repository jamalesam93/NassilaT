# Model cards — Nassila grounding (Sanad / Ouroboros)

| Version | Card | HF adapter | Eval |
|---------|------|------------|------|
| v1–v1.3 | *(git history)* | `QinEmPeRoR93/nassila-grounding-e4b-v1*` | NO-GO |
| **v1.4a** | [MODEL_CARD_v1_4.md](./MODEL_CARD_v1_4.md) | `QinEmPeRoR93/nassila-grounding-e4b-v1.4a-adapter` | **SHIP** |
| **v1.4b** | [MODEL_CARD_v1_4.md](./MODEL_CARD_v1_4.md) | `QinEmPeRoR93/nassila-grounding-e4b-v1.4b-adapter` | NO-GO |

**Agent brief:** [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md)

**Vast llama.cpp:** [LLAMA_CPP_VAST.md](./LLAMA_CPP_VAST.md) (pinned **b9608**)

## Identity (all E4B variants)

| Field | Value |
|-------|-------|
| Task | `l3_grounding` only |
| Worker | **Sanad** |
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
| Supported h-001–h-010 | ≥8/10 |
