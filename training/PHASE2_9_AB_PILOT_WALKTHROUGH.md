# Phase 2.9 — E4B vs 12B A/B pilot (v1.10)

Controlled comparison on **shared v1.10 data** with a **hardened 90-row holdout** (legacy 45 + extension 45). Canonical gates: Nassila [`docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md) §10 + [`scripts/compare_ab_pilot.py`](./scripts/compare_ab_pilot.py).

---

## Prerequisites

- Vast GPU with llama.cpp **b9608** (see [`LLAMA_CPP_VAST.md`](./LLAMA_CPP_VAST.md))
- E4B arm: same GPU class as prior v1.x runs
- 12B arm: **~24GB+** VRAM for QLoRA train/merge (A5000 / A6000 / 4090 with headroom)
- Local or Vast: `python scripts/build_hardened_holdout.py` (writes `data/eval_holdout_90.jsonl`)

**Harness size:** 115 eval rows total = 5 legacy core + 20 extended + **90 holdout** (was 70 with 45-row holdout).

---

## Step 0 — Hardened holdout (local or Vast)

```bash
cd training
python scripts/build_hardened_holdout.py
python scripts/check_contamination.py data/l3_grounding_train_v110.jsonl
```

Extension rows `h-046`..`h-090` are **distinct** from train boost text (contamination gate must be 0).

---

## Step 1 — E4B baseline (control)

```bash
PHASE=10 bash scripts/run_vast_pipeline.sh
```

Or full A/B script with multi-seed (recommended):

```bash
ARM=e4b PHASE=10 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

**Artifacts:** `outputs/nassila-grounding-e4b-v1.10/`, `exports/*-q6_k.gguf`, `reports/v1_10_*` or `reports/ab_e4b_q6_k_v110/`.

---

## Step 2 — 12B arm (same v1.10 data)

Destroy/recreate Vast instance with larger GPU if needed:

```bash
ARM=12b PHASE=10 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

**Train once** → merge → F16 GGUF → quantize **Q4_K_M, Q6_K, Q8_0** → eval each quant on hardened harness.

**Artifacts:** `outputs/nassila-grounding-12b-v1.10/`, `reports/ab_12b_q4_k_m_v110/`, `reports/ab_12b_q6_k_v110/`, `reports/ab_12b_q8_0_v110/`.

---

## Step 3 — Multi-seed eval (optional standalone)

If you already have a GGUF served on port 1234:

```bash
python scripts/run_multi_seed_eval.py \
  --model nassila-grounding \
  --base-url http://127.0.0.1:1234 \
  --out-dir reports/ab_e4b_q6_k_v110 \
  --seeds 42 43 44 \
  --repair
```

Writes `multi_seed_aggregate.json` with mean metrics across seeds.

---

## Step 4 — Decision gates

```bash
python scripts/compare_ab_pilot.py \
  --baseline reports/ab_e4b_q6_k_v110/multi_seed_aggregate.json \
  --candidate reports/ab_12b_q6_k_v110/multi_seed_aggregate.json \
  --label "12B Q6_K" \
  --out reports/ab_decision_12b_q6_k.json
```

Repeat for Q4_K_M and Q8_0 candidates.

| Gate | Threshold |
|------|-----------|
| Combined expect delta vs E4B-Q6 | ≥ +3 pts (0.03) |
| `multi_claim` holdout pass rate | ≥ 0.80 |
| Quote validity holdout | ≥ E4B-Q6 baseline |
| Hard rows (optional) | h-043, h-045, h-084, h-085, h-088 pass |

**Outcomes:**

- **adopt_12b_optional_tier** — ship E4B default + optional 12B quant ladder
- **defer_12b_to_shahid_only** — keep iterating Sanad on E4B; reserve 12B for Shahid multimodal

---

## File index

| Path | Role |
|------|------|
| `data/eval_holdout_90.jsonl` | Hardened holdout (canonical) |
| `data/eval_holdout_extension_45.jsonl` | New rows only |
| `scripts/build_hardened_holdout.py` | Merge legacy + extension |
| `scripts/run_ab_pilot_pipeline.sh` | E4B or 12B full pipeline |
| `scripts/train_qlora_gemma4_12b.py` | 12B QLoRA |
| `scripts/run_multi_seed_eval.py` | ≥3 decode seeds |
| `scripts/compare_ab_pilot.py` | A/B decision report |

---

## Legacy 45-row reports

For regression against v1.0–v1.9 history, score with:

```bash
python scripts/run_eval_reports.py \
  --predictions reports/v1_10_predictions.jsonl \
  --holdout data/eval_holdout_45.jsonl \
  --repair
```
