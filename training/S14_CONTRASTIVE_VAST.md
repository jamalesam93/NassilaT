# S14 contrastive v2 on Vast (llama.cpp + HF)

**Standing policy (2026-07-27):** Tier 3 **body eval batches run on Vast** for speed. Laptop is for drafting/freezing/scoring local S12 only when needed. **Not S15 training.**

**Goal:** Score `eval_holdout_body_contrastive_frozen_v2.jsonl` (308 rows) with **S12** (`nassila-sanad-e4b`) and **S14** (`nassila-sanad-12b`) on Vast AI via `llama-server`.

**S12 Vast result:** expect **79.87%** · false_supported **20.13%** (`reports/tier3_body_contrastive_frozen_v2_s12_vast_eval.json`)  
**S14 Vast result:** expect **95.45%** · false_supported **4.22%** (`reports/tier3_body_contrastive_frozen_v2_s14_vast_eval.json`)  

---

## Spec

| Setting | Value |
|---------|--------|
| GPU | **RTX 4090 24 GB** (preferred) |
| Disk | ≥ 40 GB (GGUF ~10 GB + llama.cpp build) |
| Image | NGC PyTorch / Ubuntu + CUDA |
| Runtime | **llama.cpp `llama-server`** on `:8080` |
| S14 (this run) | [QinEmPeRoR93/nassila-sanad-12b](https://huggingface.co/QinEmPeRoR93/nassila-sanad-12b) `nassila-sanad-12b-q6_k.gguf` |
| S12 (also on Vast) | [QinEmPeRoR93/nassila-sanad-e4b](https://huggingface.co/QinEmPeRoR93/nassila-sanad-e4b) `nassila-sanad-e4b-q6_k.gguf` (~5.8–6.2 GB) |

**Do not** use Ollama install on this Vast path — `curl` to ollama.com often resets. Nanbeige fork not needed for S14 (stock llama.cpp + public GGUF).

---

## Lessons (keep)

1. **WSL SSH** — Windows OpenSSH publickey fails; use WSL: `ssh -p <direct_port> root@<public_ip>`.
2. **Paths with spaces** — run `scp`/`ssh` inside `wsl bash -lc` with `/mnt/e/Cursor Projects/...`, not PowerShell-expanded `e:/...` into WSL scp.
3. **Reuse the box** — keep `/workspace/llama.cpp` build and `/workspace/models/s14/*.gguf` across eval slices.
4. **Never** `pkill -f run_s14...` inside an SSH command that itself contains that string (kills the session).
5. **vastai** — API key lives in `%USERPROFILE%\.config\vastai\vast_api_key` after `vastai set api-key`; do not re-ask.

### Current instance (as of 2026-07-27)

| Field | Value |
|-------|--------|
| ID | `46030207` |
| GPU | 1× RTX 4090 · ~$0.42/hr |
| Public IP | `174.136.205.7` |
| Direct SSH | port **20008** (WSL) |
| Proxy SSH | `ssh5.vast.ai:30206` |
| Remote kit | `/workspace/nassila-s14/training` |
| Run log | `outputs/s14_contrastive_run.log` |

Confirm with `vastai show instances` — IPs/ports change on re-rent.

---

## 1 — Login + instance

```powershell
cd "E:\Cursor Projects\NassilaT\training"
vastai show instances
# If needed: .\scripts\vast_s14_contrastive_rent.ps1
```

---

## 2 — Sync up (WSL)

```bash
# from WSL
cd "/mnt/e/Cursor Projects/NassilaT/training"
sed -i 's/\r$//' scripts/run_s14_contrastive_vast.sh
scp -P 20008 scripts/run_l3_eval_batch.py scripts/evaluate_outputs.py \
  scripts/json_repair.py scripts/lmstudio_smoke_test.py \
  scripts/validate_dataset.py scripts/corpus_utils.py \
  scripts/run_s14_contrastive_vast.sh \
  root@174.136.205.7:/workspace/nassila-s14/training/scripts/
scp -P 20008 data/eval_holdout_body_contrastive_frozen_v2.jsonl \
  root@174.136.205.7:/workspace/nassila-s14/training/data/
```

Or PowerShell helper (fix host/port from `vastai show instances --raw`):

```powershell
.\scripts\vast_s14_contrastive_sync.ps1 -SshHost 174.136.205.7 -SshPort 20008 -Direction up
```

---

## 3 — Run on instance

```bash
ssh -p 20008 root@174.136.205.7
cd /workspace/nassila-s14/training
tmux new -s s14   # preferred for long runs
nohup bash scripts/run_s14_contrastive_vast.sh > outputs/s14_contrastive_run.log 2>&1 < /dev/null &
tail -f outputs/s14_contrastive_run.log
```

Stages: deps → build llama.cpp CUDA (once) → HF GGUF download → `llama-server` → smoke → 308-row batch → `evaluate_outputs.py`.

After first successful build/download on this disk, later slices are much faster (reuse artifacts).

---

## 4 — Sync down

```powershell
.\scripts\vast_s14_contrastive_sync.ps1 -SshHost 174.136.205.7 -SshPort 20008 -Direction down
```

Artifacts:

- `reports/tier3_body_contrastive_frozen_v2_predictions_s14_vast.jsonl`
- `reports/tier3_body_contrastive_frozen_v2_s14_vast_eval.json`

Compare false-supported to S12 **25.32%** and contrastive v1 S14 **5.95%**.

**Teardown:** destroy only when pausing the Vast-first eval cadence (`vastai destroy instance 46030207`). Prefer keeping the warm 4090 while iterating slices.

---

## Next slices (same machine pattern)

| Slice | Rows | Status |
|-------|------|--------|
| Support v4 | 308 | Done (do not re-score) |
| Multiclaim v1 | 100 | Scored local; optional Vast re-confirm |
| Contrastive v2 S12 | 308 | **Done on Vast** (79.87% expect pass / 20.13% false supported) |
| Contrastive v2 S14 | 308 | **Done on Vast** (95.45% expect pass / 4.22% false supported) |
| Future body evals | — | **Vast by default** |
