# Nassila training roadmap — Ouroboros

**North star:** one local model identity (**Ouroboros**) for all Nassila AI tasks, forged **one worker at a time**. **Agent brief:** [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md). Vision: [`docs/OUROBOROS.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS.md).

**Live operator map (checklist, ship status, next actions):** [`OUROBOROS_OPERATOR_MAP.md`](./OUROBOROS_OPERATOR_MAP.md) — prefer that file for day-to-day truth. This roadmap is the **long-horizon phase table** only.

**Status (2026-08):** Sanad **S15** (`Qwen/Qwen3.5-4B`) + **12B S14** (`nassila-sanad-12b`) on HF; laptop smoke + HF verify **PASS**. Nassila desktop **v1.5.0** (Raqim Web, Tier A Rust WASM engine, Wayback archive, metadata resolver).

---

## Ouroboros phases (product + training)

| Phase | Worker | Task id(s) | Artifact | Base model | Status |
|-------|--------|------------|----------|------------|--------|
| **0** | Baseline eval | `l3_grounding` | Stock Gemma 4 E4B Q6_K | E4B | Done |
| **0.5** | App guardrails | — | JSON repair, retry, caps | — (app code) | Shipped in Nassila |
| **1** | Cloud QLoRA setup | `l3_grounding` | Smoke LoRA on Vast | E4B | Done |
| **1.5** | Paper corpus (PC) | — | `paper_corpus_enriched.jsonl` | — | In progress |
| **2** | L3 Sanad train/eval | `l3_grounding` | `nassila-sanad-4b` (S15) / `nassila-sanad-12b` (S14) | Qwen3.5 4B / 12B | **Shipped** (S15 / S14) |
| **2b** | 12B multi_claim loop | `l3_grounding` | S14 12B selected; S15 default tier live | Qwen3.5 4B / 12B | S15 **GO**; S14 **GO**; v1.13 **NO-GO** |
| **3** | Manuscript ingest (**Maktab**) | `doc_extract` | `@firecrawl/pdf-inspector-wasm` + WASM extract | Rust WASM | **Shipped** (v1.5.0) |
| **3b** | Cited PDF text (**Masdar**) | `source_pdf_extract` | Same | E4B / Qwen | **P1** — Tier 3; corpus in progress |
| **4** | Tables / figures (**Shahid**) | `table_figure_grounding` | `nassila-agent-e12b-v1` | 12B multimodal | Future (Tier 3+) |
| **5** | Webpage AI | `webpage_*`, `issue_explain` | Metadata resolver + host extractors | Deterministic + LLM | **Shipped** (v1.5.0) |
| **6** | Multi-task merge | All | Single `nassila-agent-*` GGUF | Best fit | Research track |

**Deterministic (not trained):** Crossref / PubMed / OpenAlex L1+L2, citeproc, predatory lists, webpage metadata resolver, WASM PDF extract.

---

## Phase 2 — Sanad (complete)

| Milestone | Status |
|-----------|--------|
| Qwen3.5 4B S15 default-tier | **GO** — [`nassila-sanad-4b`](https://huggingface.co/QinEmPeRoR93/nassila-sanad-4b) (94.48% combined, 100% quote) |
| 12B S14 Tier 2 | **GO** — [`nassila-sanad-12b`](https://huggingface.co/QinEmPeRoR93/nassila-sanad-12b) (h-045 / h-088 fix) |
| 12B v1.13 multi_claim boost | **NO-GO** — do not publish |
| Laptop smoke + HF verify | **PASS** — [`outputs/LAPTOP_SMOKE_SIGNOFF.md`](./outputs/LAPTOP_SMOKE_SIGNOFF.md) |
| Nassila Sanad product UX | **Shipped** — Passage grounding, Set up Sanad, tier chips, loop Sanad bar |
| Nassila app release | **v1.5.0** — [release notes](https://github.com/jamalesam93/Nassila/blob/main/CHANGELOG.md) |
| Tier 3 (full-text Sanad) | **Not met** (product) — PDF-body **draft** scored S14 Ollama 2026-07-22: 84 rows, parse 98.8%, expect/quote 96.4%; freeze + quote ≥98% + e2e still open — [`EVAL_GONOGO_TIER3_MEMO.md`](./EVAL_GONOGO_TIER3_MEMO.md) |
| v1.15+ refinement | **Parked** until Tier 3 corpus / go-no-go |

Historical v1.0–v1.13 walkthroughs: [`archive/`](./archive/).

---

## Phase 1.5 — Paper corpus (in progress)

| Step | Doc / script |
|------|----------------|
| Ingest | [`CORPUS_PIPELINE.md`](./CORPUS_PIPELINE.md), `scripts/build_paper_corpus.py` |
| Abstract backfill | `scripts/enrich_corpus_abstracts.py` |
| Fulltext PDF fetch | **In progress** — OA pilot + `cache/oa_fulltext/pdfs/`; body draft via `draft_body_holdout_from_pdfs.py` |

**Exit:** `data/paper_corpus_enriched.jsonl` with ≥2,000 papers, abstract ≥120 chars.

---

## Phase 3+ — Maktab / Masdar → Ouroboros merge

**Current focus (P1):** loop-fed **Maktab** (manuscript structure ingest) and **Masdar** (cited-source excerpts for Sanad). Train each task with JSONL ([`DATASET_SCHEMA.md`](./DATASET_SCHEMA.md)), eval independently, then multi-task merge when ready.

| Task | Unblocks in app |
|------|-----------------|
| `doc_extract` (**Maktab**) | Richer structure than pdf.js-only; loop-fed, not a peer worker tab |
| `source_pdf_extract` (**Masdar**) | Full-text chunks for Sanad → Tier 3 |
| `table_figure_grounding` (**Shahid**) | Figure/table claims |
| `webpage_metadata` / `webpage_classify` | [`docs/WEBPAGE_ROADMAP.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/WEBPAGE_ROADMAP.md) |

