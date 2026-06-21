# Post–v1.14 map — Sanad training + product

**Status (2026-06):** v1.13 **NO-GO**; v1.14 **GO**. **Ship checkpoints:** E4B **v1.12** (default-tier), 12B **v1.14** (Tier 2 + h-045/h-088 split fix). **Laptop smoke PASS** (RTX 4060 8 GB, 2026-06-21). 12B v1.12 remains the higher-combined fallback/reference.

**Agent brief:** [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md)  
**Ship policy:** [`docs/DUAL_TIER_POLICY.md`](../docs/DUAL_TIER_POLICY.md)  
**Decisions log:** [`EVAL_GONOGO.md`](./EVAL_GONOGO.md)  
**Laptop acceptance:** [`LAPTOP_SMOKE_TEST.md`](./LAPTOP_SMOKE_TEST.md)

---

## What v1.13 proved

Multi-seed mean (`reports/ab_12b_q6_k_v113/`):

| Metric | v1.12 ship | v1.13 | Tier 2 bar |
|--------|------------|-------|------------|
| Combined expect | 94.20% | **88.99%** | ≥90% |
| JSON parse | 100% | **95.65%** | ≥98% |
| Quote (holdout) | 100% | **94.74%** | ≥98% |
| Tier 2 pass | 3/3 | **0/3** | all six gates |
| multi_claim | 69.23% | 64.10% | stretch ≥80% |

**Root cause (v1.14 runbook):** 12 v113 parity rows (all `weak`) merged under the **850-row cap** → `prepare_v15_train.py` trimmed **11 `supported`** rows → verdict-boundary regressions (h-038, h-051, h-082, eval-012) plus inference flakes (h-028, h-037). **h-045 / h-088** worsened from v1.12 `min_claims` failures to **`parse_json`** on all seeds.

**Rule:** Do **not** publish v1.13. Use **v1.14** (cap 874 + v114 counterbalance + prompt sync).

---

## Current ship

| HF id | Checkpoint | Gate | Role |
|-------|------------|------|------|
| `nassila-sanad-e4b` | **v1.12** | E4B default-tier | 8 GB default |
| `nassila-sanad-12b` | **v1.14** | Tier 2 | Quality tier; subgroup split fix |

12B v1.14 trades lower combined score (**90.43%**) for fixed h-045 / h-088 and higher `multi_claim` (**84.62%**). v1.12 remains the reference if future work prioritizes maximum combined score again.

---

## v1.14 result

Full spec: [`docs/V113_12B_REGRESSION_FIX_REPORT.md`](../docs/V113_12B_REGRESSION_FIX_REPORT.md)  
Operator walkthrough: [`PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md`](./PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md)

Reports: `reports/ab_12b_q6_k_v114/`.

| Metric | v1.12 | v1.14 |
|--------|-------|-------|
| Combined expect | **94.20%** | **90.43%** |
| JSON parse | 100% | **100%** |
| Quote (holdout) | 100% | **100%** |
| False supported | 2.86% | **2.86%** |
| multi_claim | 69.23% | **84.62%** |
| Tier 2 pass | 3/3 | **3/3** |

**Decision:** select v1.14 because it fixes h-045 / h-088 on all seeds while keeping Tier 2. The combined-score regression is accepted as a product tradeoff for subgroup-split correctness.

**Stop publishing rule:** Any attempt with Tier 2 fail → keep **v1.12** on HF.

---

## Next: laptop smoke test — **DONE**

Local acceptance **PASS** (2026-06-21, RTX 4060 8 GB): [`outputs/LAPTOP_SMOKE_SIGNOFF.md`](./outputs/LAPTOP_SMOKE_SIGNOFF.md).

Proceed to [`HF_RELEASE_VERIFY.md`](./HF_RELEASE_VERIFY.md).

---

## v1.15+ future refinement

Optional later work: recover v1.12-level combined score while preserving v1.14 h-045 / h-088 behavior. Start from v1.14 as the selected checkpoint; hyperparameter escalation remains last resort.

---

## Parallel tracks (after laptop smoke + HF verify)

| Track | Repo | When |
|-------|------|------|
| **UI reform** | Nassila `docs/DESIGN.md`, `docs/PRODUCT.md` | After E4B v1.12 + 12B v1.14 laptop smoke pass |
| **HF / model cards** | `MODEL_CARD_sanad_*.md`, lean HF READMEs | After smoke pass; see [`HF_PUBLISH.md`](./HF_PUBLISH.md) |
| **Maktab / Masdar corpus** | [`PHASE3_TIER3_GROUNDWORK.md`](./PHASE3_TIER3_GROUNDWORK.md), [`CORPUS_PIPELINE.md`](./CORPUS_PIPELINE.md) | After Tier 2 stable; unblocks Tier 3 |

---

## Doc map (minimal reading)

| Read | Purpose |
|------|---------|
| This file | Where you are; what next |
| [`LAPTOP_SMOKE_TEST.md`](./LAPTOP_SMOKE_TEST.md) | Local GGUF acceptance |
| `docs/V113_12B_REGRESSION_FIX_REPORT.md` | v1.14 RCA + implementation checklist |
| `PHASE2_14_…` | Vast commands |
| `DUAL_TIER_POLICY.md` | E4B vs 12B gates |
| `EVAL_GONOGO.md` | GO/NO-GO history |
| `MODEL_CARD_sanad_12b.md` | HF-facing 12B truth |
| Nassila `OUROBOROS_CONTEXT.md` | Workers + tiers |

Historical walkthroughs: [`archive/`](./archive/).
