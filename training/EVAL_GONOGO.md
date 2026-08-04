# Eval go / no-go — Sanad (`l3_grounding`)

**Canonical gates:** [Nassila `docs/OUROBOROS_CONTEXT.md` §10](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md). Do not duplicate thresholds here — use §10 and `scripts/tier_gates.py`.

**Ship checkpoints:** S15 **4B** (`nassila-sanad-4b`, Qwen 3.5 4B — default-tier), 12B **v1.14** (`nassila-sanad-12b` — Tier 2 + h-045/h-088 split fix). E4B **S12** retired as default. See [`OUROBOROS_OPERATOR_MAP.md`](./OUROBOROS_OPERATOR_MAP.md).

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

### Tier 2 — 12B quality tier only

| Gate | Target | Slice |
|------|--------|-------|
| Combined expect | ≥90% (target ≥92%) | **115** rows (90-row holdout) |
| JSON parse (repair) | ≥98% | Combined |
| Supported h-001–h-010 | ≥8/10 | Holdout |
| Core legacy 5 | 5/5 | Legacy |
| Quote validity | ≥98% | Holdout |
| False supported | ≤5% | Holdout |

Plus manual review of 20 hard holdout rows.

### E4B default-tier — `nassila-sanad-e4b` ship → **RETIRED** (replaced by S15 4B)

> **Status (2026-08):** E4B **S12 retired** as the default tier. The app/website now default to `nassila-sanad-4b` (**S15**, Qwen 3.5 4B). E4B remains published on HF for legacy users only.

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

**Decision (dual-tier):** E4B ships on **E4B default-tier** (`e4b_default_gates`). **`nassila-sanad-12b`** moved from v1.10 → v1.12 → **v1.14** as quality tier.

### v1.11 E4B — **NO-GO** (do not publish)

Multi-seed mean: **80.58%** combined, **77.19%** quote, **11.91%** false-supported. Root cause: relaxed compound `supported` + scope boost with `supported` studied subgroup. h-043 passes; h-045/h-088 still fail with forbidden `supported`.

Reports: `reports/ab_e4b_q6_k_v111/`. Do not publish.

### v1.12 E4B — **GO** (ship `nassila-sanad-e4b`, checkpoint v1.12)

Multi-seed mean (seeds 42/43/44, Q6_K, 115-row harness): **89.27%** combined, **92.98%** quote (holdout), **3.81%** false-supported (holdout).

| Check | Result |
|-------|--------|
| `e4b_default_gates.model_gates_passed` | **true** (3/3 seeds) |
| `v110_baseline_beat.all_met` | **true** (3/3 seeds) |
| `tier2_gates.model_gates_passed` | false (expected for E4B) |

Reports: `reports/ab_e4b_q6_k_v112/`. Walkthrough (archive): [`archive/PHASE2_11_V112_WALKTHROUGH.md`](./archive/PHASE2_11_V112_WALKTHROUGH.md).

**Publish:** `exports/nassila-sanad-e4b-q6_k.gguf` → `QinEmPeRoR93/nassila-sanad-e4b`. Model card: [`MODEL_CARD_sanad_e4b.md`](./MODEL_CARD_sanad_e4b.md).

**12B v1.12 spend:** greenlit (`v110_baseline_beat` met).

### v1.12 12B quality — **GO** (reference / fallback quality tier)

Multi-seed mean (Q6_K): **94.20%** combined, **100%** quote, **2.86%** false-supported. **Tier 2 PASS** (3/3 seeds). Reports: `reports/ab_12b_q6_k_v112/`.

Keep as fallback/reference. h-045 / h-088 still fail (`multi_claim` 69.23%); known limitation, not a Tier 2 blocker.

### v1.13 12B multi_claim — **NO-GO** (do not publish)

Trained 2026-06; reports: `reports/ab_12b_q6_k_v113/`.

| Metric | v1.12 | v1.13 mean | Tier 2 |
|--------|-------|------------|--------|
| Combined expect | 94.20% | **88.99%** | ≥90% FAIL |
| Quote (holdout) | 100% | **94.74%** | ≥98% FAIL |
| JSON parse (repair) | 100% | **~95.7%** | ≥98% FAIL |
| Tier 2 pass | 3/3 | **0/3** | FAIL |

**h-045 / h-088:** regressed from bundled `min_claims` fail (v1.12) to **`parse_json`** (`No JSON object`) on all seeds — boost did not fix splits; destabilized outputs.

**Keep shipping 12B v1.12.** Do not publish v1.13 GGUF. Walkthrough (archive): [`archive/PHASE2_13_12B_MULTI_CLAIM_WALKTHROUGH.md`](./archive/PHASE2_13_12B_MULTI_CLAIM_WALKTHROUGH.md).

