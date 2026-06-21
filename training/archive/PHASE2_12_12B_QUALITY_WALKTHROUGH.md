# Phase 2.12 — 12B Q6_K quality tier (main product)

**Co-equal with E4B v1.12** — same data, prompt, and boost as E4B recovery. Targets **Tier 2** on the 115-row harness (corrected v1.11 gold).

Policy: [`docs/DUAL_TIER_POLICY.md`](../../docs/DUAL_TIER_POLICY.md). Spec: [`V112_RECOVERY_PLAN.md`](./V112_RECOVERY_PLAN.md).

## Instance

| Field | Value |
|-------|--------|
| GPU | **A100 80GB+** (or A6000 48GB if 12B only) |
| Disk | **≥200 GB** recommended (12B merge + F16 + Q6_K + base cache) |
| Prerequisite | **E4B v1.12 GO (2026-06-19)** — `e4b_default_gates` + `v110_baseline_beat` met on all seeds |

Do **not** run 12B v1.12 on the same **100 GB** disk used for E4B-only — 12B HF merge + F16 GGUF needs more headroom.

## Vast (second instance — after E4B reports saved)

```bash
cd training
git pull
python scripts/check_contamination.py data/l3_grounding_train_v112.jsonl

# Quality ship target — Q6_K only (saves hours vs Q4/Q6/Q8 ladder)
ARM=12b PHASE=12 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

Reports: `reports/ab_12b_q6_k_v112/`.

Optional regrade of **v1.10** weights on new gold (no train, ~1–2 h):

```bash
SKIP_TRAIN=1 ARM=12b PHASE=10 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

Only if you still have `outputs/nassila-sanad-12b-v1.10/lora_adapter` on the instance.

## Success criteria

| Check | Target |
|-------|--------|
| `tier2_gates.model_gates_passed` | **true** (all seeds) |
| Combined expect (mean) | ≥ **94.79%** (beat v1.10 12B); stretch **≥96%** on corrected gold |
| Quote validity (holdout) | ≥ **98%** |
| False supported (holdout) | ≤ **5%** |
| h-045, h-088 | pass or improve vs v1.10 (`multi_claim`) |

**Publish when Tier 2 passes:** `exports/nassila-sanad-12b-q6_k.gguf` → `QinEmPeRoR93/nassila-sanad-12b`.

v1.10 12B remains valid fallback until v1.12 passes Tier 2.

## Rsync before destroy

```bash
scp -r -P <PORT> root@<host>:/root/nassila/training/reports/ab_12b_q6_k_v112 "E:\Cursor Projects\NassilaT\training\reports\"
```

Include all `seed_*_predictions.jsonl` files.

## Session order (A100)

1. **12B v1.12** (main) — `ARM=12b PHASE=12`
