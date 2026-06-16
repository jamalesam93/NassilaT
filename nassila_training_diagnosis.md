# Nassila L3 grounding — training diagnosis

> **Canonical themes** for Sanad (`l3_grounding`) v1.0–v1.5. Summarized in [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md) §9. Full holdout matrix: [`training/reports/holdout_failure_matrix.md`](./training/reports/holdout_failure_matrix.md).

## Whack-a-mole (v1.0–v1.3)

Each cycle fixed one cluster while regressing another until v1.4 schema + prompt discipline.

## v1.3 root cause

Mixed JSON key order in training labels (`rationale` last vs `hasNumericClaim` last) caused parse failures that looked like verdict errors. **Fix:** `canonical_claim()` with fixed key order; `hasNumericClaim` always last.

## Persistent failure clusters (v1.4a)

| Row | Mode | Theme |
|-----|------|-------|
| h-006, h-010 | `wrong_verdict` | Paraphrase-supported scored as `weak` or `not_in_source` |
| h-043 | `forbidden_verdict` | Multi-claim passage: spurious `supported` on absent sub-claim |
| h-045 | `wrong_verdict` | Multi-claim: pediatric/adult scope not surfaced as `not_in_source` |

## h-001 pattern (historical)

Correct quotes with wrong verdict — paraphrase bias toward `weak`. Partially recovered in v1.4a.

## v1.5 candidates (§6.2)

1. **Contrastive rows** — paraphrase-supported vs same excerpt with `not_in_source` (see `data/l3_grounding_v15_boost.jsonl`).
2. **Quote-fidelity rows** — verbatim `sourceQuotes` copied from excerpt (`-quote-` ids in boost file).
3. **Multi-claim partial rows** — one supported + one `not_in_source` per passage (`-multi-` ids).
4. **Loss weighting** — optional contrastive weight on paraphrase-supported (experiment in v1.5 train recipe).

## v1.4b lesson

More epochs (3 @ 1.5e-4) did not improve quote validity or combined expect. v1.5 needs **data / loss / contrastive**, not hyperparams alone.

## App guardrail (v1.5)

Engine quote-substring check (`grounding-llm.ts`) demotes invalid-quote `supported` → `warn`. This is the **product-safety gate** alongside the **model gate** (raw quote validity ≥98% on holdout). See Nassila §10.
