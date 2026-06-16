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
python scripts/run_l3_eval_batch.py --model "nassila-grounding-e4b-v1.8" `
  --data data/eval_samples.jsonl data/eval_samples_extended.jsonl data/eval_holdout_45.jsonl `
  --retry 1 --repair --out reports/v1_8_predictions.jsonl

python scripts/run_eval_reports.py `
  --predictions reports/v1_8_predictions.jsonl --repair --prefix v1_8_
```

Read `reports/v1_8_eval_combined_report.json` → `tier2_gates.model_gates_passed`.

## Tier 2 model gates (summary — see §10 for full table)

| Gate | Target | Slice |
|------|--------|-------|
| Combined expect | ≥90% (target ≥92%) | 70 rows |
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

- Do **not** rerun v1.7 (zero delta vs v1.6)
- Iterate via `l3_grounding_v18_boost.jsonl` + prompt if v1.8 still misses
- Do not publish adapter as Tier 2 ship until `tier2_gates.model_gates_passed` is true
