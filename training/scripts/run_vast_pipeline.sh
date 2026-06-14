#!/usr/bin/env bash
# Nassila v1.4 Vast pipeline: validate → train → merge → GGUF → eval → reports
# See training/PHASE2_7_V1_4_WALKTHROUGH.md
#
# Usage:
#   PHASE=4b bash scripts/run_vast_pipeline.sh
#   SKIP_TRAIN=1 PHASE=4b bash scripts/run_vast_pipeline.sh   # merge+eval only
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$TRAINING_DIR"

PHASE="${PHASE:-4b}"
SKIP_TRAIN="${SKIP_TRAIN:-0}"
REPAIR="${REPAIR:-1}"
LLAMA_BIN="${LLAMA_BIN:-$HOME/llama.cpp/build/bin}"

TRAIN_FILE="data/l3_grounding_train_v14a.jsonl"
CHAT_FILE="data/l3_grounding_chat.jsonl"

case "$PHASE" in
  4a) OUTPUT_SUFFIX="v1.4a"; REPORTS_PREFIX="v1_4a_" ;;
  4b) OUTPUT_SUFFIX="v1.4b"; REPORTS_PREFIX="v1_4b_" ;;
  *)
    echo "PHASE must be 4a or 4b (got: $PHASE)" >&2
    exit 1
    ;;
esac

OUTPUT_DIR="outputs/nassila-grounding-e4b-${OUTPUT_SUFFIX}"
MERGED_DIR="exports/hf-merged-${OUTPUT_SUFFIX}-bf16"
GGUF_F16="exports/nassila-grounding-e4b-${OUTPUT_SUFFIX}-f16.gguf"
GGUF_Q6="exports/nassila-grounding-e4b-${OUTPUT_SUFFIX}-q6_k.gguf"

echo "=== v1.4 pipeline phase=${PHASE} (${OUTPUT_SUFFIX}) ==="

if [[ ! -f "$TRAIN_FILE" ]]; then
  echo "--- Build seq-safe train file ---"
  python scripts/prepare_v14_train.py
fi

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
  echo "--- Train QLoRA (phase ${PHASE}, save_strategy=no) ---"
  python scripts/train_qlora_gemma4_e4b.py \
    --train-file "$TRAIN_FILE" \
    --phase "$PHASE" \
    --chat-file "$CHAT_FILE"
fi

ADAPTER_DIR="${OUTPUT_DIR}/lora_adapter"
if [[ ! -d "$ADAPTER_DIR" ]]; then
  echo "Adapter not found: $ADAPTER_DIR" >&2
  exit 1
fi

echo "--- Merge adapter ---"
python scripts/merge_adapter_gemma4.py \
  --adapter-dir "$ADAPTER_DIR" \
  --out-dir "$MERGED_DIR" \
  --max-seq-length 2048

echo "--- GGUF convert (F16) ---"
python "$HOME/llama.cpp/convert_hf_to_gguf.py" "$MERGED_DIR" \
  --outfile "$GGUF_F16" \
  --outtype f16

echo "--- GGUF quantize (Q6_K) ---"
"$LLAMA_BIN/llama-quantize" "$GGUF_F16" "$GGUF_Q6" Q6_K
ls -lh "$GGUF_Q6"

echo "--- Start llama-server (background) ---"
"$LLAMA_BIN/llama-server" \
  -m "$GGUF_Q6" \
  --host 127.0.0.1 \
  --port 1234 \
  --ctx-size 4096 &
SERVER_PID=$!
sleep 15

REPAIR_FLAG=""
if [[ "$REPAIR" == "1" ]]; then
  REPAIR_FLAG="--repair"
fi

echo "--- Batch eval ---"
python scripts/run_l3_eval_batch.py \
  --base-url http://127.0.0.1:1234 \
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

echo "=== Done. Reports: reports/${REPORTS_PREFIX}* ==="
echo "Update MODEL_CARD_v1_4.md with GO/NO-GO from ${REPORTS_PREFIX}eval_combined_report.json"
