#!/usr/bin/env bash
# Nanbeige4.2-3B zero-shot Sanad grounding probe on Vast (inference only).
#
# Prereqs on instance: NVIDIA L4/A10 (22GB+), 80GB+ disk, CUDA PyTorch image.
# From training/ after git pull or rsync:
#
#   chmod +x scripts/run_nanbeige_vast_probe.sh
#   bash scripts/run_nanbeige_vast_probe.sh
#
# Env overrides:
#   SKIP_VLLM_BUILD=1     — vLLM already installed
#   SKIP_SERVER=1         — vLLM server already running on :8000
#   SKIP_EVAL=1           — only build + smoke
#   MODEL_PATH=...        — default Nanbeige/Nanbeige4.2-3B
#   VLLM_PORT=8000
#   MAX_MODEL_LEN=8192
#   TEMPERATURE=0.2
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$TRAINING_DIR"

MODEL_PATH="${MODEL_PATH:-Nanbeige/Nanbeige4.2-3B}"
VLLM_PORT="${VLLM_PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
TEMPERATURE="${TEMPERATURE:-0.2}"
VLLM_DIR="${VLLM_DIR:-/workspace/vllm-nanbeige}"
REPORT_PREFIX="${REPORT_PREFIX:-nanbeige_zeroshot}"
PREDICTIONS="outputs/${REPORT_PREFIX}_predictions.jsonl"
SERVER_LOG="outputs/${REPORT_PREFIX}_vllm_server.log"
SERVER_PID_FILE="outputs/${REPORT_PREFIX}_vllm.pid"

mkdir -p outputs

cleanup_server() {
  if [[ -f "$SERVER_PID_FILE" ]]; then
    local pid
    pid="$(cat "$SERVER_PID_FILE")"
    if kill -0 "$pid" 2>/dev/null; then
      echo "Stopping vLLM server (pid $pid)..."
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
    rm -f "$SERVER_PID_FILE"
  fi
}
trap cleanup_server EXIT

echo "=== Nanbeige Vast probe ==="
echo "  model:         $MODEL_PATH"
echo "  port:          $VLLM_PORT"
echo "  max_model_len: $MAX_MODEL_LEN"
echo "  temperature:   $TEMPERATURE"
echo "  training dir:  $TRAINING_DIR"
echo

if [[ "${SKIP_VLLM_BUILD:-0}" != "1" ]]; then
  echo "=== [1/6] Install Nanbeige vLLM fork ==="
  if [[ ! -d "$VLLM_DIR/.git" ]]; then
    git clone -b nanbeige42 https://github.com/Nanbeige/vllm.git "$VLLM_DIR"
  else
    echo "  vLLM dir exists: $VLLM_DIR"
  fi
  pip install -q requests
  pip install -e "$VLLM_DIR"
else
  echo "=== [1/6] SKIP_VLLM_BUILD=1 ==="
fi

if [[ "${SKIP_SERVER:-0}" != "1" ]]; then
  echo "=== [2/6] Start vLLM server (background) ==="
  cleanup_server
  nohup vllm serve "$MODEL_PATH" \
    --host 0.0.0.0 \
    --port "$VLLM_PORT" \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.85 \
    --max-model-len "$MAX_MODEL_LEN" \
    --enable-auto-tool-choice \
    --tool-call-parser nanbeige \
    --reasoning-parser nanbeige \
    >"$SERVER_LOG" 2>&1 &
  echo $! >"$SERVER_PID_FILE"
  echo "  pid=$(cat "$SERVER_PID_FILE") log=$SERVER_LOG"

  echo "=== [3/6] Wait for server ==="
  for i in $(seq 1 120); do
    if curl -sf "http://127.0.0.1:${VLLM_PORT}/health" >/dev/null 2>&1 \
      || curl -sf "http://127.0.0.1:${VLLM_PORT}/v1/models" >/dev/null 2>&1; then
      echo "  server ready (${i}0s)"
      break
    fi
    if ! kill -0 "$(cat "$SERVER_PID_FILE")" 2>/dev/null; then
      echo "vLLM server exited early. Tail of log:" >&2
      tail -n 40 "$SERVER_LOG" >&2 || true
      exit 1
    fi
    if [[ "$i" -eq 120 ]]; then
      echo "Server did not become ready in 20 min. Tail of log:" >&2
      tail -n 40 "$SERVER_LOG" >&2 || true
      exit 1
    fi
    sleep 10
  done
else
  echo "=== [2-3/6] SKIP_SERVER=1 (expect vLLM on :${VLLM_PORT}) ==="
fi

BASE_URL="http://127.0.0.1:${VLLM_PORT}"

echo "=== [4/6] Curl smoke tests ==="
curl -sf "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL_PATH}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with the single word: ok\"}],\"temperature\":0.2,\"max_tokens\":16}" \
  | head -c 400
echo
echo

python scripts/lmstudio_smoke_test.py \
  --base-url "$BASE_URL" \
  --model "$MODEL_PATH" \
  --task l3_grounding \
  --id eval-002 \
  --repair \
  --disable-thinking

if [[ "${SKIP_EVAL:-0}" == "1" ]]; then
  echo "SKIP_EVAL=1 — stopping after smoke"
  exit 0
fi

echo "=== [5/6] 95-row L3 eval (production prompt, disable-thinking) ==="
python scripts/run_l3_eval_batch.py \
  --base-url "$BASE_URL" \
  --model "$MODEL_PATH" \
  --data data/eval_samples.jsonl data/eval_holdout_90.jsonl \
  --retry 1 \
  --repair \
  --disable-thinking \
  --temperature "$TEMPERATURE" \
  --timeout 300 \
  --out "$PREDICTIONS"

echo "=== [6/6] Score + memo ==="
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

echo
echo "Done. Artifacts:"
echo "  $PREDICTIONS"
echo "  outputs/${REPORT_PREFIX}_eval_combined_report.json"
echo "  outputs/${REPORT_PREFIX}_eval_holdout_report.json"
echo "  reports/${REPORT_PREFIX}_probe_2026-07.md"
echo
echo "Download to PC, then destroy the Vast instance:"
echo "  scp -P PORT -r root@HOST:${TRAINING_DIR}/outputs/${REPORT_PREFIX}_* ./training/outputs/"
echo "  scp -P PORT root@HOST:${TRAINING_DIR}/reports/${REPORT_PREFIX}_probe_2026-07.md ./training/reports/"
