#!/usr/bin/env bash
set -euo pipefail
HOST=174.136.205.7
PORT=20008
REMOTE=/workspace/nassila-s14/training
LOCAL="/mnt/e/Cursor Projects/NassilaT/training"

ssh -p "$PORT" -o StrictHostKeyChecking=accept-new "root@$HOST" \
  "mkdir -p $REMOTE/data $REMOTE/outputs $REMOTE/reports $REMOTE/scripts"

sed -i 's/\r$//' "$LOCAL/scripts/run_s14_contrastive_vast.sh"

scp -P "$PORT" \
  "$LOCAL/scripts/run_l3_eval_batch.py" \
  "$LOCAL/scripts/evaluate_outputs.py" \
  "$LOCAL/scripts/json_repair.py" \
  "$LOCAL/scripts/lmstudio_smoke_test.py" \
  "$LOCAL/scripts/validate_dataset.py" \
  "$LOCAL/scripts/corpus_utils.py" \
  "$LOCAL/scripts/run_s14_contrastive_vast.sh" \
  "root@$HOST:$REMOTE/scripts/"

scp -P "$PORT" \
  "$LOCAL/data/eval_holdout_body_contrastive_frozen_v2.jsonl" \
  "root@$HOST:$REMOTE/data/"

ssh -p "$PORT" "root@$HOST" "ls -la $REMOTE/scripts $REMOTE/data"
