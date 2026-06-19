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

## Ship gates (dual-tier — canonical: [`docs/DUAL_TIER_POLICY.md`](../docs/DUAL_TIER_POLICY.md))

### Tier 2 — 12B / 31B premium only

| Gate | Target | Slice |
|------|--------|-------|
| Combined expect | ≥90% (target ≥92%) | **115** rows (90-row holdout) |
| JSON parse (repair) | ≥98% | Combined |
| Supported h-001–h-010 | ≥8/10 | Holdout |
| Core legacy 5 | 5/5 | Legacy |
| Quote validity | ≥98% | Holdout |
| False supported | ≤5% | Holdout |

Plus manual review of 20 hard holdout rows.

### E4B default-tier — `nassila-sanad-e4b` ship

| Gate | Target |
|------|--------|
| Combined expect | ≥88% |
| Quote validity (holdout) | ≥88% |
| False supported (holdout) | ≤7% |
| JSON / h-001–h-010 / legacy 5 | same as Tier 2 |

**v1.12 recovery** must also **beat v1.10 baseline** (88.12% / 89.47% / 6.57% false-sup). Reports expose `e4b_default_gates` and `v110_baseline_beat`.

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

**Decision (dual-tier):** E4B ships on **E4B default-tier** (`e4b_default_gates`). **`nassila-sanad-12b`** (v1.10) is quality tier (Tier 2 PASS). **`nassila-sanad-31b`** (v1.12 train) is premium tier (Tier 2 target).

### v1.11 E4B — **NO-GO** (do not publish)

Multi-seed mean: **80.58%** combined, **77.19%** quote, **11.91%** false-supported. Root cause: relaxed compound `supported` + scope boost with `supported` studied subgroup. h-043 passes; h-045/h-088 still fail with forbidden `supported`.

Reports: `reports/ab_e4b_q6_k_v111/`. **Keep v1.10 as best E4B** until v1.12 recovery passes.

### v1.12 E4B recovery (operator — A6000 ~100GB)

```bash
ARM=e4b PHASE=12 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

Train: `data/l3_grounding_train_v112.jsonl`. Walkthrough: [`PHASE2_11_V112_WALKTHROUGH.md`](./PHASE2_11_V112_WALKTHROUGH.md). Rsync `reports/ab_e4b_q6_k_v112/` → destroy instance.

### v1.12 12B quality (operator — A100, main product)

Run **only after** E4B `v110_baseline_beat` passes.

```bash
ARM=12b PHASE=12 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

Walkthrough: [`PHASE2_12_12B_QUALITY_WALKTHROUGH.md`](./PHASE2_12_12B_QUALITY_WALKTHROUGH.md). Publish when `tier2_gates` pass.

### v1.12 31B (optional — same A100 after 12B)

```bash
ARM=31b PHASE=12 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

Walkthrough: [`PHASE2_12_31B_PREMIUM_WALKTHROUGH.md`](./PHASE2_12_31B_PREMIUM_WALKTHROUGH.md).
