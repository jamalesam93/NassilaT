# v1.4 Vast evaluation — PENDING

Run on Vast after local prep (see [PHASE2_7_V1_4_WALKTHROUGH.md](../PHASE2_7_V1_4_WALKTHROUGH.md)):

```bash
PHASE=4a bash scripts/run_vast_pipeline.sh
```

After completion, this directory should contain:

- `v1_4a_predictions.jsonl`
- `v1_4a_eval_combined_report.json`
- `v1_4a_eval_holdout_report.json`
- `v1_4a_eval_core_extended_report.json`
- `holdout_failure_matrix.md` (updated via `compare_eval_versions.py`)

Update [MODEL_CARD_v1_4.md](../MODEL_CARD_v1_4.md) with GO/NO-GO metrics.
