#!/usr/bin/env bash
# Nassila Sanad train + eval pipeline (E4B default / 12B quality / 31B premium).
#
# Prerequisite: hardened holdout built:
#   python scripts/build_hardened_holdout.py
#
# E4B v1.10 baseline:
#   ARM=e4b PHASE=10 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
#
# E4B v1.12 recovery (default-tier ship target):
#   ARM=e4b PHASE=12 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
#
# 12B quality tier (Tier 2):
#   ARM=12b PHASE=10 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
#
# 31B premium tier (Tier 2, same v1.12 data):
#   ARM=31b PHASE=12 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
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

case "$PHASE" in
  10)
    TRAIN_FILE="data/l3_grounding_train_v110.jsonl"
    CHAT_FILE="data/l3_grounding_chat_v110.jsonl"
    CHECKPOINT_SUFFIX="v1.10"
    REPORT_SUFFIX="v110"
    PREPARE_CMD=(
      python scripts/prepare_v15_train.py
      --base data/l3_grounding_train_v14a.jsonl
      --boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v18_boost.jsonl data/l3_grounding_v110_boost.jsonl
      --out "$TRAIN_FILE"
    )
    ;;
  11)
    TRAIN_FILE="data/l3_grounding_train_v111.jsonl"
    CHAT_FILE="data/l3_grounding_chat_v111.jsonl"
    CHECKPOINT_SUFFIX="v1.11"
    REPORT_SUFFIX="v111"
    PREPARE_CMD=(
      python scripts/prepare_v15_train.py
      --base data/l3_grounding_train_v14a.jsonl
      --boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v18_boost.jsonl data/l3_grounding_v110_boost.jsonl data/l3_grounding_v111_boost.jsonl
      --out "$TRAIN_FILE"
    )
    ;;
  12)
    TRAIN_FILE="data/l3_grounding_train_v112.jsonl"
    CHAT_FILE="data/l3_grounding_chat_v112.jsonl"
    CHECKPOINT_SUFFIX="v1.12"
    REPORT_SUFFIX="v112"
    PREPARE_CMD=(
      python scripts/prepare_v15_train.py
      --base data/l3_grounding_train_v14a.jsonl
      --boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v18_boost.jsonl data/l3_grounding_v110_boost.jsonl data/l3_grounding_v112_boost.jsonl
      --out "$TRAIN_FILE"
    )
    ;;
  *)
    echo "PHASE must be 10, 11, or 12 (got: $PHASE)" >&2
    exit 1
    ;;
esac

case "$ARM" in
  e4b)
    REPORTS_PREFIX="v${PHASE}_"
    TRAIN_SCRIPT=(python scripts/train_qlora_gemma4_e4b.py --phase "$PHASE")
    BASE_MODEL="google/gemma-4-E4B-it"
    QUANTS=(Q6_K)
    OUTPUT_DIR="outputs/nassila-sanad-e4b-${CHECKPOINT_SUFFIX}"
    MERGED_DIR="exports/hf-merged-sanad-e4b-${CHECKPOINT_SUFFIX}-bf16"
    GGUF_F16="exports/nassila-sanad-e4b-${CHECKPOINT_SUFFIX}-f16.gguf"
    GGUF_PUBLIC_BASENAME="nassila-sanad-e4b"
    ;;
  12b)
    if [[ "$PHASE" != "10" ]]; then
      echo "12B arm only supports PHASE=10 (got: $PHASE)" >&2
      exit 1
    fi
    REPORTS_PREFIX="v1_10_12b_"
    TRAIN_SCRIPT=(python scripts/train_qlora_gemma4_12b.py --phase "$PHASE")
    BASE_MODEL="google/gemma-4-12B-it"
    QUANTS=(Q4_K_M Q6_K Q8_0)
    OUTPUT_DIR="outputs/nassila-sanad-12b-${CHECKPOINT_SUFFIX}"
    MERGED_DIR="exports/hf-merged-sanad-12b-${CHECKPOINT_SUFFIX}-bf16"
    GGUF_F16="exports/nassila-sanad-12b-${CHECKPOINT_SUFFIX}-f16.gguf"
    GGUF_PUBLIC_BASENAME="nassila-sanad-12b"
    ;;
  31b)
    if [[ "$PHASE" != "12" ]]; then
      echo "31B premium arm only supports PHASE=12 (got: $PHASE)" >&2
      exit 1
    fi
    REPORTS_PREFIX="v1_12_31b_"
    TRAIN_SCRIPT=(python scripts/train_qlora_gemma4_31b.py --phase "$PHASE")
    BASE_MODEL="google/gemma-4-31B-it"
    QUANTS=(Q4_K_M Q6_K)
    OUTPUT_DIR="outputs/nassila-sanad-31b-${CHECKPOINT_SUFFIX}"
    MERGED_DIR="exports/hf-merged-sanad-31b-${CHECKPOINT_SUFFIX}-bf16"
    GGUF_F16="exports/nassila-sanad-31b-${CHECKPOINT_SUFFIX}-f16.gguf"
    GGUF_PUBLIC_BASENAME="nassila-sanad-31b"
    ;;
  *)
    echo "ARM must be e4b, 12b, or 31b (got: $ARM)" >&2
    exit 1
    ;;
esac

echo "=== Sanad pipeline arm=${ARM} phase=${PHASE} checkpoint=${CHECKPOINT_SUFFIX} ==="

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
  GGUF_QUANT="exports/${GGUF_PUBLIC_BASENAME}-${QUANT_SUFFIX}.gguf"

  echo "--- GGUF quantize (${QUANT}) → ${GGUF_QUANT} ---"
  "$LLAMA_BIN/llama-quantize" "$GGUF_F16" "$GGUF_QUANT" "$QUANT"
  ls -lh "$GGUF_QUANT"

  REPORT_QUANT_PREFIX="${REPORTS_PREFIX}${QUANT_SUFFIX}_"
  AB_OUT="reports/ab_${ARM}_${QUANT_SUFFIX}_${REPORT_SUFFIX}"

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
      --model "${GGUF_PUBLIC_BASENAME}-${QUANT_SUFFIX}" \
      --base-url http://127.0.0.1:1234 \
      --out-dir "$AB_OUT" \
      --seeds $SEEDS \
      $REPAIR_FLAG
  else
    echo "--- Batch eval (${QUANT}) ---"
    python scripts/run_l3_eval_batch.py \
      --base-url http://127.0.0.1:1234 \
      --model "${GGUF_PUBLIC_BASENAME}" \
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

echo "=== Sanad pipeline arm=${ARM} phase=${PHASE} done ==="
echo "Reports: reports/ab_${ARM}_*_${REPORT_SUFFIX}/"
echo "Publish GGUF: exports/${GGUF_PUBLIC_BASENAME}-*.gguf"
echo "HF repos: QinEmPeRoR93/${GGUF_PUBLIC_BASENAME} (GGUF), QinEmPeRoR93/${GGUF_PUBLIC_BASENAME}-adapter (private)"
