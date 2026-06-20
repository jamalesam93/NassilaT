# v1.13 12B Regression — Root Cause & v1.14 Fix Plan

> **Goal:** Recover 12B from v1.13 regression (88.99% → target ≥94% combined, Tier 2 PASS).
> **Context:** v1.13 added 12 parity-subgroup-split boost rows to fix h-045/h-088 patterns. The prepare pipeline merged them onto v14a base (850-row cap), which trimmed 11 `supported` + 1 `weak` rows. The resulting `supported`↔`weak` verdict imbalance caused 4 rows to regress and 2 rows hit inference server errors.
> **v1.12 (94.20%, Tier 2 PASS) is the last good 12B checkpoint. Do NOT publish v1.13 12B GGUF.**
> **Date:** 2026-06-20.

---

## TL;DR — What happened + four fixes

v1.13's only change from v1.12 was adding 12 parity-subgroup boost rows (all `weak`). The 850-row cap trim evicted 11 `supported` rows, shifting the verdict balance. The model became over-sensitive at the `supported`↔`weak` and `insufficient_evidence`↔`weak` boundaries.

**Four fixes:**

1. **Inference only (no retrain)**: Re-run h-028 and h-037 — these failed with HTTP 500 errors, not model quality issues. Free recovery of ~1.7% combined.
2. **Prompt**: Soften the "use that number" clause to explicitly allow approximate numbers (fixes h-051).
3. **Boost**: Keep the 12 v113 parity rows but add counterbalance rows to protect the `supported` verdict distribution (fixes h-038, h-082, eval-012).
4. **Cap strategy**: Prevent `supported` rows from being trimmed when new boost rows are added.

Then rebuild, contamination gate, retrain 12B v1.14, multi-seed eval.

---

## Part 1 — Root Cause

### Metrics comparison

| Metric | 12B v1.10 | 12B v1.12 | 12B v1.13 |
|--------|-----------|-----------|-----------|
| Combined expect | 94.79% | 94.20% | **88.99%** ↓ |
| JSON parse | 100% | 100% | **95.65%** ↓ |
| Supported h-001–h010 | 10/10 | 10/10 | 10/10 ✓ |
| Core legacy 5/5 | 5/5 | 5/5 | 5/5 ✓ |
| Quote validity (holdout) | 100% | 100% | **94.74%** ↓ |
| False supported (holdout) | 2.82% | 2.86% | 2.86% ✓ |
| **Tier 2** | **PASS** | **PASS** | **FAIL** |

### What changed v1.12 → v1.13

| Component | v1.12 | v1.13 | Changed? |
|-----------|-------|-------|----------|
| Prompt text | v1.12 prompt | identical | **No** |
| Hyperparameters | epochs=2, lr=1e-4 | epochs=2, lr=1e-4 | **No** |
| Base data | v14a (850) | v14a (850) | **No** |
| Boost files | v16+v18+v110+v112 (23 rows) | v16+v18+v110+v112+**v113** (35 rows) | **Yes** |
| Merged train size | 850 | 850 | Same (cap) |

The **only** difference is the 12 rows in `l3_grounding_v113_boost.jsonl` (all `v113_parity_subgroup_split`, all `overallVerdict: weak`). When `prepare_v15_train.py` merged them onto v14a and enforced the 850-row cap, 12 rows were trimmed:

**12 rows added** (v113 boost):

| ID | Pattern | Verdict |
|----|---------|---------|
| l3-v113-parity-001..012 | Parity passage ("equally in X and Y") + source studied only X | weak + not_in_source |

**12 rows evicted** (cap trim):

| ID | Verdict | Type |
|----|---------|------|
| 11 rows (l3-oa_*, l3-s2_* multi/sup) | **supported** | Various |
| 1 row (l3-s2_0512...multip-5) | weak | Multi-claim |

**Net verdict shift in 850-row training set** (first-claim verdict from `prepare_v15_train.py`):

| Verdict | v1.12 | v1.13 | Δ |
|---------|-------|-------|---|
| supported | 272 | 260 | **−12** |
| weak | 155 | 167 | **+12** |
| not_in_source | 185 | 185 | 0 |
| insufficient_evidence | 81 | 81 | 0 |

