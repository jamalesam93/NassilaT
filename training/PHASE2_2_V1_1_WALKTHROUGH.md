# Phase 2.2 — Retrain v1.1 (700 rows) + GGUF export

**Prerequisite:** Phase 2.1 committed on `main` (`l3_grounding_train.jsonl` = 700 rows).

**Goal:** `nassila-grounding-e4b-v1.1` — same QLoRA recipe as v1, new labels with paraphrase-supported rows.

**Eval targets (go/no-go):** expect pass ≥90% · quote validity ≥98% · false supported ≤5%

---

## Part 0 — PC sanity check (optional, 1 min)

```powershell
cd training
python scripts/validate_dataset.py data/l3_grounding_train.jsonl
```

Expect `OK: 700 record(s)`.

---

## Part 1 — Rent Vast

| Setting | Value |
|---------|-------|
| Template | **PyTorch NGC (CUDA 13)** |
| GPU | **1× RTX A6000 48 GB** (recommended; 4090 24 GB may OOM) |
| Disk | **100 GB** |

After SSH:

```bash
nvidia-smi   # CUDA 12.4+ or 13.x required
sudo bash -c 'printf "nameserver 8.8.8.8\nnameserver 1.1.1.1\n" > /etc/resolv.conf'
```

---

## Part 2 — Clone + deps

```bash
git clone https://github.com/jamalesam93/NassilaT.git ~/nassila
cd ~/nassila
git pull   # if reusing instance: cd ~/nassila && git pull

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install --no-deps trl peft accelerate bitsandbytes transformers datasets
pip install -U "huggingface_hub[cli]"
export HF_TOKEN="hf_your_write_token"
```

---

## Part 3 — Train (QLoRA)

```bash
cd ~/nassila/training
python scripts/train_qlora_gemma4_e4b.py \
  --train-file data/l3_grounding_train.jsonl \
  --output-dir outputs/nassila-grounding-e4b-v1.1
```

**Expect:** ~175 steps (700 rows × 2 epochs, effective batch 8). ~10–20 min on A6000.

**Output:** `outputs/nassila-grounding-e4b-v1.1/lora_adapter/`

| Hyperparameter | Value |
|----------------|-------|
| `MAX_SEQ_LENGTH` | 1536 |
| `LORA_R` | 16 |
| `NUM_EPOCHS` | 2 |
| `BATCH_SIZE` × `GRAD_ACCUM` | 1 × 8 |
| Gradient checkpointing | `unsloth` |

---

## Part 4 — Export GGUF (manual path — required for Gemma 4)

`export_gguf.py` (Unsloth `save_pretrained_gguf`) is **broken for Gemma 4** — use merge + llama.cpp.

### 4a — Merge adapter → bf16 HF

```bash
cd ~/nassila/training
python scripts/merge_adapter_gemma4.py \
  --adapter-dir outputs/nassila-grounding-e4b-v1.1/lora_adapter \
  --out-dir exports/hf-merged-v1.1-bf16
```

Expect ~15 GB, multi-shard `safetensors` + `config.json`.

### 4b — llama.cpp convert + quantize

```bash
cd ~
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp && cmake -B build && cmake --build build -j --config Release

cd ~/nassila/training
python ~/llama.cpp/convert_hf_to_gguf.py exports/hf-merged-v1.1-bf16 \
  --outfile exports/nassila-grounding-e4b-v1.1-f16.gguf \
  --outtype f16

~/llama.cpp/build/bin/llama-quantize \
  exports/nassila-grounding-e4b-v1.1-f16.gguf \
  exports/nassila-grounding-e4b-v1.1-q6_k.gguf \
  Q6_K
```

Expect Q6_K ~5.8–6.2 GB.

---

## Part 5 — Upload Hugging Face

**Option A (recommended):** separate v1.1 repos for A/B vs v1.

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

**Option B:** overwrite v1 repos — add README note that artifact is v1.1-trained.

Model card: 700 train rows, paraphrase-supported mix, link to NassilaT commit `4ee08ee+`.

---

## Part 6 — PC eval (LM Studio)

1. Download `nassila-grounding-e4b-v1.1-q6_k.gguf` (or scp from Vast).
2. Load in LM Studio; server on port **1234**.
3. Run tuned eval (same harness as v1 baseline):

```powershell
cd training
.\scripts\run_baseline_eval.ps1   # point at tuned model id in LM Studio
```

Compare to `outputs/baseline_report.json` and v1 `outputs/v1_report.json`.

**Go/no-go:** expect ≥90% · quotes ≥98% · false supported ≤5%.

---

## Part 7 — Destroy Vast instance

Destroy (not stop) after upload + optional scp backup of GGUF.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| OOM at step 0 | Rent **A6000 48 GB**; do not raise seq length |
| `Gemma4ClippableLinear` merge error | Use `merge_adapter_gemma4.py`, not vanilla PEFT on 4-bit |
| Unsloth GGUF ~112 MB only | Broken path — use llama.cpp recipe above |
| `hf upload` path error | Pass explicit filename for GGUF, not `.` as path_in_repo |
| CUDA 12.2 host | Destroy; rent CUDA 13 NGC template |
