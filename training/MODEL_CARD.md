# Model cards — Nassila Sanad (Ouroboros)

Public HF ids use **worker + size**; Sanad checkpoint (**S12**, **S14**, …) is on the card only. **S** = Sanad. See [`OUROBOROS_OPERATOR_MAP.md`](./OUROBOROS_OPERATOR_MAP.md) § Sanad checkpoint naming.

| Artifact | Card | HF repo | Ship checkpoint | Tier 2 |
|----------|------|---------|-----------------|--------|
| **Sanad E4B Q6_K** | [MODEL_CARD_sanad_e4b.md](./MODEL_CARD_sanad_e4b.md) | `QinEmPeRoR93/nassila-sanad-e4b` | **S12** *(legacy v1.12)* | N/A (default-tier) |
| **Sanad 12B Q6_K** | [MODEL_CARD_sanad_12b.md](./MODEL_CARD_sanad_12b.md) | `QinEmPeRoR93/nassila-sanad-12b` | **S14** *(legacy v1.14)* | **PASS** |
| v1.4a adapter | [archive/MODEL_CARD_v1_4.md](./archive/MODEL_CARD_v1_4.md) | legacy adapter repo | v1.4a | NO-GO |

**Agent brief:** [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md)

**Operator:** [OUROBOROS_OPERATOR_MAP.md](./OUROBOROS_OPERATOR_MAP.md) · [PHASE2_9_AB_PILOT_WALKTHROUGH.md](./PHASE2_9_AB_PILOT_WALKTHROUGH.md)

## Identity

| Field | Value |
|-------|-------|
| Task | `l3_grounding` only |
| Worker | **Sanad** |
| Default | Gemma 4 E4B · `nassila-sanad-e4b` **S12** |
| Quality | Gemma 4 12B · `nassila-sanad-12b` **S14** |
| Export quant | Q6_K GGUF |
| Excerpt type | **Abstract only** |

## Eval targets

- **E4B:** `e4b_default_gates` — [`docs/DUAL_TIER_POLICY.md`](../docs/DUAL_TIER_POLICY.md)
- **12B:** `tier2_gates` — Nassila `docs/OUROBOROS_CONTEXT.md` §10 (115-row harness)

## v1.14 decision

v1.13 **NO-GO** — do not publish. v1.14 **GO** — selected for 12B quality because it fixes h-045/h-088 while preserving Tier 2. See [`PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md`](./PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md).
