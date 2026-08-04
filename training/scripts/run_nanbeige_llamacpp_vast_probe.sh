#!/usr/bin/env bash
# Nanbeige4.2-3B zero-shot probe via official llama.cpp fork (Vast-friendly).
#
# Per https://huggingface.co/Nanbeige/Nanbeige4.2-3B — llama.cpp section.
# Uses community GGUF (no official GGUF yet); ~30-60 min to eval vs hours for vLLM compile.
#
#   chmod +x scripts/run_nanbeige_llamacpp_vast_probe.sh
#   bash scripts/run_nanbeige_llamacpp_vast_probe.sh
#
# Env:
#   BUILD_JOBS=8              — keep SSH responsive on Vast
#   GGUF_URL=...              — override GGUF download URL
#   SKIP_BUILD=1              — llama.cpp already built
#   SKIP_DOWNLOAD=1           — GGUF already on disk
#   SKIP_SERVER=1             — server already on :8000
#   SKIP_EVAL=1               — build + smoke only
#   LLAMA_PORT=8000
#   CTX_SIZE=8192
#   TEMPERATURE=0.2
#
set -e

# Fix CRLF if scripts were uploaded from Windows
if grep -q $'\r' "$0" 2>/dev/null; then
  sed -i 's/\r$//' "$0"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$TRAINING_DIR"

find scripts -type f \( -name '*.sh' -o -name '*.py' \) -exec grep -l $'\r' {} + 2>/dev/null \
  | xargs -r sed -i 's/\r$//' || true

LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-/workspace/llama.cpp-nanbeige}"
MODELS_DIR="${MODELS_DIR:-/workspace/models/nanbeige}"
GGUF_FILE="${GGUF_FILE:-Nanbeige4.2-3B-UD-Q6_K.gguf}"
GGUF_PATH="${MODELS_DIR}/${GGUF_FILE}"
# Community GGUF (Andgihat); pin URL override via GGUF_URL
GGUF_URL="${GGUF_URL:-https://huggingface.co/Andgihat/Nanbeige4.2-3B-GGUF/resolve/main/${GGUF_FILE}}"
BUILD_JOBS="${BUILD_JOBS:-8}"
LLAMA_PORT="${LLAMA_PORT:-8000}"
CTX_SIZE="${CTX_SIZE:-8192}"
TEMPERATURE="${TEMPERATURE:-0.2}"
REPORT_PREFIX="${REPORT_PREFIX:-nanbeige_zeroshot}"
PREDICTIONS="outputs/${REPORT_PREFIX}_predictions.jsonl"
SERVER_LOG="outputs/${REPORT_PREFIX}_llama_server.log"
SERVER_PID_FILE="outputs/${REPORT_PREFIX}_llama.pid"

mkdir -p outputs "$MODELS_DIR"

cleanup_server() {
  if [[ -f "$SERVER_PID_FILE" ]]; then
    local pid
    pid="$(cat "$SERVER_PID_FILE")"
    if kill -0 "$pid" 2>/dev/null; then
      echo "Stopping llama-server (pid $pid)..."
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
    rm -f "$SERVER_PID_FILE"
  fi
}
trap cleanup_server EXIT

LLAMA_BIN="${LLAMA_CPP_DIR}/build/bin"
SERVER="${LLAMA_BIN}/llama-server"

echo "=== Nanbeige llama.cpp probe ==="
echo "  fork:    Nanbeige/llama.cpp@nanbeige42"
echo "  gguf:    $GGUF_PATH"
echo "  jobs:    $BUILD_JOBS"
echo "  port:    $LLAMA_PORT"
echo "  ctx:     $CTX_SIZE"
echo

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  echo "=== [1/6] Build Nanbeige llama.cpp ==="
  apt-get update -qq && apt-get install -y -qq git build-essential cmake 2>/dev/null || true
  pip install -q requests huggingface_hub 2>/dev/null || pip3 install -q requests huggingface_hub

  if [[ ! -d "$LLAMA_CPP_DIR/.git" ]]; then
    git clone -b nanbeige42 https://github.com/Nanbeige/llama.cpp.git "$LLAMA_CPP_DIR"
  fi
  cmake -S "$LLAMA_CPP_DIR" -B "$LLAMA_CPP_DIR/build" -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
  cmake --build "$LLAMA_CPP_DIR/build" --config Release -j"$BUILD_JOBS"
  echo "  built: $SERVER"
else
  echo "=== [1/6] SKIP_BUILD=1 ==="
fi

