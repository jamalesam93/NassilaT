# Phase 2.12 — Gemma 4 31B (optional experiment)

**Side quest** — same v1.12 data + prompt as E4B/12B. **E4B + 12B Q6_K are the main product tiers.**

Policy: [`docs/DUAL_TIER_POLICY.md`](../docs/DUAL_TIER_POLICY.md).

## Model

| Field | Value |
|-------|--------|
| Base | `google/gemma-4-31B-it` |
| Public id | `nassila-sanad-31b` |
| Train checkpoint | v1.12 (same JSONL as E4B/12B v1.12) |
| VRAM | **~48GB+** for QLoRA; **A100 80GB** recommended |
| Disk | **≥500 GB** if running after 12B on same instance |
| Quant eval | Q4_K_M, Q6_K (pipeline default) |

**Prerequisite:** **12B v1.12** on same A100 session (or skip 31B entirely).

## Vast (same A100 instance as 12B, if budget allows)

```bash
cd training
git pull
# transformers>=5.10.2 for Gemma 4 31B (upgrade Unsloth/zoo before run)
ARM=31b PHASE=12 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

Reports: `reports/ab_31b_q6_k_v112/` (and `ab_31b_q4_k_m_v112/`).

## Success criteria

| Gate | Target |
|------|--------|
| `tier2_gates.model_gates_passed` | **true** (115-row harness) |
| vs 12B v1.12 | Must **beat** 12B Q6_K on Tier 2 to justify premium tier |

**Publish when Tier 2 passes and beats 12B:** `exports/nassila-sanad-31b-q6_k.gguf` (private HF).

If 31B ≤ 12B v1.12, **12B remains quality tier** — no product change.

## Tier ladder

| Tier | Model | Gate |
|------|-------|------|
| Default | `nassila-sanad-e4b` | E4B default-tier (v1.12 target) |
| **Quality (main)** | **`nassila-sanad-12b`** | **Tier 2 (v1.12 target)** |
| Optional | `nassila-sanad-31b` | Tier 2 experiment |

## Rsync before destroy

```bash
scp -r -P <PORT> root@<host>:/root/nassila/training/reports/ab_31b_q6_k_v112 ./training/reports/
scp -r -P <PORT> root@<host>:/root/nassila/training/reports/ab_12b_q6_k_v112 ./training/reports/
```

Include `seed_*_predictions.jsonl` for both arms.
