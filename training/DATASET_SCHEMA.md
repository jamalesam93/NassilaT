# Dataset Schema

All training files use **JSONL** (one JSON object per line). Each record must include a `task` field. See [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md) for the seven workers.

Task ids are defined in [`src/shared/nassila-agent-tasks.ts`](../src/shared/nassila-agent-tasks.ts).

---

## Task registry

| Task id | Phase | Schema section below | Training status |
|---------|-------|----------------------|-----------------|
| `l3_grounding` | 1 | Yes | **Active** — v1 ship target |
| `doc_extract` | 2+ | **Locked (v1)** | Planned — manuscript PDF/DOCX → text |
| `source_pdf_extract` | 2+ | **Locked (v1)** | Planned — cited OA PDF → text |
| `table_figure_grounding` | 3+ | Stub | Planned — multimodal |
| `webpage_metadata` | 2+ | Yes | Planned |
| `webpage_classify` | 2+ | Yes | Planned |
| `issue_explain` | 2+ | Yes | Planned |

**v1 JSONL:** only `l3_grounding` rows are required for `nassila-grounding-e4b-v1`. Other tasks use the same `task` + `id` conventions; expand schemas when you start collecting data.

---

## Shared fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Stable unique id, e.g. `l3-001` |
| `task` | string | yes | One of the task ids in the registry table |
| `version` | number | no | Schema version; use `1` |

---

## Task: `l3_grounding`

Matches Nassila L3 / [`buildGroundingUserPrompt`](../src/engine/manuscript/grounding-llm.ts).

### Input fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `passage` | string | yes | Manuscript text around the citation |
| `source_excerpt` | string | yes | Verbatim excerpt from cited work (≤ ~4200 chars in app) |
| `meta` | object | yes | `{ "label": string, "url"?: string }` |

### Output object (`output`) — optional

Each `l3_grounding` row needs **either** an `output` (gold reference) **or** an `expect` block (machine checks). Eval-only files can ship just `expect`. When `output` is present it must match parser expectations in [`parseGroundingJson`](../src/engine/manuscript/grounding-llm.ts).

```json
{
  "claims": [
    {
      "claim": "Mortality increased by about 30%",
      "verdict": "supported",
      "hasNumericClaim": true,
      "sourceQuotes": ["mortality increased by approximately 30%"],
      "rationale": ["Numeric claim matches excerpt wording"]
    }
  ],
  "overallVerdict": "support",
  "overallRationale": ["All atomic claims are supported by the excerpt"]
}
```

### Claim verdict enum

Allowed values for `claims[].verdict`:

- `supported` — excerpt clearly supports; **must** include 1–3 `sourceQuotes` copied verbatim from `source_excerpt`
- `weak` — partial/vague alignment
- `not_in_source` — not found in excerpt (excerpt may be incomplete)
- `contradicted` — excerpt conflicts with claim
- `insufficient_evidence` — cannot determine from excerpt

### Overall verdict enum

Optional `output.overallVerdict`:

- `support`
- `weak`
- `unrelated`
- `insufficient_evidence`

### Validation rules

1. `sourceQuotes` for `supported` claims must be **substrings** of `source_excerpt` (case-sensitive match on normalized whitespace optional in validator).
2. At least one claim when verdict is not purely `insufficient_evidence`.
3. No markdown code fences in stored assistant target text.
4. Prefer conservative labels: when unsure, use `weak` or `not_in_source`, not `supported`.

### Full example record

```json
{
  "id": "l3-001",
  "task": "l3_grounding",
  "version": 1,
  "passage": "Several trials reported higher mortality in the treatment arm (Chen et al., 2021).",
  "source_excerpt": "Across three RCTs, mortality in the treatment group was higher by approximately 30% compared with placebo.",
  "meta": { "label": "full text oa europe pmc", "url": "https://example.org/paper/123" },
  "output": {
    "claims": [
      {
        "claim": "Higher mortality in the treatment arm",
        "verdict": "supported",
        "sourceQuotes": ["mortality in the treatment group was higher"],
        "hasNumericClaim": false
      },
      {
        "claim": "Mortality higher by approximately 30%",
        "verdict": "supported",
        "sourceQuotes": ["higher by approximately 30% compared with placebo"],
        "hasNumericClaim": true
      }
    ],
    "overallVerdict": "support"
  }
}
```

