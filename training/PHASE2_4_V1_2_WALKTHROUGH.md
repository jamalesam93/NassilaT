# Phase 2.4 — v1.2 on Vast (train → eval → download only if pass)

One linear checklist. **Everything through go/no-go runs on Vast.** PC download (~6 GB) happens **only after eval passes**.

**Prerequisite:** `l3_grounding_train.jsonl` = **850** rows on `main` (Phase 2.3, seed 44).

**Go/no-go targets:** expect pass ≥90% · quote validity ≥98% · false supported ≤5% · supported holdout h-001–h-010 ≥8/10

**v1.2 changes vs v1.1:** holdout-shaped Sanad rows (`-sanad-`), chunked excerpts, anti-false-weak labels, **3 epochs** @ **1.5e-4**, eval with **`--chat-template`** matching train.

---

## PC baseline (before Vast)

Run stock E4B with chat template aligned to training:

```powershell
cd training
# LM Studio or llama-server with google/gemma-4-e4b loaded on :1234

python scripts/run_l3_eval_batch.py `
  --base-url http://localhost:1234 `
  --model "google/gemma-4-e4b" `
  --data data/eval_samples.jsonl data/eval_holdout_45.jsonl `
  --chat-template --retry 1 --repair `
  --out reports/baseline_v1_2_chat_predictions.jsonl

python scripts/evaluate_outputs.py `
  --eval data/eval_samples.jsonl data/eval_holdout_45.jsonl `
  --predictions reports/baseline_v1_2_chat_predictions.jsonl `
  --report reports/baseline_v1_2_chat_report.json --repair
```

Save `reports/baseline_v1_2_chat_report.json` for comparison.

---

## Step A — Rent Vast and setup

Same as [PHASE2_2_V1_1_WALKTHROUGH.md](./PHASE2_2_V1_1_WALKTHROUGH.md) Step A (`git pull` for latest `main`).

**llama.cpp** — **[LLAMA_CPP_VAST.md](./LLAMA_CPP_VAST.md)** (pinned **`b9608`**). Do **not** clone floating `main` or run `cmake --build build -j`.

```bash
cd ~
rm -rf llama.cpp
git clone --depth 1 --branch b9608 https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
cmake -B build -DGGML_CUDA=ON -DLLAMA_BUILD_UI=OFF
grep LLAMA_BUILD_UI build/CMakeCache.txt
cmake --build build --target llama-server llama-quantize -j
ls -la build/bin/llama-server build/bin/llama-quantize
```

---

## Step B — Train

```bash
cd ~/nassila/training
source ~/nassila/.venv/bin/activate

python scripts/train_qlora_gemma4_e4b.py \
  --train-file data/l3_grounding_train.jsonl \
  --output-dir outputs/nassila-grounding-e4b-v1.2
```

- **Hyperparams:** 3 epochs, LR 1.5e-4 (defaults in script)
- **Output:** `outputs/nassila-grounding-e4b-v1.2/lora_adapter/`

---

## Step C — Merge

```bash
python scripts/merge_adapter_gemma4.py \
  --adapter-dir outputs/nassila-grounding-e4b-v1.2/lora_adapter \
  --out-dir exports/hf-merged-v1.2-bf16
```

---

## Step D — GGUF (Q6_K)

```bash
python ~/llama.cpp/convert_hf_to_gguf.py exports/hf-merged-v1.2-bf16 \
  --outfile exports/nassila-grounding-e4b-v1.2-f16.gguf \
  --outtype f16

~/llama.cpp/build/bin/llama-quantize \
  exports/nassila-grounding-e4b-v1.2-f16.gguf \
  exports/nassila-grounding-e4b-v1.2-q6_k.gguf \
  Q6_K
```

---

## Step E — Eval on Vast (go/no-go)

### Terminal 1 — server

```bash
~/llama.cpp/build/bin/llama-server \
  -m exports/nassila-grounding-e4b-v1.2-q6_k.gguf \
  --host 127.0.0.1 --port 1234 -c 4096
```

### Terminal 2 — eval (use `--chat-template`)

```bash
python scripts/run_l3_eval_batch.py \
  --base-url http://127.0.0.1:1234 \
  --model "nassila-grounding-e4b-v1.2" \
  --data data/eval_samples.jsonl data/eval_holdout_45.jsonl \
  --chat-template --retry 1 --repair \
  --out outputs/v1_2_predictions.jsonl

python scripts/run_eval_reports.py \
  --predictions outputs/v1_2_predictions.jsonl \
  --out-dir outputs --repair

cat outputs/eval_combined_report.json
```

---

## Step F — Upload HF (optional)

```bash
cd ~/nassila/training/outputs/nassila-grounding-e4b-v1.2/lora_adapter
hf upload YOUR_USER/nassila-grounding-e4b-v1.2-adapter . . --repo-type model

cd ~/nassila/training/exports
hf upload YOUR_USER/nassila-grounding-e4b-v1.2 \
  nassila-grounding-e4b-v1.2-q6_k.gguf \
  nassila-grounding-e4b-v1.2-q6_k.gguf \
  --repo-type model
```

Fill [MODEL_CARD_v1_2.md](./MODEL_CARD_v1_2.md) after eval.

---

## Step G — Download to PC (GO only)

```powershell
hf download YOUR_USER/nassila-grounding-e4b-v1.2 `
  nassila-grounding-e4b-v1.2-q6_k.gguf `
  --local-dir .\models\nassila-grounding-e4b-v1.2
```

---

## Quick reference

| Step | Path |
|------|------|
| Train output | `outputs/nassila-grounding-e4b-v1.2/lora_adapter/` |
| GGUF | `exports/nassila-grounding-e4b-v1.2-q6_k.gguf` |
| Eval report | `outputs/v1_2_report.json` |
| Dataset audit | `reports/v1_2_audit_summary.json` |

See [OUROBOROS.md](./OUROBOROS.md) for worker **Sanad** (`l3_grounding`) naming.
