#!/usr/bin/env bash
# Transformers fallback when Nanbeige vLLM pip install fails on Vast.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$TRAINING_DIR"

MODEL_PATH="${MODEL_PATH:-Nanbeige/Nanbeige4.2-3B}"
REPORT_PREFIX="${REPORT_PREFIX:-nanbeige_zeroshot}"
PREDICTIONS="outputs/${REPORT_PREFIX}_predictions.jsonl"
TEMPERATURE="${TEMPERATURE:-0.2}"

mkdir -p outputs reports

echo "=== Nanbeige Transformers fallback probe ==="
pip install -q requests transformers accelerate sentencepiece protobuf

python scripts/lmstudio_smoke_test.py --help >/dev/null 2>&1 || true

python scripts/run_nanbeige_transformers_batch.py \
  --model "$MODEL_PATH" \
  --data data/eval_samples.jsonl data/eval_holdout_90.jsonl \
  --retry 1 \
  --repair \
  --temperature "$TEMPERATURE" \
  --out "$PREDICTIONS"

python scripts/run_eval_reports.py \
  --predictions "$PREDICTIONS" \
  --prefix "${REPORT_PREFIX}_" \
  --repair

python scripts/score_nanbeige_probe.py \
  --predictions "$PREDICTIONS" \
  --combined-report "outputs/${REPORT_PREFIX}_eval_combined_report.json" \
  --holdout-report "outputs/${REPORT_PREFIX}_eval_holdout_report.json" \
  --legacy-report "outputs/${REPORT_PREFIX}_eval_report.json" \
  --out "reports/${REPORT_PREFIX}_probe_2026-07.md"

echo "Done: $PREDICTIONS"
echo "Memo: reports/${REPORT_PREFIX}_probe_2026-07.md"
