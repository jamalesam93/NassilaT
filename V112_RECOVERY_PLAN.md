# v1.12 Recovery Plan — E4B Sanad + 31B premium

> **Goal:** Recover from v1.11 regression; E4B ships on **default-tier** gates. **12B v1.12** is the **main quality tier** (Tier 2). **31B** is optional on the same A100 session.
> **Policy:** [`docs/DUAL_TIER_POLICY.md`](docs/DUAL_TIER_POLICY.md)
> **Context:** v1.11 introduced per-conjunct `supported` permission + 12 scope-boost rows; E4B over-applied both, causing a `supported` epidemic (false-supported 6.57%→11.91%, 12 rows regressed).
> **v1.10 (88.12%) remains the best E4B checkpoint. Do NOT publish v1.11 GGUF.**
> **Status:** Prep implemented in repo — operator runs `PHASE=12` on Vast.
> **Date:** 2026-06-18.

---

## TL;DR — Three changes, then retrain

1. **Prompt:** Replace per-conjunct `supported` with a **conditional compound guardrail** ("if any sibling conjunct is `contradicted` or `not_in_source`, no `supported` on siblings — use `weak` at most"). Re-emphasize passage-claim extraction. Keep scope-silence rule.
2. **Boost:** Cut scope rows from 12→6, all `weak` on studied subgroup (aligns with h-045 gold which forbids `supported` on parity passages).
3. **Eval:** No changes. h-043 gold (Option A) stays. h-045 gold stays.

Then rebuild chat file, contamination gate, train E4B v1.12, multi-seed eval.

---

## Part 1 — Root Cause Summary (v1.11 regression)

Three changes all pulled in the same dangerous direction:

| Change | Intended effect | Actual effect on E4B |
|--------|----------------|---------------------|
| Removed "never supported on compound" guardrail | Allow per-conjunct `supported` (for h-043) | E4B spammed `supported` on every conjunct with a source match |
| Added 12 scope-boost rows (10 `weak`, 2 `supported` on studied subgroup) | Teach scope-silence splitting | Model learned "find source sentence → copy as claim → quote → supported/weak" shortcut |
| 2 scope rows with `supported` on studied subgroup | Prevent "scope ⇒ always weak" over-generalization | Taught the exact pattern h-045/h-088 forbid (`supported` on studied arm) |

**Result:** 3 rows fixed (h-031, h-043, h-085), 12 regressed, 12 still failing. Net: −7.5 pts combined, −12.3 pts quote validity, +5.3 pts false-supported.

**Key regressions (seed 42):**

| Row | v1.10 | v1.11 | What happened |
|-----|-------|-------|---------------|
| eval-002, eval-010, eval-012, eval-017, h-012, h-014, h-015 | `contradicted` | `supported` | Model copies source's number as claim text, ignores passage's different number |
| h-042 | `contradicted` + `not_in_source` | `supported` + `supported` | Both conjuncts get `supported`, even "rates were not analyzed" |
| eval-021, h-006, h-047 | `supported` | `weak` (seed-dependent) | Over-hedged some paraphrase-supported rows |

**h-045 status:** Model correctly splits (2 claims) and correctly assigns `not_in_source` to children — but assigns `supported` to adults, which the gold forbids. The scope-silence rule partially worked; the studied-subgroup verdict conflicts with the gold.

---

## Part 2 — Prompt Changes

### Files to edit (must stay in sync)

| File | Function |
|------|----------|
| `src/engine/manuscript/grounding-llm.ts` → `buildGroundingUserPrompt` | App-side prompt |
| `training/scripts/validate_dataset.py` → `build_grounding_user_prompt` | Train-side prompt |
| `training/fixtures/grounding_prompt_golden.txt` | Sync test golden |

### Current state (v1.11 prompt — needs replacement)

