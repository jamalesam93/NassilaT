# Phase 2 Walkthrough — Production QLoRA + GGUF (`nassila-grounding-e4b-v1`)

**v1.1 retrain (700 rows):** use [PHASE2_2_V1_1_WALKTHROUGH.md](./PHASE2_2_V1_1_WALKTHROUGH.md) — manual GGUF export required for Gemma 4.

**Full step-by-step (PC + Vast + eval):** [PHASE2_TRAINING_GUIDE.md](./PHASE2_TRAINING_GUIDE.md)

After **Phase 1.5** (corpus) and label generation on your PC.

**Prerequisite files on GitHub / Vast clone:**

- `data/l3_grounding_train.jsonl` (validated)
- `data/paper_corpus_enriched.jsonl` (optional reference)

---

## Part 0 — PC before renting

```powershell
cd training
python scripts/validate_dataset.py data/l3_grounding_train.jsonl
python scripts/run_l3_eval_batch.py --model "google/gemma-4-e4b" `
  --data data/eval_samples.jsonl data/eval_holdout_45.jsonl `
  --retry 1 --repair --out outputs/baseline_predictions.jsonl
```

Save baseline report for comparison after tuning.

---

## Part 1 — Vast instance

| Setting | Value |
|---------|-------|
| Template | **PyTorch NGC (Cuda 13)** |
| GPU | 1× RTX 4090 |
| Disk | **100 GB** |

**First command after SSH:**

```bash
nvidia-smi
```

CUDA Version must be **12.4+ or 13.x**. If **12.2**, destroy and rent another host.

```bash
sudo bash -c 'printf "nameserver 8.8.8.8\nnameserver 1.1.1.1\n" > /etc/resolv.conf'
git clone https://github.com/jamalesam93/NassilaT.git ~/nassila
cd ~/nassila
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install --no-deps trl peft accelerate bitsandbytes transformers datasets
pip install -U "huggingface_hub[cli]"
export HF_TOKEN="hf_your_write_token"
```

---

## Part 2 — Train

```bash
cd ~/nassila/training
python scripts/train_qlora_gemma4_e4b.py \
  --train-file data/l3_grounding_train.jsonl \
  --output-dir outputs/nassila-grounding-e4b-v1
```

Expect `outputs/nassila-grounding-e4b-v1/lora_adapter/adapter_model.safetensors`.

---

## Part 3 — Export GGUF

```bash
python scripts/export_gguf.py \
  --adapter-dir outputs/nassila-grounding-e4b-v1/lora_adapter \
  --out-dir exports/nassila-grounding-e4b-v1-q6_k
```

---

## Part 4 — Upload Hugging Face

```bash
cd outputs/nassila-grounding-e4b-v1/lora_adapter
hf upload YOUR_USER/nassila-grounding-e4b-v1-adapter . . --repo-type model

cd ~/nassila/training/exports/nassila-grounding-e4b-v1-q6_k
hf upload YOUR_USER/nassila-grounding-e4b-v1 . . --repo-type model
```

See [HF_PUBLISH.md](./HF_PUBLISH.md) for model card template.

---

## Part 5 — Eval on PC (LM Studio)

1. Import GGUF into LM Studio; start server on port 1234.
2. Run tuned predictions and compare to baseline ([EVALUATION_GUIDE.md](./EVALUATION_GUIDE.md)).

---

## Part 6 — Destroy instance

Destroy (not just stop) when upload completes.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Pickle error on checkpoint | `save_strategy="no"` already in train script |
| CUDA 12.2 host | New instance with CUDA 13 |
| HF auth fails | `export HF_TOKEN=...` instead of interactive login |
