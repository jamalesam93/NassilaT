#!/usr/bin/env bash
# Clean restart: kill S14 watch + stuck S12 dl, wget GGUF, run batch.
set -euo pipefail
cd /workspace/nassila-s14/training

# Kill leftover S14 watcher and stuck S12 runner/download
pkill -f 'predictions_s14_vast' 2>/dev/null || true
if [[ -f outputs/s12_llama.pid ]]; then kill "$(cat outputs/s12_llama.pid)" 2>/dev/null || true; fi
pkill -x llama-server 2>/dev/null || true
ps -eo pid,cmd | awk '/bash scripts\/run_s12_contrastive_vast\.sh/ {print $1}' | while read -r pid; do
  kill "$pid" 2>/dev/null || true
done
pkill -f 'hf_hub_download|huggingface_hub' 2>/dev/null || true
sleep 2

MODELS_DIR=/workspace/models/s12
mkdir -p "$MODELS_DIR"
GGUF="$MODELS_DIR/nassila-sanad-e4b-q6_k.gguf"
URL="https://huggingface.co/QinEmPeRoR93/nassila-sanad-e4b/resolve/main/nassila-sanad-e4b-q6_k.gguf"

# Drop incomplete HF cache so we don't resume a bad partial
rm -rf "$MODELS_DIR/.cache" "$MODELS_DIR"/*.lock 2>/dev/null || true

if [[ ! -f "$GGUF" ]]; then
  echo "=== wget S12 GGUF ==="
  wget -c --progress=dot:giga -O "$GGUF" "$URL"
fi
ls -lh "$GGUF"

export SKIP_DEPS=1
export MODELS_DIR
nohup bash scripts/run_s12_contrastive_vast.sh > outputs/s12_contrastive_run.log 2>&1 < /dev/null &
echo "STARTED=$!"
echo "Watch with:"
echo "  watch -n 5 \"echo S12; ls -lh $GGUF; wc -l reports/tier3_body_contrastive_frozen_v2_predictions_s12_vast.jsonl 2>/dev/null; tail -n 3 outputs/s12_contrastive_run.log\""
sleep 8
tail -n 20 outputs/s12_contrastive_run.log