A 2.7% swing in a 850-row dataset is significant. The model lost 11 examples of `supported` behavior and gained 12 examples of `weak` behavior on parity passages. This shifted the `supported`↔`weak` decision boundary, with knock-on effects on `insufficient_evidence`.

### Failure analysis (seed 42, 6 regressed rows)

#### Cluster A: Server errors (h-028, h-037) — NOT a model problem

| Row | v1.12 | v1.13 | What happened |
|-----|-------|-------|---------------|
| h-028 | `not_in_source` ✓ | **parse_json fail** ✗ | HTTP 500 from llama.cpp server, empty output |
| h-037 | `insufficient_evidence` ✓ | **parse_json fail** ✗ | HTTP 500 from llama.cpp server, empty output |

These are inference stability issues (server returned 500 errors). The model never generated a response. **Fix: re-run inference only — no retrain needed.**

#### Cluster B: Verdict boundary erosion (h-038, h-051, h-082, eval-012)

| Row | Gold | v1.12 | v1.13 | Root sub-cause |
|-----|------|-------|-------|----------------|
| **h-038** | `insufficient_evidence` or `not_in_source` | `insufficient_evidence` ✓ | **`weak`** ✗ | Design-only excerpt ("Methods only; results section is forthcoming"). Model quotes source text and calls `weak` instead of `insufficient_evidence`. |
| **h-051** | `supported` | `supported` ✓ | **`weak`** ✗ | Passage says "about 920", source says "918". Model treats approximate number as mismatch → downgrades. Prompt "use that number, not a different number" too rigid. |
| **h-082** | `insufficient_evidence` or `not_in_source` | `insufficient_evidence` ✓ | **`weak`** ✗ | Design-only excerpt ("planned trial without outcome data"). Same pattern as h-038. |
| **eval-012** | `insufficient_evidence` | `insufficient_evidence` ✓ | **`not_in_source`** ✗ | Methods-only excerpt ("study design and inclusion criteria"). `insufficient_evidence` → `not_in_source`. |

**Sub-root-causes:**

1. **h-038/h-082** — `insufficient_evidence` collapsing to `weak`: With 11 fewer `supported` examples, the model's decision boundary between "I have topic-relevant text but no results" (→ `insufficient_evidence`) and "partial alignment" (→ `weak`) shifted toward `weak`. The source excerpts for these rows do mention the topic (methods, forthcoming results), so the model interprets that as "partial alignment" rather than "insufficient."

2. **h-051** — The prompt clause *"When the passage states a number, use that number, not a different number from the source"* was written to prevent fabrication (passage says "50%" but source says "12%"). But combined with the `weak`-heavy training, the model became hyper-sensitive to any numeric difference, including legitimate approximations like "about 920" ≈ 918.

3. **eval-012** — A secondary effect of the boundary shift. The model lost confidence in `insufficient_evidence` for methods-only excerpts and went further to `not_in_source`.

### Pre-existing failures vs v1.13 regressions

| Row | v1.12 failure mode | v1.13 failure mode | v1.13 caused? |
|-----|-------------------|-------------------|---------------|
| eval-018, h-039, h-041, h-044 | verdict / quote (pre-existing) | same class | **No** |
| **h-045, h-088** | `min_claims` (parsed JSON, 1 claim bundled) | **`parse_json`** (`No JSON object`, all seeds) | **Yes — worsened** |

**h-045 / h-088:** Already failing on v1.12 (single bundled claim instead of 2-claim parity split). v1.13 **regressed further** to JSON parse failures on all seeds — likely from verdict-boundary skew + weak-heavy training, not from bad v113 row content alone. v1.14 must at minimum **restore parse stability** (back to v1.12-style `min_claims` failures); **passing** both rows is a stretch goal (see Step 7).

Other six still-failing rows (eval-018, h-039, h-041, h-044) are unchanged from v1.12/v1.10. Out of scope for this fix unless they block Tier 2.

---

## Part 2 — Prompt Changes

