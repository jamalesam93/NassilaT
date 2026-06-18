# Phase 2.12 — Gemma 4 31B premium Sanad

**One final quality train** on the same v1.12 data + prompt as E4B recovery. Targets **Tier 2** (full quality bar), not E4B default-tier.

Policy: [`docs/DUAL_TIER_POLICY.md`](../docs/DUAL_TIER_POLICY.md).

## Model

| Field | Value |
|-------|--------|
| Base | `google/gemma-4-31B-it` |
| Public id | `nassila-sanad-31b` |
| Train checkpoint | v1.12 (same JSONL as E4B v1.12) |
| VRAM | **~48GB+** for QLoRA; Vast **A100 80GB** recommended |
| Quant eval | Q4_K_M, Q6_K (pipeline default) |

**Prerequisite:** Run **E4B v1.12** first and confirm prompt/boost are stable (`PHASE2_11_V112_WALKTHROUGH.md`).

## Vast

```bash
cd training
git pull
# transformers>=5.10.2 for Gemma 4 31B (same as 12B arm — upgrade Unsloth/zoo before run)
ARM=31b PHASE=12 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

Reports: `reports/ab_31b_q6_k_v112/` (or `q4_k_m`).

## Success criteria

| Gate | Target |
|------|--------|
| `tier2_gates.model_gates_passed` | **true** (all six gates, 115-row harness) |
| Combined expect | ≥ 94% stretch (12B v1.10 = 94.79%) |
| Quote validity (holdout) | ≥ 98% |
| False supported (holdout) | ≤ 5% |

**Publish when Tier 2 passes:** `exports/nassila-sanad-31b-q6_k.gguf` (private HF until product ship).

## Tier ladder (after 31B)

| Tier | Model | Gate |
|------|-------|------|
| Default | `nassila-sanad-e4b` | E4B default-tier |
| Quality | `nassila-sanad-12b` | Tier 2 (v1.10 PASS) |
| Premium | `nassila-sanad-31b` | Tier 2 (v1.12 train) |

Users pick download size vs quality in LM Studio presets (future Ouroboros UI).

## Notes

- 31B is multimodal in base Gemma 4; L3 train uses **text-only** grounding chat (same as 12B).
- If 31B does not beat 12B Q6_K on Tier 2, **12B remains the quality tier**; 31B stays optional/private.
- Rsync `reports/ab_31b_*_v112/` and predictions before destroying the instance.
