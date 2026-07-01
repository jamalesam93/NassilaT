# Phase 3 — Tier 3 groundwork (Maktab / Masdar)

Planning doc for full-text Sanad after E4B v1.12 + 12B v1.14 ship and laptop smoke pass.

**Operator map:** [`OUROBOROS_OPERATOR_MAP.md`](./OUROBOROS_OPERATOR_MAP.md) · **Corpus:** [`CORPUS_PIPELINE.md`](./CORPUS_PIPELINE.md) · **Schema:** [`DATASET_SCHEMA.md`](./DATASET_SCHEMA.md)

---

## Goal

Move Sanad from **abstract-only** excerpts (Tier 2) to **body-text** grounding (Tier 3):

1. **Maktab** (`doc_extract`) — manuscript PDF/DOCX → structured plain text.
2. **Masdar** (`source_pdf_extract`) — cited OA PDF → excerpt suitable for L3.
3. Re-train or continue Sanad on body-chunk excerpts with a Tier 3 eval harness.

Tier 3 product ship (Nassila `OUROBOROS_CONTEXT.md` §10) requires Tier 2 **plus** Masdar in the app loop **plus** full-text eval passing quote + expect gates.

---

## Phase 1.5 corpus status

| Criterion | Target | Current (`paper_corpus_enriched_stats.json`) |
|-----------|--------|---------------------------------------------|
| Enriched corpus exists | yes | yes |
| Papers with abstract ≥120 chars | ≥2,000 | **4,233** |

**Exit met** for abstract-backed training. Full-text PDF fetch remains **deferred** until `source_pdf_extract` (see [`CORPUS_PIPELINE.md`](./CORPUS_PIPELINE.md)).

---

## Workstreams

### A. `doc_extract` (Maktab)

| Step | Deliverable |
|------|-------------|
| 1 | Finalize JSONL schema in [`DATASET_SCHEMA.md`](./DATASET_SCHEMA.md) (`sections[]`, `warnings[]`) |
| 2 | Collect 50–100 manuscript PDF/DOCX → gold plain text (manual or Marker-assisted, not in product path) |
| 3 | Eval harness: section coverage, no catastrophic truncation |
| 4 | QLoRA smoke on E4B; defer 12B until abstract Sanad stable |

**App hook:** [`Nassila src/engine/manuscript/pdf-extract.ts`](https://github.com/jamalesam93/Nassila/blob/main/src/engine/manuscript/pdf-extract.ts)

### B. `source_pdf_extract` (Masdar)

| Step | Deliverable |
|------|-------------|
| 1 | Implement `fetch_oa_fulltext.py` (deferred in corpus pipeline) for OA PDF/HTML |
| 2 | Finalize `source_pdf_extract` schema (`excerpt`, `page_hint`) |
| 3 | Link corpus DOIs → OA full text; chunk to ≤4200 char excerpts |
| 4 | Eval: excerpt is verbatim substring of source PDF text |

**Unblocks:** Sanad Tier 3 train rows with `meta.label` = full text, not abstract-only.

### C. Tier 3 Sanad eval harness

| Step | Deliverable |
|------|-------------|
| 1 | Build `eval_holdout_body_*.jsonl` (new holdout; do not contaminate train) |
| 2 | Same gates as Tier 2 on body-chunk slice: quote validity ≥98%, false-supported ≤5% |
| 3 | Include methods-only / results-only edge cases from v1.14 lessons |

### D. Product integration (Nassila)

| Step | Deliverable |
|------|-------------|
| 1 | Ouroboros worker shell — Sanad + Maktab + Masdar nav ([`docs/DESIGN.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/DESIGN.md)) |
| 2 | Pipeline: Maktab ingest → Masdar fetch → Sanad ground |
| 3 | Honest UI copy: Tier 2 = abstracts today; Tier 3 = full text when harness passes |

---

## Suggested order

```mermaid
flowchart LR
  smoke[Laptop smoke E4B+12B] --> corpus[Corpus exit met]
  corpus --> schema[doc_extract + source_pdf_extract schema]
  schema --> masdarData[OA fulltext fetch pilot]
  masdarData --> tier3eval[Tier 3 eval JSONL]
  tier3eval --> train[Sanad body-chunk train]
  train --> product[Maktab/Masdar UI in Nassila]
```

1. Complete laptop smoke + HF verify (Phase 2 close-out).
2. Lock `doc_extract` / `source_pdf_extract` schemas.
3. Pilot OA full-text fetch on 100 corpus DOIs.
4. Draft Tier 3 holdout (30–50 rows).
5. First Maktab QLoRA smoke (E4B).
6. Masdar + Sanad body train only after eval harness exists.

---

## Out of scope (this phase)

- 12B v1.15 combined-score recovery (optional; see [`OUROBOROS_OPERATOR_MAP.md`](./OUROBOROS_OPERATOR_MAP.md))
- Multimodal Shahid (`table_figure_grounding`)

---

## Related

- [`ROADMAP.md`](./ROADMAP.md) — Ouroboros phase table
- Nassila [`docs/PRODUCT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/PRODUCT.md) — UI reform
