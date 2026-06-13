# Phase 2.2 — v1.1 on Vast (train → eval → download only if pass)

One linear checklist. **Everything through go/no-go runs on Vast.** Your PC download (~6 GB) happens **only after eval passes**.

**Prerequisite:** `l3_grounding_train.jsonl` = 700 rows on `main` (Phase 2.1).

**Go/no-go targets:** expect pass ≥90% · quote validity ≥98% · false supported ≤5%

---

## The big picture

```
┌─────────────────────────────────────────────────────────────────┐
│  ALL ON VAST (uses Vast bandwidth, not your home connection)    │
├─────────────────────────────────────────────────────────────────┤
│  A. Setup          clone repo, install deps                       │
│  B. Train          → LoRA adapter (~100 MB)                     │
│  C. Merge          adapter + base → full HF weights (~15 GB)    │
│  D. Build GGUF     llama.cpp convert + Q6_K (~6 GB)             │
│  E. Eval           llama-server + eval scripts → report.json    │
│  F. Upload HF      optional backup (still from Vast)            │
└─────────────────────────────────────────────────────────────────┘
                              │
                    eval passed?
                    ┌────┴────┐
                   NO        YES
                    │          │
            destroy instance   G. Download GGUF to PC (download manager)
            (no home download) H. LM Studio + Nassila on PC
```

### What training produces vs what eval needs

| Artifact | After step | Size | Can eval use it directly? |
|----------|------------|------|---------------------------|
| LoRA adapter | **B. Train** | ~100 MB | **No** |
| Merged HF weights | **C. Merge** | ~15 GB | **No** (not for our eval scripts) |
| Q6_K GGUF | **D. Build GGUF** | ~6 GB | **Yes** — this is what `llama-server` loads |

**You cannot skip C and D.** Training alone does not give a runnable model for eval.  
**You can skip G** until eval passes — that is the bandwidth-saving part.

### What uses your home internet

| Action | Uses home bandwidth? |
|--------|----------------------|
| SSH into Vast | Tiny |
| Train / merge / GGUF / eval on Vast | **No** |
| `hf upload` from Vast | **No** |
| Download GGUF to PC | **Yes (~6 GB)** — only after **GO** |
| HF Inference / “run in cloud” button | Not available for custom GGUF |

---

## Step A — Rent Vast and setup (once per instance)

**Rent**

| Setting | Value |
|---------|-------|
| Template | PyTorch NGC (CUDA 13) |
| GPU | RTX A6000 48 GB |
| Disk | 100 GB |

**Reuse your v1 instance if still running** — base model may already be cached (saves time on Vast).

```bash
nvidia-smi                                    # need CUDA 12.4+ or 13.x
sudo bash -c 'printf "nameserver 8.8.8.8\nnameserver 1.1.1.1\n" > /etc/resolv.conf'

git clone https://github.com/jamalesam93/NassilaT.git ~/nassila
# reusing instance:  cd ~/nassila && git pull

cd ~/nassila
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install --no-deps trl peft accelerate bitsandbytes transformers datasets
pip install -U huggingface_hub
export HF_TOKEN="hf_your_write_token"
```

**llama.cpp** — **[LLAMA_CPP_VAST.md](./LLAMA_CPP_VAST.md)** (pinned **`b9608`**). Skip if both binaries already exist on this instance.

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
  --output-dir outputs/nassila-grounding-e4b-v1.1
```

- **Time:** ~10–20 min on A6000 (~175 steps)
- **Output:** `outputs/nassila-grounding-e4b-v1.1/lora_adapter/`
- **Do not use** `export_gguf.py` — broken for Gemma 4

---

## Step C — Merge adapter into full weights

```bash
cd ~/nassila/training

python scripts/merge_adapter_gemma4.py \
  --adapter-dir outputs/nassila-grounding-e4b-v1.1/lora_adapter \
  --out-dir exports/hf-merged-v1.1-bf16
```

- **Output:** `exports/hf-merged-v1.1-bf16/` (~15 GB, `config.json` + shards)
- **Required** before GGUF conversion

---

## Step D — Convert to GGUF (Q6_K)

```bash
cd ~/nassila/training

python ~/llama.cpp/convert_hf_to_gguf.py exports/hf-merged-v1.1-bf16 \
  --outfile exports/nassila-grounding-e4b-v1.1-f16.gguf \
  --outtype f16

~/llama.cpp/build/bin/llama-quantize \
  exports/nassila-grounding-e4b-v1.1-f16.gguf \
  exports/nassila-grounding-e4b-v1.1-q6_k.gguf \
  Q6_K
