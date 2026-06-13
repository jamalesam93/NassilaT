# Phase 1 Walkthrough (Vast AI + RTX 4090 24GB) — Nassila L3 QLoRA Setup

This is a **newbie-friendly**, copy/paste walkthrough for **Phase 1** of the [**One Ring**](../docs/ONE_RING.md) training path: setting up a cloud GPU machine on **Vast AI** that can (1) download **Gemma 4 E4B Instruct** (`google/gemma-4-E4B-it`) from Hugging Face, (2) load it in **4-bit** (QLoRA), and (3) run a **tiny smoke training** to produce a LoRA adapter artifact for the first facet, **`l3_grounding`**.

Phase 1 is **not** where you get quality. Phase 1 is where you make sure the machine and tooling work so Phase 2 (real `nassila-grounding-e4b-v1` training) won’t waste your time/money.

---

## What you will have at the end of Phase 1

- A working Vast instance you can reconnect to even if your internet drops
- A working Python env on the server
- Hugging Face access for `google/gemma-4-E4B-it` (Apache 2.0; confirm **Files and versions** on HF)
- Proof the base model loads in 4-bit
- A tiny training run that produces an adapter folder:
  - `training/outputs/nassila-grounding-v1/` (example)

---

## Concepts (plain language)

- **LM Studio GGUF** (what you already downloaded) is for **running** the model locally. It is not the normal starting point for training.
- **Training** usually starts from **Hugging Face weights** (safetensors) and produces a **LoRA/QLoRA adapter**.
- Later, you **export back to GGUF** so LM Studio can run your tuned model (that’s Phase 4).

---

## Cost + disconnect safety (important)

### Use `tmux` so training survives disconnects
When you run commands inside `tmux` on the server, your job keeps running even if your home internet drops.

### Use `rsync` so big uploads/downloads can resume
Avoid `scp` for large files. Use `rsync -P` so transfers resume instead of restarting.

---

## Step 0 — Choose the Vast instance settings (for 4090 24GB)

When creating the instance in Vast:

- **GPU**: RTX 4090 (24GB)
- **Disk**: at least **100GB** free
- **RAM**: ideally **32GB+**
- **Image**: a **PyTorch + CUDA** image (fastest). Anything that already has CUDA + Python 3 installed is fine.

If Vast offers persistent storage/volume, enable it if you can. It reduces the risk of losing outputs.

---

## Step 1 — Prepare your Windows laptop (WSL2)

Open **WSL2 Ubuntu** and install tools:

```bash
sudo apt update && sudo apt install -y openssh-client rsync zip unzip
```

You will use:
- `ssh` to connect
- `tmux` on the server
- `rsync` for resumable file transfer

---

## Step 2 — Create a minimal upload bundle (so you don’t upload the whole repo)

For Phase 1 you only need the `training/` pack (scripts + sample data).

In WSL2:

```bash
cd "/mnt/e/Cursor Projects/citations-style"
zip -r training_bundle.zip training
```

This bundle should be small (usually MBs).

---

## Step 3 — SSH into Vast

Vast will show connection details:
- `HOST` (IP or hostname)
- `PORT` (SSH port)
- `USER` (often `root`)

From WSL2:

```bash
ssh -p <PORT> <USER>@<HOST>
```

Example:

```bash
ssh -p 2222 root@123.45.67.89
```

---

## Step 4 — Start `tmux` (disconnect-proof)

On the Vast server:

```bash
apt update && apt install -y tmux
tmux new -s nassila
```

If you disconnect later:

```bash
ssh -p <PORT> <USER>@<HOST>
tmux attach -t nassila
```

---

## Step 5 — Upload the bundle (resumable)

From **your laptop WSL2** (not inside Vast):

```bash
rsync -avP -e "ssh -p <PORT>" \
  "/mnt/e/Cursor Projects/citations-style/training_bundle.zip" \
  <USER>@<HOST>:~/nassila/
```

If the internet drops, run the same command again; it resumes.

On the Vast server:

```bash
mkdir -p ~/nassila && cd ~/nassila
unzip training_bundle.zip
ls -la training
```

---

## Step 6 — Create Python venv on Vast

On the Vast server:

```bash
cd ~/nassila
python3 -V
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
```

---

## Step 7 — Install training dependencies (Unsloth path)

On the Vast server (inside venv):

