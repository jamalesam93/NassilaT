# Dual-tier Sanad ship policy

> **Canonical evals:** abstract trust anchor = 115-row harness (legacy); default-tier S15 verified on `eval_holdout_body_contrastive_frozen_v2` (308 rows, single run).  
> **Scoring:** `training/scripts/run_eval_reports.py` emits gate blocks; body harness scored via `score_body_holdout_pilot.py` / `tier_gates.py`.

## Two product tiers

| Tier | HF id | Model | Ship gate | Role |
|------|-------|-------|-----------|------|
| **Default** | `nassila-sanad-4b` | Qwen 3.5 4B Q6_K (~3.3 GB) | S15 default-tier (contrastive body: false-sup ≤5%, combined ≥88) | Fast download; offline Sanad for all workers — **S15 checkpoint** |
| **Quality** | `nassila-sanad-12b` | Gemma 4 12B Q6_K | **Tier 2** (`tier2_gates`) | **Main quality tier** — S14 (v1.14) selected (v1.12 higher-combined fallback) |

**E4B `nassila-sanad-e4b` (S12) is RETIRED** as the default tier (2026-08). Research/legacy walkthroughs referencing E4B v1.12 live in `training/archive/`. **Local smoke validated** on RTX 4060 8 GB (2026-06-21).

**Do not conflate:** Tier 2 is the **quality/premium** bar. 4B (S15) ships on the **default-tier** bar (contrastive body, 2026-08).

## S15 default-tier gates (4B)

| Gate | Min / max | S15 4B (contrastive v2, single run) |
|------|-----------|-------------------------------------|
| Combined expect | ≥ **88%** | **94.48%** ✅ |
| JSON parse (with repair) | ≥ 98% | **99.35%** ✅ |
| False supported (bodies) | ≤ **5%** | **4.87%** ✅ |
| Contradicted (body) | monitor | 85.83% |
| Not-in-source (body) | monitor | 100% |
| Quote validity | ≥ 88% | **pending local verify** |

> S15 provenance: **single-run** eval on `eval_holdout_body_contrastive_frozen_v2` (308 rows). Multi-seed + quote measurement are the open re-verify items (laptop eval). Training data = same 874-row `l3_grounding_train_v114.jsonl` as S14.

## Tier 2 gates (12B quality tier)

Unchanged — see Nassila `docs/OUROBOROS_CONTEXT.md` §10:

| Gate | Threshold |
|------|-----------|
| Combined expect | ≥ 90% (operator buffer ≥ 92%) |
| Quote validity (holdout) | ≥ **98%** |
| False supported (holdout) | ≤ 5% |
| JSON parse | ≥ 98% |
| Supported h-001–h-010 | ≥ 8/10 |
| Core legacy 5 | 5/5 |

## v1.11 lesson (E4B history)

Do **not** require a small default-tier model to pass Tier 2. v1.11 chased Tier 2 via relaxed compound `supported` rules and regressed to **80.58%** combined. v1.12 recovered and shipped E4B; E4B now retired in favor of S15 (4B).

## Train / eval commands

```bash
# Instance 1 — A6000 ~100GB: S15 Qwen 3.5 4B (default-tier) — trained + merged + Q6_K (2026-08)
# Instance 2 — A100: 12B v1.14 multi_claim (selected quality checkpoint)
ARM=12b PHASE=14 MULTI_SEED=1 bash training/scripts/run_ab_pilot_pipeline.sh
```

**Ship selected:** S15 **4B** (default), 12B **v1.14** (Tier 2). v1.12 12B remains the higher-combined fallback/reference; v1.13 **NO-GO** — do not publish.

**Active:** [`training/OUROBOROS_OPERATOR_MAP.md`](../training/OUROBOROS_OPERATOR_MAP.md) · [`training/EVAL_GONOGO.md`](../training/EVAL_GONOGO.md)

**Archive:** v1.11–v1.13 + E4B walkthroughs in [`training/archive/`](../training/archive/).

## App inference note

Train prompt lives in `training/scripts/validate_dataset.py` (`sanad-grounding-v1`); Nassila `grounding-llm.ts` goldens are byte-identical (system/user split). Engine quote guardrail (Tier 2b) remains the product safety net.
