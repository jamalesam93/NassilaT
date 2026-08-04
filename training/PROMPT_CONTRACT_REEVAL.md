# Production prompt contract re-evaluation

**Status:** S12 done (single-seed) · S14 done (single-seed, Ollama) · S15 parked

Prompt contract: `sanad-grounding-v1`

Before any S15 training, re-evaluate both shipping checkpoints under the production
system/user XML prompt contract:

- [x] Confirm the split prompt goldens match the canonical Nassila fixtures.
  - 2026-07-18: `test_prompt_sync.py` **5 passed**; `fc /b` — system + user goldens **byte-identical** across Nassila ↔ NassilaT.
- [x] Run the standard holdout evaluation for Sanad S12 (E4B).
  - 2026-07-18: LM Studio `nassila-sanad-e4b`, 95 rows (`eval_samples.jsonl` + `eval_holdout_90.jsonl`), `--retry 1 --repair`, ~7.2 min.
- [x] Run the same holdout evaluation for Sanad S14 (12B).
  - 2026-07-18: **Ollama** `nassila-sanad-12b` (local GGUF via Modelfile; Gemma4 renderer). LM Studio blocked (peg-gemma4 / Channel Error on system+user). 95 rows, production system+user, `--retry 1 --repair`, ~21 min.
- [x] Record strict parse, combined, multi-claim, and quote-hallucination metrics (S12 + S14 below).
- [x] Compare results with the shipped checkpoint baselines and investigate regressions (below).
- [x] Approve the production prompt contract for continued use (not a clear regression). **S15 still parked** pending field-note curation (+ optional multi-seed).

## S12 results (`nassila-sanad-e4b`, production prompt)

Artifacts:

- `outputs/prompt_reeval_s12_predictions.jsonl`
- `outputs/prompt_reeval_s12_eval_holdout_report.json`
- `outputs/prompt_reeval_s12_eval_combined_report.json`

| Metric | This run (prod prompt) | S12 ship baseline (multi-seed mean) | Notes |
|--------|------------------------|--------------------------------------|-------|
| Rows | 95 (5 legacy + 90 holdout) | 115-row harness (incl. extended) | Extended core not in this batch |
| JSON parse (strict) | **100%** | ~100% | 95/95 |
| JSON parse (repair) | **100%** | — | 0 repairs needed |
| Combined expect | **93.68%** | **89.27%** | Single seed; not multi-seed mean |
| Holdout expect | **94.44%** | — | 85/90 |
| Quote validity (holdout) | **100%** | **92.98%** | |
| False supported (holdout) | **1.43%** | **3.81%** | |
| multi_claim (holdout) | **76.92%** | — | |
| Legacy core 5/5 | **4/5** | — | FAIL `eval-005` `min_claims:1<2` |

Holdout fails: `h-041`, `h-045`, `h-068`, `h-073`, `h-088` (includes known E4B `h-045`/`h-088` min_claims).

**Verdict (S12):** Production XML prompt does **not** look like a regression vs the shipped S12 baseline on this single-seed laptop run; combined/quote/false-supported are at or above the published multi-seed means. E4B default-tier automated gate still fails only on legacy core 5/5 (same class of `min_claims` issue). **Do not treat as multi-seed GO**.

## S14 results (`nassila-sanad-12b`, production prompt via Ollama)

Artifacts:

- `outputs/prompt_reeval_s14_predictions.jsonl`
- `outputs/prompt_reeval_s14_eval_holdout_report.json`
- `outputs/prompt_reeval_s14_eval_combined_report.json`
- Modelfile used: `outputs/Modelfile.sanad-12b` (FROM local LM Studio GGUF)

| Metric | This run (prod prompt, Ollama) | S14 ship baseline (HF table) | Notes |
|--------|--------------------------------|------------------------------|-------|
| Rows | 95 (5 legacy + 90 holdout) | Tier 2 harness | Extended core not in this batch |
| Runner | Ollama `11434` | LM Studio / Vast | LM Studio peg-gemma4 Channel Error on this laptop |
| JSON parse (strict) | **100%** | **100%** | 95/95; 0 repairs |
| Combined expect | **93.68%** | **90.43%** | Single seed |
| Holdout expect | **93.33%** | — | 84/90 |
| Quote validity (holdout) | **94.74%** | — | Below Tier 2 auto gate (≥98%) |
| False supported (holdout) | **2.86%** | **2.86%** | Matches ship table |
| multi_claim (holdout) | **76.92%** | — | |
| Legacy core 5/5 | **5/5** | — | Better than S12 re-eval on this batch |

Holdout fails: `h-003` (quote substring), `h-041`, `h-044`, `h-068`, `h-079`, `h-087` (`min_claims`).

**Gates (this run):** E4B-style default-tier gates **PASS**. Quality Tier 2 automated gates **FAIL** on holdout quote validity only (94.74% &lt; 98%); combined / parse / false-supported / legacy core / h-001–h-010 all pass.

**Verdict (S14):** Production prompt on Ollama is **not** a combined-score regression vs the published S14 ship baseline. Quote validity is the soft spot vs Tier 2’s 98% bar on this single-seed run — investigate `h-003` and whether Ollama decode vs ship LM Studio/Vast differs before treating as multi-seed GO. **App note:** prefer Ollama (or llama.cpp) for S14 locally until LM Studio peg-gemma4 is fixed; Nassila’s production path is still system+user (works on Ollama).

## How to re-run S14 (Ollama)

```powershell
cd "E:\Cursor Projects\NassilaT\training"

# If needed: ollama create nassila-sanad-12b -f outputs/Modelfile.sanad-12b

python scripts/run_l3_eval_batch.py `
  --base-url http://127.0.0.1:11434 `
  --model "nassila-sanad-12b" `
  --api-key ollama `
  --data data/eval_samples.jsonl data/eval_holdout_90.jsonl `
  --retry 1 --repair `
  --out outputs/prompt_reeval_s14_predictions.jsonl

python scripts/run_eval_reports.py `
  --predictions outputs/prompt_reeval_s14_predictions.jsonl `
  --repair `
  --holdout data/eval_holdout_90.jsonl `
  --out-dir outputs `
  --prefix prompt_reeval_s14_
```

Do not run Vast training as part of this checklist.

## Tier 3 Body Contrastive Frozen v2 Benchmark (308 rows, Vast AI)

Artifacts:
- S12: `reports/tier3_body_contrastive_frozen_v2_predictions_s12_vast.jsonl` / `reports/tier3_body_contrastive_frozen_v2_s12_vast_eval.json`
- S14: `reports/tier3_body_contrastive_frozen_v2_predictions_s14_vast.jsonl` / `reports/tier3_body_contrastive_frozen_v2_s14_vast_eval.json`

| Metric | S12 E4B (Vast `--jinja`) | S12 E4B (Local Ollama) | S14 12B (Vast AI) | Gate / Target |
|--------|--------------------------|------------------------|-------------------|---------------|
| Strict JSON parse | **100.0%** (0 repairs) | 100.0% | **98.70%** (99.68% w/ repair) | ≥98% ✅ |
| Expect checks pass rate | **79.87%** | 74.68% | **95.45%** | ≥90% (S14 ✅, S12 ❌) |
| False supported rate | **20.13%** | 25.32% | **4.22%** | ≤5% Tier2 (S14 ✅, S12 ❌) |
| `contradicted` category pass | **55.00%** | 45.00% | **89.17%** | Inform |
| `not_in_source` category pass | **95.74%** | 93.62% | **99.47%** | Inform |

