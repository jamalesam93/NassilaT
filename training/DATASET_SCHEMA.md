# Dataset Schema

All training files use **JSONL** (one JSON object per line). Each record must include a `task` field. See [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md) for the seven workers.

Task ids are defined in [`src/shared/nassila-agent-tasks.ts`](../src/shared/nassila-agent-tasks.ts).

---

## Task registry

| Task id | Phase | Schema section below | Training status |
|---------|-------|----------------------|-----------------|
| `l3_grounding` | 1 | Yes | **Active** — v1 ship target |
| `doc_extract` | 2+ | Stub | Planned — manuscript PDF/DOCX → text |
| `source_pdf_extract` | 2+ | Stub | Planned — cited OA PDF → text |
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

## Task: `doc_extract` (planned — Tier 3)

Manuscript ingest: PDF or DOCX → structured plain text for downstream L3. **Not** a replacement for Marker or layout engines; complements pdfjs/mammoth.

**Planning:** [`PHASE3_TIER3_GROUNDWORK.md`](./PHASE3_TIER3_GROUNDWORK.md) (NassilaT).

### Input fields (draft)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document_kind` | string | yes | `pdf` \| `docx` |
| `raw_text_or_pages` | string or array | yes | Extracted text (page-bounded optional) |

### Output object (draft)

```json
{
  "sections": [{ "heading": "Introduction", "text": "..." }],
  "warnings": ["scanned_pdf_low_confidence"]
}
```

Full schema TBD when Phase 3 dataset work starts.

---

## Task: `source_pdf_extract` (planned — Tier 3)

Cited open-access PDF → excerpt text for L3 when HTML/abstract is insufficient.

**Planning:** [`PHASE3_TIER3_GROUNDWORK.md`](./PHASE3_TIER3_GROUNDWORK.md) (NassilaT). OA full-text fetch deferred in [`CORPUS_PIPELINE.md`](./CORPUS_PIPELINE.md) until this task starts.

### Input fields (draft)

| Field | Type | Required |
|-------|------|----------|
| `url` | string | yes |
| `pdf_text` | string | yes |

### Output object (draft)

```json
{
  "excerpt": "verbatim passage suitable for grounding",
  "page_hint": "p. 12"
}
```

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
