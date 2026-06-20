# Dual-tier Sanad ship policy

> **Canonical eval harness:** 115 rows (5 legacy + 20 extended + 90 holdout).  
> **Scoring:** `training/scripts/run_eval_reports.py` emits **both** gate blocks.

## Three product tiers

| Tier | HF id | Model | Ship gate | Role |
|------|-------|-------|-----------|------|
| **Default** | `nassila-sanad-e4b` | Gemma 4 E4B Q6_K (~8 GB) | **E4B default-tier** (`e4b_default_gates`) | Fast download; offline Sanad for all workers |
| **Quality** | `nassila-sanad-12b` | Gemma 4 12B Q6_K | **Tier 2** (`tier2_gates`) | **Main quality tier** — v1.12 train target (v1.10 PASS is fallback) |
| **Optional** | `nassila-sanad-31b` | Gemma 4 31B Q6_K | **Tier 2** (`tier2_gates`) | Experiment only; ship if beats 12B v1.12 |

**Operator instances:** E4B v1.12 on **A6000 ~100 GB**; 12B (+ optional 31B) on **A100 80GB+ / ≥200–500 GB disk**.

**Do not conflate:** Tier 2 is the **quality/premium** bar. E4B ships on the **default-tier** bar (v1.12 checkpoint **GO** as of 2026-06-19).

## E4B default-tier gates (`tier_gates.py`)

| Gate | Min / max | v1.10 E4B mean (reference) |
|------|-----------|----------------------------|
| Combined expect | ≥ **88%** | 88.12% |
| JSON parse (with repair) | ≥ 98% | 100% |
| Supported h-001–h-010 | ≥ 8/10 | 10/10 |
| Core legacy 5 | 5/5 | 5/5 |
| Quote validity (holdout) | ≥ **88%** | 89.47% |
| False supported (holdout) | ≤ **7%** | 6.57% |

**Ship `nassila-sanad-e4b` when:** `e4b_default_gates.model_gates_passed` is true on multi-seed eval. **Current ship checkpoint: v1.12** (89.27% / 92.98% / 3.81% mean).

**v1.12 recovery minimum:** `v110_baseline_beat.all_met` — must not regress below v1.10 on combined, quote, or false-supported. **Met on all seeds (2026-06-19).**

## Tier 2 gates (12B / 31B premium)

Unchanged — see Nassila `docs/OUROBOROS_CONTEXT.md` §10:

| Gate | Threshold |
|------|-----------|
| Combined expect | ≥ 90% (operator buffer ≥ 92%) |
| Quote validity (holdout) | ≥ **98%** |
| False supported (holdout) | ≤ 5% |
| JSON parse | ≥ 98% |
| Supported h-001–h-010 | ≥ 8/10 |
| Core legacy 5 | 5/5 |

## v1.11 lesson

Do **not** require E4B to pass Tier 2. v1.11 chased Tier 2 via relaxed compound `supported` rules and regressed to **80.58%** combined. **v1.12 recovered and ships** — beats v1.10 on combined, quote, and false-supported.

## Train / eval commands

```bash
# Instance 1 — A6000 ~100GB: E4B v1.12 (default-tier)
ARM=e4b PHASE=12 MULTI_SEED=1 bash training/scripts/run_ab_pilot_pipeline.sh
# → rsync reports/ab_e4b_q6_k_v112/ → destroy

# Instance 2 — A100: 12B v1.12 quality (Tier 2 PASS recorded)
ARM=12b PHASE=12 MULTI_SEED=1 bash training/scripts/run_ab_pilot_pipeline.sh

# Instance 3 — A100: 12B v1.14+ multi_claim (after v1.13 NO-GO)
ARM=12b PHASE=14 MULTI_SEED=1 bash training/scripts/run_ab_pilot_pipeline.sh
```

**Ship frozen:** E4B **v1.12**, 12B **v1.12**. v1.13 **NO-GO** — do not publish.

**Active:** [`training/POST_V113_MAP.md`](../training/POST_V113_MAP.md) · [`training/PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md`](../training/PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md)

**Archive:** v1.11–v1.13 walkthroughs in [`training/archive/`](../training/archive/).

## App inference note

Train prompt lives in `training/scripts/validate_dataset.py`. Nassila `grounding-llm.ts` sync is deferred until Ouroboros UI revamp; engine quote guardrail (Tier 2b) remains the product safety net.