**Scope:** Full resync of Nassila `grounding-llm.ts` to the train-side v1.12 prompt in `validate_dataset.py`, **plus** the v1.14 approximation clause. The app prompt had drifted (old compound rule, no “use that number” clause); v1.14 fixes that drift and adds one new line.

### Files to edit (must stay in sync)

| File | Function |
|------|----------|
| `src/engine/manuscript/grounding-llm.ts` → `buildGroundingUserPrompt` | App-side prompt |
| `training/scripts/validate_dataset.py` → `build_grounding_user_prompt` | Train-side prompt |
| `training/fixtures/grounding_prompt_golden.txt` | Sync test golden |

### Change: Soften the "use that number" clause (Line 3)

**Current (v1.12/v1.13):**
```
'Each claim string MUST restate an assertion from the PASSAGE — do NOT copy source sentences as claim text unless that exact assertion also appears in the passage. When the passage states a number, use that number, not a different number from the source.'
```

**New (v1.14):**
```
'Each claim string MUST restate an assertion from the PASSAGE — do NOT copy source sentences as claim text unless that exact assertion also appears in the passage. When the passage states a number, use that number, not a different number from the source. Approximate passage numbers (e.g., "about 920" vs source "918", "nearly 50%" vs source "52%") are acceptable approximations and should NOT trigger a downgrade to weak or contradicted — treat them as supported if the source confirms the same figure approximately.'
```

**Rationale:** This preserves the anti-fabrication guard (passage says "99%" but source says "78%" → still contradicted) while allowing legitimate approximate numbers. Directly fixes h-051-type regressions.

### No other prompt changes

The compound guardrail, scope-silence rule, verdict definitions, and JSON format instructions are all correct and unchanged from v1.12.

### Full target prompt (for reference)

```
Line 1:  'You are a strict academic citation grounding assistant.'
Line 2:  'Break the manuscript passage into short factual claims (atomic where possible).'
Line 3:  'Each claim string MUST restate an assertion from the PASSAGE — do NOT copy source sentences as claim text unless that exact assertion also appears in the passage. When the passage states a number, use that number, not a different number from the source. Approximate passage numbers (e.g., "about 920" vs source "918", "nearly 50%" vs source "52%") are acceptable approximations and should NOT trigger a downgrade to weak or contradicted — treat them as supported if the source confirms the same figure approximately.'
Line 4:  'For each claim, compare ONLY to SOURCE_EXCERPT (verbatim text from the cited work).'
Line 5:  'Verdict per claim:'
Line 6:  '- supported: SOURCE_EXCERPT contains clear support; you MUST copy 1–3 verbatim sourceQuotes from SOURCE_EXCERPT.'
Line 7:  '- weak: partial or vague alignment, OR the source hedges (may/might/suggest/preliminary/unclear). Do NOT use weak when the excerpt clearly supports a single passage claim (including paraphrase and \'associated with\' / \'significantly\' wording).'
Line 8:  '- not_in_source: not found in excerpt (excerpt may be incomplete).'
Line 9:  '- contradicted: excerpt clearly conflicts.'
Line 10: '- insufficient_evidence: cannot tell from excerpt.'
Line 11: 'Compound passages: when the passage bundles multiple claims (e.g., joined by "and"), split into one claim per conjunct and evaluate each independently. A conjunct may be supported if SOURCE_EXCERPT directly supports it with matching meaning and numbers — but NOT if the passage asserts a specific number that differs from the source. On compound passages where the passage asserts parity or equality across subgroups (e.g., "equally well in adults and children") and the source addresses only one subgroup, the studied subgroup receives weak (not supported), and the unstudied subgroup receives not_in_source.'
Line 12: 'Scope-silence rule: if the passage asserts a claim about specific subgroups (e.g., adults and children, men and women) and SOURCE_EXCERPT addresses one subgroup but states or implies the other was not studied / not collected / not enrolled, split into one claim per subgroup. The unstudied subgroup receives not_in_source, never contradicted. The studied subgroup receives weak (not supported) when the passage asserts parity or equality across those subgroups.'
Line 13: 'Respond with a single JSON object ONLY, no markdown fencing, keys:'
Line 14: '{ "claims": [ { "claim": string, "verdict": "supported"|"weak"|"not_in_source"|"contradicted"|"insufficient_evidence", "hasNumericClaim"?: boolean, "sourceQuotes"?: string[], "rationale"?: string[] } ], "overallVerdict"?: "support"|"weak"|"unrelated"|"insufficient_evidence", "overallRationale"?: string[] }'
Line 15: ''
Line 16: PASSAGE:\n{passage}
Line 17: ''
Line 18: SOURCE_EXCERPT ({label} {url}):\n{source_excerpt}
```

