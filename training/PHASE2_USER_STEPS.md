# Phase 2 — your next steps

**Full walkthrough:** [PHASE2_TRAINING_GUIDE.md](./PHASE2_TRAINING_GUIDE.md)

## Current repo state

- [x] `data/paper_corpus_enriched.jsonl` — **4,233** papers with abstract ≥ 120 chars
- [x] **v1** train (400 rows) — trained, GGUF on HF; eval **NO-GO**
- [x] **v1.1** (700 rows) — Vast train/eval **NO-GO** (66% expect, 9.1% quote validity)
- [x] **Ouroboros** docs + worker **Sanad** (`l3_grounding`) — see [OUROBOROS.md](./OUROBOROS.md)
- [ ] **v1.2** (850 rows, seed 44) — dataset + eval alignment in repo; **your Vast train next**

**v1.1 failure (root cause):** verdict calibration + train/eval shape mismatch (full abstract + neutral openers vs holdout sentence excerpts; user-only eval vs system+user train).

## Your checklist

### v1.2 — Phase 2.3–2.4 (next)

**Plan:** [PHASE2_3_V1_2_PLAN.md](./PHASE2_3_V1_2_PLAN.md)  
**Walkthrough:** [PHASE2_4_V1_2_WALKTHROUGH.md](./PHASE2_4_V1_2_WALKTHROUGH.md)

1. **PC baseline** — stock E4B with `--chat-template` → `reports/baseline_v1_2_chat_report.json`
2. **Vast train** — `outputs/nassila-grounding-e4b-v1.2` (3 epochs)
3. **Eval on Vast** — `run_l3_eval_batch.py --chat-template` before any GGUF download
4. **GO** → download GGUF · LM Studio · fill [MODEL_CARD_v1_2.md](./MODEL_CARD_v1_2.md)

### Done (reference)

| Version | Rows | Verdict |
|---------|------|---------|
| v1 | 400 | NO-GO |
| v1.1 | 700 | NO-GO — [PHASE2_2_V1_1_WALKTHROUGH.md](./PHASE2_2_V1_1_WALKTHROUGH.md) |