The `weak` bullet ends with the compound guidance:
```
'- weak: partial or vague alignment, OR the source hedges (...). Do NOT use weak when the excerpt clearly supports a single passage claim (including paraphrase and 'associated with' / 'significantly' wording).'
```
Then two separate lines follow:
```
'Compound passages: when the passage bundles multiple claims (...), split into one claim per conjunct and evaluate each independently. A conjunct may be supported if SOURCE_EXCERPT clearly supports it, even when another conjunct is not_in_source or weak.'
'Scope-silence rule: ...'
```

### New prompt structure (v1.12)

**Line 3 — Re-emphasize passage-claim extraction (make it more prominent):**
```
'Each claim string MUST restate an assertion from the PASSAGE — do NOT copy source sentences as claim text unless that exact assertion also appears in the passage. When the passage states a number, use that number, not a different number from the source.'
```
This is a stronger version of the existing rule. It directly addresses the v1.11 regression where the model started copying source numbers (78%, 2021, 26.4) as claim text instead of using the passage's numbers (99%, 2018, 32). Bold-style emphasis in the prompt is acceptable here — this is the single most important behavioral guardrail.

**Keep the `weak` bullet as-is** (the cleaned v1.11 version without the trailing compound clause — that's correct).

**Replace the compound line with conditional guardrail:**
```
'Compound passages: when the passage bundles multiple claims (e.g., joined by "and"), split into one claim per conjunct and evaluate each independently. HOWEVER, if any conjunct receives contradicted or not_in_source, do NOT emit supported on sibling conjuncts — use weak at most for those siblings.'
```

Key difference from v1.11: the conditional clause *"if any sibling is contradicted/not_in_source → no supported on siblings"* prevents:
- h-042 pattern (both conjuncts `supported` when one should be `not_in_source`)
- h-045 pattern (studied arm `supported` when unstudied arm is `not_in_source`)
- eval-017 pattern (finding a source number and calling `supported` when the passage's different number implies `contradicted`)

While still allowing:
- h-043 pattern (pain `supported` + costs `not_in_source` → allowed because neither sibling is `contradicted`; the `not_in_source` sibling blocks `supported` on siblings... WAIT — this would break h-043)

**Critical correction:** h-043 expects pain=`supported` + costs=`not_in_source`. Under the conditional rule "if any sibling is `not_in_source` → no `supported` on siblings," h-043 would get pain=`weak` instead of `supported`. That's the same problem as the old blanket rule.

**Revised conditional rule that works for both h-043 and h-045:**
```
'Compound passages: when the passage bundles multiple claims (e.g., joined by "and"), split into one claim per conjunct and evaluate each independently. A conjunct may be supported if SOURCE_EXCERPT directly supports it with matching meaning and numbers — but NOT if the passage asserts a specific number that differs from the source. On compound passages where the passage asserts parity or equality across subgroups (e.g., "equally well in adults and children") and the source addresses only one subgroup, the studied subgroup receives weak (not supported), and the unstudied subgroup receives not_in_source.'
```

This is longer but precisely targets both failure modes:
- **h-043 allowed:** pain conjunct — source directly supports with matching meaning, no parity/equality assertion → `supported` allowed
- **h-045 blocked:** "equally well in adults and children" is a parity assertion → studied arm gets `weak`, not `supported`
- **eval-017 blocked:** passage says 99%, source says 78% → "specific number that differs" → not `supported`

**Keep the scope-silence rule as-is** (already correct):
```
'Scope-silence rule: if the passage asserts a claim about specific subgroups (e.g., adults and children, men and women) and SOURCE_EXCERPT addresses one subgroup but states or implies the other was not studied / not collected / not enrolled, split into one claim per subgroup. The unstudied subgroup receives not_in_source, never contradicted. The studied subgroup receives supported or weak per normal rules.'
```

Note: "receives supported or weak per normal rules" in the scope-silence rule is now overridden by the compound rule's parity clause for equality passages. This is intentional — the compound rule is more specific.

### Full target prompt (for reference)

```
Line 1:  'You are a strict academic citation grounding assistant.'
Line 2:  'Break the manuscript passage into short factual claims (atomic where possible).'
Line 3:  'Each claim string MUST restate an assertion from the PASSAGE — do NOT copy source sentences as claim text unless that exact assertion also appears in the passage. When the passage states a number, use that number, not a different number from the source.'
Line 4:  'For each claim, compare ONLY to SOURCE_EXCERPT (verbatim text from the cited work).'
Line 5:  'Verdict per claim:'
Line 6:  '- supported: SOURCE_EXCERPT contains clear support; you MUST copy 1–3 verbatim sourceQuotes from SOURCE_EXCERPT.'
Line 7:  '- weak: partial or vague alignment, OR the source hedges (may/might/suggest/preliminary/unclear). Do NOT use weak when the excerpt clearly supports a single passage claim (including paraphrase and \'associated with\' / \'significantly\' wording).'
Line 8:  '- not_in_source: not found in excerpt (excerpt may be incomplete).'
Line 9:  '- contradicted: excerpt clearly conflicts.'
Line 10: '- insufficient_evidence: cannot tell from excerpt.'
Line 11: 'Compound passages: when the passage bundles multiple claims (e.g., joined by "and"), split into one claim per conjunct and evaluate each independently. A conjunct may be supported if SOURCE_EXCERPT directly supports it with matching meaning and numbers — but NOT if the passage asserts a specific number that differs from the source. On compound passages where the passage asserts parity or equality across subgroups (e.g., "equally well in adults and children") and the source addresses only one subgroup, the studied subgroup receives weak (not supported), and the unstudied subgroup receives not_in_source.'
Line 12: 'Scope-silence rule: if the passage asserts a claim about specific subgroups (e.g., adults and children, men and women) and SOURCE_EXCERPT addresses one subgroup but states or implies the other was not studied / not collected / not enrolled, split into one claim per subgroup. The unstudied subgroup receives not_in_source, never contradicted. The studied subgroup receives supported or weak per normal rules.'
Line 13: 'Respond with a single JSON object ONLY, no markdown fencing, keys:'
Line 14: '{ "claims": [ { "claim": string, "verdict": "supported"|"weak"|"not_in_source"|"contradicted"|"insufficient_evidence", "hasNumericClaim"?: boolean, "sourceQuotes"?: string[], "rationale"?: string[] } ], "overallVerdict"?: "support"|"weak"|"unrelated"|"insufficient_evidence", "overallRationale"?: string[] }'
Line 15: ''
Line 16: PASSAGE:\n{passage}
Line 17: ''
Line 18: SOURCE_EXCERPT ({label} {url}):\n{source_excerpt}
```

### Test updates

**`tests/unit/grounding-llm.test.ts`** — update the existing prompt checks:
- Keep: `Scope-silence rule` present
- Keep: `never contradicted` present
- Keep: absent `never supported when the passage bundles multiple claims`
- Add: `not a different number from the source` present (passage-claim re-emphasis)
- Add: `parity or equality` present (compound guardrail)
- Add: `receives weak (not supported)` present (parity clause)

**`training/tests/unit/test_prompt_sync.py`** — update golden file:
- Update `fixtures/grounding_prompt_golden.txt` to match the new Python prompt
- Keep all existing tests (scope-silence present, blanket rule absent)

---

## Part 3 — Boost Changes

### Cut scope rows from 12→6

Remove or flip the `supported`-on-studied-subgroup rows that teach the pattern h-045/h-088 forbid:

| Row | Action |
|-----|--------|
| v111-scope-001..004 | **Keep** (existing, all `weak` on studied subgroup) |
| v111-scope-005..010 | **Remove** (repetitive — all identical pattern with different subgroup words; E4B doesn't need 8 variations of the same `weak`+`not_in_source` pattern) |
| v111-scope-011 | **Flip to `weak`** or remove (currently `supported` on studied subgroup — directly teaches the h-045-forbidden pattern) |
| v111-scope-012 | **Flip to `weak`** or remove (same) |

**Target: 6 scope rows total, all `weak` on studied subgroup.** This aligns training signal with h-045's gold (forbids `supported` on parity passages).

If you want to keep some diversity beyond the 4 existing rows, add 2 new rows with different subgroup pairs (e.g., severe/mild, early-stage/late-stage) — but both with `weak` on the studied subgroup.

### Keep all other v111 boost rows

The nosup-compound (6), two-claim-split (3), quote-fidelity (4), insufficient-design (2), and weak-mixed (2) rows are not implicated in the regression. Keep them all.

**New boost total:** 6 (scope) + 6 + 3 + 4 + 2 + 2 = **23 rows** (was 29).

### Rebuild merge

```bash
python scripts/prepare_v15_train.py \
  --base data/l3_grounding_train_v14a.jsonl \
  --boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v18_boost.jsonl \
          data/l3_grounding_v110_boost.jsonl data/l3_grounding_v111_boost.jsonl \
  --out data/l3_grounding_train_v112.jsonl

python scripts/check_contamination.py data/l3_grounding_train_v112.jsonl   # MUST be 0
python scripts/validate_dataset.py data/l3_grounding_train_v112.jsonl \
  --export-chat data/l3_grounding_chat_v112.jsonl --strict-length 2048
```

---

## Part 4 — Implementation Order

Execute in this exact order. Each step is verifiable before moving on.

### Step 1 — Edit prompt in both repos

1. Edit `src/engine/manuscript/grounding-llm.ts` — update `buildGroundingUserPrompt` per Part 2.
2. Edit `training/scripts/validate_dataset.py` — mirror identical changes in `build_grounding_user_prompt`.
3. Update `training/fixtures/grounding_prompt_golden.txt` to match the new Python prompt.
4. Update `tests/unit/grounding-llm.test.ts` — add new assertions per Part 2.
5. Run `python training/tests/unit/test_prompt_sync.py` and `npm test` — both must pass.

**Verify:** Run the Python prompt extraction against the TS source (as in `_verify_prompt_sync.py`) and confirm byte-identity.

### Step 2 — Edit boost file

1. Edit `training/data/l3_grounding_v111_boost.jsonl` — remove scope-005..010, flip scope-011/012 to `weak` (or remove them).
2. Verify: `python -c "import json; rows=[json.loads(l) for l in open('data/l3_grounding_v111_boost.jsonl') if l.strip()]; scope=[r for r in rows if 'scope' in r.get('meta',{}).get('row_type','')]; print(f'Scope rows: {len(scope)}'); [print(f'  {r[\"id\"]}: {[c[\"verdict\"] for c in r[\"output\"][\"claims\"]]}') for r in scope]"`
3. Expect: 4–6 scope rows, all `weak` on studied subgroup, 0 `supported`.

### Step 3 — Rebuild train + chat file

```bash
python scripts/prepare_v15_train.py \
  --base data/l3_grounding_train_v14a.jsonl \
  --boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v18_boost.jsonl \
          data/l3_grounding_v110_boost.jsonl data/l3_grounding_v111_boost.jsonl \
  --out data/l3_grounding_train_v112.jsonl

python scripts/check_contamination.py data/l3_grounding_train_v112.jsonl   # MUST be 0
python scripts/validate_dataset.py data/l3_grounding_train_v112.jsonl \
  --export-chat data/l3_grounding_chat_v112.jsonl --strict-length 2048
```

**Verify:** 850 rows, contamination 0, verdict mix balanced (supported ~268–275 range).

### Step 4 — Train E4B v1.12 on Vast

Update `train_qlora_gemma4_e4b.py` to add phase 12 config:

```python
"12": {
    "num_epochs": 2,
    "learning_rate": 1e-4,
    "output_name": "nassila-sanad-e4b-v1.12",
},
```

Update `run_ab_pilot_pipeline.sh` to add PHASE=12 case (same structure as PHASE=11, pointing to `l3_grounding_train_v112.jsonl`).

```bash
ARM=e4b PHASE=12 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

**Do not change hyperparameters.** Same 2 epochs, lr=1e-4, QLoRA r=16. Isolate the effect of prompt + boost changes.

### Step 5 — Verify results

| Gate | v1.10 (baseline) | v1.11 (regressed) | v1.12 (target) |
|------|------------------|--------------------|-----------------|
| Combined expect | 88.12% | 80.58% | **≥90% (operator ≥92%)** |
| JSON parse | 100% | 100% | 100% |
| Supported h-001–h-010 | 10/10 | ? | ≥8/10 |
| Core legacy 5 | 5/5 | 4/5 (eval-002 regressed) | 5/5 |
| Quote validity (holdout) | 89.47% | 77.19% | **≥90%** |
| False supported (holdout) | 6.57% | 11.91% | **≤5%** |

**Specific rows to watch:**

| Row | v1.10 | v1.11 | v1.12 must |
|-----|-------|-------|-----------|
| h-043 | fail (forbidden `supported`) | **pass** ✅ | **pass** (Option A gold unchanged) |
| h-045 | fail (`contradicted`/`weak`, no split) | fail (`supported` on adult arm) | **pass** (2-claim split, `weak`+`not_in_source`) |
| h-042 | fail | fail (`supported`+`supported`) | **pass** (`contradicted`+`not_in_source` or similar) |
| eval-017, h-012 | pass (`contradicted`) | fail (`supported`) | **pass** (back to `contradicted`) |
| eval-002, eval-010, h-014, h-015 | pass (`contradicted`) | fail (`supported`) | **pass** (back to `contradicted`) |
| eval-021, h-006, h-047 | pass (`supported`) | fail/seed-dep (`weak`) | **pass** (back to `supported`) |

**Minimum bar:** Combined expect must beat v1.10 (88.12%) and false-supported must be ≤ v1.10 (6.57%). If v1.12 doesn't beat v1.10 on combined, the prompt/boost changes introduced net harm and should be reverted entirely.

---

## Part 5 — If v1.12 Still Short (fallback)

Only after Steps 1–4 complete:

1. Inspect remaining failing rows in `multi_seed_aggregate.json`.
2. If `supported` spam persists → the parity clause didn't work; consider the blunter "no `supported` on compound passages at all" (accept h-043 as `weak` + `not_in_source`).
3. If over-hedging persists → reduce the `weak` boost rows further.
4. If numeric-mismatch regressions persist → the passage-claim re-emphasis isn't strong enough; consider adding 3–4 numeric-contrast boost rows (passage says X, source says Y → `contradicted`).
5. Escalate hyperparameters (r=32 or 3 epochs) only as last resort — not on first attempt.

---

## Part 6 — Out of Scope (explicit)

- **Do NOT change eval gold** for h-043 or h-045 (both are correct as-is post v1.11 eval fix).
- **Do NOT remove h-043/h-045 from harness.**
- **Do NOT train rows that teach `supported` on studied subgroup for parity/equality passages** (this is what caused h-045 to fail in v1.11).
- **Do NOT treat `multi_claim >= 0.80` as a Tier 2 ship gate.**
- **Do NOT publish v1.11 GGUF** under any name.

---

## Success Checklist

- [ ] Prompt identical in TS + Python (golden test passes)
- [ ] Prompt contains: passage-claim re-emphasis, parity clause, scope-silence rule
- [ ] Prompt absent: blanket "never supported when bundles multiple claims"
- [ ] Scope boost ≤6 rows, all `weak` on studied subgroup
- [ ] Contamination 0 on `l3_grounding_train_v112.jsonl`
- [ ] E4B v1.12 multi-seed: combined expect ≥ v1.10 (88.12%)
- [ ] h-043 passes (Option A gold)
- [ ] h-045 passes (2-claim split, `weak`+`not_in_source`)
- [ ] false-supported ≤ v1.10 (6.57%)
- [ ] All six Tier 2 gates pass
- [ ] Publish `nassila-sanad-e4b-q6_k.gguf` + update `MODEL_CARD_sanad_e4b.md`