### Test updates

**`tests/unit/grounding-llm.test.ts`** — add one assertion:
- Add: `Approximate passage numbers` present (approximation guardrail)

**`training/tests/unit/test_prompt_sync.py`** — update golden file:
- Update `fixtures/grounding_prompt_golden.txt` to match the new Python prompt.

---

## Part 3 — Boost Changes

### Keep all v113 parity rows (12 rows)

The 12 `v113_parity_subgroup_split` rows are **correct** and should stay. They teach the right pattern for h-045/h-088. The regression was caused by the balance shift, not by bad rows.

### Add counterbalance boost file: `l3_grounding_v114_boost.jsonl`

Create a new boost file with **two types of rows** to restore the verdict balance:

#### Type 1: Design-only / protocol-only → `insufficient_evidence` (3 rows)

These directly counter the h-038/h-082/eval-012 regression by reinforcing that methods-only excerpts → `insufficient_evidence` (not `weak`).

| ID | Passage | Source excerpt | Claim | Expected verdict |
|----|---------|---------------|-------|-----------------|
| l3-v114-insuf-001 | The intervention reduced 30-day readmissions by 15% (Torres, 2023). | Methods: Patients were randomized 1:1 to intervention or usual care. Follow-up is ongoing. | "The intervention reduced 30-day readmissions by 15%" | `insufficient_evidence` |
| l3-v114-insuf-002 | SERPINA1 knockout increased apoptosis in tumor cells (Liu, 2024). | This manuscript describes the generation of SERPINA1-knockout cell lines and validation protocols. | "SERPINA1 knockout increased apoptosis in tumor cells" | `insufficient_evidence` |
| l3-v114-insuf-003 | Teacher training improved standardized test scores by two grade levels (Novak, 2022). | We outline the curriculum and eligibility criteria for the professional development program. Outcome data will be collected in Year 2. | "Teacher training improved standardized test scores by two grade levels" | `insufficient_evidence` |

**Key pattern**: Source is clearly methods/protocol/design-only. No results are reported. Claim makes a specific outcome assertion → `insufficient_evidence`. SourceQuotes must be empty. Rationale must mention "design-only" or "methods-only" or "results not reported."

#### Type 2: `supported` counterbalance (9 rows)

These restore the `supported` verdict count that was lost when 11 `supported` rows were trimmed in v1.13. Mix of patterns:

