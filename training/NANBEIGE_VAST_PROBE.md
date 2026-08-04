# Nanbeige4.2-3B Vast zero-shot probe

> **Result (2026-08):** **NO-GO — retired.** Zero-shot probe: **65.26%** expect, **34.09%** false-supported. QLoRA fine-tune on the v1.14 dataset did **not** help (65.26% / 34.42%), and thinking mode changed nothing. Nanbeige 3B is **not** an S15-class default model — S15 shipped on **Qwen 3.5 4B** instead (`nassila-sanad-4b`). Results: [`reports/nanbeige_zeroshot_probe_2026-07.md`](./reports/nanbeige_zeroshot_probe_2026-07.md), [`outputs/nanbeige_s15_contrastive_v2_report.json`](./outputs/nanbeige_s15_contrastive_v2_report.json). Do **not** revisit at 3B scale; revisit only if a Nanbeige ~12B emerges.

Runbook below is kept for reproducibility. **Do not re-run** at 3B.

Disposable cloud probe: **no local model download**. Answers whether [Nanbeige/Nanbeige4.2-3B](https://huggingface.co/Nanbeige/Nanbeige4.2-3B) is worth a future S15 QLoRA experiment.

**Recommended path:** **llama.cpp** (Nanbeige fork + community GGUF) — ~1–2 h total on a 4090.  
**Avoid on Vast:** building **vLLM from source** (often 1–5+ h compile, SSH-hostile).

**Automation:** [`scripts/run_nanbeige_llamacpp_vast_probe.sh`](./scripts/run_nanbeige_llamacpp_vast_probe.sh)

Legacy vLLM script (not recommended): [`scripts/run_nanbeige_vast_probe.sh`](./scripts/run_nanbeige_vast_probe.sh)

---

## Vast instance spec

| Setting | Value |
|---------|--------|
| GPU | **RTX 4090 (24 GB)** — good default |
| Also OK | L4 / A10 (22–24 GB) |
| Avoid | 8 GB cards (looped KV cache) |
| Disk | **≥ 50 GB** (GGUF ~3–4 GB + llama.cpp build) |
| Image | **Ubuntu 22.04 + CUDA** or minimal PyTorch (not required) |
| Budget | ~**$1–3** · ~1–2 h |

---

## Step 1 — Rent instance (Vast UI or CLI)

**CLI (installed via `pip install vastai`):**

```powershell
cd "E:\Cursor Projects\NassilaT\training"
vastai login
.\scripts\vast_nanbeige_rent.ps1                    # search L4/A10-class offers
.\scripts\vast_nanbeige_rent.ps1 -OfferId 45767485  # print create command
```

**UI:** [vast.ai](https://vast.ai) → Search: `L4` or `A10`, disk ≥ 80 GB.

---

## Step 2 — Sync NassilaT (Windows)

From PowerShell (adjust host/port):

```powershell
.\scripts\vast_nanbeige_sync.ps1 -SshHost vast.example.com -SshPort 22222 -Direction up
```

Or on the instance:

```bash
cd /workspace
git clone https://github.com/jamalesam93/NassilaT.git
cd NassilaT/training
```

---

## Step 3 — Run probe (llama.cpp, on instance)

```bash
cd /workspace/nassila-probe/training   # or your sync path
tmux new -s nanbeige
bash scripts/run_nanbeige_llamacpp_vast_probe.sh 2>&1 | tee outputs/nanbeige_probe.log
```

Stages: build `Nanbeige/llama.cpp@nanbeige42` (cmake, **`-j 8`**) → download **Andgihat Q6_K GGUF** → `llama-server --jinja` → 95-row eval → memo.

**Resume:**

```bash
SKIP_BUILD=1 bash scripts/run_nanbeige_llamacpp_vast_probe.sh
SKIP_BUILD=1 SKIP_DOWNLOAD=1 SKIP_SERVER=1 bash scripts/run_nanbeige_llamacpp_vast_probe.sh  # eval only
```

**tmux** (recommended):

```bash
tmux new -s nanbeige
bash scripts/run_nanbeige_vast_probe.sh
# Ctrl+B, D to detach
```

---

## Step 4 — Download artifacts (PC)

```powershell
.\scripts\vast_nanbeige_sync.ps1 -SshHost vast.example.com -SshPort 22222 -Direction down
```

Files:

- `outputs/nanbeige_zeroshot_predictions.jsonl`
- `outputs/nanbeige_zeroshot_eval_*_report.json`
- `reports/nanbeige_zeroshot_probe_2026-07.md`

---

## Step 5 — Teardown

1. Confirm artifacts on PC.
2. **Destroy** the Vast instance (stops billing).
3. If verdict is **WAIT/WEAK**, do nothing until Nanbeige ships official GGUF/Ollama.

---

## HF community notes (why vLLM, not llama.cpp)

| Discussion | Takeaway |
|------------|----------|
| [#6](https://huggingface.co/Nanbeige/Nanbeige4.2-3B/discussions/6) | `json_schema` + jinja broken on llama.cpp fork |
| [#17](https://huggingface.co/Nanbeige/Nanbeige4.2-3B/discussions/17) | Tool-call parser whitespace bug in llama.cpp |
| [#18](https://huggingface.co/Nanbeige/Nanbeige4.2-3B/discussions/18) | 8 GB VRAM ≈ 32K ctx max (44 logical KV layers) |
| [#1](https://huggingface.co/Nanbeige/Nanbeige4.2-3B/discussions/1) | No official GGUF yet |

Eval scripts use **`--disable-thinking`** → `chat_template_kwargs: {enable_thinking: false}`.

---

## Probe thresholds

| Signal | Parse | Combined | Quote (holdout) |
|--------|-------|----------|-----------------|
| Strong (GO later) | ≥95% | ≥75% | ≥90% |
| Promising | ≥90% | ≥70% | ≥85% |
| Weak (WAIT) | <85% or combined <60% | | |

Baselines: [PROMPT_CONTRACT_REEVAL.md](./PROMPT_CONTRACT_REEVAL.md) (S12/S14 single-seed).

---

## Manual commands (if not using the shell script)

```bash
# Server
vllm serve Nanbeige/Nanbeige4.2-3B --host 0.0.0.0 --port 8000 \
  --max-model-len 8192 --gpu-memory-utilization 0.85 \
  --enable-auto-tool-choice --tool-call-parser nanbeige --reasoning-parser nanbeige

# Eval
python scripts/run_l3_eval_batch.py --base-url http://127.0.0.1:8000 \
  --model Nanbeige/Nanbeige4.2-3B \
  --data data/eval_samples.jsonl data/eval_holdout_90.jsonl \
  --retry 1 --repair --disable-thinking \
  --out outputs/nanbeige_zeroshot_predictions.jsonl

python scripts/run_eval_reports.py --predictions outputs/nanbeige_zeroshot_predictions.jsonl \
  --prefix nanbeige_zeroshot_ --repair

python scripts/score_nanbeige_probe.py \
  --predictions outputs/nanbeige_zeroshot_predictions.jsonl \
  --combined-report outputs/nanbeige_zeroshot_eval_combined_report.json \
  --holdout-report outputs/nanbeige_zeroshot_eval_holdout_report.json
```