Planning: [`PHASE3_TIER3_GROUNDWORK.md`](./PHASE3_TIER3_GROUNDWORK.md). **Institutional paywall access** (proxy / login session) is a separate Tier 3 product track — not Unpaywall email.

---

## Nassila app integration (summary)

Aligned with [`OUROBOROS_OPERATOR_MAP.md`](./OUROBOROS_OPERATOR_MAP.md) § C–D. Detail and checkboxes live there.

| Component | Status |
|-----------|--------|
| **Manuscript loop** (upload → sources → audit → export) | **Shipped** — primary surface |
| **Bibliography** (Raqim: import, verify, export) | **Shipped** — v1.1.2 PDF import + verify IPC |
| **Sanad L3** (`grounding-llm.ts` + local LLM) | **Shipped** — optional; HF GGUF via LM Studio / Ollama / vLLM |
| **Bibliography bridge** | **Shipped** — send refs to Raqim; audit from library |
| **Maktab / Masdar / Shahid** | Stubs → honest pipeline gaps; not fake worker apps |
| **Multi-task router** | **Future** — [`nassila-agent-tasks.ts`](https://github.com/jamalesam93/Nassila/blob/main/src/shared/nassila-agent-tasks.ts) |
| **In-app Help** (HF, Ollama, privacy) | **P2** — deferred |

---

## Suggested next actions

1. **Product (P1):** Maktab / Masdar stubs → loop-fed ingest and cited-PDF excerpts.
2. **Product (Tier 3):** Institutional full-text access design (SEC-06 review).
3. **Docs (P2):** In-app Help when loop IA stable.
4. **Training (P2):** Park **v1.15** until Tier 3 corpus; continue Phase 1.5 corpus in parallel.

---

## Quick links

| Doc | Purpose |
|-----|---------|
| [`OUROBOROS_OPERATOR_MAP.md`](./OUROBOROS_OPERATOR_MAP.md) | **Current operator map** (done vs left) |
| [`LAPTOP_SMOKE_TEST.md`](./LAPTOP_SMOKE_TEST.md) | Local GGUF acceptance |
| [`HF_RELEASE_VERIFY.md`](./HF_RELEASE_VERIFY.md) | Post-smoke release checklist |
| [`PHASE3_TIER3_GROUNDWORK.md`](./PHASE3_TIER3_GROUNDWORK.md) | Maktab/Masdar next |
| [`README.md`](./README.md) | Training pack index |
| [`docs/DUAL_TIER_POLICY.md`](../docs/DUAL_TIER_POLICY.md) | E4B vs 12B gates |
| [`EVAL_GONOGO.md`](./EVAL_GONOGO.md) | GO/NO-GO log |
| [`DATASET_SCHEMA.md`](./DATASET_SCHEMA.md) | JSONL per task |
| [`CORPUS_PIPELINE.md`](./CORPUS_PIPELINE.md) | Phase 1.5 corpus |
