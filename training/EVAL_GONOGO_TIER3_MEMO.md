# Tier 3 model vs pipeline go/no-go memo

> **Superseded (2026-08):** the "no S15 train" conclusion below was later reversed — **S15 shipped** on Qwen 3.5 4B (`nassila-sanad-4b`, contrastive v2: 94.48% combined expect, 4.87% false-supported, single-run). This memo remains as the historical record of the S12/S14 pilot. See [`EVAL_GONOGO.md`](./EVAL_GONOGO.md).

**Status:** PARTIAL — support freeze **100%** S12+S14; contrastive false-supported **measured** (S14 near gate, S12 above); product e2e still open  
**Date:** 2026-07-23  
**Operator:** Jamal  
**Checkpoints evaluated:** S12 (E4B) · S14 (12B) on Ollama · support freeze + contrastive draft

## 1. Context

| Item | Value |
|------|-------|
| App version | 1.4.0 (Raqim Statute) — Masdar-lite / loop exist; full Tier 3 product path still building |
| Prompt contract | `sanad-grounding-v1` |
| Body holdout (support) | `data/eval_holdout_body_frozen_v1.jsonl` (**84** rows) |
| Body holdout (contrastive) | `data/eval_holdout_body_contrastive_frozen_v1.jsonl` (**84** rows; from draft via `freeze_body_contrastive_from_draft.py`) |
| Body holdout (scale draft) | `data/eval_holdout_body_scale_draft.jsonl` (**166** = 84 + 82) — S12 **98.8%** · S14 **97.0%** expect/quote (2026-07-24) |
| Body holdout (scale freeze v2) | `data/eval_holdout_body_scale_frozen_v2.jsonl` (**234**) — S12 **99.15%** · S14 **97.86%** expect/quote (2026-07-25) |
| Predictions S12 freeze v2 | `reports/tier3_body_scale_frozen_v2_predictions_s12_ollama.jsonl` |
| Predictions S14 freeze v2 | `reports/tier3_body_scale_frozen_v2_predictions_s14_ollama.jsonl` |
| Batch3 DOI list | `data/source_pdf_extract_batch3_FETCH.md` + `*_dois.txt` / `*_dois.csv` / `*_doi_list.jsonl` |
| Predictions S12 support | `reports/tier3_body_frozen_v1_predictions_s12_ollama.jsonl` |
| Predictions S14 support | `reports/tier3_body_frozen_v1_predictions_s14_ollama.jsonl` |
| Predictions S12 contrastive | `reports/tier3_body_contrastive_predictions_s12_ollama.jsonl` |
| Predictions S14 contrastive | `reports/tier3_body_contrastive_predictions_s14_ollama.jsonl` |
| Field-note boosts | `data/l3_grounding_masdar_lite_boost.jsonl` (49 rows) |
| Real manuscripts re-run | _pending post–1.7_ |

## 2. Retrieval suite (pipeline)

| Signal | Result | Pass? |
|--------|--------|-------|
| OA / attach resolution rate | ~99/100 pilot PDFs filed (row 98 non-OA skipped) | partial |
| `l3Coverage` full-text vs abstract-only | not measured this run (offline PDF draft) | n/a |
| Chunk `pageHint` present when PDF attached | used when set (e.g. NEJM L025 p. 8) | partial |
| Gold passage tokens in top excerpt | soft-hyphen join + masthead filter; quote cmp hardened | strong (for draft freeze) |

**Retrieval verdict:** acceptable for **frozen pilot corpus** — not yet a product retrieval claim.

## 3. Grounding suite (Sanad)

| Metric | Body support S12 | Body support S14 | Contrastive S12 | Contrastive S14 | Gate |
|--------|------------------|------------------|-----------------|-----------------|------|
| Expect / quote (support) | **100%** | **100%** | — | — | ≥90% / ≥98% ✅ |
| JSON parse | **100%** | **100%** | **100%** | **100%** | ≥98% ✅ |
| False supported | n/a (support-only) | n/a | **19.05%** ❌ | **5.95%** (≤5% ❌ / ≤7% E4B ✅) | ≤5% Tier2 |
| Contrastive expect | — | — | 80.95% | **94.05%** | inform |
| Cross-doc slice | — | — | 94.6% | **100%** | inform |

