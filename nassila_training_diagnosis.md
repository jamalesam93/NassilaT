# Nassila L3 grounding — training diagnosis

> **Canonical themes** for Sanad (`l3_grounding`) v1.0–v1.6. Summarized in [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md) §9. Full holdout matrix: [`training/reports/holdout_failure_matrix.md`](./training/reports/holdout_failure_matrix.md).

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

## v1.5 result — NO-GO, and the result is not trustworthy (train/eval contamination)

`reports/v1_5_eval_combined_report.json`: combined expect **88.57%** (gate ≥90% → **FAIL**). Five of six model gates passed, including the apparent headline wins — but those wins are contaminated.

**Critical methodology bug:** 7 of the 27 v1.5 boost rows reused **verbatim eval passages/excerpts** (detected by `scripts/check_contamination.py`):

| Boost row | Duplicates eval row |
|-----------|---------------------|
| `l3-v15-para-001` | h-006 / eval-021 (passage + excerpt) |
| `l3-v15-para-002` | h-010 (passage), eval-007 (excerpt) |
| `l3-v15-contrast-001` | eval-021 (passage) |
| `l3-v15-contrast-002` | h-010 (passage) |
| `l3-v15-contrast-006` | eval-021 (excerpt) |
| `l3-v15-multi-001` | h-043 (passage + excerpt) |
| `l3-v15-multi-002` | h-045 (passage) |

The EVALUATION_GUIDE rule "never train on eval ids used for go/no-go" was violated. So the v1.5 gains on **h-006/h-010** (supported h-001–h-010 jumped 8→10/10) and likely much of the **quote-validity 81.8%→100%** jump reflect **memorization**, not generalization. The numbers cannot be used as a Tier 2 decision. `l3-v15-multi-001` even taught a label (`supported`) that conflicts with the h-043 gold (`forbidden supported`).

## v1.5 regression — eroded the hedge middle

Even setting contamination aside, the v1.5 boost was skewed (19 `supported` + 8 `not_in_source`, **0 `weak`, 0 `insufficient_evidence`**). It pushed the decision boundary toward the supported/not_in_source poles and eroded the middle:

| Row | v1.4a | v1.5 | New v1.5 verdict | Theme |
|-----|-------|------|------------------|-------|
| h-032 | pass (weak) | `wrong_verdict` | called `not_in_source` | association + hedge → should be `weak` |
| h-034 | pass (weak) | `wrong_verdict` | called `not_in_source` | general effect → should be `weak` |
| eval-012 | pass | `wrong_verdict` | over-decisive | thin excerpt → should be `insufficient_evidence` |
| eval-024 | (varies) | `wrong_verdict` | under-called supported | gun-shy after contrastive flood |

Net: holdout stayed 41/45 (traded h-006/h-010 gains for h-032/h-034 losses); extended core dropped 17→16/20. Combined 90.0%→88.57%.

## v1.6 fixes (current)

1. **Decontaminate.** New boost `data/l3_grounding_v16_boost.jsonl` (32 rows) shares **0** passages/excerpts with any eval row. `scripts/prepare_v15_train.py` now HARD-FAILS on contamination (`check_contamination.py` gate), so this bug cannot recur.
2. **Rebalance the middle.** Boost now includes **6 `weak` (hedged)** rows (de-hedged claim vs `may/could/appears/seem` quote — the h-032/h-034 pattern) and **4 `insufficient_evidence`** rows (methods/design-only excerpt — the eval-012 pattern).
3. **Keep what is clean and worked.** Quote-fidelity rows (verbatim copy) retained — they were not contaminated; verbatim-quote discipline is the genuine v1.5 signal worth keeping.
4. **Distinct paraphrase / multi rows.** Paraphrase-supported (h-006/h-010 pattern) and multi-claim partial rows are rewritten with **new** text so the next holdout score is a true test.

Build: `python scripts/prepare_v15_train.py --base data/l3_grounding_train_v14a.jsonl --boost data/l3_grounding_v16_boost.jsonl --out data/l3_grounding_train_v16.jsonl` → 850 rows, verdict mix contradicted 142 / supported 343 / weak 108 / not_in_source 185 / insufficient 72; validate + audit + contamination all pass.
