# Phase 2.6 — v1.3 on Vast (train → eval → download only if pass)

One linear checklist. **Everything through go/no-go runs on Vast.** PC download (~6 GB) happens **only after eval passes**.

**Prerequisite:** `l3_grounding_train.jsonl` = **850** rows on `main` (Phase 2.5, seed 45). Commit `27f07b2` or later.

**Baseline to beat:** [reports/v1_2_eval_combined_report.json](./reports/v1_2_eval_combined_report.json) — 86% combined, 91.1% holdout, 9/10 supported, 0% false supported.

**Go/no-go targets:** combined expect ≥90% · quote validity ≥98% · false supported ≤5% · supported holdout h-001–h-010 ≥8/10

**v1.3 changes vs v1.2:** multi-claim (`-multi-`, `-multip-`), polarity (`-pol-`), overclaim (`-over-`), semantic Sanad (`-sanadsem-`); **2 epochs** @ **1e-4**; eval with **`--chat-template`**.

---

## The big picture

```
┌─────────────────────────────────────────────────────────────────┐
│  ALL ON VAST (uses Vast bandwidth, not your home connection)    │
├─────────────────────────────────────────────────────────────────┤
│  A. Setup          clone/pull repo, venv, llama.cpp             │
│  B. Train          → LoRA adapter (~200 MB)                     │
│  C. Merge          adapter + base → full HF weights (~15 GB)    │
│  D. Build GGUF     llama.cpp convert + Q6_K (~6 GB)             │
│  E. Eval           llama-server + eval scripts → report.json    │
│  F. Upload HF      adapter backup (optional; ~200 MB)           │
└─────────────────────────────────────────────────────────────────┘
                              │
                    eval passed?
                    ┌────┴────┐
                   NO        YES
                    │          │
            destroy instance   G. Download GGUF to PC
            (no home download) H. LM Studio on PC
```

**You cannot skip C and D.** Training alone does not give a runnable model for eval.

---

## PC baseline (optional — already done for v1.2)

If you already ran stock E4B with `--chat-template` and saved [reports/v1_2_eval_combined_report.json](./reports/v1_2_eval_combined_report.json), **skip this**.

Otherwise on PC (LM Studio or llama-server on :1234):

```powershell
cd training

python scripts/run_l3_eval_batch.py `
  --base-url http://localhost:1234 `
  --model "google/gemma-4-e4b" `
  --data data/eval_samples.jsonl data/eval_holdout_45.jsonl `
  --chat-template --retry 1 --repair `
  --out reports/baseline_v1_3_chat_predictions.jsonl

python scripts/run_eval_reports.py `
  --predictions reports/baseline_v1_3_chat_predictions.jsonl `
  --out-dir reports --repair
```

---

## Step A — Rent Vast and setup

**Rent**

| Setting | Value |
|---------|-------|
| Template | PyTorch NGC (CUDA 12.4+ or 13.x) |
| GPU | RTX A6000 48 GB |
| Disk | 100 GB |

Use **WSL + SSH + tmux** (same workflow as v1.2).

**Fresh instance:**

```bash
nvidia-smi
sudo bash -c 'printf "nameserver 8.8.8.8\nnameserver 1.1.1.1\n" > /etc/resolv.conf'

git clone https://github.com/jamalesam93/NassilaT.git ~/nassila
cd ~/nassila
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install --no-deps trl peft accelerate bitsandbytes transformers datasets
pip install -U huggingface_hub requests
export HF_TOKEN="hf_your_write_token"
```

**Reusing a prior instance** (v1.2 still running):

```bash
cd ~/nassila && git pull
source ~/nassila/.venv/bin/activate
export HF_TOKEN="hf_..."
```

**Verify dataset:**

```bash
cd ~/nassila/training
python scripts/validate_dataset.py data/l3_grounding_train.jsonl
python scripts/audit_l3_labels.py data/l3_grounding_train.jsonl
```

Expect **850** rows, audit **PASS**.

**llama.cpp** — follow **[LLAMA_CPP_VAST.md](./LLAMA_CPP_VAST.md)** (pinned tag **`b9608`**, UI off, build only `llama-server` + `llama-quantize`). **Do not** clone floating `main`.

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

**tmux** (recommended): `tmux new -s v13` — detach with `Ctrl+B` then `D`.

---

## Step B — Train

```bash
cd ~/nassila/training
source ~/nassila/.venv/bin/activate

python scripts/train_qlora_gemma4_e4b.py \
  --train-file data/l3_grounding_train.jsonl \
  --output-dir outputs/nassila-grounding-e4b-v1.3
```

- **Hyperparams:** 2 epochs, LR 1e-4 (defaults in script)
- **Time:** ~15–20 min on A6000 (~214 steps)
- **Output:** `outputs/nassila-grounding-e4b-v1.3/lora_adapter/`
- **Do not** use Unsloth `save_pretrained_gguf` — use Steps C + D

---

## Step C — Merge

```bash
cd ~/nassila/training
source ~/nassila/.venv/bin/activate

python scripts/merge_adapter_gemma4.py \
  --adapter-dir outputs/nassila-grounding-e4b-v1.3/lora_adapter \
  --out-dir exports/hf-merged-v1.3-bf16
```

- **Output:** `exports/hf-merged-v1.3-bf16/` (~15 GB)

---

## Step D — GGUF (Q6_K)