---

## Task: `doc_extract` (Tier 3 — schema v1)

Manuscript ingest: PDF or DOCX → structured plain text for downstream L3. **Not** a replacement for Marker or layout engines; complements pdfjs/mammoth.

**Planning:** [`PHASE3_TIER3_GROUNDWORK.md`](./PHASE3_TIER3_GROUNDWORK.md) (NassilaT).

### Input fields (v1)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document_kind` | string | yes | `pdf` \| `docx` |
| `source_path` | string | no | Original path (not embedded in JSONL for privacy) |
| `raw_text` | string | yes | Full extracted plain text |
| `page_boundaries` | array | no | `[{ "page": 1, "start": 0, "end": 1234 }]` |

### Output object (v1)

```json
{
  "sections": [{ "heading": "Introduction", "text": "...", "page_hint": "p. 2" }],
  "warnings": ["scanned_pdf_low_confidence"],
  "page_count": 12
}
```

### Validation rules

1. `sections[].text` must be verbatim substrings of `raw_text` (whitespace normalization optional in validator).
2. Record `label_provenance` in `meta` when human-curated.

---

## Task: `source_pdf_extract` (Tier 3 — schema v1)

Cited open-access PDF → excerpt text for L3 when HTML/abstract is insufficient.

**Pilot fetch:** [`scripts/fetch_oa_fulltext.py`](./scripts/fetch_oa_fulltext.py). **Eval holdout:** `data/eval_holdout_body_pilot.jsonl`.

### Input fields (v1)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | yes | OA or attached source URL |
| `doi` | string | no | Canonical DOI when known |
| `pdf_text` | string | no | Full extracted text (when available) |

### Output object (v1)

```json
{
  "excerpt": "verbatim passage suitable for grounding",
  "page_hint": "p. 12",
  "fetch_status": "pdf_verified",
  "pdf_bytes": 842112,
  "pdf_path": "cache/oa_fulltext/pdfs/051_10.1063_1.1316015.pdf",
  "notes": "optional operator notes"
}
```

**`fetch_status` values** (honest provenance — do not label paywalls as OA):

| Value | Meaning |
|-------|---------|
| `pdf_verified` | Live probe returned PDF bytes from the selected URL |
| `pdf_filed` | Operator attached a local PDF (`file_operator_pdf.py`) |
| `paywall_or_auth` | Login/purchase wall or 401/403 |
| `html_only` | Landing page without automatable PDF |
| `url_resolved` | URL chosen but not verified (`--no-probe` legacy) |

**`meta.access_tier`** (how bytes were obtained):

| Value | Meaning |
|-------|---------|
| `oa_unpaywall_verified` | Unpaywall candidate + verified PDF |
| `oa_unpaywall_url_only` | Unpaywall URL, probe failed |
| `operator_override_verified` | Operator URL override + verified PDF |
| `operator_override_url_only` | Operator URL override, not verified |
| `operator_attached_pdf` | Local PDF filed for training |
| `operator_grey_mirror` | Training-only grey mirror PDF (not product path) |

### Validation rules

1. `excerpt` must be a verbatim substring of `pdf_text` when `pdf_text` is present.
2. `excerpt` length ≤ 4200 chars (app `GROUNDING_EXCERPT_MAX_CHARS`).
3. Never mix boost rows from this task into `eval_holdout_body_*.jsonl`.

---

## Task: `table_figure_grounding` (planned)

Multimodal: claims vs table cells or figure captions. Expect **12B** (or successor) base; schema TBD.

---

## Task: `webpage_metadata`

