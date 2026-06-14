#!/usr/bin/env bash
# Nassila v1.4 Vast pipeline: validate → train → merge → GGUF → eval → reports
# See training/PHASE2_7_V1_4_WALKTHROUGH.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$TRAINING_DIR"

PHASE="${PHASE:-4a}"
CHECKPOINT="${CHECKPOINT:-}"
SKIP_TRAIN="${SKIP_TRAIN:-0}"
REPAIR="${REPAIR:-1}"

TRAIN_FILE="data/l3_grounding_train.jsonl"
CHAT_FILE="data/l3_grounding_chat.jsonl"
REPORTS_PREFIX="v1_4${PHASE}_"

echo "=== v1.4 pipeline phase=${PHASE} ==="

echo "--- Validate train JSONL ---"
python scripts/validate_dataset.py "$TRAIN_FILE"

echo "--- Structural audit ---"
python scripts/audit_l3_labels.py "$TRAIN_FILE" --json "reports/v1_4_audit_summary.json"

echo "--- Export chat + strict length ---"
python scripts/validate_dataset.py "$TRAIN_FILE" \
  --export-chat "$CHAT_FILE" \
  --strict-length 2048

echo "--- Sequence length audit ---"
python scripts/audit_chat_seq_lengths.py "$CHAT_FILE" --max-length 2048 \
  --json "reports/v1_4_seq_audit.json"

if [[ "$SKIP_TRAIN" != "1" ]]; then
  echo "--- Train QLoRA (phase ${PHASE}) ---"
  python scripts/train_qlora_gemma4_e4b.py \
    --train-file "$TRAIN_FILE" \
    --phase "$PHASE" \
    --chat-file "$CHAT_FILE"
fi

OUTPUT_DIR="outputs/nassila-grounding-e4b-v1.4${PHASE}"
ADAPTER_DIR="${OUTPUT_DIR}/lora_adapter"
if [[ -n "$CHECKPOINT" ]]; then
  ADAPTER_DIR="${OUTPUT_DIR}/${CHECKPOINT}"
  echo "Using checkpoint: $ADAPTER_DIR"
fi

echo "--- Merge adapter ---"
python scripts/merge_adapter_gemma4.py \
  --adapter "$ADAPTER_DIR" \
  --out "${OUTPUT_DIR}/merged"

echo "--- Export GGUF (Q6_K) ---"
python scripts/export_gguf.py \
  --model "${OUTPUT_DIR}/merged" \
  --out "${OUTPUT_DIR}/gguf-q6_k"

echo "--- Start llama-server (background) ---"
# Assumes llama.cpp built per LLAMA_CPP_VAST.md (branch b9608)
LLAMA_BIN="${LLAMA_BIN:-$HOME/llama.cpp/build/bin}"
GGUF="${OUTPUT_DIR}/gguf-q6_k/nassila-grounding-q6_k.gguf"
"$LLAMA_BIN/llama-server" -m "$GGUF" --port 8080 --ctx-size 4096 &
SERVER_PID=$!
sleep 15

REPAIR_FLAG=""
if [[ "$REPAIR" == "1" ]]; then
  REPAIR_FLAG="--repair"
fi

echo "--- Batch eval ---"
python scripts/run_l3_eval_batch.py \
  --base-url http://127.0.0.1:8080 \
  --model nassila-grounding \
  --data data/eval_samples.jsonl data/eval_samples_extended.jsonl data/eval_holdout_45.jsonl \
  --chat-template --retry 1 $REPAIR_FLAG \
  --out "reports/${REPORTS_PREFIX}predictions.jsonl"

echo "--- Score reports ---"
python scripts/run_eval_reports.py \
  --predictions "reports/${REPORTS_PREFIX}predictions.jsonl" \
  --out-dir reports \
  --prefix "${REPORTS_PREFIX}" \
  $REPAIR_FLAG

echo "--- Cross-version failure matrix ---"
python scripts/compare_eval_versions.py --out reports/holdout_failure_matrix.md

kill "$SERVER_PID" 2>/dev/null || true

echo "=== Done. Reports under reports/${REPORTS_PREFIX}* ==="
echo "Update MODEL_CARD_v1_4.md with GO/NO-GO from eval_combined_report.json"
