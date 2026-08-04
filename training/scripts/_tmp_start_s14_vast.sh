#!/usr/bin/env bash
# Upload HF-pull script + ensure eval data, then start S14 contrastive run.
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

# Kill any prior run, then start fresh in background
ssh -p "$PORT" "root@$HOST" bash -s <<'REMOTE'
set -euo pipefail
cd /workspace/nassila-s14/training
sed -i 's/\r$//' scripts/run_s14_contrastive_vast.sh
chmod +x scripts/run_s14_contrastive_vast.sh
pkill -f run_s14_contrastive_vast.sh 2>/dev/null || true
pkill -f 'run_l3_eval_batch.py.*contrastive_frozen_v2' 2>/dev/null || true
sleep 1
nohup bash scripts/run_s14_contrastive_vast.sh > outputs/s14_contrastive_vast.log 2>&1 &
echo STARTED_PID=$!
sleep 3
head -n 30 outputs/s14_contrastive_vast.log || true
REMOTE