Future task aligned with [`docs/WEBPAGE_ROADMAP.md`](../docs/WEBPAGE_ROADMAP.md). Suggest CSL-like fields from page signals.

### Input fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | yes | Final or requested URL |
| `fetch_status` | number | no | HTTP status |
| `page_signals` | object | yes | Structured hints from fetch/parser |
| `visible_text_snippet` | string | no | Short visible text |

`page_signals` example:

```json
{
  "content_type": "text/html",
  "json_ld_types": ["BlogPosting"],
  "og_title": "Annual Report 2024",
  "og_site_name": "WHO",
  "detected_platform": "substack",
  "is_paywall_heuristic": false,
  "is_pdf_url": false
}
```

### Output object

```json
{
  "suggested_type": "report",
  "fields": {
    "title": "Annual Report 2024",
    "author": [{ "family": "World Health Organization", "given": "" }],
    "issued": { "date-parts": [[2024]] },
    "URL": "https://www.who.int/example",
    "container-title": null
  },
  "confidence": "medium",
  "issues": ["No individual author; organization used as author"],
  "user_message": "This looks like an organizational report, not a generic webpage."
}
```

`suggested_type` should align with CSL types used in the app (`webpage`, `post`, `post-weblog`, `report`, `article-journal`, etc.).

---

## Task: `webpage_classify`

Lightweight classification only (host/platform + grey literature tag).

### Output object

```json
{
  "platform": "youtube",
  "grey_tags": ["webpage"],
  "recommended_csl_type": "webpage",
  "rationale": ["Video landing page; treat as webpage with stable video URL"]
}
```

---

## Task: `issue_explain`

Explain a deterministic issue to the user (no auto-fix).

### Input fields

| Field | Type | Required |
|-------|------|----------|
| `issue_code` | string | yes |
| `issue_context` | object | yes |

Example `issue_context`:

```json
{
  "url": "https://example.com/paper.pdf",
  "http_status": 200,
  "content_type": "application/pdf",
  "message": "URL points to PDF, not HTML webpage"
}
```

### Output object

```json
{
  "explanation": "This URL returns a PDF file, not a normal webpage. Nassila could not extract HTML metadata.",
  "suggested_actions": [
    "Cite as a report or document if appropriate",
    "Use a landing page URL if the journal provides one"
  ],
  "severity": "warning"
}
```

---

## Eval records (`eval_samples.jsonl`)

Eval rows extend `l3_grounding` (or other tasks) with expected checks:

| Field | Type | Description |
|-------|------|-------------|
| `expect` | object | Machine-checkable expectations |

Example:

```json
{
  "id": "eval-003",
  "task": "l3_grounding",
  "passage": "...",
  "source_excerpt": "...",
  "meta": { "label": "abstract" },
  "output": { "... gold for reference ..." },
  "expect": {
    "must_parse_json": true,
    "any_claim_verdict": ["contradicted"],
    "forbidden_claim_verdict": ["supported"],
    "quotes_must_be_substrings": true
  }
}
```

Do **not** train on rows you use for final eval.

---

## Chat training format (derived)

Trainers often convert each record to:

```json
{
  "messages": [
    { "role": "system", "content": "You are a strict academic citation grounding assistant." },
    { "role": "user", "content": "<full user prompt>" },
    { "role": "assistant", "content": "<json.dumps(output)>" }
  ]
}
```

The user prompt text should match production [`buildGroundingUserPrompt`](../src/engine/manuscript/grounding-llm.ts) line-for-line aside from variable content.

---

## File naming conventions

| File | Purpose |
|------|---------|
| `l3_grounding_train.jsonl` | Training (private OK) |
| `l3_grounding_eval.jsonl` | Held-out eval |
| `webpage_*_train.jsonl` | Phase 2 training |
| `eval_samples.jsonl` | Public synthetic eval template (repo) |
| `eval_holdout_45.jsonl` | Larger eval set with `expect` blocks; do **not** train on it |
