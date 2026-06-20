# Paper corpus pipeline (Phase 1.5)

PC-only workflow: merge JSON exports, backfill abstracts, feed Phase 2 `l3_grounding` training.

No GPU required.

---

## Prerequisites

```powershell
cd training
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-corpus.txt
```

Optional environment variables:

| Variable | Purpose |
|----------|---------|
| `OPENALEX_MAILTO` | Polite pool email for OpenAlex API |
| `S2_API_KEY` | Semantic Scholar API key (optional backfill) |

---

## Step 1 — Ingest JSON exports

Drop files matching `data/*_papers_*.json`, then:

```powershell
python scripts/build_paper_corpus.py
```

**Outputs:**

- `data/paper_corpus.jsonl`
- `data/paper_corpus_stats.json`

---

## Step 2 — Backfill missing abstracts

```powershell
python scripts/enrich_corpus_abstracts.py --mailto your@email.com
```

Resumable cache: `training/cache/api/`. Manifest: `training/cache/enrich_manifest.jsonl`.

**Outputs:**

- `data/paper_corpus_enriched.jsonl`
- `data/paper_corpus_enriched_stats.json`

Test with a small batch:

```powershell
python scripts/enrich_corpus_abstracts.py --limit 50
```

---

## Step 3 — Add more JSON later

1. Add new `*_papers_*.json` under `data/`
2. Re-run Step 1 and Step 2 (cache avoids redundant API calls)

---

## Exit criteria (Phase 1.5)

- `paper_corpus_enriched.jsonl` exists
- Stats show ≥ 2,000 papers with abstract ≥ 120 characters

---

## Not in this sprint

OA PDF/HTML download (`fetch_oa_fulltext.py`) — deferred until `source_pdf_extract` (Phase 3b). See [ROADMAP.md](./ROADMAP.md).

---

## Phase 2 next

```powershell
python scripts/generate_l3_from_corpus.py --target-rows 400 --export-review data/l3_review_queue.csv
python scripts/validate_dataset.py data/l3_grounding_train.jsonl
```

See [archive/PHASE2_7_V1_4_WALKTHROUGH.md](./archive/PHASE2_7_V1_4_WALKTHROUGH.md) for QLoRA on Vast.
