# Phase 2.11 — E4B v1.12 recovery (default-tier ship)

**Status: GO (2026-06-19)** — E4B default-tier + v1.10 baseline beat on all seeds. Reports: `reports/ab_e4b_q6_k_v112/`. Publish GGUF → [`QinEmPeRoR93/nassila-sanad-e4b`](https://huggingface.co/QinEmPeRoR93/nassila-sanad-e4b).

Recovers from v1.11 regression. Spec: [`V112_RECOVERY_PLAN.md`](./V112_RECOVERY_PLAN.md). Policy: [`docs/DUAL_TIER_POLICY.md`](../../docs/DUAL_TIER_POLICY.md).

**12B quality train** — see [`PHASE2_12_12B_QUALITY_WALKTHROUGH.md`](./PHASE2_12_12B_QUALITY_WALKTHROUGH.md) (archive).

## What changed vs v1.11

1. **Prompt v1.12** — passage-number discipline + parity compound guardrail; scope rows use `weak` only.
2. **Boost** — `l3_grounding_v112_boost.jsonl` (23 rows, 6 scope, all `weak` on studied subgroup).
3. **Gates** — ship E4B on **E4B default-tier**, not Tier 2. Tier 2 remains for 12B.

## Instance (E4B only)

| Field | Value |
|-------|--------|
| GPU | **A6000** (48 GB) or similar — sufficient for E4B QLoRA |
| Disk | **~100 GB** OK for E4B (train + merge + Q6_K eval) |
| Do **not** run 12B on this disk — destroy after rsync |

## Local prep (done in repo)

- `data/l3_grounding_train_v112.jsonl` (850 rows, contamination 0)
- `fixtures/grounding_prompt_golden.txt` (v1.12 prompt)

## Vast

```bash
cd training
git pull
python scripts/check_contamination.py data/l3_grounding_train_v112.jsonl
ARM=e4b PHASE=12 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

## Success criteria

| Check | Target |
|-------|--------|
| `e4b_default_gates.model_gates_passed` | **true** (all seeds or mean) |
| `v110_baseline_beat.all_met` | **true** — must beat v1.10 (88.12% / 89.47% quote / 6.57% false-sup) |
| `tier2_gates.model_gates_passed` | nice-to-have; **not** E4B ship requirement |
| h-043, h-045 | pass |
| eval-002, eval-017, h-012 | back to `contradicted` (no `supported` spam) |

**Publish E4B when default-tier passes:** `exports/nassila-sanad-e4b-q6_k.gguf` → `QinEmPeRoR93/nassila-sanad-e4b`.

If v1.12 fails baseline beat, **keep shipping v1.10 E4B** — do not publish v1.11.

**Stop gate for 12B spend:** only rent A100 for 12B v1.12 after E4B `v110_baseline_beat` is met (confirms v1.12 recipe is safe).

## Rsync before destroy (required)

```powershell
scp -r -P <PORT> root@<host>:/root/nassila/training/reports/ab_e4b_q6_k_v112 "E:\Cursor Projects\NassilaT\training\reports\"
```

Must include `seed_*_predictions.jsonl` for forensics.

Optional disk cleanup on instance after quantize (if tight on 100 GB):

```bash
rm -f exports/nassila-sanad-e4b-v1.12-f16.gguf
rm -rf exports/hf-merged-sanad-e4b-v1.12-bf16
```

Keep `reports/ab_e4b_q6_k_v112/` until rsync completes. Upload GGUF from PC or instance — see [`PHASE2_9_AB_PILOT_WALKTHROUGH.md`](./PHASE2_9_AB_PILOT_WALKTHROUGH.md) Part 9.

## Recorded result (2026-06-19)

| Metric (mean) | v1.10 | v1.11 | **v1.12** |
|---------------|-------|-------|-----------|
| Combined expect | 88.12% | 80.58% | **89.27%** |
| Quote (holdout) | 89.47% | 77.19% | **92.98%** |
| False supported (holdout) | 6.57% | 11.91% | **3.81%** |

Spot rows: eval-002, eval-017, h-012, h-043 pass all seeds. h-045 still fails (non-blocking vs v1.10).