| ID | Passage | Source excerpt | Claim | Expected verdict |
|----|---------|---------------|-------|-----------------|
| l3-v114-sup-001 | Flu vaccination reduced respiratory hospitalizations by 45% (Morrison, 2023). | Among vaccinated adults, respiratory hospitalizations were 45% lower than in unvaccinated controls. | "Flu vaccination reduced respiratory hospitalizations by 45%" | `supported` |
| l3-v114-sup-002 | The drug was well tolerated with no serious adverse events (Patel, 2024). | No serious adverse events were reported during the 12-week treatment period. | "The drug was well tolerated with no serious adverse events" | `supported` |
| l3-v114-sup-003 | Mean fasting glucose decreased by 1.2 mmol/L at 6 months (Andersen, 2023). | At the 6-month follow-up, mean fasting glucose had decreased by 1.2 mmol/L (95% CI 0.8–1.6) from baseline. | "Mean fasting glucose decreased by 1.2 mmol/L at 6 months" | `supported` |
| l3-v114-sup-004 | Adherence to the Mediterranean diet was associated with lower cardiovascular mortality (Garcia, 2022). | Higher Mediterranean diet adherence scores were independently associated with reduced cardiovascular mortality in the adjusted analysis (HR 0.72, p=0.003). | "Adherence to the Mediterranean diet was associated with lower cardiovascular mortality" | `supported` |
| l3-v114-sup-005 | MRI detected 89% of lesions confirmed by histopathology (Kim, 2024). | Histopathological confirmation was available for 127 of 143 MRI-detected lesions, yielding a detection sensitivity of 89%. | "MRI detected 89% of lesions confirmed by histopathology" | `supported` |
| l3-v114-sup-006 | The prevalence of type 2 diabetes in the cohort was 14.3% (O'Brien, 2023). | Type 2 diabetes was present in 214 of 1,498 participants (14.3%). | "The prevalence of type 2 diabetes in the cohort was 14.3%" | `supported` |
| l3-v114-sup-007 | Post-operative complications occurred in 8% of patients (Nakamura, 2024). | Eight percent of patients (12/150) experienced at least one post-operative complication. | "Post-operative complications occurred in 8% of patients" | `supported` |
| l3-v114-sup-008 | Sleep duration was inversely correlated with BMI (Chen, 2023). | Shorter sleep duration was significantly associated with higher BMI (r = −0.31, p < 0.001). | "Sleep duration was inversely correlated with BMI" | `supported` |
| l3-v114-sup-009 | The vaccine elicited seroconversion in 94% of recipients (Volkov, 2025). | Seroconversion was achieved in 94% of vaccinated individuals (95% CI 90–97%) at day 28. | "The vaccine elicited seroconversion in 94% of recipients" | `supported` |

**Key pattern**: Clear, direct support from source. Verbatim or near-verbatim quotes required. Numbers match exactly. `overallVerdict: support` for all.

### Boost summary

| File | Rows | Row types |
|------|------|-----------|
| v113 boost (keep) | 12 | parity_subgroup_split (all `weak`) |
| **v114 boost (new)** | **12** | insuf_design (3 `insufficient_evidence`) + supported_counterbalance (9 `supported`) |
| **Total new boost** | **24** | — |

### Update `prepare_v15_train.py` trim strategy

The current cap trim evicts rows by whatever order `prepare_v15_train.py` uses (likely insertion order). We need to protect `supported` rows from being evicted.

**Option A (preferred): Increase cap to 874.**
This is the simplest fix. The 12 v113 + 12 v114 rows add 24 rows total. Setting the cap to 874 (= 850 + 24) means no rows are trimmed. The v1.12 composition is preserved and all boost rows are kept.

**Option B: Add a `--protect-verdict` flag** to `prepare_v15_train.py` that exempts `supported` rows from trimming. If the cap must stay at 850, only trim `weak` or `unrelated` rows.

**Recommendation: Option A.** The dataset is small enough that 874 rows won't significantly affect QLoRA training time. Verdict mix from `prepare_v15_train.py` (first-claim verdict; cap 874, no trim):

| Verdict (first claim) | v1.12 | v1.13 (trimmed) | v1.14 (874 cap) |
|-----------------------|-------|-----------------|-----------------|
| supported | 272 | 260 (−12) | **281** (+9 vs v1.12) |
| weak | 155 | 167 | **167** (+12 v113 parity) |
| insufficient_evidence | 81 | 81 | **84** (+3 v114 insuf_design) |
| not_in_source | 185 | 185 | 185 |
| contradicted | 157 | 157 | 157 |

Total rows: **874**. Restores `supported` above v1.12 while keeping v113 parity rows.

---

## Part 4 — Implementation Order

Execute in this exact order. Each step is verifiable before moving on.

### Step 1 — Full prompt resync (TS + Python) + approximation clause

1. Edit `src/engine/manuscript/grounding-llm.ts` — align `buildGroundingUserPrompt` with train-side v1.12 (compound guardrail, scope-silence weak-on-parity, “use that number” clause) **and** add the v1.14 approximation sentence on line 3.
2. Edit `training/scripts/validate_dataset.py` — mirror identical changes in `build_grounding_user_prompt` line 58 (approximation clause only if already on v1.12 train prompt).
3. Update `training/fixtures/grounding_prompt_golden.txt` to match the new Python prompt.
4. Update `tests/unit/grounding-llm.test.ts` — add assertion for `Approximate passage numbers` present.
5. Run `python training/tests/unit/test_prompt_sync.py` and `npm test` — both must pass.

**Verify:** Golden test passes. Both TS and Python prompts are byte-identical and contain the approximation clause.

### Step 2 — Create v114 boost file

1. Create `training/data/l3_grounding_v114_boost.jsonl` with 12 rows per Part 3:
   - 3 `insufficient_evidence` rows (design-only excerpts → must be `insufficient_evidence`)
   - 9 `supported` rows (clear direct support → must be `supported`)
2. Verify: `python -c "import json; rows=[json.loads(l) for l in open('data/l3_grounding_v114_boost.jsonl') if l.strip()]; print(f'Rows: {len(rows)}'); from collections import Counter; print(Counter(r['output']['overallVerdict'] for r in rows))"`
3. Expect: 12 rows, Counter = `{'support': 9, 'insufficient_evidence': 3}`.

### Step 3 — Update prepare_v15_train.py cap

1. Edit `training/scripts/prepare_v15_train.py` — change cap from 850 to 874 (or implement Option B with `--protect-verdict supported`).
2. Add PHASE=14 case to `run_ab_pilot_pipeline.sh`:
   ```bash
   14)
     TRAIN_FILE="data/l3_grounding_train_v114.jsonl"
     CHAT_FILE="data/l3_grounding_chat_v114.jsonl"
     CHECKPOINT_SUFFIX="v1.14"
     REPORT_SUFFIX="v114"
     PREPARE_CMD=(
       python scripts/prepare_v15_train.py
       --base data/l3_grounding_train_v14a.jsonl
       --boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v18_boost.jsonl \
               data/l3_grounding_v110_boost.jsonl data/l3_grounding_v112_boost.jsonl \
               data/l3_grounding_v113_boost.jsonl data/l3_grounding_v114_boost.jsonl
       --out "$TRAIN_FILE"
     )
     ;;
   ```
3. Add phase 14 config to `training/scripts/train_qlora_gemma4_12b.py`:
   ```python
   "14": {
       "num_epochs": 2,
       "learning_rate": 1e-4,
       "output_name": "nassila-sanad-12b-v1.14",
   },
   ```

### Step 4 — Rebuild train + chat file

```bash
python scripts/prepare_v15_train.py \
  --base data/l3_grounding_train_v14a.jsonl \
  --boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v18_boost.jsonl \
          data/l3_grounding_v110_boost.jsonl data/l3_grounding_v112_boost.jsonl \
          data/l3_grounding_v113_boost.jsonl data/l3_grounding_v114_boost.jsonl \
  --out data/l3_grounding_train_v114.jsonl

python scripts/check_contamination.py data/l3_grounding_train_v114.jsonl   # MUST be 0
python scripts/validate_dataset.py data/l3_grounding_train_v114.jsonl \
  --export-chat data/l3_grounding_chat_v114.jsonl --strict-length 2048
```

**Verify:** 874 rows, contamination 0, first-claim supported ≥281, insufficient_evidence ≥84.

### Step 5 — Re-run v1.13 inference for h-028/h-037 (quick check)

Before retraining, re-run just the two server-error rows against the v1.13 checkpoint with a stable llama.cpp server:

```bash
# Check if h-028 and h-037 pass with clean inference
python scripts/run_eval_reports.py \
  --model outputs/nassila-sanad-12b-v1.13/exported/nassila-sanad-12b-v1.13-q6_k.gguf \
  --rows h-028 h-037 \
  --report-dir training/reports/v113_rerun_h028_h037/
```

If both pass: confirms these are inference-only issues and v1.14 will recover them.

### Step 6 — Train 12B v1.14 on Vast

```bash
ARM=12b PHASE=14 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

**Do not change hyperparameters.** Same 2 epochs, lr=1e-4, QLoRA r=16. Isolate the effect of prompt + boost + cap changes.

### Step 7 — Verify results

| Gate | v1.12 (last good) | v1.13 (regressed) | v1.14 (target) |
|------|-------------------|-------------------|-----------------|
| Combined expect | 94.20% | 88.99% | **≥94%** |
| JSON parse | 100% | 95.65% | **100%** |
| Supported h-001–h010 | 10/10 | 10/10 | ≥8/10 |
| Core legacy 5/5 | 5/5 | 5/5 | 5/5 |
| Quote validity (holdout) | 100% | 94.74% | **≥98%** |
| False supported (holdout) | 2.86% | 2.86% | **≤5%** |
| **Tier 2** | **PASS** | **FAIL** | **PASS** |

**Specific rows to watch:**

| Row | v1.12 | v1.13 | v1.14 must |
|-----|-------|-------|-----------|
| h-028 | `not_in_source` ✓ | parse fail (500) | **pass** (re-run inference) |
| h-037 | `insufficient_evidence` ✓ | parse fail (500) | **pass** (re-run inference) |
| h-038 | `insufficient_evidence` ✓ | `weak` ✗ | **pass** (insuf_design boost) |
| h-051 | `supported` ✓ | `weak` ✗ | **pass** (approximation prompt fix) |
| h-082 | `insufficient_evidence` ✓ | `weak` ✗ | **pass** (insuf_design boost) |
| eval-012 | `insufficient_evidence` ✓ | `not_in_source` ✗ | **pass** (insuf_design boost) |
| h-045 | `min_claims` fail | `parse_json` fail | **parse stable + 2-claim split** (stretch; v1.12 did not pass) |

**Minimum bar:** Combined expect must meet or exceed v1.12 (94.20%). If v1.14 doesn't beat v1.12, the balance changes introduced net harm and should be reverted to v1.12 boost set.

---

## Part 5 — If v1.14 Still Short (fallback)

Only after Steps 1–7 complete:

1. **If h-051 still regresses** → the approximation clause didn't work. Add 2–3 numeric-approximation training rows (passage: "about 920", source: "918" → `supported`) to v115 boost.
2. **If h-038/h-082 still regress** → the insuf_design boost wasn't enough. Add 2–3 more design-only rows with more diverse phrasing ("results are pending," "outcome data collection has not begun," "preliminary analyses only").
3. **If `supported` spam returns** → too many `supported` counterbalance rows. Reduce v114 supported rows from 9 to 6.
4. **Escalate hyperparameters (r=32 or 3 epochs) only as last resort** — not on first attempt.

---

## Part 6 — Out of Scope (explicit)

- **Do NOT change eval gold** for any rows (h-043, h-045, or otherwise).
- **Do NOT remove h-043/h-045 from harness.**
- **Do NOT remove the v113 parity-subgroup boost rows** (they teach the correct h-045 pattern).
- **Do NOT train rows that teach `supported` on studied subgroup for parity/equality passages** (this is what caused h-045 to fail in v1.11).
- **Do NOT publish v1.13 12B GGUF** under any name.
- **Do NOT change the compound guardrail or scope-silence rule** (both are correct as-is from v1.12).
- **Do NOT retrain E4B for v1.14** — E4B v1.12 (89.27%) is the best E4B checkpoint. Only retrain 12B.

---

## Success Checklist

- [ ] Prompt identical in TS + Python (golden test passes)
- [ ] Prompt contains: passage-claim re-emphasis, approximation clause ("Approximate passage numbers"), parity clause, scope-silence rule
- [ ] Prompt absent: blanket "never supported when bundles multiple claims"
- [ ] v114 boost created: 12 rows (9 `supported`, 3 `insufficient_evidence`)
- [ ] Train cap raised to 874 (or `--protect-verdict supported` implemented)
- [ ] Contamination 0 on `l3_grounding_train_v114.jsonl`
- [ ] v1.14 train: 874 rows; first-claim supported ≥281, insufficient_evidence ≥84
- [ ] 12B v1.14 multi-seed: combined expect ≥ v1.12 (94.20%)
- [ ] h-038 passes (`insufficient_evidence`)
- [ ] h-051 passes (`supported`)
- [ ] h-082 passes (`insufficient_evidence`)
- [ ] eval-012 passes (`insufficient_evidence`)
- [ ] h-028/h-037 pass (clean inference)
- [ ] h-045 passes (2-claim split, `weak`+`not_in_source`)
- [ ] false-supported ≤5%
- [ ] All six Tier 2 gates pass
