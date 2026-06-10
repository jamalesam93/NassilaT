# Baseline eval — requires LM Studio local server on http://localhost:1234
Set-Location $PSScriptRoot\..

python scripts/run_l3_eval_batch.py `
  --model "google/gemma-4-e4b" `
  --data data/eval_samples.jsonl data/eval_holdout_45.jsonl `
  --retry 1 --repair `
  --out outputs/baseline_predictions.jsonl

python scripts/run_eval_reports.py `
  --predictions outputs/baseline_predictions.jsonl `
  --repair
# Copy even when checks fail (e.g. LM Studio was down)
Copy-Item -Force outputs/eval_combined_report.json outputs/baseline_report.json
