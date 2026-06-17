# Phase 2 training guide — `nassila-grounding-e4b-v1`

End-to-end checklist for **abstract-only** `l3_grounding`: corpus → labels → baseline → Vast QLoRA → GGUF → eval → Hugging Face.

**Goal:** shippable local model `nassila-grounding-e4b-v1` (Gemma 4 E4B + QLoRA, Q6_K GGUF for LM Studio).

**Out of scope for Phase 2:** PDF/fulltext fetch, `source_pdf_extract` training, manuscript audit UI in the desktop app.

---

## What you need

| Requirement | Notes |
|-------------|-------|
| **PC (Windows)** | Corpus, label generation, baseline/tuned eval via LM Studio |
| **LM Studio** | Stock Gemma 4 E4B Q6_K for baseline; tuned GGUF after export |
| **Vast.ai** | 1× RTX 4090, PyTorch NGC CUDA 13, ~100 GB disk |
| **Hugging Face** | Write token for adapter + GGUF upload |
| **NassilaT repo** | `training/` folder with data + scripts |

---

## Files used in Phase 2

### Training input (required on Vast)

| File | Role |
|------|------|
| `data/l3_grounding_train.jsonl` | **QLoRA training set** (300–500 rows for v1) |
| `data/eval_samples.jsonl` | 5 core eval rows — **never train on this** |
| `data/eval_holdout_45.jsonl` | 45 holdout eval rows — **never train on this** |

### Corpus / label pipeline (PC)

| File | Role |
|------|------|
| `data/paper_corpus_enriched.jsonl` | Paper pool (abstract ≥ 120 chars for sampling) |
| `data/l3_grounding_candidates.jsonl` | All generated rows before balancing |
| `data/l3_review_queue.csv` | ~15% spot-check sample for human review |
| `data/eval_corpus_holdout_papers.jsonl` | 50 papers held out of train sampling |

### Outputs

| Path | Role |
|------|------|
| `outputs/nassila-grounding-e4b-v1/lora_adapter/` | LoRA weights after Vast train |
| `exports/nassila-grounding-e4b-v1-q6_k/` | GGUF for LM Studio |
| `outputs/baseline_report.json` | Stock model metrics |
| `outputs/v1_predictions.jsonl` | Tuned model eval predictions |

---

## Step 0 — Phase 1.5 corpus (PC)

Skip if `data/paper_corpus_enriched.jsonl` already exists with enough abstracts.

```powershell
cd training
pip install -r requirements-corpus.txt

python scripts/build_paper_corpus.py
python scripts/enrich_corpus_abstracts.py --mailto your@email.com
```

**Exit check:** `data/paper_corpus_enriched_stats.json` shows `abstract_ge_120` ≥ 2,000 (current corpus: **4,233**).

Details: [CORPUS_PIPELINE.md](./CORPUS_PIPELINE.md).

---

## Step 1 — Generate training labels (PC)

Rule-based `l3_grounding` rows from abstracts. Every row uses `source_excerpt` = abstract and `meta.label: "abstract"`.

```powershell
cd training
python scripts/generate_l3_from_corpus.py `
  --corpus data/paper_corpus_enriched.jsonl `
  --target-rows 400 `
  --export-review data/l3_review_queue.csv `
  --review-fraction 0.15
```

**Produces:**

- `data/l3_grounding_train.jsonl` — 400 balanced rows
- `data/l3_grounding_candidates.jsonl` — intermediate pool
- `data/l3_review_queue.csv` — spot-check queue
- `data/eval_corpus_holdout_papers.jsonl` — 50 held-out papers

**Tier guidance (plan):**

| Tier | `--target-rows` | When |
|------|-----------------|------|
| v1 first train | 300–500 | First Vast run |
| v1 stronger | 600–800 | Eval passes but margin is thin |
| Strong v1 | 1,000–1,500 | Only if spot-check reject rate stays low |

---

## Step 2 — Validate dataset (PC)

```powershell
python scripts/validate_dataset.py data/l3_grounding_train.jsonl
```

Must print `OK: 400 record(s)`. Fix generator issues before Vast if validation fails.

---

## Step 3 — Label QA (PC)

### 3a — Automated structural audit (all rows)

```powershell
python scripts/audit_l3_labels.py data/l3_grounding_train.jsonl --json outputs/l3_audit_report.json
```

Must print `PASS` before training. Catches truncation collisions, missing quotes, and template-prefix regressions.

### 3b — Human review

**Full v1 set (400 rows):** `data/l3_review_full_400.csv`  
**Spot sample (~15%):** `data/l3_review_queue.csv`

```powershell
python scripts/export_l3_review.py --out data/l3_review_full_400.csv
```

1. Open the CSV in Excel (UTF-8 with BOM).
2. Compare **`passage`** + **`claim`** to **`source_quote`** and **`source_excerpt_preview`** (preview is centered on the quote, not the abstract opening).
3. Mark `approve`: `yes` / `no`.
4. If any `no`: remove those `id` values from `data/l3_grounding_train.jsonl` (or regenerate with a new `--seed`).

For **v1 (400 rows)**, full manual review is reasonable. For **600–800+** rows, rely on `audit_l3_labels.py` plus spot-check **10–20%** only.

**Label rules (generator v2):** verdicts follow quote overlap, numeric flip, hedging, or absent claims — not fixed passage prefixes.

---

## Step 4 — Baseline eval (PC + LM Studio)

