# Nassila — Gemma 4 E4B Training Pack

This folder is a **self-contained guide** for fine-tuning **Nassila-specific** local models on **Google Gemma 4 E4B**, then running them in **LM Studio** and connecting them to the desktop app.

**Strategy:** [**Ouroboros**](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS.md) — seven workers, forged one at a time. **v1** ships **Sanad** (`l3_grounding`) → **v1.4a**. **Agent brief:** [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md). See [ROADMAP.md](./ROADMAP.md).

It is documentation-first: sample data, schemas, diagrams, and helper scripts. It does **not** ship model weights, checkpoints, or private training data.

---

## What you already have (LM Studio Q6_K)

If you downloaded **Gemma 4 E4B Instruct Q6_K** in LM Studio, you have a **runtime model** — great for:

- Testing prompts before training
- Baseline evaluation (stock model vs fine-tuned)
- Running inference after you export your tuned model back to GGUF

You **cannot** reliably fine-tune that GGUF file directly. Fine-tuning starts from the **base/instruct checkpoint** (Hugging Face or Unsloth), produces a **LoRA adapter**, then you **merge/export** to GGUF for LM Studio.

```
LM Studio Q6_K GGUF  →  inference only (baseline + final deployment)
Hugging Face E4B IT  →  QLoRA training  →  adapter  →  export Q6_K GGUF  →  LM Studio
```

---

## Quick start (read in this order)

| Step | Document | What you do |
|------|----------|-------------|
| 0 | [Nassila `OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md) | **Agents:** workers, v1.4 state, v1.6 training |
| 1 | [TRAINING_GUIDE.md](./TRAINING_GUIDE.md) | Full walkthrough: environment, data, train, export, test |
| 1.1 | [CORPUS_PIPELINE.md](./CORPUS_PIPELINE.md) | Phase 1.5: merge JSON exports, backfill abstracts (PC) |
| 1.2 | [PHASE2_8_V1_5_WALKTHROUGH.md](./PHASE2_8_V1_5_WALKTHROUGH.md) | **Current:** v1.8 Vast pipeline (Sanad) |
| 1.2a | [PHASE2_7_V1_4_WALKTHROUGH.md](./PHASE2_7_V1_4_WALKTHROUGH.md) | v1.4 Vast pipeline (reference) |
| 1.3 | [PHASE1_VAST_4090_WALKTHROUGH.md](./PHASE1_VAST_4090_WALKTHROUGH.md) | Phase 1: Vast smoke QLoRA |
| 2 | [DATASET_SCHEMA.md](./DATASET_SCHEMA.md) | Exact JSONL formats for each task |
| 3 | [EVALUATION_GUIDE.md](./EVALUATION_GUIDE.md) | Metrics and pass/fail thresholds |
| 4 | [LM_STUDIO_INTEGRATION.md](./LM_STUDIO_INTEGRATION.md) | Serve model locally; point Nassila at it |
| 5 | [ROADMAP.md](./ROADMAP.md) | Ouroboros phases (Sanad now → merge later) |
| 6 | [MODEL_CARD_v1_4.md](./MODEL_CARD_v1_4.md) | Ship metrics (v1.4a SHIP, v1.4b NO-GO) |

---

## Folder layout

```
training/
  README.md                 ← you are here
  TRAINING_GUIDE.md         ← main step-by-step guide
  DATASET_SCHEMA.md         ← JSONL field definitions
  EVALUATION_GUIDE.md       ← how to score your model
  LM_STUDIO_INTEGRATION.md  ← local server + app wiring
  ROADMAP.md                ← Ouroboros training phases
  MODEL_CARD_v1_4.md        ← ship metrics (v1.4a SHIP)
  requirements.txt          ← Python deps for scripts
  data/
    l3_grounding_samples.jsonl    ← 8 train-style examples
    webpage_citation_samples.jsonl
    eval_samples.jsonl            ← 5 eval rows with expect blocks
    eval_holdout_45.jsonl         ← 45-row balanced holdout (eval-only)
  scripts/
    validate_dataset.py
    evaluate_outputs.py           ← strict vs repaired parse rates
    lmstudio_smoke_test.py        ← supports --id, --retry, --repair
    run_l3_eval_batch.py          ← batch runner with retry/repair
    json_repair.py                ← shared JSON repair (commas, ?:, fences)
    train_qlora_gemma4_e4b.py
  figures/
    training_pipeline.mmd
    app_integration_flow.mmd
```

Product vision: [Nassila `docs/OUROBOROS.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS.md) · agent brief [`OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md). App: [`WEBPAGE_ROADMAP.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/WEBPAGE_ROADMAP.md).

