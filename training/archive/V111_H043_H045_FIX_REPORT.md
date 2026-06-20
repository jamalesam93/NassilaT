# v1.11 Fix Report — h-043 & h-045 Root Cause Analysis

> **For:** Cursor / Composer implementation on v1.11 (E4B first, 12B if it works).
> **Source of truth:** `training/data/eval_holdout_90.jsonl`, `training/scripts/evaluate_outputs.py`, and the actual multi-seed predictions under `training/reports/ab_*/seed_*_predictions.jsonl`.
> **Date:** 2026-06-18.

**Implementation status (2026-06-17):** Steps 1–3 complete locally. Eval gold fixed; v1.10 regrade confirms h-043 pass (seeds 42–44: combined 87.83% / 89.56% / 89.56%); h-045 still fail. Prompt scope-silence + per-conjunct compound rule synced (TS + Python + golden fixture). v111 boost expanded to 29 rows (12 scope-split); train v111 rebuilt (contamination 0). **Pending:** Vast `ARM=e4b PHASE=11 MULTI_SEED=1` — see [`training/archive/PHASE2_10_V111_WALKTHROUGH.md`](training/archive/PHASE2_10_V111_WALKTHROUGH.md).

---

## TL;DR

The diagnosis docs describe h-043 and h-045 as "unfixable multi-claim failures." After reading the **actual model outputs** across all 12 prediction files (E4B + 12B × 3 quants × 3 seeds), the reality is different — and more fixable — than documented:

| Row | Documented failure mode | **Actual** failure mode | Verdict |
|-----|-------------------------|-------------------------|---------|
| **h-043** | "spurious `supported` on absent sub-claim" | Model emits `supported` on the **pain** conjunct, which **is** in the source ("Pain scores were similar between groups"). The gold forbids `supported` entirely. | **Gold label is likely wrong.** The model is doing the right thing. |
| **h-045** | "scope not surfaced as `not_in_source`" | E4B correctly splits and calls `weak`; 12B bundles into a single claim and calls `contradicted`. The gold wants `not_in_source`/`insufficient_evidence` **and** a 2-claim split. | **Fixable** — but via prompt + eval, not data. |

Neither row should block v1.11. Read on for the full evidence and the exact changes to make.

---

## Part 1 — The Actual Gold Rows

From `training/data/eval_holdout_90.jsonl`:

### h-043

```json
{
  "id": "h-043",
  "passage": "Both groups had similar pain scores and identical hospital costs (Park, 2020).",
  "source_excerpt": "Pain scores were similar between groups. Cost analyses were beyond the scope of this report.",
  "expect": {
    "must_parse_json": true,
    "forbidden_claim_verdict": ["supported"],
    "any_claim_verdict": ["not_in_source", "insufficient_evidence"]
  }
}
```

**What the eval demands:** No claim may be `supported`. At least one claim must be `not_in_source` or `insufficient_evidence`.

**What a careful reader sees:** The passage says "similar pain scores" — the source says "Pain scores were similar between groups." That is **direct, unhedged, factual support.** The natural verdict for the pain conjunct is `supported`. The gold forbids it anyway.

### h-045

```json
{
  "id": "h-045",
  "passage": "The intervention worked equally well in adults and children (Daniels, 2024).",
  "source_excerpt": "Efficacy was demonstrated in adults; pediatric data were not collected.",
  "expect": {
    "must_parse_json": true,
    "forbidden_claim_verdict": ["supported"],
    "any_claim_verdict": ["not_in_source", "insufficient_evidence"]
  }
}
```

**What the eval demands:** No `supported`. At least one `not_in_source`/`insufficient_evidence`. (Note: no `min_claims: 2` here — unlike the diagnosis docs imply.)

**What a careful reader sees:** The source addresses adults (`supported`/`weak`) but is silent on children (scope not studied → `not_in_source`). The gold wants the pediatric conjunct isolated as `not_in_source`. This is a defensible **scope-silence convention.**

---

## Part 2 — What the Models Actually Output

### h-043 predictions (all 12 runs)

Every single run — E4B Q6, 12B Q4/Q6/Q8, all 3 seeds — produces **substantially identical output**:

```json
{
  "claims": [
    {
      "claim": "Both groups had similar pain scores",
      "verdict": "supported",
      "sourceQuotes": ["Pain scores were similar between groups"]
    },
    {
      "claim": "identical hospital costs",
      "verdict": "not_in_source",          // Q6/Q8; 12B Q4 says "contradicted"
      "sourceQuotes": [],
      "rationale": ["Cost analyses were beyond the scope of this report"]
    }
  ],
  "overallVerdict": "weak"
}
```