if [[ ! -x "$SERVER" ]]; then
  echo "llama-server not found at $SERVER" >&2
  exit 1
fi

if [[ "${SKIP_DOWNLOAD:-0}" != "1" ]]; then
  echo "=== [2/6] Download community GGUF ==="
  if [[ ! -f "$GGUF_PATH" ]]; then
    python3 - <<PY
from huggingface_hub import hf_hub_download
import shutil
path = hf_hub_download(
    repo_id="Andgihat/Nanbeige4.2-3B-GGUF",
    filename="${GGUF_FILE}",
    local_dir="${MODELS_DIR}",
)
print("downloaded", path)
PY
    if [[ ! -f "$GGUF_PATH" ]]; then
      echo "hf_hub_download failed; trying wget..."
      wget -q -O "$GGUF_PATH" "$GGUF_URL"
    fi
  fi
  ls -lh "$GGUF_PATH"
else
  echo "=== [2/6] SKIP_DOWNLOAD=1 ==="
fi

if [[ "${SKIP_SERVER:-0}" != "1" ]]; then
  echo "=== [3/6] Start llama-server ==="
  cleanup_server
  nohup "$SERVER" \
    -m "$GGUF_PATH" \
    -ngl 99 \
    -c "$CTX_SIZE" \
    --jinja \
    --host 0.0.0.0 \
    --port "$LLAMA_PORT" \
    >"$SERVER_LOG" 2>&1 &
  echo $! >"$SERVER_PID_FILE"
  echo "  pid=$(cat "$SERVER_PID_FILE") log=$SERVER_LOG"

  echo "=== [4/6] Wait for server ==="
  for i in $(seq 1 60); do
    if curl -sf "http://127.0.0.1:${LLAMA_PORT}/health" >/dev/null 2>&1 \
      || curl -sf "http://127.0.0.1:${LLAMA_PORT}/v1/models" >/dev/null 2>&1; then
      echo "  server ready (${i}0s)"
      break
    fi
    if ! kill -0 "$(cat "$SERVER_PID_FILE")" 2>/dev/null; then
      echo "llama-server exited. Log tail:" >&2
      tail -n 30 "$SERVER_LOG" >&2 || true
      exit 1
    fi
    if [[ "$i" -eq 60 ]]; then
      tail -n 30 "$SERVER_LOG" >&2 || true
      exit 1
    fi
    sleep 10
  done
else
  echo "=== [3-4/6] SKIP_SERVER=1 ==="
fi

BASE_URL="http://127.0.0.1:${LLAMA_PORT}"
MODEL_NAME="nanbeige4.2-3b"

echo "=== [5/6] Smoke test ==="
curl -sf "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL_NAME}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with the single word: ok\"}],\"temperature\":0.2,\"max_tokens\":16}" \
  | head -c 400
echo
echo

python3 scripts/lmstudio_smoke_test.py \
  --base-url "$BASE_URL" \
  --model "$MODEL_NAME" \
  --task l3_grounding \
  --id eval-002 \
  --repair \
  --disable-thinking

if [[ "${SKIP_EVAL:-0}" == "1" ]]; then
  echo "SKIP_EVAL=1 — done after smoke"
  exit 0
fi

EVAL_FILES="${EVAL_FILES:-data/eval_samples.jsonl data/eval_holdout_90.jsonl}"

echo "=== [6/6] Batch eval + score (${EVAL_FILES}) ==="
python3 scripts/run_l3_eval_batch.py \
  --base-url "$BASE_URL" \
  --model "$MODEL_NAME" \
  --data $EVAL_FILES \
  --retry 1 \
  --repair \
  --disable-thinking \
  --temperature "$TEMPERATURE" \
  --timeout 300 \
  --out "$PREDICTIONS"

python3 scripts/run_eval_reports.py \
  --predictions "$PREDICTIONS" \
  --prefix "${REPORT_PREFIX}_" \
  --repair

python3 scripts/score_nanbeige_probe.py \
  --predictions "$PREDICTIONS" \
  --combined-report "outputs/${REPORT_PREFIX}_eval_combined_report.json" \
  --holdout-report "outputs/${REPORT_PREFIX}_eval_holdout_report.json" \
  --legacy-report "outputs/${REPORT_PREFIX}_eval_report.json" \
  --out "reports/${REPORT_PREFIX}_probe_2026-07.md"

echo
echo "Done."
echo "  $PREDICTIONS"
echo "  reports/${REPORT_PREFIX}_probe_2026-07.md"
