# Model cards — Nassila Sanad (Ouroboros)

Public HF ids use **worker + size**; Sanad checkpoint (**S12**, **S14**, …) is on the card only. **S** = Sanad. See [`OUROBOROS_OPERATOR_MAP.md`](./OUROBOROS_OPERATOR_MAP.md) § Sanad checkpoint naming.

| Artifact | Card | HF repo | Ship checkpoint | Tier 2 |
|----------|------|---------|-----------------|--------|
| **Sanad 4B Q6_K** | [hf_readmes/nassila-sanad-4b/README.md](./hf_readmes/nassila-sanad-4b/README.md) | `QinEmPeRoR93/nassila-sanad-4b` | **S15** *(v1.15)* | N/A (default-tier) |
| **Sanad 12B Q6_K** | [MODEL_CARD_sanad_12b.md](./MODEL_CARD_sanad_12b.md) | `QinEmPeRoR93/nassila-sanad-12b` | **S14** *(legacy v1.14)* | **PASS** |
| Sanad E4B Q6_K (retired) | [MODEL_CARD_sanad_e4b.md](./MODEL_CARD_sanad_e4b.md) | `QinEmPeRoR93/nassila-sanad-e4b` | S12 *(legacy v1.12)* | N/A (retired) |
| v1.4a adapter | [archive/MODEL_CARD_v1_4.md](./archive/MODEL_CARD_v1_4.md) | legacy adapter repo | v1.4a | NO-GO |

**Agent brief:** [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md)

**Operator:** [OUROBOROS_OPERATOR_MAP.md](./OUROBOROS_OPERATOR_MAP.md) · [EVAL_GONOGO.md](./EVAL_GONOGO.md)

## Identity

| Field | Value |
|-------|-------|
| Task | `l3_grounding` only |
| Worker | **Sanad** |
| Default | Qwen 3.5 4B · `nassila-sanad-4b` **S15** |
| Quality | Gemma 4 12B · `nassila-sanad-12b` **S14** |
| Retired | Gemma 4 E4B · `nassila-sanad-e4b` **S12** |
| Export quant | Q6_K GGUF |
| Excerpt type | **Abstract only** (body grounding in progress, Tier 3) |

## Eval targets

- **4B (S15):** default-tier on `eval_holdout_body_contrastive_frozen_v2` — [`docs/DUAL_TIER_POLICY.md`](../docs/DUAL_TIER_POLICY.md)
- **12B (S14):** `tier2_gates` — Nassila `docs/OUROBOROS_CONTEXT.md` §10 (115-row harness)

## v1.14 / S15 decisions

v1.13 **NO-GO** — do not publish. v1.14 **GO** — selected for 12B quality because it fixes h-045/h-088 while preserving Tier 2. **S15 GO (2026-08)** — Qwen 3.5 4B default tier (contrastive v2: 94.48% combined expect, 4.87% false-supported; quote pending local verify). See [`EVAL_GONOGO.md`](./EVAL_GONOGO.md).
