#!/usr/bin/env bash
# S15 contrastive v2 on Vast (llama.cpp + HF GGUF) — dual-branch audit.
#
# Why: the laptop run (LM Studio, /no_think fast path) did NOT reproduce the
# claimed 94.48% / 4.87% numbers. This script runs the SAME shipped GGUF on
# llama.cpp with BOTH prompt branches to isolate the cause:
#
#   branch A (fast):  --disable-thinking  -> appends /no_think to user turn
#   branch B (claim): no flag             -> appends "keep reasoning concise" note
#
# Model: https://huggingface.co/QinEmPeRoR93/nassila-sanad-4b
# Artifacts pulled down by vast_s15_contrastive_sync.ps1 -Direction down.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$TRAINING_DIR"
sed -i 's/\r$//' "$0" 2>/dev/null || true

LLAMA_PORT="${LLAMA_PORT:-8081}"
BASE_URL="http://127.0.0.1:${LLAMA_PORT}"
TEMPERATURE="${TEMPERATURE:-0.2}"
SEED="${SEED:-42}"
EVAL_DATA="data/eval_holdout_body_contrastive_frozen_v2.jsonl"
PRED_A="reports/s15_contrastive_v2_vast_fast_predictions.jsonl"
PRED_B="reports/s15_contrastive_v2_vast_claim_predictions.jsonl"
EVAL_A="reports/s15_contrastive_v2_vast_fast_eval.json"
EVAL_B="reports/s15_contrastive_v2_vast_claim_eval.json"
MODELS_DIR="${MODELS_DIR:-/workspace/models/s15}"
GGUF_PATH="${MODELS_DIR}/nassila-sanad-4b-q6_k.gguf"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-/workspace/llama.cpp}"
SERVER="${LLAMA_CPP_DIR}/build/bin/llama-server"
SERVER_LOG="outputs/s15_llama_server.log"
SERVER_PID_FILE="outputs/s15_llama.pid"
MODEL_NAME="${MODEL_NAME:-nassila-sanad-4b}"

mkdir -p outputs reports data "$MODELS_DIR"

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

echo "=== S15 contrastive Vast (dual-branch audit) ==="
echo "  data: $EVAL_DATA"
[[ -f "$EVAL_DATA" ]] || { echo "missing $EVAL_DATA"; exit 1; }

echo "=== deps ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git build-essential cmake curl wget >/dev/null
if ! command -v nvcc >/dev/null 2>&1 || nvcc --version 2>/dev/null | grep -q "release 11\."; then
  echo "installing CUDA 13 toolkit (nvcc 11.x/absent is too old for llama.cpp)"
  wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb -O /tmp/cuda-keyring.deb
  dpkg -i /tmp/cuda-keyring.deb >/dev/null 2>&1 || true
  apt-get update -qq
  apt-get install -y -qq cuda-toolkit-13-3 >/dev/null || true
  export PATH="/usr/local/cuda-13.3/bin:$PATH"
  command -v nvcc >/dev/null 2>&1 || { echo "nvcc still missing after CUDA 13 install"; }
fi
export PATH="/usr/local/cuda/bin:/usr/local/cuda-13.3/bin:$PATH"
pip install -q requests huggingface_hub || pip3 install -q requests huggingface_hub

if [[ ! -x "$SERVER" ]]; then
  echo "=== build llama.cpp CUDA ==="
  if [[ ! -d "$LLAMA_CPP_DIR/.git" ]]; then
    git clone --depth 1 https://github.com/ggerganov/llama.cpp.git "$LLAMA_CPP_DIR"
  fi
  rm -rf "$LLAMA_CPP_DIR/build"
  cmake -S "$LLAMA_CPP_DIR" -B "$LLAMA_CPP_DIR/build" -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
  cmake --build "$LLAMA_CPP_DIR/build" --config Release -j8 --target llama-server
fi
[[ -x "$SERVER" ]] || { echo "no llama-server at $SERVER"; exit 1; }

if [[ ! -f "$GGUF_PATH" ]]; then
  echo "=== download S15 GGUF from HF ==="
  python3 - <<'PY'
from huggingface_hub import hf_hub_download
import os
path = hf_hub_download(
    repo_id="QinEmPeRoR93/nassila-sanad-4b",
    filename="nassila-sanad-4b-q6_k.gguf",
    local_dir=os.environ.get("MODELS_DIR", "/workspace/models/s15"),
)
print("downloaded", path)
PY
fi
ls -lh "$GGUF_PATH"

echo "=== start llama-server ==="
cleanup_server
# Qwen3.5 reasoning model: suppress think blocks server-side; skip chat parsing
# so llama.cpp never rejects our system+user JSON (same shape as S14 run).
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

echo "=== batch A: fast path (--disable-thinking /no_think), seed $SEED ==="
if [[ ! -f "$PRED_A" ]]; then
  python3 scripts/run_l3_eval_batch.py \
    --base-url "$BASE_URL" \
    --api-key ollama \
    --model "$MODEL_NAME" \
    --data "$EVAL_DATA" \
    --retry 1 \
    --repair \
    --temperature "$TEMPERATURE" \
    --seed "$SEED" \
    --disable-thinking \
    --timeout 300 \
    --sleep 0.1 \
    --out "$PRED_A" || { echo "batch A runner failed"; }
  python3 scripts/evaluate_outputs.py \
    --eval "$EVAL_DATA" \
    --predictions "$PRED_A" \
    --report "$EVAL_A" \
    --repair || true
else
  echo "PRED_A exists -> skip batch A"
fi

echo "=== batch B: claim branch (concise-reasoning note, no /no_think), seed $SEED ==="
if [[ ! -f "$PRED_B" ]]; then
  python3 scripts/run_l3_eval_batch.py \
    --base-url "$BASE_URL" \
    --api-key ollama \
    --model "$MODEL_NAME" \
    --data "$EVAL_DATA" \
    --retry 1 \
    --repair \
    --temperature "$TEMPERATURE" \
    --seed "$SEED" \
    --timeout 300 \
    --sleep 0.1 \
    --out "$PRED_B" || { echo "batch B runner failed"; }
  python3 scripts/evaluate_outputs.py \
    --eval "$EVAL_DATA" \
    --predictions "$PRED_B" \
    --report "$EVAL_B" \
    --repair || true
else
  echo "PRED_B exists -> skip batch B"
fi

echo "Done: $PRED_A $EVAL_A | $PRED_B $EVAL_B"
