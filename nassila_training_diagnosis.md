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

## v1.9 result — calibration regression vs v1.8 (clean NO-GO)

`reports/v1_9_eval_combined_report.json`: **90%** combined (63/70) — **down from v1.8 91.43%**. Contamination 0. **4/6 model gates pass** (lost false-supported gate).

| Gate | v1.8 | v1.9 | |
|------|------|------|---|
| Combined expect | **91.43% ✅** | 90% ✅ (barely) | −1 row |
| Quote validity holdout | 90.91% ❌ | 90.91% ❌ | flat |
| False supported holdout | **2.94% ✅** | **5.88% ❌** | regression |
| Supported h-001–h-010 | 9/10 | 9/10 | h-009 fixed, **h-008 regressed** |

**v1.9 wins vs v1.8:** h-009, eval-020, eval-024 (supported calibration worked on extended).

**v1.9 losses vs v1.8:** h-008 (`weak` on adjuvant survival — same text as eval-020), h-034 (`not_in_source` vs `insufficient`), h-041 (new `supported` on sleep conjunct), eval-012 (`not_in_source` vs `insufficient`); false-supported 2/34 = h-041 + h-043.

**Lesson:** v19's 6 broad supported-calibration rows overrode v18 compound discipline. h-043 unchanged (still forbidden `supported` on pain).

## v1.10 fixes (current)

1. **Drop v19 boost from merge** — revert to v16 + v18 + **v110** (87 boost rows).
2. **Prompt:** compound-passage line — split conjuncts; mixed outcomes → weak/contradicted/not_in_source, never supported on bundled claims.
3. **v110 boost (20 rows):** 3 narrow supported (h-009/h-008 pattern), 3 weak-mixed (h-034), 3 insufficient design-only (eval-012), 6 nosup compound (h-041/h-043), 3 scope split (h-045), 2 two-claim split (eval-018).

Build: `--boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v18_boost.jsonl data/l3_grounding_v110_boost.jsonl --out data/l3_grounding_train_v110.jsonl` → `PHASE=10`.

## Hardened harness + A/B pilot (v1.10+)

**Root cause (harness brittleness):** On the legacy 45-row holdout, quote validity (10/11) and false-supported (2/34) gates flipped on **one row each**. Version seesaw (v1.8 91.43% → v1.9 90%) mixed genuine regression with measurement noise.

**Fix:** `data/eval_holdout_extension_45.jsonl` (h-046..h-090) + `build_hardened_holdout.py` → **`eval_holdout_90.jsonl`** (115-row combined harness). Contamination gate includes extension; v1.10 train verified 0 overlap.

**A/B pilot:** Same v1.10 data; E4B-Q6 control vs 12B Q4/Q6/Q8. Scripts: `run_ab_pilot_pipeline.sh`, `train_qlora_gemma4_12b.py`, `run_multi_seed_eval.py`, `compare_ab_pilot.py`. Walkthrough: [`training/PHASE2_9_AB_PILOT_WALKTHROUGH.md`](./training/PHASE2_9_AB_PILOT_WALKTHROUGH.md).

**A/B script gates:** combined expect ≥ E4B + 3 pts; `multi_claim` pass ≥ 0.8; quote validity ≥ E4B-Q6. **Recorded outcome:** dual-tier adopted — see **v1.10 A/B result** below.

