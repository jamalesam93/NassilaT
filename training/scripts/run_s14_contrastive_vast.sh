#!/usr/bin/env bash
# S14 contrastive v2 on Vast: HF GGUF + llama.cpp (no Ollama install).
# Model: https://huggingface.co/QinEmPeRoR93/nassila-sanad-12b
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$TRAINING_DIR"
sed -i 's/\r$//' "$0" 2>/dev/null || true

LLAMA_PORT="${LLAMA_PORT:-8081}"
BASE_URL="http://127.0.0.1:${LLAMA_PORT}"
TEMPERATURE="${TEMPERATURE:-0.2}"
EVAL_DATA="data/eval_holdout_body_contrastive_frozen_v2.jsonl"
PREDICTIONS="reports/tier3_body_contrastive_frozen_v2_predictions_s14_vast.jsonl"
EVAL_REPORT="reports/tier3_body_contrastive_frozen_v2_s14_vast_eval.json"
MODELS_DIR="${MODELS_DIR:-/workspace/models/s14}"
GGUF_PATH="${MODELS_DIR}/nassila-sanad-12b-q6_k.gguf"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-/workspace/llama.cpp}"
SERVER="${LLAMA_CPP_DIR}/build/bin/llama-server"
SERVER_LOG="outputs/s14_llama_server.log"
SERVER_PID_FILE="outputs/s14_llama.pid"
MODEL_NAME="${MODEL_NAME:-nassila-sanad-12b}"

mkdir -p outputs reports data "$MODELS_DIR"

# Vast NGC images often bind Jupyter on :8080 — default to 8081.
if ss -ltn 2>/dev/null | grep -q ":${LLAMA_PORT} " && [[ "${LLAMA_PORT}" == "8081" || "${LLAMA_PORT}" == "8080" ]]; then
  if ! curl -sf "http://127.0.0.1:${LLAMA_PORT}/health" >/dev/null 2>&1 \
    && ! curl -sf "http://127.0.0.1:${LLAMA_PORT}/v1/models" >/dev/null 2>&1; then
    echo "port ${LLAMA_PORT} busy (not llama); trying 8081/8090"
    for p in 8081 8090 8091; do
      if ! ss -ltn 2>/dev/null | grep -q ":${p} "; then
        LLAMA_PORT="$p"
        BASE_URL="http://127.0.0.1:${LLAMA_PORT}"
        break
      fi
    done
  fi
fi

cleanup_server() {
  if [[ -f "$SERVER_PID_FILE" ]]; then
    pid="$(cat "$SERVER_PID_FILE")"
    kill "$pid" 2>/dev/null || true
    rm -f "$SERVER_PID_FILE"
  fi
}
trap cleanup_server EXIT

echo "=== S14 contrastive Vast (llama.cpp + HF) ==="
echo "  data: $EVAL_DATA"
[[ -f "$EVAL_DATA" ]] || { echo "missing $EVAL_DATA"; exit 1; }

echo "=== deps ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git build-essential cmake curl wget >/dev/null
pip install -q requests huggingface_hub || pip3 install -q requests huggingface_hub

if [[ ! -x "$SERVER" ]]; then
  echo "=== build llama.cpp CUDA ==="
  if [[ ! -d "$LLAMA_CPP_DIR/.git" ]]; then
    git clone --depth 1 https://github.com/ggerganov/llama.cpp.git "$LLAMA_CPP_DIR"
  fi
  cmake -S "$LLAMA_CPP_DIR" -B "$LLAMA_CPP_DIR/build" -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
  cmake --build "$LLAMA_CPP_DIR/build" --config Release -j8 --target llama-server
fi
[[ -x "$SERVER" ]] || { echo "no llama-server at $SERVER"; exit 1; }

if [[ ! -f "$GGUF_PATH" ]]; then
  echo "=== download GGUF from HF ==="
  python3 - <<'PY'
from huggingface_hub import hf_hub_download
import os
path = hf_hub_download(
    repo_id="QinEmPeRoR93/nassila-sanad-12b",
    filename="nassila-sanad-12b-q6_k.gguf",
    local_dir=os.environ.get("MODELS_DIR", "/workspace/models/s14"),
)
print("downloaded", path)
PY
fi
ls -lh "$GGUF_PATH"

echo "=== start llama-server ==="
# Gemma4 peg/channel parser rejects valid JSON as HTTP 500 — use content parser.
cleanup_server
nohup "$SERVER" \
  -m "$GGUF_PATH" \
  -ngl 99 \
  -c 4096 \
  --host 127.0.0.1 \
  --port "$LLAMA_PORT" \
  --reasoning-format none \
  --skip-chat-parsing \
  >"$SERVER_LOG" 2>&1 &
echo $! >"$SERVER_PID_FILE"
echo "pid=$(cat "$SERVER_PID_FILE") port=$LLAMA_PORT log=$SERVER_LOG"

for i in $(seq 1 90); do
  if curl -sf "$BASE_URL/health" >/dev/null 2>&1 || curl -sf "$BASE_URL/v1/models" >/dev/null 2>&1; then
    echo "server ready (${i})"
    break
  fi
  if ! kill -0 "$(cat "$SERVER_PID_FILE")" 2>/dev/null; then
    echo "server died:"; tail -n 50 "$SERVER_LOG"; exit 1
  fi
  if [[ "$i" -eq 90 ]]; then
    echo "server timeout:"; tail -n 50 "$SERVER_LOG"; exit 1
  fi
  sleep 5
done

echo "=== smoke ==="
curl -sf "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL_NAME}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with the single word: ok\"}],\"temperature\":0.2,\"max_tokens\":16}" \
  | head -c 400
echo

echo "=== batch 308 ==="
python3 scripts/run_l3_eval_batch.py \
  --base-url "$BASE_URL" \
  --api-key ollama \
  --model "$MODEL_NAME" \
  --data "$EVAL_DATA" \
  --retry 1 \
  --repair \
  --temperature "$TEMPERATURE" \
  --timeout 300 \
  --sleep 0.1 \
  --out "$PREDICTIONS"

python3 scripts/evaluate_outputs.py \
  --eval "$EVAL_DATA" \
  --predictions "$PREDICTIONS" \
  --report "$EVAL_REPORT" \
  --repair

echo "Done: $PREDICTIONS $EVAL_REPORT"