```bash
source ~/nassila/.venv/bin/activate
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install --no-deps trl peft accelerate bitsandbytes transformers datasets
```

If this step is slow, let it run—this is mostly server-side downloads.

---

## Step 8 — Hugging Face access

Do this on your **laptop first** (before renting Vast) if you can — saves GPU hourly cost.

### 8.1 Confirm model access (browser)

- Open https://huggingface.co/google/gemma-4-E4B-it
- **Files and versions** should list `model.safetensors` (~16 GB)
- License is **Apache 2.0** — no separate “Agree and access repository” step for this model

### 8.2 Create a Read token

https://huggingface.co/settings/tokens → **Read**

### 8.3 Optional test on your laptop (PowerShell or WSL)

```powershell
pip install -U huggingface_hub
hf auth login
hf auth whoami
hf download google/gemma-4-E4B-it config.json --local-dir ./hf_test
```

### 8.4 Login on the Vast server

```bash
pip install -U huggingface_hub
hf auth login
hf auth whoami
```

Paste your token when prompted (right-click paste in many SSH clients).

---

## Step 9 — Phase 1 “gate”: can the base model load in 4-bit?

This is the most important proof-of-life step.

On the Vast server:

```bash
python - <<'PY'
from unsloth import FastLanguageModel
model, tok = FastLanguageModel.from_pretrained(
    model_name="google/gemma-4-E4B-it",
    max_seq_length=4096,
    load_in_4bit=True,
)
print("OK: Gemma 4 E4B IT loaded in 4-bit")
PY
```

If it fails:
- Check `hf auth whoami`, the model id (`google/gemma-4-E4B-it`), and that Unsloth/CUDA installed correctly.
- Fix this before continuing (don’t start training until this works).

---

## Step 10 — Validate the sample dataset (fast)

On the Vast server:

```bash
cd ~/nassila/training
python scripts/validate_dataset.py data/l3_grounding_samples.jsonl
```

This checks the JSONL shape (including `sourceQuotes` constraints).

---

## Step 11 — Tiny QLoRA smoke training (Phase 1 completion)

This should create an adapter folder. Quality is not the goal yet.

On the Vast server:

```bash
cd ~/nassila/training
python scripts/train_qlora_gemma4_e4b.py \
  --train-file data/l3_grounding_samples.jsonl \
  --output-dir outputs/nassila-grounding-v1
```

After it finishes:

```bash
ls -la outputs/nassila-grounding-v1
```

If this succeeds, Phase 1 is “done.”

If it OOMs on a 4090 24GB (rare for a tiny run), the usual fix is reducing sequence length from 4096 to 2048 in the script config.

---

## Step 12 — Download results (resumable) — optional for Phase 1

You can postpone big downloads until later. For Phase 1, downloading the adapter is optional.

From **your laptop WSL2**:

```bash
rsync -avP --partial --append-verify -e "ssh -p <PORT>" \
  <USER>@<HOST>:~/nassila/training/outputs/nassila-grounding-v1/ \
  "/mnt/e/Cursor Projects/citations-style/training/outputs/nassila-grounding-v1/"
```

If the internet drops, re-run the same command.

---

## Troubleshooting cheatsheet

### “403 / permission denied”
- Run `hf auth login` and `hf auth whoami` on the server.
- Confirm you can open **Files and versions** for `google/gemma-4-E4B-it` in the browser.

### “Model not found”
- The repo id differs. Verify the exact Hugging Face model id and update `BASE_MODEL` in:
  - `training/scripts/train_qlora_gemma4_e4b.py`

### “CUDA / bitsandbytes / torch” errors
- Switch to a different Vast image that already has PyTorch+CUDA matching drivers.
- Recreate the instance if needed (this is usually faster than deep debugging).

### “OOM”
On a 4090 24GB, you should be fine, but if it happens:
- Use `MAX_SEQ_LENGTH = 2048`
- Keep batch size 1; use gradient accumulation
- Reduce LoRA rank if needed (e.g. 16 instead of 32)

---

## Phase 1 exit criteria (print and check)

- [ ] You can SSH into Vast reliably
- [ ] You started a `tmux` session
- [ ] `hf auth login` / `hf auth whoami` works
- [ ] Gemma loads in 4-bit (Unsloth) without error
- [ ] Dataset validates
- [ ] Smoke training produces `outputs/nassila-grounding-v1/`

Next is Phase 2 (build real dataset) and Phase 3 (train for quality + eval).

