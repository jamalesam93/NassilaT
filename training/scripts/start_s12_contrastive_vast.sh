#!/usr/bin/env bash
set -euo pipefail
cd /workspace/nassila-s14/training
pkill -x llama-server 2>/dev/null || true
sleep 1
SKIP_DEPS=1 nohup bash scripts/run_s12_contrastive_vast.sh > outputs/s12_contrastive_run.log 2>&1 < /dev/null &
echo "STARTED=$!"
sleep 15
tail -n 30 outputs/s12_contrastive_run.log
ps -eo pid,etime,cmd | grep -E 'run_s12_contrastive|llama-server|run_l3_eval' | grep -v grep || true