**The model is not failing.** It correctly:
- Splits the compound claim into two atomic claims (the exact behavior every boost since v1.7 has tried to teach)
- Assigns `supported` to the pain conjunct with a valid verbatim quote
- Assigns `not_in_source` to the cost conjunct with correct rationale

The **only** reason the row fails is the `forbidden_claim_verdict: ["supported"]` gate. The model emits a `supported` verdict on a claim that **the source directly supports.** That is correct behavior by any sane citation-grounding definition.

### h-045 predictions

| Arm | Behavior |
|-----|----------|
| **E4B Q6** (all seeds) | **Single claim**, `weak`, with correct rationale: *"partial alignment; efficacy in adults but no data on children."* |
| **12B Q6/Q4/Q8** (all seeds) | **Single claim**, `contradicted`, with rationale: *"pediatric data were not collected, contradicting equal efficacy."* |

**Both fail** for the same reason: neither emits `not_in_source`. E4B's `weak` is actually more defensible than 12B's `contradicted` — "data were not collected" is silence, not refutation.

The gold wants a **2-claim split** (adults + children) where the children claim is `not_in_source`. Neither model splits here. This is the real, fixable gap.

---

## Part 3 — Root Cause: Why They Keep Failing

### h-043 is a mislabeled row (the gold is wrong)

The gold forbids `supported`, but the source **literally says** "Pain scores were similar between groups" — a verbatim match for the passage claim "Both groups had similar pain scores." There is no hedge, no scope limitation, no qualification. The model would have to **lie** (call a directly-supported claim `weak` or `not_in_source`) to pass this row.

This is the same class of bug as the v1.8 eval-018 fix, where the gold expected an incorrect `supported` that had to be corrected to `contradicted` + `not_in_source`. h-043's gold is the mirror image: it forbids a correct `supported`.

**Evidence the gold is fragile:** During the v1.5 contamination incident, `l3-v15-multi-001` (a contaminated copy of h-043) was added to training with a `supported` label — and the model happily learned it, because `supported` is the correct answer. The only reason h-043 has "never passed" is that the eval demands an incorrect label.

### h-045 is a real gap (scope-silence convention is under-specified)

This one is fixable. The failure is consistent and structural:

1. **Neither model splits the compound claim.** The passage "worked equally well in adults and children" is a single compound claim. The gold wants it split into "adults" (supported/weak) + "children" (not_in_source). The models treat it as one unitary claim.

2. **The verdict choice reflects absent reasoning about scope.** E4B says `weak` (defensible — partial evidence); 12B says `contradicted` (less defensible — silence ≠ refutation). Neither recognizes that "pediatric data were not collected" is a scope-silence signal that should produce a separate `not_in_source` claim for the children conjunct.

3. **The prompt never teaches scope-silence splitting.** The v1.10 prompt rule says "split conjuncts on compound passages; mixed outcomes → weak/contradicted/not_in_source." But it does **not** say: "when the source is silent about a specific subgroup mentioned in the passage, that subgroup is `not_in_source`." The convention is implicit, never stated.

---

## Part 4 — The Fixes

### Fix 1 (h-043): Correct the gold label — DO NOT train around it

**File:** `training/data/eval_holdout_90.jsonl` and `training/data/eval_holdout_45.jsonl` (both contain the same row).

**Change the `expect` block** from:

```json
"expect": {
  "must_parse_json": true,
  "forbidden_claim_verdict": ["supported"],
  "any_claim_verdict": ["not_in_source", "insufficient_evidence"]
}
```

**to one of the two options below.**

**Option A — Recommended (accept `supported` on the pain conjunct):**

```json
"expect": {
  "must_parse_json": true,
  "min_claims": 2,
  "any_claim_verdict": ["not_in_source", "insufficient_evidence"]
}
```

Rationale: drops the `forbidden_claim_verdict: ["supported"]` line (the source genuinely supports pain similarity), adds `min_claims: 2` to preserve the compound-split requirement that makes this a multi-claim test. The cost conjunct must still be `not_in_source`.

**Option B — Conservative (keep `supported` forbidden but make it a monitor row):**

Add `"meta": {"eval_category": "multi_claim", "monitor_only": true}` and exclude h-043 from the `forbidden_claim_verdict` gate computation in `scripts/tier_gates.py`. This keeps the row in the harness for visibility without making it a ship blocker.

**Why Option A over B:** Option A is honest. The source supports the pain claim. Forcing the model to deny a directly-supported claim would corrupt its calibration — exactly the whack-a-mole pattern seen in v1.9, where supported-calibration rows caused false-supported regression. **Do not add training rows that teach the model to call `supported` claims `weak`.** That will break h-008/h-011/h-031 (the rows where E4B already wrongly calls `weak`).

