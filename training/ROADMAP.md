# Nassila training roadmap — Ouroboros

**North star:** one local model identity (**Ouroboros**) for all Nassila AI tasks, forged **one worker at a time**. **Agent brief:** [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md). Vision: [`docs/OUROBOROS.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS.md).

**Current arc (Sanad):** E4B **v1.12** + 12B **v1.14** ship on HF. **v1.13 NO-GO**; v1.14 fixes h-045/h-088 while preserving Tier 2. See [`POST_V114_MAP.md`](./POST_V114_MAP.md).

---

## Ouroboros phases (product + training)

| Phase | Worker | Task id(s) | Artifact | Base model |
|-------|--------|------------|----------|------------|
| **0** | Baseline eval | `l3_grounding` | Stock Gemma 4 E4B Q6_K | E4B |
| **0.5** | App guardrails | — | JSON repair, retry, caps | — (app code) |
| **1** | Cloud QLoRA setup | `l3_grounding` | Smoke LoRA on Vast | E4B |
| **1.5** | Paper corpus (PC) | — | `paper_corpus_enriched.jsonl` | — |
| **2** | L3 Sanad train/eval | `l3_grounding` | `nassila-sanad-e4b` / `nassila-sanad-12b` | E4B / 12B |
| **2b** | 12B multi_claim loop | `l3_grounding` | v1.14 selected; future refinement optional | 12B |
| **3** | Manuscript ingest | `doc_extract` | Facet or agent merge | E4B → 12B |
| **3b** | Cited PDF text | `source_pdf_extract` | Same | E4B |
| **4** | Tables / figures | `table_figure_grounding` | `nassila-agent-e12b-v1` | 12B multimodal |
| **5** | Webpage AI | `webpage_*`, `issue_explain` | Merge into agent | E4B / 12B |
| **6** | Multi-task merge | All | Single `nassila-agent-*` GGUF | Best fit |

**Not in the Ring:** Crossref/PubMed/OpenAlex, citeproc, predatory lists, Marker (optional GPL ingest only).

---

## Phase 2 — Sanad ship status

| Milestone | Status |
|-----------|--------|
| E4B v1.12 default-tier | **GO** — `nassila-sanad-e4b` |
| 12B v1.12 Tier 2 | **GO** — fallback/reference |
| 12B v1.13 multi_claim boost | **NO-GO** — do not publish |
| 12B v1.14 multi_claim | **GO** — `nassila-sanad-12b` selected |
| Product Sanad UI | Nassila — ready for E4B v1.12 + 12B v1.14 tier plan |
| Tier 3 (full-text) | **Not met** — needs Masdar + harness; see [`PHASE3_TIER3_GROUNDWORK.md`](./PHASE3_TIER3_GROUNDWORK.md) |
| Laptop smoke | **PASS** (2026-06-21, RTX 4060 8 GB) — [`outputs/LAPTOP_SMOKE_SIGNOFF.md`](./outputs/LAPTOP_SMOKE_SIGNOFF.md) |

Historical v1.0–v1.13 walkthroughs: [`archive/`](./archive/).

---

## Phase 1.5 — Paper corpus (in progress)

| Step | Doc / script |
|------|----------------|
| Ingest | [`CORPUS_PIPELINE.md`](./CORPUS_PIPELINE.md), `scripts/build_paper_corpus.py` |
| Abstract backfill | `scripts/enrich_corpus_abstracts.py` |
| Fulltext PDF fetch | **Deferred** — before Phase 3b |

**Exit:** `data/paper_corpus_enriched.jsonl` with ≥2,000 papers abstract ≥120 chars.

---

## Phase 3+ — More workers → Ouroboros merge

Train each task with its JSONL ([`DATASET_SCHEMA.md`](./DATASET_SCHEMA.md)), eval independently, then **multi-task merge** into one GGUF.

| Task | Unblocks in app |
|------|-----------------|
| `doc_extract` | Better PDF/DOCX than pdfjs-only |
| `source_pdf_extract` | Body text for Sanad → Tier 3 |
| `table_figure_grounding` | Figure/table claims |
| `webpage_metadata` / `webpage_classify` | [`docs/WEBPAGE_ROADMAP.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/WEBPAGE_ROADMAP.md) |

**Start Maktab/Masdar planning** after laptop smoke pass; see [`PHASE3_TIER3_GROUNDWORK.md`](./PHASE3_TIER3_GROUNDWORK.md).

---

## App integration status

| Component | Status |
|-----------|--------|
| L3 engine (`grounding-llm.ts`) | Ready |
| Manuscript audit UI | **Not mounted** in shipping app |
| Ouroboros worker shell | Spec in Nassila `docs/DESIGN.md` — not built |
| Task router (multi-task) | **Future** — [`nassila-agent-tasks.ts`](https://github.com/jamalesam93/Nassila/blob/main/src/shared/nassila-agent-tasks.ts) |

---

## Quick links

| Doc | Purpose |
|-----|---------|
| [`POST_V114_MAP.md`](./POST_V114_MAP.md) | **Current operator map** |
| [`LAPTOP_SMOKE_TEST.md`](./LAPTOP_SMOKE_TEST.md) | Local GGUF acceptance |
| [`HF_RELEASE_VERIFY.md`](./HF_RELEASE_VERIFY.md) | Post-smoke release checklist |
| [`PHASE3_TIER3_GROUNDWORK.md`](./PHASE3_TIER3_GROUNDWORK.md) | Maktab/Masdar next |
| [`README.md`](./README.md) | Training pack index |
| [`docs/DUAL_TIER_POLICY.md`](../docs/DUAL_TIER_POLICY.md) | E4B vs 12B gates |
| [`EVAL_GONOGO.md`](./EVAL_GONOGO.md) | GO/NO-GO log |
| [`PHASE2_9_AB_PILOT_WALKTHROUGH.md`](./PHASE2_9_AB_PILOT_WALKTHROUGH.md) | A/B pipeline |
| [`DATASET_SCHEMA.md`](./DATASET_SCHEMA.md) | JSONL per task |
| [`CORPUS_PIPELINE.md`](./CORPUS_PIPELINE.md) | Phase 1.5 corpus |
