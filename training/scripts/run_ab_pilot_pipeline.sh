#!/usr/bin/env bash
# Nassila A/B pilot: E4B v1.10 baseline vs Gemma 4 12B quant ladder (shared v1.10 data).
#
# Prerequisite: hardened holdout built locally or on Vast:
#   python scripts/build_hardened_holdout.py
#
# E4B baseline (control):
#   ARM=e4b PHASE=10 bash scripts/run_ab_pilot_pipeline.sh
#
# 12B arm (train once, eval Q4/Q6/Q8):
#   ARM=12b PHASE=10 bash scripts/run_ab_pilot_pipeline.sh
#
# Multi-seed aggregation (after server eval):
#   ARM=e4b MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$TRAINING_DIR"

ARM="${ARM:-e4b}"
PHASE="${PHASE:-10}"
SKIP_TRAIN="${SKIP_TRAIN:-0}"
REPAIR="${REPAIR:-1}"
MULTI_SEED="${MULTI_SEED:-0}"
LLAMA_BIN="${LLAMA_BIN:-$HOME/llama.cpp/build/bin}"
SEEDS="${SEEDS:-42 43 44}"

TRAIN_FILE="data/l3_grounding_train_v110.jsonl"
CHAT_FILE="data/l3_grounding_chat_v110.jsonl"
PREPARE_CMD=(
  python scripts/prepare_v15_train.py
  --base data/l3_grounding_train_v14a.jsonl
  --boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v18_boost.jsonl data/l3_grounding_v110_boost.jsonl
  --out "$TRAIN_FILE"
)

case "$ARM" in
  e4b)
    OUTPUT_SUFFIX="v1.10"
    REPORTS_PREFIX="v1_10_"
    TRAIN_SCRIPT=(python scripts/train_qlora_gemma4_e4b.py --phase "$PHASE")
    BASE_MODEL="google/gemma-4-E4B-it"
    QUANTS=(Q6_K)
    ;;
  12b)
    OUTPUT_SUFFIX="v1.10-12b"
    REPORTS_PREFIX="v1_10_12b_"
    TRAIN_SCRIPT=(python scripts/train_qlora_gemma4_12b.py --phase "$PHASE")
    BASE_MODEL="google/gemma-4-12B-it"
    QUANTS=(Q4_K_M Q6_K Q8_0)
    ;;
  *)
    echo "ARM must be e4b or 12b (got: $ARM)" >&2
    exit 1
    ;;
esac

if [[ "$ARM" == "e4b" ]]; then
  OUTPUT_DIR="outputs/nassila-grounding-e4b-${OUTPUT_SUFFIX}"
  MERGED_DIR="exports/hf-merged-${OUTPUT_SUFFIX}-bf16"
  GGUF_F16="exports/nassila-grounding-e4b-${OUTPUT_SUFFIX}-f16.gguf"
else
  OUTPUT_DIR="outputs/nassila-grounding-12b-${OUTPUT_SUFFIX}"
  MERGED_DIR="exports/hf-merged-12b-${OUTPUT_SUFFIX}-bf16"
  GGUF_F16="exports/nassila-grounding-12b-${OUTPUT_SUFFIX}-f16.gguf"
fi

echo "=== A/B pilot arm=${ARM} phase=${PHASE} ==="

echo "--- Build hardened holdout (90 rows) ---"
python scripts/build_hardened_holdout.py

if [[ ! -f "$TRAIN_FILE" ]]; then
  echo "--- Build train file ---"
  "${PREPARE_CMD[@]}"
fi

echo "--- Contamination gate ---"
python scripts/check_contamination.py "$TRAIN_FILE"

echo "--- Validate train JSONL ---"
python scripts/validate_dataset.py "$TRAIN_FILE"

if [[ ! -f "$CHAT_FILE" ]]; then
  python scripts/validate_dataset.py "$TRAIN_FILE" \
    --export-chat "$CHAT_FILE" \
    --strict-length 2048
fi

if [[ "$SKIP_TRAIN" != "1" ]]; then
  echo "--- Train QLoRA (${ARM}, save_strategy=no) ---"
  "${TRAIN_SCRIPT[@]}" --train-file "$TRAIN_FILE" --chat-file "$CHAT_FILE"
fi

