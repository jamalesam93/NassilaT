# Dual-tier Sanad ship policy

> **Canonical eval harness:** 115 rows (5 legacy + 20 extended + 90 holdout).  
> **Scoring:** `training/scripts/run_eval_reports.py` emits **both** gate blocks.

## Three product tiers

| Tier | HF id | Model | Ship gate | Role |
|------|-------|-------|-----------|------|
| **Default** | `nassila-sanad-e4b` | Gemma 4 E4B Q6_K (~8 GB) | **E4B default-tier** (`e4b_default_gates`) | Fast download; offline Sanad for all workers |
| **Quality** | `nassila-sanad-12b` | Gemma 4 12B Q6_K | **Tier 2** (`tier2_gates`) | Optional quality; first Tier 2 PASS (v1.10) |
| **Premium** | `nassila-sanad-31b` | Gemma 4 31B Q4/Q6 | **Tier 2** (`tier2_gates`) | Best local Sanad; one final Vast train on v1.12 data |

**Do not conflate:** Tier 2 is the **quality/premium** bar. E4B ships on the **default-tier** bar anchored to v1.10 observed capacity.

## E4B default-tier gates (`tier_gates.py`)

| Gate | Min / max | v1.10 E4B mean (reference) |
|------|-----------|----------------------------|
| Combined expect | ≥ **88%** | 88.12% |
| JSON parse (with repair) | ≥ 98% | 100% |
| Supported h-001–h-010 | ≥ 8/10 | 10/10 |
| Core legacy 5 | 5/5 | 5/5 |
| Quote validity (holdout) | ≥ **88%** | 89.47% |
| False supported (holdout) | ≤ **7%** | 6.57% |

**Ship `nassila-sanad-e4b` when:** `e4b_default_gates.model_gates_passed` is true on multi-seed eval.

**v1.12 recovery minimum:** `v110_baseline_beat.all_met` — must not regress below v1.10 on combined, quote, or false-supported (even if default-tier passes).

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

Do **not** require E4B to pass Tier 2. v1.11 chased Tier 2 via relaxed compound `supported` rules and regressed to **80.58%** combined. **v1.10 remains the E4B reference checkpoint** until v1.12 beats it on the default-tier + baseline beat bar.

## Train / eval commands

```bash
# E4B v1.12 recovery (default-tier target)
ARM=e4b PHASE=12 MULTI_SEED=1 bash training/scripts/run_ab_pilot_pipeline.sh

# 31B premium (Tier 2 target, same v1.12 data + prompt)
ARM=31b PHASE=12 MULTI_SEED=1 bash training/scripts/run_ab_pilot_pipeline.sh
```

Walkthroughs: [`PHASE2_11_V112_WALKTHROUGH.md`](training/PHASE2_11_V112_WALKTHROUGH.md), [`PHASE2_12_31B_PREMIUM_WALKTHROUGH.md`](training/PHASE2_12_31B_PREMIUM_WALKTHROUGH.md).

## App inference note

Train prompt lives in `training/scripts/validate_dataset.py`. Nassila `grounding-llm.ts` sync is deferred until Ouroboros UI revamp; engine quote guardrail (Tier 2b) remains the product safety net.