### v1.14 12B multi_claim — **GO** (selected quality tier)

Multi-seed mean (Q6_K): **90.43%** combined, **100%** quote, **2.86%** false-supported, **84.62%** `multi_claim`. **Tier 2 PASS** (3/3 seeds). Reports: `reports/ab_12b_q6_k_v114/`.

| Metric | v1.12 | v1.14 | Decision |
|--------|-------|-------|----------|
| Combined expect | **94.20%** | **90.43%** | regression accepted |
| Quote (holdout) | 100% | **100%** | PASS |
| JSON parse (repair) | 100% | **100%** | PASS |
| multi_claim | 69.23% | **84.62%** | target met |
| h-045 / h-088 | fail | **pass all seeds** | target met |
| Tier 2 pass | 3/3 | **3/3** | PASS |

**Publish:** `exports/nassila-sanad-12b-q6_k.gguf` from **v1.14** → `QinEmPeRoR93/nassila-sanad-12b`. v1.12 remains the higher-combined fallback/reference.

### S15 4B — **GO** (ship `nassila-sanad-4b`, default-tier, 2026-08)

QLoRA fine-tune of **`Qwen/Qwen3.5-4B`** on the same **874-row `l3_grounding_train_v114.jsonl`** used for v1.14 (no new S15 boost data). Training converged at epoch 1.73, step 193/330: loss **0.3464**, token acc **91.90%**. Eval with **thinking disabled** (llama.cpp `/no_think`; Qwen thinking mode truncates output).

**Eval (single run):** `eval_holdout_body_contrastive_frozen_v2` (308 rows):

| Metric | S15 4B | Gate |
|--------|--------|------|
| Combined expect | **94.48%** | ≥88 default |
| JSON (with repair) | **99.35%** | ≥98% |
| False-supported | **4.87%** | ≤5% ✓ |
| Contradicted | 85.83% | monitor |
| Not-in-source | 100% | monitor |
| Quote validity | *not measured on this harness* | **pending local verify** |

**Provenance caveat:** this is a **single-run** contrastive body eval. No multi-seed abstract-harness run or quote measurement exists for S15 yet — backfill those with a local laptop eval (`llama-server` + `run_l3_eval_batch.py --disable-thinking`) before presenting the card quote figure as verified.

**Nanbeige 3B probe:** failed (34.42% false-supported, fine-tuned) — **NO-GO, archived**. See [`NANBEIGE_VAST_PROBE.md`](./NANBEIGE_VAST_PROBE.md).

**Publish:** `exports/nassila-sanad-4b-q6_k.gguf` → `QinEmPeRoR93/nassila-sanad-4b`. Model card: [`hf_readmes/nassila-sanad-4b/README.md`](./hf_readmes/nassila-sanad-4b/README.md).

---

## Tier 3 prep — **S15 SHIPPED** (2026-08); body grooming continues

**Status:** S15 (Qwen 3.5 4B) trained and shipped on the same v1.14 data; body contrastive harness `frozen_v2` is the new default-tier eval. W7+ / Maktab-M11 / institutional access still parked.

| Gate | Artifact | Status |
|------|----------|--------|
| Field-note boosts | `data/l3_grounding_masdar_lite_boost.jsonl` | **Complete** (49/49 masdar-lite-jul13) |
| Body holdout pilot | `eval_holdout_body_pilot.jsonl` (5) + `eval_holdout_body_draft.jsonl` (78 proxy) + combined draft | Structure validated; operator review + model scoring pending |
| **Body contrastive v2** | `eval_holdout_body_contrastive_frozen_v2.jsonl` (308) | **S15 ship evidence** (single run) |
| Schemas | `DATASET_SCHEMA.md` (`doc_extract`, `source_pdf_extract`) | Locked v1 |
| OA pilot script | `scripts/fetch_oa_fulltext.py` | Ready; operator runs W4 |
| Body gate scorer | `scripts/score_body_holdout_pilot.py` + `tier_gates.evaluate_tier3_body_gates` | Ready |
| Product measurements | Post–1.7 manuscript reruns | **Not started** |
| Go/no-go memo | [`S15_UNPARK_CRITERIA.md`](./S15_UNPARK_CRITERIA.md) | **S15 criteria MET** — see S15 entry above |

**Decision (2026-08):** S15 shipped as default tier on contrastive v2 single-run. **Recommendation:** run a committed multi-seed + quote-bearing laptop eval to close the provenance gap before marketing the quote figure; keep S14 quality tier unchanged.

**Next operator steps:** continue field-note labels; run W4 OA pilot; grow body holdout toward 100 docs / 400–500 claims; cut app **1.4.0 Raqim Statute**.
