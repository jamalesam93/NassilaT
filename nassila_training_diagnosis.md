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

## v1.6 result — clean NO-GO (trustworthy; v1.4a remains ship)

`reports/v1_6_eval_combined_report.json`: combined expect **88.57%** (gate ≥90% → **FAIL**), but **contamination = 0** (verified), so unlike v1.5 these numbers are usable. Model gates 4/6: JSON 100%, supported h-001–h-010 10/10, core legacy 5/5, quote validity holdout **100%** all pass; **combined expect 88.57%** and **false-supported holdout 5.88%** (cap ≤5%) fail. Quote validity is now genuinely solved (no memorization).

The 8 combined failures cluster into two themes:

| Theme | Rows | Pattern |
|-------|------|---------|
| **Compound / multi-claim** | h-042, h-043, h-045, eval-018 | Model merges a two-part claim and grants blanket `supported` when only one conjunct holds; eval-018 failed `min_claims:2` (didn't split). Drives the holdout false-supported overflow. |
| **Evidential weak / insufficient** | h-032, h-034, eval-012, eval-013 | v1.6 weak rows taught *modal* hedges (`may/could/appears`); misses use *evidential* hedging (`association suggested but causality unclear`, `mixed`, `small studies hint`). Did not generalize. |

Everything else is solid: supported 10/10, contradicted 10/10, not_in_source clean.

## v1.7 fixes (current)

1. **Harder compound rows.** New boost `data/l3_grounding_v17_boost.jsonl` adds **8 `v17_compound_hard`** rows: 2-claim splits where one conjunct is contradicted (numeric mismatch / direction flip) and/or out-of-scope (`not_in_source` / `insufficient_evidence`). Teaches splitting (fixes eval-018 `min_claims`) and conservative verdicts (fixes h-042/h-043/h-045 false-supported).
2. **Evidential-strength weak.** **6 `v17_weak_evidential`** rows hedge with `suggested / appears / preliminary / limited / unclear / possibly` (audit-canonical de-hedged-claim shape) — the h-032/h-034 generalization gap.
3. **More insufficient.** **3 `v17_insufficient`** rows (protocol/discussion/analysis-plan-only excerpts) — the eval-012 pattern.
4. **Keep v1.6 boost intact** (still clean and useful); v1.7 merges both boost files via the multi-`--boost` prepare flag.

Build: `python scripts/prepare_v15_train.py --base data/l3_grounding_train_v14a.jsonl --boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v17_boost.jsonl --out data/l3_grounding_train_v17.jsonl` → 850 rows, verdict mix contradicted 145 / supported 330 / weak 114 / not_in_source 185 / insufficient 76; contamination 0, validate OK, structural audit PASS, seq max 1250 ≤ 2048.

## v1.7 result — zero delta vs v1.6 (clean NO-GO; boost ineffective)

`reports/v1_7_eval_combined_report.json` is **bit-for-bit identical** to v1.6 on all Tier 2 gates (88.57% combined, 4/6 pass). Same 8 failing rows with the same failure modes. Prediction inspection shows **why** the v1.7 boost did not transfer:

| Row | Model behavior (root cause) |
|-----|----------------------------|
| h-042 | Extracted claims **from SOURCE** ("18% mortality") not **from PASSAGE** ("50%/30%") → spurious `supported` |
| h-043 | Split correctly but used `supported` on pain conjunct; eval forbids any `supported` |
| h-045 | Single `contradicted` on whole sentence; eval wants `not_in_source`/`insufficient` on pediatric part |
| h-032/h-034 | `not_in_source` instead of `weak` when topic **is** in excerpt but hedged |
| eval-012 | `not_in_source` instead of `insufficient_evidence` on design-only excerpt |
| eval-013 | `supported` on hedged verbatim passage |
| eval-018 | Single claim; gold expected 2 claims (gold was wrong — fixed in v1.8 eval harness) |

**Lesson:** 17 boost rows at ~2% of train cannot override a systematic prompt failure (claim text from excerpt). v1.7 boost **dropped** for v1.8.

## v1.8 fixes (current)

1. **Prompt (train + Nassila engine):** "Each claim string must restate an assertion from the PASSAGE…" — fixes h-042-style source-as-claim regression.
2. **Eval harness:** `eval-018` gold/expect → `contradicted` + `not_in_source`, `min_claims: 2` (removed incorrect `supported` gold).
3. **v18 boost (35 rows, replaces v17):** 10 passage-number compound, 6 no-`supported` multi (`weak`+`not_in_source`), 4 subgroup scope, 8 weak-when-topic-in-excerpt, 4 insufficient design-only, 3 hedge-in-passage.
4. **Merge v16 + v18 only** (67 boost rows total).

Build: `--boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v18_boost.jsonl --out data/l3_grounding_train_v18.jsonl` → contradicted 152 / supported 308 / weak 129 / not_in_source 185 / insufficient 76; contamination 0, audit PASS, seq max 1202.

## v1.8 result — major progress, one gate short (clean NO-GO)

`reports/v1_8_eval_combined_report.json`: **91.43%** combined (64/70) — **first version to pass combined ≥90%**. Contamination 0. **5/6 model gates pass**; ship blocked only by **quote validity holdout 90.91%** (need ≥98%).

| Gate | v1.6/7 | v1.8 | |
|------|--------|------|---|
| Combined expect | 88.57% ❌ | **91.43% ✅** | +2 rows |
| Quote validity holdout | 100% | **90.91% ❌** | regression |
| False supported holdout | 5.88% ❌ | **2.94% ✅** | fixed |
| Supported h-001–h-010 | 10/10 | 9/10 | h-009 regressed |

**Fixed vs v1.6/v1.7:** h-032, h-034, h-042, eval-012, eval-013; compound/multi mostly recovered; passage-claim prompt worked.

**Remaining 6 failures:** h-009, h-043, h-045 (holdout); eval-018, eval-020, eval-024 (extended). Root cause of quote gate: **h-009** called `weak` instead of `supported` on clear paraphrase (`significantly elevated`). v1.8 weak boost over-corrected.

## v1.9 fixes (current)

1. **Prompt:** clarify weak vs supported (`associated with` / `significantly` → supported when excerpt clearly supports).
2. **v19 boost (14 rows):** 6 supported-calibration, 3 nosup (h-043), 2 scope (h-045), 3 two-claim split (eval-018).
3. **Merge v16 + v18 + v19** (81 boost rows).

Build: `--boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v18_boost.jsonl data/l3_grounding_v19_boost.jsonl --out data/l3_grounding_train_v19.jsonl` → `PHASE=9`.
