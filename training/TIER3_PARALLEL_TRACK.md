# Tier 3 parallel track (data only)

**Status:** active parallel · **S15 train:** PARKED  
**Date:** 2026-07-27

**Eval runtime (standing, 2026-07-27):** Tier 3 **body evaluation batches run on Vast** (RTX 4090) for speed — llama.cpp + HF GGUF, WSL SSH. Laptop drafts/freezes; do not burn laptop hours on full S14 body batches. Runbook: [`S14_CONTRASTIVE_VAST.md`](./S14_CONTRASTIVE_VAST.md). Agent rule: `.cursor/rules/vast-body-eval.mdc`.

Work that may proceed without *training* GPU spend (eval on Vast is expected):

1. Human-label `field-notes/masdar-lite-jul13-*` into boost JSONL (expected verdicts) — **done** (49/49 boost export).
2. Keep production prompt contract `sanad-grounding-v1` locked; re-eval complete — see [`PROMPT_CONTRACT_REEVAL.md`](./PROMPT_CONTRACT_REEVAL.md).
3. Pilot `fetch_oa_fulltext.py` (~100 DOIs) — **done:** `data/source_pdf_extract_pilot.jsonl` (2026-07-21). Operator PDFs under `cache/oa_fulltext/pdfs/` (~99 filed; row 98 skipped non-OA). **Batch2:** `source_pdf_extract_batch2.jsonl` — **99** PDFs filed (1 SciELO DOI dropped).
4. Lock `doc_extract` / `source_pdf_extract` schemas after OA pilot — schemas v1 in [`DATASET_SCHEMA.md`](./DATASET_SCHEMA.md).
5. Draft body holdout — **advanced past abstract proxy:**
   - Frozen pilot: [`data/eval_holdout_body_pilot.jsonl`](./data/eval_holdout_body_pilot.jsonl) (5 rows).
   - Support freeze: [`data/eval_holdout_body_frozen_v1.jsonl`](./data/eval_holdout_body_frozen_v1.jsonl) (84) — S12+S14 **100%** parse/expect/quote (2026-07-23).
   - Contrastive freeze: [`data/eval_holdout_body_contrastive_frozen_v1.jsonl`](./data/eval_holdout_body_contrastive_frozen_v1.jsonl) (84) — false-supported S12 **19.05%** · S14 **5.95%**.
   - Scale draft: [`data/eval_holdout_body_scale_draft.jsonl`](./data/eval_holdout_body_scale_draft.jsonl) (**166**) — S12 **98.8%** · S14 **97.0%** expect/quote (2026-07-24).
   - **Scale support freeze:** [`data/eval_holdout_body_scale_frozen_v1.jsonl`](./data/eval_holdout_body_scale_frozen_v1.jsonl) (**159**). Re-scored 2026-07-24: S12+S14 expect/quote **98.74%**.
   - **Scale freeze v2:** [`eval_holdout_body_scale_frozen_v2.jsonl`](./data/eval_holdout_body_scale_frozen_v2.jsonl) (**234**) — re-scored S12 **99.15%** · S14 **97.86%**. **Freeze v3 postponed** until after batch4.
   - **Scale freeze v4:** [`eval_holdout_body_scale_frozen_v4.jsonl`](./data/eval_holdout_body_scale_frozen_v4.jsonl) (**308**) — S12 **99.68%** · S14 **99.35%** expect/quote.
   - **Scale freeze v5:** [`eval_holdout_body_scale_frozen_v5.jsonl`](./data/eval_holdout_body_scale_frozen_v5.jsonl) (**408**) — sliced scores: [`reports/tier3_body_product_holdout_summary.json`](./reports/tier3_body_product_holdout_summary.json).
   - **Multiclaim slice:** [`eval_holdout_body_multiclaim_frozen_v1.jsonl`](./data/eval_holdout_body_multiclaim_frozen_v1.jsonl) (**100**).
   - **Contrastive v2:** [`eval_holdout_body_contrastive_frozen_v2.jsonl`](./data/eval_holdout_body_contrastive_frozen_v2.jsonl) (**308** from v4) — S12 false-supported **25.32%** (worse than v1 **19.05%** at scale); **S14 on Vast** (instance `46030207`, log `outputs/s14_contrastive_run.log`).
   - **PDF-body draft:** [`scripts/draft_body_holdout_from_pdfs.py`](./scripts/draft_body_holdout_from_pdfs.py) (DOI-strict PDF resolve for batch2+).
6. Go/no-go memo: [`EVAL_GONOGO_TIER3_MEMO.md`](./EVAL_GONOGO_TIER3_MEMO.md) — support clear; contrastive near on S14; e2e still open — **NO-GO train**.
7. Qualify Arabic grounding as **unvalidated** until a native AR slice exists — do not claim AR Sanad metrics.

**Do not:** start S15 / M01 / Md01 trains until go/no-go preserves h-045/h-088 and product-scale body holdout (or explicit model-gap decision).

See Nassila `docs/Nassila-Ouroboros-Future.md` §6 and app Phase 0–1.4.0 train.