### Fix 2 (h-045): Teach scope-silence splitting via prompt + boost

This requires two coordinated changes.

#### 2a. Prompt rule — add explicit scope-silence convention

**Files:** `src/engine/manuscript/grounding-llm.ts` (`buildGroundingUserPrompt`) and `training/scripts/validate_dataset.py` (`build_grounding_user_prompt` — they must stay in sync).

Add this rule to the compound-claim guidance section of the prompt:

> **Scope-silence rule.** If the passage asserts a claim about a specific population, subgroup, or condition (e.g., "in adults and children", "in men and women", "in pediatric and elderly patients"), and the source excerpt (a) addresses one subgroup but (b) explicitly states or implies the other subgroup was not studied / not collected / not part of the analysis, then:
> - Split into one claim per subgroup.
> - The unstudied subgroup receives verdict `not_in_source`, **never** `contradicted`. Silence about a subgroup is absence of evidence, not evidence of refutation.
> - The studied subgroup receives `supported` / `weak` per the normal rules.

This is the **single most important change.** 12B currently calls h-045 `contradicted` because nothing in the prompt tells it that "data were not collected" means `not_in_source`. State it explicitly.

#### 2b. Boost rows — increase scope-split density

The current `l3_grounding_v111_boost.jsonl` has only **4 scope rows** (`v111-scope-001..004`). That is ~0.5% of the 850-row dataset — below the threshold where boost rows reliably transfer (v1.7 showed ~2% is too low; v1.10's working boosts were ~10%).

**Expand to 10–12 scope-split rows.** Use diverse subgroup pairings so the model learns the pattern, not the specific words:

| id | subgroup pair | source pattern |
|----|---------------|----------------|
| v111-scope-001..004 | (existing) adults/teens, adults/infants, adults/children, adults/adolescents | "may have been observed in adults; [pediatric] not collected" |
| v111-scope-005 | men/women | " efficacy in men; women not enrolled" |
| v111-scope-006 | elderly/young | "response in elderly; young adults excluded" |
| v111-scope-007 | urban/rural | "urban sites; rural sites not part of study" |
| v111-scope-008 | severe/mild | "severe cohort only; mild disease not assessed" |
| v111-scope-009 | early-stage/late-stage | "early-stage enrolled; late-stage not collected" |
| v111-scope-010 | summer/winter | "summer season only; winter data not gathered" |
| v111-scope-011 | high-dose/low-dose | "high-dose arm; low-dose not studied" |
| v111-scope-012 | monolingual/bilingual | "monolingual cohort; bilingual group not part of analysis" |

**Critical:** keep the "studied subgroup" verdict as `weak` (hedged) OR add a mix where some are `supported` (unhedged source). The current v111 scope rows all use `weak` for the studied subgroup ("may have been observed"). Add 3–4 rows where the studied subgroup is **cleanly `supported`** (e.g., "Efficacy was demonstrated in adults" → `supported`), so the model does not learn that scope rows always mean `weak`.

**Each scope row must have `min_claims: 2`** implied by structure (one claim per subgroup).

#### 2c. Eval harness — add `min_claims: 2` to h-045

Update h-045's `expect` block:

```json
"expect": {
  "must_parse_json": true,
  "min_claims": 2,
  "forbidden_claim_verdict": ["supported"],
  "any_claim_verdict": ["not_in_source", "insufficient_evidence"]
}
```

This makes the compound-split requirement explicit and machine-checkable, consistent with eval-018's v1.8 treatment.

---

## Part 5 — Implementation Order for Cursor/Composer

Execute in this exact order. Each step is verifiable before moving on.

### Step 1 — Fix the eval rows (no training needed)

1. Edit `training/data/eval_holdout_90.jsonl`: change h-043's `expect` (Option A) and add `min_claims: 2` to h-045.
2. Edit `training/data/eval_holdout_45.jsonl`: apply identical changes (both files share the rows).
3. Re-run the **existing** v1.10 predictions through the eval harness to confirm the gate flips:

```bash
python scripts/run_eval_reports.py \
  --predictions reports/ab_e4b_q6_k_v110/seed_42_predictions.jsonl \
  --repair --prefix v110_regraded_ \
  --holdout data/eval_holdout_90.jsonl
```

**Expected result:** E4B v1.10 should jump from 88.12% to ~89–90% combined (h-043 now passes; h-045 still fails until retrained). 12B v1.10 should jump to ~96%. This confirms the eval fix is correct **before** spending GPU on retraining.

### Step 2 — Add the prompt rule (both repos)

1. `src/engine/manuscript/grounding-llm.ts` — add the scope-silence rule to `buildGroundingUserPrompt`.
2. `training/scripts/validate_dataset.py` — mirror the identical rule in `build_grounding_user_prompt` so train-time and inference-time prompts match. **These two functions must stay byte-identical** (v1.4a lesson #3).

### Step 3 — Expand the v111 boost

1. Add 6–8 new scope-split rows to `training/data/l3_grounding_v111_boost.jsonl` per the table in §2b. Mix `weak` and `supported` verdicts on the studied subgroup.
2. Rebuild the merged dataset:

```bash
python scripts/prepare_v15_train.py \
  --base data/l3_grounding_train_v14a.jsonl \
  --boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v18_boost.jsonl \
          data/l3_grounding_v110_boost.jsonl data/l3_grounding_v111_boost.jsonl \
  --out data/l3_grounding_train_v111.jsonl
python scripts/check_contamination.py data/l3_grounding_train_v111.jsonl   # MUST be 0
python scripts/validate_dataset.py data/l3_grounding_train_v111.jsonl
```

### Step 4 — Train E4B v1.11 on Vast

```bash
ARM=e4b PHASE=11 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

Same hyperparameters (2 epochs, lr=1e-4, QLoRA r=16). Do **not** change hyperparameters yet — isolate the effect of the eval fix + prompt + boost first.

### Step 5 — Verify against regraded gates

After training, check the `reports/ab_e4b_q6_k_v111/multi_seed_aggregate.json`:
- Combined expect: target ≥92% (was 88.12%)
- Quote validity holdout: target ≥98% (was 89.47%)
- False supported holdout: target ≤5% (was 6.57%)
- h-045 specifically: should now split and emit `not_in_source` on the pediatric conjunct

### Step 6 — If E4B passes, retrain 12B with the same recipe

```bash
ARM=12b PHASE=11 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

The same data + prompt changes should push 12B from 94.79% toward 96–97%, and may also fix h-088 (the `min_claims` row in the extension holdout that 12B currently fails at 69.23% multi_claim rate).

---

## Part 6 — Why NOT to Try These (Anti-Recommendations)

1. **Do NOT add training rows that teach the model to call a directly-supported claim `weak`.** This is what h-043 currently demands. It will break calibration and regress h-008/h-011/h-031. Fix the gold instead.

2. **Do NOT increase LoRA rank (r=32) or epochs (3) in the first v1.11 run.** The v1.4b experiment proved 3 epochs @ 1.5e-4 does not help. Isolate the data/prompt/eval changes first; only escalate hyperparameters if the clean run falls short.

3. **Do NOT remove h-043 or h-045 from the harness.** Keep them — but fix h-043's label and tighten h-045's `min_claims`. Removing rows weakens the harness; correcting labels strengthens it.

4. **Do NOT trust the A/B `multi_claim >= 0.80` sub-gate.** It is not a Tier 2 gate. h-088 and similar `min_claims` rows are hard across all versions. Treat multi_claim as a monitoring metric, not a ship blocker (this is already the documented policy in `OUROBOROS_CONTEXT.md` §11).

---

## Part 7 — Expected Outcomes

### After Step 1 only (regrade existing predictions, no retraining)

| Metric | E4B v1.10 (current) | E4B v1.10 (regraded) |
|--------|---------------------|----------------------|
| Combined expect | 88.12% | **~89.2%** (h-043 now passes) |
| h-043 | fail | **pass** |
| h-045 | fail | still fail (needs prompt + retrain) |

### After full v1.11 (Steps 1–4)

| Metric | E4B v1.10 | E4B v1.11 (target) | 12B v1.10 | 12B v1.11 (target) |
|--------|-----------|--------------------|-----------|--------------------|
| Combined expect | 88.12% | **≥92%** | 94.79% | **≥96%** |
| Quote validity | 89.47% | **≥98%** | 100% | 100% |
| False supported | 6.57% | **≤5%** | 2.82% | ≤2.5% |
| h-043 | fail | **pass** (label fixed) | fail | **pass** |
| h-045 | fail | **pass** (prompt + boost) | fail | **pass** |
| Tier 2 | FAIL | **PASS** | PASS | PASS |

The two single biggest levers, in order of impact:

1. **Fix h-043's gold label** (instant +1 point on E4B, free, no GPU cost)
2. **Add the scope-silence prompt rule** (the reason 12B calls h-045 `contradicted` instead of `not_in_source`)

Do these two before anything else. They alone may close most of the gap.