```

- **Final file:** `exports/nassila-grounding-e4b-v1.1-q6_k.gguf` (~6 GB)
- This is the file you will eventually load in LM Studio — but eval it on Vast first

---

## Step E — Eval on Vast (go/no-go)

### Terminal 1 — start server

```bash
cd ~/nassila/training
source ~/nassila/.venv/bin/activate

~/llama.cpp/build/bin/llama-server \
  -m exports/nassila-grounding-e4b-v1.1-q6_k.gguf \
  --host 127.0.0.1 \
  --port 1234 \
  -c 4096
```

Leave running.

### Terminal 2 — run eval

```bash
cd ~/nassila/training
source ~/nassila/.venv/bin/activate

# quick check server is up
curl -s http://127.0.0.1:1234/v1/models | head

# predictions (~15+ min)
python scripts/run_l3_eval_batch.py \
  --base-url http://127.0.0.1:1234 \
  --model "nassila-grounding-e4b-v1.1" \
  --data data/eval_samples.jsonl data/eval_holdout_45.jsonl \
  --retry 1 --repair \
  --out outputs/v1_1_predictions.jsonl

# score
python scripts/evaluate_outputs.py \
  --eval data/eval_samples.jsonl data/eval_holdout_45.jsonl \
  --predictions outputs/v1_1_predictions.jsonl \
  --report outputs/v1_1_report.json \
  --repair

cat outputs/v1_1_report.json
```

If `--model` fails, copy the exact id from `curl .../v1/models`.

### Go / no-go

| Metric | Pass? |
|--------|-------|
| Expect pass rate | ≥ 90% |
| Quote validity (holdout) | ≥ 98% |
| False supported | ≤ 5% |

**NO-GO:** save `v1_1_report.json` (small — `scp` or copy-paste). Destroy instance. **Do not download GGUF.**

**GO:** continue to F (and G on PC).

---

## Step F — Upload to Hugging Face (from Vast, optional but recommended)

Do this **before** destroying the instance so your PC can resume-download later.

```bash
export HF_TOKEN="hf_..."

cd ~/nassila/training/outputs/nassila-grounding-e4b-v1.1/lora_adapter
hf upload jamalesam93/nassila-grounding-e4b-v1.1-adapter . . --repo-type model

cd ~/nassila/training/exports
hf upload jamalesam93/nassila-grounding-e4b-v1.1 \
  nassila-grounding-e4b-v1.1-q6_k.gguf \
  nassila-grounding-e4b-v1.1-q6_k.gguf \
  --repo-type model
```

---

## Step G — Download to PC (only after GO)

```powershell
pip install -U huggingface_hub
hf download jamalesam93/nassila-grounding-e4b-v1.1 `
  nassila-grounding-e4b-v1.1-q6_k.gguf `
  --local-dir .\models\nassila-grounding-e4b-v1.1
```

`hf download` resumes interrupted transfers — works well with download managers that wrap it.

---

## Step H — LM Studio on PC

1. Import `nassila-grounding-e4b-v1.1-q6_k.gguf` into LM Studio
2. Start local server on port **1234**
3. Point Nassila preset at `http://localhost:1234`

---

## Step I — Destroy Vast instance

Destroy (not stop) after upload and/or you have the GGUF on PC.

---

## Quick reference — file paths on Vast

| Step | Path |
|------|------|
| Train output | `~/nassila/training/outputs/nassila-grounding-e4b-v1.1/lora_adapter/` |
| Merged HF | `~/nassila/training/exports/hf-merged-v1.1-bf16/` |
| **GGUF for eval + PC** | `~/nassila/training/exports/nassila-grounding-e4b-v1.1-q6_k.gguf` |
| Eval report | `~/nassila/training/outputs/v1_1_report.json` |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| OOM during train | Use A6000 48 GB; do not raise seq length |
| Merge fails on Gemma4ClippableLinear | Use `merge_adapter_gemma4.py` only |
| Unsloth GGUF ~112 MB | Wrong path — use Steps C + D |
| `hf upload` fails on GGUF | Pass explicit filename (see Step F) |
| CUDA 12.2 on host | Destroy; rent CUDA 13 template |
| Connection refused during eval | Start `llama-server` in Terminal 1 first |
| `llama-ui` / `asset_60_data` / HF UI download failed | [LLAMA_CPP_VAST.md](./LLAMA_CPP_VAST.md) — re-clone **`b9608`**, never floating `main` |
