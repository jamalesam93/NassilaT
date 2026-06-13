# Phase 2.6 — v1.3 on Vast (train → eval → download only if pass)

**Prerequisite:** `l3_grounding_train.jsonl` = **850** rows (seed 45) on `main`.

**Baseline to beat:** [reports/v1_2_eval_combined_report.json](./reports/v1_2_eval_combined_report.json) — 86% combined, 91.1% holdout, 9/10 supported.

**Go/no-go:** combined expect ≥90% · quote validity ≥98% · false supported ≤5% · supported ≥8/10

---

## Step B — Train

```bash
cd ~/nassila/training
source ~/nassila/.venv/bin/activate
git pull

python scripts/train_qlora_gemma4_e4b.py \
  --train-file data/l3_grounding_train.jsonl \
  --output-dir outputs/nassila-grounding-e4b-v1.3
```

Defaults: **2 epochs**, LR **1e-4**.

---

## Step C — Merge

```bash
python scripts/merge_adapter_gemma4.py \
  --adapter-dir outputs/nassila-grounding-e4b-v1.3/lora_adapter \
  --out-dir exports/hf-merged-v1.3-bf16
```

---

## Step D — GGUF (Q6_K)

```bash
python ~/llama.cpp/convert_hf_to_gguf.py exports/hf-merged-v1.3-bf16 \
  --outfile exports/nassila-grounding-e4b-v1.3-f16.gguf --outtype f16

~/llama.cpp/build/bin/llama-quantize \
  exports/nassila-grounding-e4b-v1.3-f16.gguf \
  exports/nassila-grounding-e4b-v1.3-q6_k.gguf Q6_K
```

---

## Step E — Eval

**Pane 1:** `llama-server -m exports/nassila-grounding-e4b-v1.3-q6_k.gguf --host 127.0.0.1 --port 1234 -c 4096`

**Pane 2:**

```bash
python scripts/run_l3_eval_batch.py \
  --base-url http://127.0.0.1:1234 \
  --model "nassila-grounding-e4b-v1.3" \
  --data data/eval_samples.jsonl data/eval_holdout_45.jsonl \
  --chat-template --retry 1 --repair \
  --out outputs/v1_3_predictions.jsonl

python scripts/run_eval_reports.py \
  --predictions outputs/v1_3_predictions.jsonl \
  --out-dir outputs --repair

cat outputs/eval_combined_report.json
```

---

## Step F — HF adapter (NO-GO or GO)

```bash
cd outputs/nassila-grounding-e4b-v1.3/lora_adapter
hf upload QinEmPeRoR93/nassila-grounding-e4b-v1.3-adapter . . --repo-type model
```

Fill [MODEL_CARD_v1_3.md](./MODEL_CARD_v1_3.md) after eval.
