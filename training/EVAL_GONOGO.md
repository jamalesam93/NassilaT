# Eval go / no-go — `nassila-grounding-e4b-v1`

## Baseline reference

See [`outputs/baseline_report_reference.json`](./outputs/baseline_report_reference.json) (Phase 0: 100% JSON w/ repair, 82% expect pass).

**Live baseline:** start LM Studio, then:

```powershell
.\scripts\run_baseline_eval.ps1
```

## Tuned model (after Vast)

```powershell
python scripts/run_l3_eval_batch.py --model "nassila-grounding-e4b-v1" `
  --data data/eval_samples.jsonl data/eval_holdout_45.jsonl `
  --retry 1 --repair --out outputs/v1_predictions.jsonl

python scripts/run_eval_reports.py `
  --predictions outputs/v1_predictions.jsonl --repair `
  --report outputs/v1_report.json
```

## Go criteria ([EVALUATION_GUIDE.md](./EVALUATION_GUIDE.md))

| Metric | Baseline | Tuned must |
|--------|----------|------------|
| JSON parse (repair) | 100% | ≥ 95% (aim 99%) |
| Expect pass | 82% | ≥ 90% |
| Quote validity | — | ≥ 98% |
| False supported | — | ≤ 5% |

Plus manual review of 20 hard holdout rows.

## No-go actions

- Expand `l3_grounding_train.jsonl` to 600–800 rows (`generate_l3_from_corpus.py --target-rows 700`)
- Re-run Vast QLoRA
- Do not publish smoke adapter as v1