**Notes:** Contrastive draft built via `draft_body_contrastive_from_frozen.py` (claim-salient `%` / `n=` / year mutations, polarity flips, cross-doc excerpt swaps). Weak bare-citation digit flips were dropped after they inflated false-supported without real contradictions. Residual S14 fails are numeric overclaims that still emit a `supported` claim alongside a correct `contradicted`.

**Grounding verdict:** Support freeze remains strong. False-supported is now **measured**: S14 is **near** the ≤5% gate; S12 is clearly above E4B ≤7%. **Still not product GO** — e2e / retrieval + optional contrastive freeze hygiene next; **no S15 train** from this alone.

### Contrastive v2 Holdout Suite (`eval_holdout_body_contrastive_frozen_v2.jsonl` — 308 rows, Vast AI)

| Metric | S12 E4B (Vast `--jinja`) | S12 E4B (Local Ollama) | S14 12B (Vast AI) | Gate / Target |
|--------|--------------------------|------------------------|-------------------|---------------|
| Strict JSON parse | **100.0%** (0 repairs) | 100.0% | **98.70%** (99.68% w/ repair) | ≥98% ✅ |
| Expect checks pass rate | **79.87%** | 74.68% | **95.45%** | ≥90% (S14 ✅, S12 ❌) |
| False supported rate | **20.13%** | 25.32% | **4.22%** | ≤5% Tier2 (S14 ✅, S12 ❌) |
| `contradicted` category pass | **55.00%** | 45.00% | **89.17%** | Inform |
| `not_in_source` category pass | **95.74%** | 93.62% | **99.47%** | Inform |

## 4. End-to-end product suite

| Check | Observation | Pass? |
|-------|-------------|-------|
| Mapping coverage on real MS | not re-run this milestone | |
| Preflight blockers | not re-run | |
| False L3 pass (Phase 0-C) | not re-run | |
| Abstract-only honesty labels | n/a (PDF-body freeze) | |

## 5. Decision matrix

| Outcome | Action |
|---------|--------|
| **Pipeline gap** | Fix chunking/Masdar/Resolve; **no S15/W8 train** |
| **Model gap** | Un-park W8 body-chunk Sanad; optional W9 abstract recovery on S14 |
| **Both gaps** | Pipeline first; re-score before any Vast spend |
| **Neither gap** | Tier 3 product claim candidate; proceed to 1.8 Shahid planning |

## 6. Decision

- [ ] **PARKED** — insufficient for product GO (holdout / manuscripts / post–1.7)
- [x] **NO-GO train (for now)** — support freeze clear; contrastive false-supported measured (S14 near gate, S12 gap); prioritize e2e + scale before Vast S15
- [ ] **GO W8** — body-chunk Sanad on S14 base
- [ ] **GO W9** (optional) — abstract recovery if abstract gap remains

**Signed rationale:** Support freeze is model-ready on this pilot. Contrastive scoring (2026-07-23) shows S14 false-supported **5.95%** (5/84) vs ≤5% Tier-2 gate — close, not clear. S12 at **19%** fails the E4B false-supported bar. Cross-doc mismatches are handled well (especially S14). Do **not** un-park S15; next is post–1.7 manuscript e2e and product-scale freeze, with optional human review of residual numeric contrastive rows.

---

See also [`S15_UNPARK_CRITERIA.md`](./S15_UNPARK_CRITERIA.md), [`TIER3_EVAL_SUITES.md`](./TIER3_EVAL_SUITES.md), Nassila [`docs/Nassila-Ouroboros-Future.md`](../../Nassila/docs/Nassila-Ouroboros-Future.md) §6.