ADAPTER_DIR="${OUTPUT_DIR}/lora_adapter"
if [[ ! -d "$ADAPTER_DIR" ]]; then
  echo "Adapter not found: $ADAPTER_DIR" >&2
  exit 1
fi

echo "--- Merge adapter (${BASE_MODEL}) ---"
python scripts/merge_adapter_gemma4.py \
  --adapter-dir "$ADAPTER_DIR" \
  --out-dir "$MERGED_DIR" \
  --base-model "$BASE_MODEL" \
  --max-seq-length 2048

echo "--- GGUF convert (F16) ---"
python "$HOME/llama.cpp/convert_hf_to_gguf.py" "$MERGED_DIR" \
  --outfile "$GGUF_F16" \
  --outtype f16

REPAIR_FLAG=""
if [[ "$REPAIR" == "1" ]]; then
  REPAIR_FLAG="--repair"
fi

for QUANT in "${QUANTS[@]}"; do
  QUANT_SUFFIX=$(echo "$QUANT" | tr '[:upper:]' '[:lower:]')
  if [[ "$ARM" == "e4b" ]]; then
    GGUF_QUANT="exports/nassila-grounding-e4b-${OUTPUT_SUFFIX}-${QUANT_SUFFIX}.gguf"
  else
    GGUF_QUANT="exports/nassila-grounding-12b-${OUTPUT_SUFFIX}-${QUANT_SUFFIX}.gguf"
  fi

  echo "--- GGUF quantize (${QUANT}) ---"
  "$LLAMA_BIN/llama-quantize" "$GGUF_F16" "$GGUF_QUANT" "$QUANT"
  ls -lh "$GGUF_QUANT"

  REPORT_QUANT_PREFIX="${REPORTS_PREFIX}${QUANT_SUFFIX}_"
  AB_OUT="reports/ab_${ARM}_${QUANT_SUFFIX}_v110"

  echo "--- Start llama-server (${QUANT}) ---"
  "$LLAMA_BIN/llama-server" \
    -m "$GGUF_QUANT" \
    --host 127.0.0.1 \
    --port 1234 \
    --ctx-size 4096 &
  SERVER_PID=$!
  sleep 15

  if [[ "$MULTI_SEED" == "1" ]]; then
    echo "--- Multi-seed eval (${QUANT}, seeds: ${SEEDS}) ---"
    python scripts/run_multi_seed_eval.py \
      --model "nassila-grounding-${ARM}-${QUANT_SUFFIX}" \
      --base-url http://127.0.0.1:1234 \
      --out-dir "$AB_OUT" \
      --seeds $SEEDS \
      $REPAIR_FLAG
  else
    echo "--- Batch eval (${QUANT}) ---"
    python scripts/run_l3_eval_batch.py \
      --base-url http://127.0.0.1:1234 \
      --model "nassila-grounding" \
      --data data/eval_samples.jsonl data/eval_samples_extended.jsonl data/eval_holdout_90.jsonl \
      --chat-template --retry 1 $REPAIR_FLAG \
      --out "reports/${REPORT_QUANT_PREFIX}predictions.jsonl"

    python scripts/run_eval_reports.py \
      --predictions "reports/${REPORT_QUANT_PREFIX}predictions.jsonl" \
      --out-dir reports \
      --prefix "${REPORT_QUANT_PREFIX}" \
      --holdout data/eval_holdout_90.jsonl \
      $REPAIR_FLAG
  fi

  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
done

if [[ "$ARM" == "12b" && "$MULTI_SEED" == "1" && -f reports/ab_e4b_q6_k_v110/multi_seed_aggregate.json ]]; then
  for QUANT in Q4_K_M Q6_K Q8_0; do
    QUANT_SUFFIX=$(echo "$QUANT" | tr '[:upper:]' '[:lower:]')
    CAND="reports/ab_12b_${QUANT_SUFFIX}_v110/multi_seed_aggregate.json"
    if [[ -f "$CAND" ]]; then
      python scripts/compare_ab_pilot.py \
        --baseline reports/ab_e4b_q6_k_v110/multi_seed_aggregate.json \
        --candidate "$CAND" \
        --label "12B ${QUANT}" \
        --out "reports/ab_decision_12b_${QUANT_SUFFIX}.json" || true
    fi
  done
fi

echo "=== A/B pilot arm=${ARM} done ==="
echo "Next: compare reports/ab_* and run compare_ab_pilot.py when both arms complete."
