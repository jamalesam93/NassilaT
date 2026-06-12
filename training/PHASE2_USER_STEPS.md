# Phase 2 — your next steps

**Full walkthrough:** [PHASE2_TRAINING_GUIDE.md](./PHASE2_TRAINING_GUIDE.md)

## Current repo state

- [x] `data/paper_corpus_enriched.jsonl` — **4,233** papers with abstract ≥ 120 chars
- [x] **v1** train (400 rows) — trained, GGUF on HF; eval **NO-GO** (62% expect, 0% quote validity on holdout supported)
- [x] **Phase 2.1** dataset refresh — **700** rows, validated + audit **PASS** (`outputs/l3_audit_report_v1_1.json`)
- [x] `data/l3_review_queue_v1_1.csv` — **human spot-check complete** (105 rows, 99.05% alignment)
- [x] Paraphrase-supported generator + unit tests in `tests/test_generate_l3_from_corpus.py`

**v1.1 train verdict mix (seed 43):** supported **266** (262 paraphrase + 4 direct) · not_in_source 154 · contradicted 126 · weak 98 · insufficient_evidence 56

**v1 eval failure (why 2.1):** model over-called `weak` on numeric paraphrase cases; holdout supported category 0% pass. v1.1 adds eval-style paraphrase rows with `sourceQuotes` = original abstract sentence.

## Your checklist

### v1 (done)

1. ~~Label QA~~ · ~~baseline eval~~ · ~~Vast train~~ · ~~tuned eval (NO-GO)~~ · ~~HF publish (v1)~~

### v1.1 — Phase 2.2 (done, NO-GO)

- Trained 700 rows on Vast; eval on Vast (66% expect, 9.1% quote validity)
- Adapter on HF: `QinEmPeRoR93/nassila-grounding-e4b-v1.1-adapter`
- Report: [reports/v1_1_eval_combined_report.json](./reports/v1_1_eval_combined_report.json)
- Walkthrough: [PHASE2_2_V1_1_WALKTHROUGH.md](./PHASE2_2_V1_1_WALKTHROUGH.md)

### v1.2 — Phase 2.3 (next)

**Plan:** [PHASE2_3_V1_2_PLAN.md](./PHASE2_3_V1_2_PLAN.md)

1. **Dataset** — holdout-shaped supported rows, anti-false-weak pairs, rebalance
2. **Eval alignment** — chat-template eval matching train
3. **Vast train** — 3 epochs, `nassila-grounding-e4b-v1.2`
4. **Eval on Vast** before any GGUF download
