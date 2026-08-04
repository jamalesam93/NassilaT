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

## Not in this sprint (completed W4 pilot script)

OA PDF/HTML download pilot: [`scripts/fetch_oa_fulltext.py`](./scripts/fetch_oa_fulltext.py) — resolves OA URLs via Unpaywall, **probes** candidates for real PDF bytes, and records honest `fetch_status` + `meta.access_tier`. Excerpt text still requires app/Masdar PDF extract before training.

```powershell
python scripts/fetch_oa_fulltext.py --limit 100 --mailto you@example.com
python scripts/fetch_oa_fulltext.py --limit 100 --skip-existing --out data/source_pdf_extract_batch2.jsonl --mailto you@example.com
python scripts/fetch_oa_fulltext.py --reprobe-pilot --mailto you@example.com
```

Use `--no-probe` only for legacy URL-only rows. Operator-filed PDFs (training corpus): [`scripts/file_operator_pdf.py`](./scripts/file_operator_pdf.py) — place files under `cache/oa_fulltext/pdfs/` and run with `--grey` when sourced outside Unpaywall/OA product paths.

Outputs:

- `data/source_pdf_extract_pilot.jsonl`
- `cache/oa_fulltext/manifest.jsonl` (one row per DOI; rewritten each run — safe to re-run)
- `cache/oa_fulltext/url_overrides.json` — operator corrections when Unpaywall points at the wrong work

URL selection rejects **untrusted repository** hits that do not embed the DOI (avoids mismatched full text). Trusted mirrors (PMC, arXiv, …) and publisher URLs are kept. Overrides always win.

```powershell
python scripts/fetch_oa_fulltext.py --apply-overrides
python scripts/fetch_oa_fulltext.py --reprobe-pilot --mailto you@example.com
python scripts/fetch_oa_fulltext.py --dedupe-manifest
python scripts/audit_oa_urls.py
python scripts/download_oa_pdfs.py --from-line 51 --to-line 100 --skip-existing
python scripts/file_operator_pdf.py --scan-dir cache/oa_fulltext/pdfs --grey
```

Audit output: `cache/oa_fulltext/url_audit.jsonl` (high-risk hosts / no-DOI repos / doi.org-only landings).

PDF download output: `cache/oa_fulltext/pdfs/` + `pdf_download_log.jsonl`. Rows that need a browser/login go in `pdf_manual_needed.jsonl`.

### W6 — Body holdout draft (Tier 3 eval)

1. **Frozen pilot** (hand-authored): `data/eval_holdout_body_pilot.jsonl` (5 rows; incl. 1 AR unvalidated).
2. **Draft from OA + abstracts** (legacy proxy path):

```powershell
python scripts/draft_body_holdout_from_oa.py --limit 100
```

Writes `data/eval_holdout_body_draft.jsonl` — abstract proxies. Prefer the PDF-body path below when filed PDFs exist.

3. **Draft from filed PDFs** (preferred — real body excerpts):

```powershell
# Optional: exclude non-OA rows (e.g. line 98)
python scripts/draft_body_holdout_from_pdfs.py --oa data/source_pdf_extract_pilot_skip98.jsonl --limit 1000 --out data/eval_holdout_body_pdf_draft_skip98.jsonl
```

Rejects CID/TOC/reference-heavy pages; uses `page_hint` when set. **Do not** mix boost JSONL into holdout.

4. **Validate + score (Ollama S14 example, 2026-07-22):**

```powershell
python scripts/validate_dataset.py data/eval_holdout_body_pdf_draft_skip98.jsonl
python scripts/run_l3_eval_batch.py --base-url http://localhost:11434 --api-key ollama --model nassila-sanad-12b:latest --data data/eval_holdout_body_pdf_draft_skip98.jsonl --repair --retry 1 --timeout 300 --out reports/tier3_body_pdf_predictions_s14_ollama.jsonl
python scripts/run_eval_reports.py --predictions reports/tier3_body_pdf_predictions_s14_ollama.jsonl --holdout data/eval_holdout_body_pdf_draft_skip98.jsonl --repair
```

**Milestone (draft, not product GO):** 84 PDF-body rows · parse **98.8%** · expect/quote **96.4%** on S14 via Ollama. Quote bar still short of Tier 2 quality gate (≥98%). See [`EVAL_GONOGO_TIER3_MEMO.md`](./EVAL_GONOGO_TIER3_MEMO.md).

Product gate (later): ≥100 docs / 400–500 claims with **reviewed** body excerpts — see [`TIER3_EVAL_SUITES.md`](./TIER3_EVAL_SUITES.md).

**Scale progress (2026-07-26):** Freeze v4 **308** (10 dropped from v3). **S12** re-score: expect/quote **99.68%** (1 residual fail). S14 on v4 not run.
See [ROADMAP.md](./ROADMAP.md) Phase 3b.

---

## Phase 2 next

```powershell
python scripts/generate_l3_from_corpus.py --target-rows 400 --export-review data/l3_review_queue.csv
python scripts/validate_dataset.py data/l3_grounding_train.jsonl
```

See [archive/PHASE2_7_V1_4_WALKTHROUGH.md](./archive/PHASE2_7_V1_4_WALKTHROUGH.md) for QLoRA on Vast.
