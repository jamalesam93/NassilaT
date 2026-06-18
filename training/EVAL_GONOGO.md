# Eval go / no-go — Sanad (`l3_grounding`)

**Canonical gates:** [Nassila `docs/OUROBOROS_CONTEXT.md` §10](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md). Do not duplicate thresholds here — use §10 and `scripts/tier_gates.py`.

**Checkpoint:** `nassila-grounding-e4b-v1.4a` (Tier 1). **Ship target:** Tier 2 model gates + Tier 2b app guardrail.

## Baseline reference

See [`outputs/baseline_report_reference.json`](./outputs/baseline_report_reference.json) (Phase 0: 100% JSON w/ repair, 82% expect pass).

**Live baseline:** start LM Studio, then:

```powershell
.\scripts\run_baseline_eval.ps1
```

## Tuned model (after Vast)

```powershell
python scripts/run_l3_eval_batch.py --model "nassila-grounding-e4b-v1.10" `
  --data data/eval_samples.jsonl data/eval_samples_extended.jsonl data/eval_holdout_90.jsonl `
  --retry 1 --repair --out reports/v1_10_predictions.jsonl

python scripts/run_eval_reports.py `
  --predictions reports/v1_10_predictions.jsonl --repair --prefix v1_10_ `
  --holdout data/eval_holdout_90.jsonl
```

Read `reports/v1_8_eval_combined_report.json` → `tier2_gates.model_gates_passed`.

## Tier 2 model gates (summary — see §10 for full table)

| Gate | Target | Slice |
|------|--------|-------|
| Combined expect | ≥90% (target ≥92%) | **115** rows (90-row holdout) |
| JSON parse (repair) | ≥98% | Combined |
| Supported h-001–h-010 | ≥8/10 | Holdout |
| Core legacy 5 | 5/5 | Legacy |
| Quote validity | ≥98% | Holdout |
| False supported | ≤5% | Holdout |

Plus manual review of 20 hard holdout rows.

## v1.8 train prep + Vast

```bash
python scripts/prepare_v15_train.py --base data/l3_grounding_train_v14a.jsonl \
  --boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v18_boost.jsonl \
  --out data/l3_grounding_train_v18.jsonl
python scripts/check_contamination.py data/l3_grounding_train_v18.jsonl
python scripts/validate_dataset.py data/l3_grounding_train_v18.jsonl
```

Boost: `l3_grounding_v16_boost.jsonl` + `l3_grounding_v18_boost.jsonl` (passage-claim compound; no-supported multi; v1.7 dropped).

```bash
PHASE=8 bash scripts/run_vast_pipeline.sh
```

## No-go actions

- Do **not** rerun v1.7 (zero delta vs v1.6) or **v1.9** (regressed vs v1.8: false-supported gate lost)
- **Best clean run so far:** v1.8 at 91.43% combined (5/6 gates); ship blocked on quote validity holdout
- Iterate via `l3_grounding_v110_boost.jsonl` (drops v19 sup overdose) — `PHASE=10`
- Do not publish adapter as Tier 2 ship until `tier2_gates.model_gates_passed` is true

## v1.10 train prep + Vast

```bash
python scripts/prepare_v15_train.py \
  --base data/l3_grounding_train_v14a.jsonl \
  --boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v18_boost.jsonl data/l3_grounding_v110_boost.jsonl \
  --out data/l3_grounding_train_v110.jsonl
PHASE=10 bash scripts/run_vast_pipeline.sh
```

## A/B pilot (E4B vs 12B)

After v1.10 E4B baseline, run 12B arm on same data. See [`PHASE2_9_AB_PILOT_WALKTHROUGH.md`](./PHASE2_9_AB_PILOT_WALKTHROUGH.md).

```bash
python scripts/build_hardened_holdout.py
ARM=e4b PHASE=10 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
# new Vast instance (~24GB+)
ARM=12b PHASE=10 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
python scripts/compare_ab_pilot.py \
  --baseline reports/ab_e4b_q6_k_v110/multi_seed_aggregate.json \
  --candidate reports/ab_12b_q6_k_v110/multi_seed_aggregate.json \
  --label "12B Q6_K"
```

### A/B result (recorded)

Harness: **115 rows** (90-row holdout). Multi-seed means (42/43/44).

| Arm | Combined | Quote (holdout) | False sup | Tier 2 §10 |
|-----|----------|-----------------|-----------|------------|
| E4B v1.10 Q6_K | 88.12% | 89.47% | 6.57% | **NO-GO** |
| **12B v1.10 Q6_K** | **94.79%** | **100%** | **2.82%** | **PASS** (`nassila-sanad-12b`) |

**Decision (dual-tier):** E4B stays default/fast tier (`nassila-sanad-e4b`). **`nassila-sanad-12b`** (checkpoint v1.10) is the optional quality tier and first Tier-2-passing Sanad checkpoint. Continue E4B **v1.11** on Vast to close the gap.

### v1.11 E4B (operator — close default-tier gap)

**Harness v1.11 gold (2026-06-17):** h-043 Option A (`min_claims: 2`, no forbidden `supported`); h-045 `min_claims: 2`. Regrade of v1.10 predictions confirms h-043 passes without retrain; h-045 still fails until train.

```bash
ARM=e4b PHASE=11 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

Train file: `data/l3_grounding_train_v111.jsonl` (29-row v111 boost, 12 scope-split). Walkthrough: [`PHASE2_10_V111_WALKTHROUGH.md`](./PHASE2_10_V111_WALKTHROUGH.md). Publish `exports/nassila-sanad-e4b-q6_k.gguf` when all six Tier 2 gates pass.

Reports: `reports/ab_e4b_q6_k_v111/` (after Vast run).
