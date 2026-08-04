#!/usr/bin/env bash
# One-shot restart for S14 contrastive on Vast (peg fix).
set -euo pipefail
cd /workspace/nassila-s14/training

# Stop prior llama-server / batch
if [[ -f outputs/s14_llama.pid ]]; then
  kill "$(cat outputs/s14_llama.pid)" 2>/dev/null || true
fi
pkill -x llama-server 2>/dev/null || true
pkill -f 'run_l3_eval_batch.py' 2>/dev/null || true
# Do not pkill the restart helper by name overlap with run_s14 if we're careful:
# kill only the long-running runner if present
ps -eo pid,cmd | awk '/bash scripts\/run_s14_contrastive_vast\.sh/ && !/restart_s14/ {print $1}' | while read -r pid; do
  kill "$pid" 2>/dev/null || true
done
sleep 2

mv -f reports/tier3_body_contrastive_frozen_v2_predictions_s14_vast.jsonl \
  reports/tier3_body_contrastive_frozen_v2_predictions_s14_vast.bad_peg500.jsonl 2>/dev/null || true

export LLAMA_PORT=8081
nohup bash scripts/run_s14_contrastive_vast.sh > outputs/s14_contrastive_run.log 2>&1 < /dev/null &
echo "STARTED=$!"
sleep 20
echo "=== log ==="
tail -n 40 outputs/s14_contrastive_run.log
echo "=== procs ==="
ps -eo pid,etime,cmd | grep -E 'llama-server|run_l3_eval|run_s14_contrastive' | grep -v grep || true