1. In **LM Studio**, load stock **Gemma 4 E4B** (Q6_K).
2. Start the **local server** on `http://localhost:1234`.
3. Run:

```powershell
.\scripts\run_baseline_eval.ps1
```

**Saves:** `outputs/baseline_predictions.jsonl`, `outputs/baseline_report.json`.

**Reference (Phase 0):** 100% JSON parse with repair, ~82% expect pass — see `outputs/baseline_report_reference.json`.

If LM Studio is not running, every row fails with connection refused; fix the server before comparing tuned vs baseline.

---

## Step 5 — Rent Vast instance

| Setting | Value |
|---------|-------|
| Template | **PyTorch NGC (CUDA 13)** |
| GPU | 1× RTX 4090 (or similar 24 GB+) |
| Disk | **100 GB** |

SSH in and verify CUDA:

```bash
nvidia-smi
```

CUDA must be **12.4+ or 13.x**. If you see **12.2**, destroy the instance and rent another host.

---

## Step 6 — Vast environment setup

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

Ensure `data/l3_grounding_train.jsonl` is on the instance (clone from git after you commit/push, or `scp` the file).

---

## Step 7 — QLoRA train (Vast)

```bash
cd ~/nassila/training
tmux new -s train

python scripts/train_qlora_gemma4_e4b.py \
  --train-file data/l3_grounding_train.jsonl \
  --output-dir outputs/nassila-grounding-e4b-v1
```

**Expect:** `outputs/nassila-grounding-e4b-v1/lora_adapter/adapter_model.safetensors`

Train script uses `save_strategy="no"` to avoid Phase 1 pickle checkpoint issues.

Typical runtime: **2–6 hours** depending on host and settings.

---

## Step 8 — Export GGUF (Vast)

```bash
python scripts/export_gguf.py \
  --adapter-dir outputs/nassila-grounding-e4b-v1/lora_adapter \
  --out-dir exports/nassila-grounding-e4b-v1-q6_k
```

Download or upload from Vast before destroying the instance.

---

## Step 9 — Upload Hugging Face (Vast or PC)

```bash
cd outputs/nassila-grounding-e4b-v1/lora_adapter
hf upload YOUR_USER/nassila-grounding-e4b-v1-adapter . . --repo-type model

cd ~/nassila/training/exports/nassila-grounding-e4b-v1-q6_k
hf upload YOUR_USER/nassila-grounding-e4b-v1 . . --repo-type model
```

Model card template: [MODEL_CARD.md](./MODEL_CARD.md). Full notes: [HF_PUBLISH.md](./HF_PUBLISH.md).

---

## Step 10 — Tuned eval + go/no-go (PC + LM Studio)

1. Import **GGUF** into LM Studio as `nassila-grounding-e4b-v1`.
2. Start local server on port 1234.
3. Run:

```powershell
python scripts/run_l3_eval_batch.py --model "nassila-grounding-e4b-v1" `
  --data data/eval_samples.jsonl data/eval_holdout_45.jsonl `
  --retry 1 --repair --out outputs/v1_predictions.jsonl

python scripts/run_eval_reports.py `
  --predictions outputs/v1_predictions.jsonl --repair
Copy-Item -Force outputs/eval_combined_report.json outputs/v1_report.json
```

4. Compare to baseline. **Go criteria** ([EVAL_GONOGO.md](./EVAL_GONOGO.md)):

| Metric | Tuned must |
|--------|------------|
| JSON parse (with repair) | ≥ 95% (aim 99%) |
| Expect pass | ≥ 90% |
| Quote validity | ≥ 98% |
| False `supported` | ≤ 5% |

5. Manually review **20 hard holdout** cases from `eval_holdout_45.jsonl`.

**If no-go:** expand train set (`--target-rows 700`), re-validate, re-run Vast — do **not** ship the Phase 1 smoke adapter as v1.

---

## Step 11 — Destroy Vast instance

Destroy (not just stop) after adapter + GGUF are uploaded or downloaded.

---

## Quick checklist

- [ ] `paper_corpus_enriched.jsonl` — abstracts backfilled
- [ ] `l3_grounding_train.jsonl` — 400 rows, validated
- [ ] `l3_review_queue.csv` — spot-checked
- [ ] `baseline_report.json` — LM Studio baseline saved
- [ ] Vast QLoRA — `lora_adapter/` produced
- [ ] GGUF Q6_K — LM Studio loads model
- [ ] HF — adapter + GGUF published
- [ ] Tuned eval — meets go criteria
- [ ] Vast instance destroyed

---

## Budget (approximate)

| Stage | Time | GPU cost |
|-------|------|----------|
| Corpus + labels | 2–4 hr | $0 |
| Vast train + export | 2–6 hr | ~$1–4 |

---

## Related docs

| Doc | Purpose |
|-----|---------|
| [PHASE2_7_V1_4_WALKTHROUGH.md](./PHASE2_7_V1_4_WALKTHROUGH.md) | Vast-focused commands (current) |
| [EVALUATION_GUIDE.md](./EVALUATION_GUIDE.md) | Metric definitions |
| [EVAL_GONOGO.md](./EVAL_GONOGO.md) | Ship / no-ship gates |
| [DATASET_SCHEMA.md](./DATASET_SCHEMA.md) | JSONL field reference |
| [ROADMAP.md](./ROADMAP.md) | One Ring phases |