---

## What to train first (Ouroboros workers)

| Priority | Task id | v1? | App hook |
|----------|---------|-----|----------|
| **1** | `l3_grounding` | **Yes** | [`grounding-llm.ts`](../src/engine/manuscript/grounding-llm.ts) |
| 2 | `doc_extract` | No | [`pdf-extract.ts`](../src/engine/manuscript/pdf-extract.ts) |
| 3 | `source_pdf_extract` | No | `pdf_pending` in manuscript audit |
| 4 | `webpage_*`, `issue_explain` | No | [`docs/WEBPAGE_ROADMAP.md`](../docs/WEBPAGE_ROADMAP.md) |
| 5 | `table_figure_grounding` | No | Multimodal (12B tier) |

Train **`l3_grounding` first** → `nassila-grounding-e4b-v1`. Merge additional tasks into **`nassila-agent-*`** when each facet passes eval ([`EVALUATION_GUIDE.md`](./EVALUATION_GUIDE.md)).

---

## Hardware expectations (realistic)

| Stage | Minimum | Comfortable |
|-------|---------|-------------|
| Baseline inference (LM Studio Q6_K) | 12–16 GB RAM | GPU with 8+ GB VRAM |
| QLoRA fine-tune E4B | ~17 GB VRAM (Unsloth guidance) | 24 GB VRAM or cloud A40/L4 |
| Export to GGUF | CPU disk space ~10–15 GB | Same |

If you only have a laptop with LM Studio, you can still **prepare data**, **validate datasets**, **run baseline eval**, and **train later** on a cloud GPU.

---

## Helper commands

```bash
# From repo root
cd training
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Validate sample datasets
python scripts/validate_dataset.py data/l3_grounding_samples.jsonl
python scripts/validate_dataset.py data/webpage_citation_samples.jsonl

# Smoke-test LM Studio (server must be running)
python scripts/lmstudio_smoke_test.py --base-url http://localhost:1234 --model "your-model-id"

# Evaluate model outputs against eval set
python scripts/evaluate_outputs.py --eval data/eval_samples.jsonl --predictions path/to/predictions.jsonl
```

---

## Important principles

1. **Deterministic code stays authoritative** — registries, URL fetch, JSON parse, overlap checks in the app are guardrails; the model assists, it does not judge alone.
2. **Never reward hallucinated quotes** — `sourceQuotes` must be substrings of the source excerpt (validated in `validate_dataset.py`).
3. **Keep train and eval separate** — do not train on `eval_samples.jsonl`.
4. **Respect copyright** — use synthetic samples, OA excerpts, or data you have rights to use; do not dump full paywalled PDFs into a public repo.
5. **Gemma license** — comply with [Google Gemma terms](https://ai.google.dev/gemma/terms) for fine-tuned derivatives.

---

## Diagrams

See [`figures/training_pipeline.mmd`](./figures/training_pipeline.mmd) and [`figures/app_integration_flow.mmd`](./figures/app_integration_flow.mmd). Render them in any Mermaid viewer or paste into GitHub markdown.

---

## Next step

Open **[TRAINING_GUIDE.md](./TRAINING_GUIDE.md)** and follow the baseline section before spending time on QLoRA. Product branding: **[../docs/BRAND.md](../docs/BRAND.md)**.
