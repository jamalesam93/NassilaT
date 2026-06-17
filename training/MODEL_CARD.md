# Model cards — Nassila Sanad (Ouroboros)

Public HF ids use **worker + size**; train checkpoint (v1.10, v1.11, …) is on the card only.

| Artifact | Card | HF repo | Checkpoint | Tier 2 |
|----------|------|---------|------------|--------|
| **Sanad 12B Q6_K** | [MODEL_CARD_sanad_12b.md](./MODEL_CARD_sanad_12b.md) | `QinEmPeRoR93/nassila-sanad-12b` (private) | v1.10 | **PASS** |
| **Sanad E4B Q6_K** | [MODEL_CARD_sanad_e4b.md](./MODEL_CARD_sanad_e4b.md) | `QinEmPeRoR93/nassila-sanad-e4b` | v1.11 (target) | pending |
| v1.4a adapter | [archive/MODEL_CARD_v1_4.md](./archive/MODEL_CARD_v1_4.md) | `nassila-grounding-e4b-v1.4a-adapter` | v1.4a | NO-GO |

**Agent brief:** [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md)

**Operator walkthrough:** [PHASE2_9_AB_PILOT_WALKTHROUGH.md](./PHASE2_9_AB_PILOT_WALKTHROUGH.md)

## Identity

| Field | Value |
|-------|-------|
| Task | `l3_grounding` only |
| Worker | **Sanad** |
| Default base | Gemma 4 E4B · `nassila-sanad-e4b` |
| Optional base | Gemma 4 12B · `nassila-sanad-12b` |
| Export quant | Q6_K GGUF |
| Excerpt type | **Abstract only** |

## Eval targets (Tier 2)

See Nassila `docs/OUROBOROS_CONTEXT.md` §10 — six gates on 115-row hardened harness.
