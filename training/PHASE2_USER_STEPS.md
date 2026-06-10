# Phase 2 — your next steps

**Full walkthrough:** [PHASE2_TRAINING_GUIDE.md](./PHASE2_TRAINING_GUIDE.md)

## Current repo state

- [x] `data/paper_corpus_enriched.jsonl` — **4,233** papers with abstract ≥ 120 chars
- [x] `data/l3_grounding_train.jsonl` — **400** rows, validated + structurally audited
- [x] `data/l3_review_full_400.csv` — **full human review complete** (100% internal consistency)
- [x] `scripts/audit_l3_labels.py` — PASS on all 400 rows
- [x] Train script (`save_strategy=no`), `export_gguf.py`, Vast walkthrough

**Train verdict mix (locked for v1):** supported 124 · not_in_source 97 · contradicted 76 · weak 74 · insufficient_evidence 29

## Your checklist

1. ~~**Label QA**~~ — done
2. **Baseline eval** — LM Studio + `.\scripts\run_baseline_eval.ps1`
3. **Vast train** — [PHASE2_TRAINING_GUIDE.md § Step 5–8](./PHASE2_TRAINING_GUIDE.md#step-5--rent-vast-instance)
4. **Tuned eval** — [EVAL_GONOGO.md](./EVAL_GONOGO.md)
5. **HF publish** — [HF_PUBLISH.md](./HF_PUBLISH.md)