```bash
cd ~/nassila/training

python ~/llama.cpp/convert_hf_to_gguf.py exports/hf-merged-v1.3-bf16 \
  --outfile exports/nassila-grounding-e4b-v1.3-f16.gguf \
  --outtype f16

~/llama.cpp/build/bin/llama-quantize \
  exports/nassila-grounding-e4b-v1.3-f16.gguf \
  exports/nassila-grounding-e4b-v1.3-q6_k.gguf \
  Q6_K

ls -lh exports/nassila-grounding-e4b-v1.3-q6_k.gguf
```

Expect **~6 GB**.

---

## Step E — Eval on Vast (go/no-go)

Split tmux: `Ctrl+B` then `Shift+5` (`%`). Switch panes: `Ctrl+B` then arrow keys.

### Pane 1 — llama-server (leave running)

```bash
cd ~/nassila/training
source ~/nassila/.venv/bin/activate

~/llama.cpp/build/bin/llama-server \
  -m exports/nassila-grounding-e4b-v1.3-q6_k.gguf \
  --host 127.0.0.1 \
  --port 1234 \
  -c 4096
```

### Pane 2 — batch predict + score

```bash
cd ~/nassila/training
source ~/nassila/.venv/bin/activate

curl -s http://127.0.0.1:1234/v1/models | head

python scripts/run_l3_eval_batch.py \
  --base-url http://127.0.0.1:1234 \
  --model "nassila-grounding-e4b-v1.3" \
  --data data/eval_samples.jsonl data/eval_holdout_45.jsonl \
  --chat-template --retry 1 --repair \
  --out outputs/v1_3_predictions.jsonl

python scripts/run_eval_reports.py \
  --predictions outputs/v1_3_predictions.jsonl \
  --out-dir outputs \
  --repair

cat outputs/eval_combined_report.json
```

**Score with `run_eval_reports.py`** (not two `--eval` files on `evaluate_outputs.py`).

### Go / no-go

| Metric | Target | v1.2 (beat this) |
|--------|--------|------------------|
| Combined expect pass | ≥90% | 86% |
| Quote validity (holdout) | ≥98% | 90.9% |
| False supported (holdout) | ≤5% | 0% |
| Supported h-001–h-010 | ≥8/10 | 9/10 |
| Core eval (stretch) | 5/5 | 2/5 |

**NO-GO:** save `outputs/eval_combined_report.json` (small — `scp` to PC). Upload adapter only. **Do not download GGUF.**

**GO:** Step F (optional) → Step G (download GGUF).

Inspect failures:

```bash
python -c "
import json
d=json.load(open('outputs/eval_holdout_report.json'))
for r in d['per_row']:
    if r.get('failures') and not r.get('checks_passed'):
        print(r['id'], r['failures'])
"
```

---

## Step F — Upload to Hugging Face (from Vast)

```bash
export HF_TOKEN="hf_..."

cd ~/nassila/training/outputs/nassila-grounding-e4b-v1.3/lora_adapter
hf upload QinEmPeRoR93/nassila-grounding-e4b-v1.3-adapter . . --repo-type model
```

Upload **GGUF only after GO** (optional):

```bash
cd ~/nassila/training/exports
hf upload QinEmPeRoR93/nassila-grounding-e4b-v1.3 \
  nassila-grounding-e4b-v1.3-q6_k.gguf \
  nassila-grounding-e4b-v1.3-q6_k.gguf \
  --repo-type model
```

Fill [MODEL_CARD_v1_3.md](./MODEL_CARD_v1_3.md) after eval.

---

## Step G — Download to PC (GO only)

```powershell
pip install -U huggingface_hub
hf download QinEmPeRoR93/nassila-grounding-e4b-v1.3 `
  nassila-grounding-e4b-v1.3-q6_k.gguf `
  --local-dir .\models\nassila-grounding-e4b-v1.3
```

Then LM Studio: load GGUF → local server on port **1234**.

---

## Step H — Destroy Vast instance

Destroy (not stop) after reports saved and/or adapter uploaded.

---

## Quick reference

| Step | Path on Vast |
|------|----------------|
| Train output | `~/nassila/training/outputs/nassila-grounding-e4b-v1.3/lora_adapter/` |
| Merged HF | `~/nassila/training/exports/hf-merged-v1.3-bf16/` |
| **GGUF for eval** | `~/nassila/training/exports/nassila-grounding-e4b-v1.3-q6_k.gguf` |
| Eval report | `~/nassila/training/outputs/eval_combined_report.json` |
| Dataset audit | `~/nassila/training/reports/v1_3_audit_summary.json` |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Permission denied` SSH from PowerShell | Use **WSL** for SSH (same key as before) |
| `Connection refused` during eval | Start `llama-server` in pane 1 first |
| Wrong `--model` id | Copy id from `curl http://127.0.0.1:1234/v1/models` |
| OOM during train | A6000 48 GB; do not raise seq length |
| Merge fails | Use `merge_adapter_gemma4.py` only |
| `llama-ui` / `asset_60_data` / HF UI download failed | [LLAMA_CPP_VAST.md](./LLAMA_CPP_VAST.md) — re-clone **`b9608`**, never floating `main` |
| SSH dropped mid-train | `tmux attach -t v13` |

See [PHASE2_5_V1_3_PLAN.md](./PHASE2_5_V1_3_PLAN.md) for dataset rationale.
