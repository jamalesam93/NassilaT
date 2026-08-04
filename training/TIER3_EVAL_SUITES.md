# Tier 3 evaluation suites

Tier 3 requires **three independent suites** — do not conflate retrieval errors with Sanad model errors.

## 1. Retrieval evaluation

**Question:** Was the correct source found? Did top-k chunks contain the needed evidence?

| Signal | Where measured |
|--------|----------------|
| OA / Europe PMC / attach resolution | App `resolveL3Source` + `l3Coverage` |
| Excerpt contains gold passage tokens | NassilaT body holdout metadata |
| Locator (`page_hint`) | App `sourcePageHint` + Masdar chunking |

**Artifacts:** field notes (`masdar_lite`), future `retrieval_eval_*.jsonl`.

## 2. Grounding evaluation (Sanad)

**Question:** Given a **gold excerpt**, did Sanad produce correct claims, verdicts, and quotes?

| Harness | Rows | Gates |
|---------|------|-------|
| Abstract (Tier 2) | `eval_holdout_90.jsonl` + legacy | `tier_gates.evaluate_tier2_gates` |
| Body (Tier 3) support freeze | `eval_holdout_body_frozen_v1.jsonl` (84) | parse / expect / quote |
| Body (Tier 3) scale freeze | `eval_holdout_body_scale_frozen_v5.jsonl` (408) | **Sliced report** — support from v4 (S12 **99.68%** · S14 **99.35%**); multiclaim S12 **85%** · S14 **89%** (`reports/tier3_body_product_holdout_summary.json`) |
| Body (Tier 3) scale freeze (v4 support) | `eval_holdout_body_scale_frozen_v4.jsonl` (308) | canonical support scores — do not re-run |
| Body (Tier 3) multiclaim slice | `eval_holdout_body_multiclaim_frozen_v1.jsonl` (100) | `min_claims: 2`; scored (see product summary) |
| Body (Tier 3) contrastive freeze | `eval_holdout_body_contrastive_frozen_v2.jsonl` (308; v4 parents) | S12 false-supported **25.32%** (expect **74.68%**); S14 pending |
| Body (Tier 3) contrastive freeze (v1) | `eval_holdout_body_contrastive_frozen_v1.jsonl` (84) | legacy pilot; S12 **19.05%** · S14 **5.95%** false-supported |
| Body (Tier 3) PDF draft | `eval_holdout_body_pdf_draft_skip98.jsonl` | pre-freeze |

**Latest Ollama:** support v4 S12 **99.68%** · S14 **99.35%**. Multiclaim S12 **85%** · S14 **89%**. Contrastive v2 S12 false-supported **25.32%** (v1 was **19.05%**); S14 pending.

**Claim-density path:** v5 bundle (408 / floor **508**) — report via `summarize_body_product_holdout.py` (no support re-score). Contrastive **v2** (308) from v4 parents replaces v1 for scale false-supported.

**Rules:** frozen holdout for ship claims; `quotes_must_be_substrings`; Arabic reported separately (**unvalidated** until native AR slice).

## 3. End-to-end product evaluation

**Question:** Mapping → Raqim → Masdar → Sanad → UI/report — does the loop behave honestly?

| Check | App surface |
|-------|-------------|
| Mapping coverage | Sharh-lite + preflight (1.7) |
| No false L3 pass | Engine Phase 0-C invariant |
| Abstract-only honesty | Coverage labels in findings |
| Prompt contract version | Audit export metadata |

**Artifacts:** packaged smoke, real-manuscript reruns, optional diagnostic bundle export.

## Pilot → product scale

| Stage | Docs | Claims | Purpose |
|-------|------|--------|---------|
| Pilot | 30 | ~150 | Tier 3 train smoke / gate stub |
| Product | ≥100 | 400–500 | Tier 3 product claim |

See [`S15_UNPARK_CRITERIA.md`](./S15_UNPARK_CRITERIA.md) and Nassila [`docs/Nassila-Ouroboros-Future.md`](../../Nassila/docs/Nassila-Ouroboros-Future.md) §6.
