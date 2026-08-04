# Nanbeige4.2-3B zero-shot probe (2026-07-27)

**Model:** [Nanbeige/Nanbeige4.2-3B](https://huggingface.co/Nanbeige/Nanbeige4.2-3B)  
**Harness:** `sanad-grounding-v1` · 95 rows (`eval_samples` + `eval_holdout_90`)  
**Runner:** Vast RTX 4090 + `Nanbeige/llama.cpp@nanbeige42` + Andgihat Q6_K GGUF · `enable_thinking: false`

## Verdict

**GO (later)** — Strong zero-shot signal — schedule QLoRA on Nanbeige when S15 un-parks (after S15_UNPARK_CRITERIA data gates).

## Metrics (this run)

| Metric | Nanbeige | S12 | S14 | Probe target |
|--------|----------|-----|-----|--------------|
| JSON parse (strict) | 100.00% | 100.00% | 100.00% | ≥90% |
| Combined expect | 85.27% | 93.68% | 93.68% | ≥70% promising |
| Holdout expect | 85.56% | 94.44% | 93.33% | — |
| Quote validity (holdout) | 100.00% | 100.00% | 94.74% | ≥85% |
| False supported (holdout) | 8.57% | 1.43% | 2.86% | ≤10% |
| Legacy core 5/5 | 4/5 | 4/5 | 5/5 | info |

## Artifacts

- Predictions: `/workspace/nassila-probe/training/outputs/nanbeige_zeroshot_predictions.jsonl`
- Combined report: `/workspace/nassila-probe/training/outputs/nanbeige_zeroshot_eval_combined_report.json`
- Holdout report: `/workspace/nassila-probe/training/outputs/nanbeige_zeroshot_eval_holdout_report.json`

## Notes

- Zero-shot base model — not comparable to fine-tuned Sanad S12/S14 on combined expect alone.
- Do not start S15 QLoRA from this probe alone; see `S15_UNPARK_CRITERIA.md`.
- Body holdout deferred until abstract probe passes strong/ambiguous bar.
