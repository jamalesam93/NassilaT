# Post–v1.13 map — Sanad training + product

**Status (2026-06):** v1.13 **NO-GO**. **Ship checkpoints unchanged:** E4B **v1.12** (default-tier), 12B **v1.12** (Tier 2). **Active work:** **v1.14** per [`docs/V113_12B_REGRESSION_FIX_REPORT.md`](../docs/V113_12B_REGRESSION_FIX_REPORT.md).

**Agent brief:** [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md)  
**Ship policy:** [`docs/DUAL_TIER_POLICY.md`](../docs/DUAL_TIER_POLICY.md)  
**Decisions log:** [`EVAL_GONOGO.md`](./EVAL_GONOGO.md)

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

**Rule:** Do **not** publish v1.13. Use **v1.14** (cap 874 + v114 counterbalance + prompt sync) — not a smaller ad-hoc boost.

---

## Current ship (frozen until v1.14 passes)

| HF id | Checkpoint | Gate | Role |
|-------|------------|------|------|
| `nassila-sanad-e4b` | **v1.12** | E4B default-tier | 8 GB default |
| `nassila-sanad-12b` | **v1.12** | Tier 2 | Quality tier |

Known limitation on both: **h-045 / h-088** (multi_claim subgroup splits). Not a Tier 2 ship blocker for 12B v1.12; product Tier 2b guardrails still apply.

---

## v1.14 runbook (canonical)

Full spec: [`docs/V113_12B_REGRESSION_FIX_REPORT.md`](../docs/V113_12B_REGRESSION_FIX_REPORT.md)  
Operator walkthrough: [`PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md`](./PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md)

**Four fixes (one coordinated attempt — not one lever at a time):**

1. **Prompt** — full TS↔Python resync to train-side v1.12 + approximation clause (h-051).
2. **Boost** — keep v113 parity rows + new `l3_grounding_v114_boost.jsonl` (3 insuf_design + 9 supported counterbalance).
3. **Cap** — `prepare_v15_train.py` default **874** (850 + 24 boost rows; no trim).
4. **Train** — 12B v1.14, same hyperparameters (2 epochs, lr=1e-4); multi-seed eval.

**Minimum bar:** Combined expect ≥ v1.12 (94.20%), Tier 2 PASS, JSON parse 100%.  
**Stretch:** h-045 / h-088 pass (v1.12 never passed; v1.14 must at least restore parse stability).

**Stop publishing rule:** Any attempt with Tier 2 fail → keep **v1.12** on HF.

---

## v1.15+ fallback (only if v1.14 fails)

See Part 5 of the v1.14 runbook: numeric-approximation rows, more insuf_design rows, reduce supported counterbalance, hyperparameter escalation last.

---

## Parallel tracks (after v1.14 stabilizes or if GPU allows)

| Track | Repo | When |
|-------|------|------|
| **UI reform** | Nassila `docs/DESIGN.md`, `docs/PRODUCT.md` | After 12B v1.14+ passes **or** when you accept v1.12 known gaps |
| **HF / model cards** | `MODEL_CARD_sanad_*.md`, lean HF READMEs | Any time |
| **Maktab / Masdar corpus** | `CORPUS_PIPELINE.md`, Phase 3 in [`ROADMAP.md`](./ROADMAP.md) | After Tier 2 model stable; unblocks Tier 3 |
| **31B experiment** | [`PHASE2_12_31B_PREMIUM_WALKTHROUGH.md`](./PHASE2_12_31B_PREMIUM_WALKTHROUGH.md) | Optional; only if beats 12B v1.12+ |

---

## Doc map (minimal reading)

| Read | Purpose |
|------|---------|
| This file | Where you are; what next |
| `docs/V113_12B_REGRESSION_FIX_REPORT.md` | v1.14 RCA + implementation checklist |
| `PHASE2_14_…` | Vast commands |
| `DUAL_TIER_POLICY.md` | E4B vs 12B gates |
| `EVAL_GONOGO.md` | GO/NO-GO history |
| `MODEL_CARD_sanad_12b.md` | HF-facing 12B truth |
| Nassila `OUROBOROS_CONTEXT.md` | Workers + tiers |

Historical walkthroughs: [`archive/`](./archive/).
