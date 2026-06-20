# Phase 2.10 — E4B v1.11 (h-043 / h-045 fix)

Closes the E4B Tier 2 gap on the **115-row harness** after v1.10 A/B. Implementation spec: [`V111_H043_H045_FIX_REPORT.md`](./V111_H043_H045_FIX_REPORT.md).

**Local prep (done):** eval gold fix, prompt scope-silence sync, v111 boost expanded (29 rows → 12 scope-split), `l3_grounding_train_v111.jsonl` + `l3_grounding_chat_v111.jsonl` (contamination 0).

---

## Step 0 — Verify regrade (no GPU)

On a machine with v1.10 prediction JSONL under `reports/ab_e4b_q6_k_v110/`:

```bash
cd training
python scripts/build_hardened_holdout.py   # if eval gold not yet merged
python scripts/run_eval_reports.py \
  --predictions reports/ab_e4b_q6_k_v110/seed_42_predictions.jsonl \
  --repair --prefix v110_regraded_ --out-dir reports \
  --holdout data/eval_holdout_90.jsonl
```

**Stop gate:** `h-043` → pass on all seeds; `h-045` → still fail until after train.

**Recorded regrade (2026-06-17, E4B v1.10 Q6_K):**

| Seed | 115-row combined expect | h-043 | h-045 |
|------|-------------------------|-------|-------|
| 42 | 87.83% | pass | fail |
| 43 | 89.56% | pass | fail |
| 44 | 89.56% | pass | fail |

Reports: `reports/v110_regraded_eval_combined_report.json` (seed 42).

---

## Step 1 — Train + eval on Vast

Prerequisites: same as [`PHASE2_9_AB_PILOT_WALKTHROUGH.md`](./PHASE2_9_AB_PILOT_WALKTHROUGH.md) (llama.cpp b9608, `git pull` on NassilaT).

```bash
cd training
git pull
python scripts/check_contamination.py data/l3_grounding_train_v111.jsonl   # MUST be 0
python scripts/validate_dataset.py data/l3_grounding_train_v111.jsonl

ARM=e4b PHASE=11 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

**Do not** change hyperparams on first v1.11 run (2 ep, 1e-4, r=16).

Output: `reports/ab_e4b_q6_k_v111/multi_seed_aggregate.json` + per-seed `*_combined_report.json`.

---

## Step 2 — Tier 2 gates (all six on 115-row harness)

| Gate | E4B v1.10 mean | v1.11 target |
|------|----------------|--------------|
| Combined expect | 88.12% | ≥90% (operator ≥92%) |
| Quote validity (holdout) | 89.47% | ≥98% |
| False supported (holdout) | 6.57% | ≤5% |

Also verify per-row: **h-045** (2-claim split + `not_in_source` on unstudied subgroup), **h-088**, quote-invalid rows.

---

## Step 3 — Publish (only if Tier 2 PASS)

1. GGUF → `QinEmPeRoR93/nassila-sanad-e4b` (private until ship).
2. Update [`MODEL_CARD_sanad_e4b.md`](./MODEL_CARD_sanad_e4b.md) with v1.11 metrics.
3. Nassila: update [`docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md) E4B status.

**12B v1.11:** optional after E4B passes — `ARM=12b PHASE=11 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh`.

---

## Step 4 — Rsync reports back

```bash
# From PC (adjust host)
scp -r root@<vast-host>:/root/nassila/training/reports/ab_e4b_q6_k_v111 ./training/reports/
```
