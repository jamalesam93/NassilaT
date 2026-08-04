#!/usr/bin/env bash
set -euo pipefail
cd /workspace/models/s12
EXPECTED=6217261376
GGUF=nassila-sanad-e4b-q6_k.gguf
URL='https://huggingface.co/QinEmPeRoR93/nassila-sanad-e4b/resolve/main/nassila-sanad-e4b-q6_k.gguf'
LOG=/workspace/nassila-s14/training/outputs/s12_wget_finish.log

pkill -x wget 2>/dev/null || true
pkill -x aria2c 2>/dev/null || true
rm -f "${GGUF}.aria2"

SIZE=$(stat -c%s "$GGUF" 2>/dev/null || echo 0)
echo "current=$SIZE expected=$EXPECTED"
if [[ "$SIZE" -lt "$EXPECTED" ]]; then
  echo "resuming wget..."
  wget -c --progress=dot:mega -O "$GGUF" "$URL" 2>&1 | tee "$LOG"
fi
SIZE=$(stat -c%s "$GGUF")
echo "final=$SIZE"
[[ "$SIZE" -eq "$EXPECTED" ]] || { echo "SIZE MISMATCH"; exit 1; }

cd /workspace/nassila-s14/training
# kill any half runners
ps -eo pid,cmd | awk '/bash scripts\/run_s12_contrastive_vast\.sh/ {print $1}' | while read -r pid; do kill "$pid" 2>/dev/null || true; done
pkill -x llama-server 2>/dev/null || true
sleep 1
SKIP_DEPS=1 nohup bash scripts/run_s12_contrastive_vast.sh > outputs/s12_contrastive_run.log 2>&1 < /dev/null &
echo "BATCH_STARTED=$!"
sleep 10
tail -n 25 outputs/s12_contrastive_run.log