**Policy:** Dual-tier — E4B default download; 12B optional quality tier when Tier 2 passes. See Nassila [`docs/OUROBOROS.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS.md).

## v1.10 A/B result (E4B vs 12B, hardened 115-row harness)

Multi-seed means (seeds 42/43/44) on `eval_holdout_90.jsonl` + combined 115-row harness. Reports: `training/reports/ab_*_v110/`, decisions: `ab_decision_12b_*.json`.

| Arm | Combined expect | Quote val (holdout) | False sup (holdout) | multi_claim | Tier 2 §10 |
|-----|-----------------|---------------------|---------------------|-------------|------------|
| **E4B v1.10 Q6_K** | 88.12% | 89.47% | 6.57% | 58.98% | **FAIL** (all seeds) |
| **12B v1.10 Q6_K** | **94.79%** | **100%** | **2.82%** | 69.23% | **PASS** (all seeds) |
| 12B Q4_K_M | 93.91% | 94.74% | 4.23% | 61.54% | FAIL |
| 12B Q8_0 | 92.46% | 96.49% | 4.23% | 61.54% | borderline (seed 42 only) |

**Quant ladder:** Q6_K is the sweet spot for 12B (best combined + only quant with 100% quote validity across seeds).

**`compare_ab_pilot.py` vs Tier 2:** The A/B script recommends `defer_12b_to_shahid_only` on all quants because its extra **`multi_claim >= 0.80`** sub-gate fails (12B Q6_K = 69.23%). That sub-gate is **not** a Tier 2 ship gate. Combined-delta (+6.67 pts) and quote-vs-baseline pass. Persistent multi_claim misses: h-043 (`forbidden_verdict`), h-045 (`wrong_verdict`), h-088 (`min_claims`) — see [`training/reports/holdout_failure_matrix.md`](./training/reports/holdout_failure_matrix.md).

**Adopted decision (dual-tier):**

1. **E4B** remains the **default/fast** tier (smaller download; still below Tier 2 on hardened harness — continue iterating v1.11+ on E4B).
2. **12B Q6_K** is recorded as Sanad's **first Tier-2-passing checkpoint** and **optional quality tier** (`nassila-sanad-12b-q6_k.gguf`, train checkpoint v1.10).
3. Unmet `multi_claim >= 0.80` is a **known limitation**, not a ship blocker for the optional tier.
4. **Shahid** multimodal still reserves 12B when that worker forges.

**HF (operator):** adapters private — `QinEmPeRoR93/nassila-sanad-12b-adapter`, `QinEmPeRoR93/nassila-sanad-e4b-adapter`, `QinEmPeRoR93/nassila-sanad-31b-adapter` (v1.12); GGUF — `nassila-sanad-12b` (private), `nassila-sanad-e4b` (default-tier), `nassila-sanad-31b` (premium, Tier 2). Policy: [`docs/DUAL_TIER_POLICY.md`](./docs/DUAL_TIER_POLICY.md). See [`training/PHASE2_9_AB_PILOT_WALKTHROUGH.md`](./training/PHASE2_9_AB_PILOT_WALKTHROUGH.md) Part 9.

## Dual-tier ship policy (2026-06-17)

- **E4B default-tier:** combined ≥88%, quote ≥88%, false-supported ≤7% (+ JSON/legacy gates). **v1.10 PASS** — shippable as `nassila-sanad-e4b`.
- **Tier 2:** full six gates — **12B v1.10 PASS**, **31B v1.12** target.
- **v1.11 NO-GO:** 80.58% combined regression; do not publish.

## v1.12 recovery (E4B + 31B premium — implemented locally 2026-06-17)

Prompt v1.12 (parity compound guardrail, scope rows `weak` only). Boost: `l3_grounding_v112_boost.jsonl` (23 rows). Train: `l3_grounding_train_v112.jsonl`. Gates: `tier_gates.py` → `e4b_default_gates` + `v110_baseline_beat`.

```bash
ARM=e4b PHASE=12 MULTI_SEED=1 bash training/scripts/run_ab_pilot_pipeline.sh
ARM=31b PHASE=12 MULTI_SEED=1 bash training/scripts/run_ab_pilot_pipeline.sh
```

Walkthroughs: [`training/PHASE2_11_V112_WALKTHROUGH.md`](./training/PHASE2_11_V112_WALKTHROUGH.md), [`training/PHASE2_12_31B_PREMIUM_WALKTHROUGH.md`](./training/PHASE2_12_31B_PREMIUM_WALKTHROUGH.md).

## v1.11 fixes (E4B gap — trained, NO-GO)

**Eval harness (Step 1):**

- **h-043 (Option A):** removed `forbidden_claim_verdict: ["supported"]`; added `min_claims: 2`. Model was correct; gold was wrong (same class as eval-018).
- **h-045:** added `min_claims: 2` (aligns with h-088).
- Regenerated `eval_holdout_90.jsonl` via `build_hardened_holdout.py`.

**Regrade v1.10 predictions (no retrain):** E4B Q6_K seeds 42/43/44 — h-043 **pass** on all; h-045 still **fail**. Combined expect: 87.83% / 89.56% / 89.56% (was 86.96% / 88.70% / 88.70% on old gold).

**Prompt (Step 2):** scope-silence rule + per-conjunct compound evaluation in Nassila `grounding-llm.ts` and `validate_dataset.py` (golden: `training/fixtures/grounding_prompt_golden.txt`; tests: Nassila `grounding-llm.test.ts`, NassilaT `tests/unit/test_prompt_sync.py`).

**Data (Step 3):** `l3_grounding_v111_boost.jsonl` expanded to **29 rows** (12 scope-split incl. v111-scope-005..012; 2 with `supported` studied subgroup). Merge → `l3_grounding_train_v111.jsonl` (850 rows, contamination 0) + `l3_grounding_chat_v111.jsonl`.

**Operator (Step 4 — Vast):**

```bash
ARM=e4b PHASE=11 MULTI_SEED=1 bash training/scripts/run_ab_pilot_pipeline.sh
```

Walkthrough: [`training/PHASE2_10_V111_WALKTHROUGH.md`](./training/PHASE2_10_V111_WALKTHROUGH.md). **Result: NO-GO** — see `reports/ab_e4b_q6_k_v111/`. Pursue v1.12 recovery instead.
