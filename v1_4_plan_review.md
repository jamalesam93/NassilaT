# Cross-Review: Cursor's v1.4 Plan vs. Training Diagnosis

## Overall Verdict

> [!TIP]
> **The plan is solid.** Cursor correctly validated all diagnosis findings against the actual codebase, confirmed the root causes with evidence from `v1_3_predictions.jsonl`, and proposes fixes in the right priority order. The plan addresses **8 of 9 diagnosed issues** and explicitly defers items that shouldn't be in scope (12B upgrade, new row types, Docker pre-bake).

There are **1 gap**, **2 risks**, and **2 missed opportunities** worth flagging before execution.

---

## Issue-by-Issue Coverage Matrix

| # | Diagnosed Issue | Severity | Plan Section | Addressed? | Notes |
|---|---|---|---|---|---|
| 1 | Inconsistent JSON schema | 🔴 Critical | P0 — `canonical_claim` | ✅ **Yes, correctly** | Fixed key order, `hasNumericClaim` always last scalar |
| 2 | Balancing bug (specialized rows crowded out) | 🟠 High | P0 — Priority balancing | ✅ **Yes, correctly** | `PRIORITY_SUFFIXES`, all priority rows guaranteed |
| 3 | Prompt format duplication | 🟠 High | P1 — Prompt dedup | ⚠️ **Partially** | See Gap 1 below |
| 4 | Hyperparameter oscillation | 🟡 Medium | P1 — Restore v1.2 | ✅ **Yes** | 3 epochs, 1.5e-4; but see Risk 1 |
| 5 | Tiny core eval set | 🟡 Medium | P2 — Expanded core eval | ✅ **Yes** | 5 → ≥20 rows, legacy 5 kept for backward compat |
| 6 | No mid-training eval loop | 🟡 Medium | P1 — Checkpoints + eval loss | ✅ **Yes, pragmatically** | Eval loss mid-train; full harness only post-GGUF |
| 7 | Sequence length truncation risk | 🟡 Low-Med | P1 — Seq-length validation | ✅ **Yes** | `audit_chat_seq_lengths.py` + raise to 2048 |
| 8 | Supported-paraphrase bias inversion | 🟢 Low | Implicitly addressed | ✅ **Indirect** | Priority balancing ensures `-sanad-` rows survive |
| 9 | Process overhead / iteration cost | 🟢 Low | P2 — `run_vast_pipeline.sh` | ✅ **Yes** | Single-command pipeline; Docker deferred (reasonable) |

---

## What the Plan Gets Right

### 1. `canonical_claim` helper (P0, Issue 1) — Excellent

The single-function approach is exactly the right fix. By forcing all 15+ generator functions through one helper, schema drift becomes structurally impossible. The key insight — **`hasNumericClaim` as last key (scalar terminator)** — directly solves the bracket-confusion pattern.

The plan also correctly extends the audit script to fail if `hasNumericClaim` is not the last serialized key. This prevents regression.

### 2. Priority balancing (P0, Issue 2) — Excellent

The `PRIORITY_SUFFIXES` approach with guaranteed inclusion before generic quota filling is the right architecture. The plan includes a unit test with synthetic pools, which is important — the current `balance_rows` has no tests.

### 3. Explicit "NOT doing" list — Smart

The plan explicitly excludes 12B model upgrade, new row types, Docker pre-bake, and UI shipping. This shows discipline and prevents scope creep.

### 4. Failure taxonomy (P2, Issue 6.3) — Good addition

Adding `failure_mode` enum (`parse_json`, `wrong_verdict`, `quote_invalid`, `forbidden_verdict`, `min_claims`) to per-row reports is exactly what's needed for cross-version tracking. The diagnosis identified this gap.

### 5. Contingency plan (line 255) — Thoughtful

> "If JSON parse recovers but supported stays low → v1.5 targets loss weighting / contrastive pairs (h-001 smoking gun from diagnosis §6.2)"

This shows understanding that v1.4 may not solve everything and pre-plans the next step.

---

## ~~Gap 1~~ — Prompt Deduplication: Safe for v1.4 ✅

**Plan says:** Remove duplicated system line from `build_grounding_user_prompt` line 56; verify `grounding-llm.ts` stays aligned.

**Original concern:** If the training prompt is changed but the production app isn't updated simultaneously, prompt mismatch during inference.

**Updated assessment:** NassilaT is a **standalone training repo** — the production app lives in [Nassila](https://github.com/jamalesam93/Nassila) and will only be merged once the Sanad worker passes go/no-go. This means prompt dedup in NassilaT is **safe for v1.4** — there's no live production deployment to break. When merging NassilaT into Nassila, the `grounding-llm.ts` prompt can be aligned at that point as part of the merge checklist. **This is a non-issue for v1.4.**

---

## Risk 1 — Still Changing Multiple Variables Simultaneously

**Plan says (line 160):**
> "v1.4 changes schema + balancing + hyperparams together only because diagnosis ties them to one regression; document in plan that v1.5+ changes one knob at a time."

**The risk:** This is a reasonable pragmatic choice, but it's worth noting that the plan changes **at minimum 5 variables** in one iteration:

1. JSON schema (key order + always emit all keys)
2. Balancing algorithm (priority inclusion)
3. Epochs (2 → 3)
4. Learning rate (1e-4 → 1.5e-4)
5. Seed (45 → 46)
6. Prompt format (system line dedup)
7. Sequence length (1536 → 2048)

If v1.4 passes go/no-go, great. If it doesn't, you'll have the **same diagnostic problem** as before — which of the 7 changes helped and which hurt?

**Recommendation:** Consider a **two-step v1.4**:
- **v1.4a**: Schema fix + priority balancing only (same hyperparams as v1.3). This isolates whether the data fixes alone restore v1.2-level JSON stability.
- **v1.4b**: If v1.4a restores JSON parse to ~100%, add hyperparameter changes.

This costs one extra Vast run (~$3-5) but gives clean attribution.

---

## Risk 2 — `canonical_claim` Default Value Subtlety

**Plan proposes:**
```python
def canonical_claim(*, claim, verdict, source_quotes=None, rationale=None, has_numeric=None):
    return {
        "claim": claim,
        "verdict": verdict,
        "sourceQuotes": source_quotes or [],
        "rationale": rationale or [],
        "hasNumericClaim": has_numeric if has_numeric is not None else bool(re.search(r"\d", claim)),
    }
```

**The risk:** `source_quotes or []` means if `source_quotes=[]` is explicitly passed (empty list), it stays `[]`. Good. But if a generator accidentally passes `source_quotes=None` for a `supported` verdict, the training label will have `"sourceQuotes": []` — a supported claim with no quotes. The existing `validate_l3_record` would catch this (line 135: `supported requires sourceQuotes`), but only if validation runs **after** the canonical helper, not before.

**Recommendation:** Add an assertion inside `canonical_claim`:
```python
if verdict == "supported" and not source_quotes:
    raise ValueError(f"supported claim must have sourceQuotes: {claim[:60]}")
```

---

## Missed Opportunity 1 — Per-Row Cross-Version Failure Tracking

The plan adds `failure_mode` to per-row reports, which is great. But it doesn't create a **cross-version comparison view**. The diagnosis identified that the same rows (h-001–h-010) fail across versions but with **different failure modes** (wrong verdict in v1.0/v1.1 → parse failure in v1.3).

**Recommendation:** Add a small script or report section that loads all `v1_*_eval_holdout_report.json` files and produces a matrix:

| Row | v1.0 | v1.1 | v1.2 | v1.3 | v1.4 |
|---|---|---|---|---|---|
| h-001 | wrong_verdict | wrong_verdict | ✅ | ✅ | ? |
| h-002 | wrong_verdict | wrong_verdict | ✅ | parse_json | ? |

This would make regression detection instant.

---

## Missed Opportunity 2 — Adapter Checkpoint Selection

The plan adds `save_strategy="steps"` and `save_total_limit=3`, which saves intermediate checkpoints. But it doesn't specify **how to select the best checkpoint** for merge/GGUF. The plan says `load_best_model_at_end=True` based on eval loss — but eval loss may not correlate with the JSON parse rate metric that matters most.

**Recommendation:** After training, save the 3 checkpoints. Run the full 50-row eval harness on the **final** checkpoint first. If it passes, ship it. If it doesn't, run the harness on the other two checkpoints and pick the best. This is cheap (each eval run is ~15 min) and could save a wasted iteration.

---

## Summary Verdict

| Aspect | Rating |
|---|---|
| **Diagnosis coverage** | 8/9 issues addressed (Issue 3 partially) |
| **Technical correctness** | ✅ All proposed code changes are sound |
| **Priority ordering** | ✅ P0/P1/P2 matches diagnosis impact ranking |
| **Scope discipline** | ✅ Explicit "NOT doing" list prevents creep |
| **Risk awareness** | ⚠️ Multi-variable change acknowledged but not mitigated |
| **Execution feasibility** | ✅ Clear 8-step order; single Vast run at end |

**Bottom line:** The plan will very likely fix the v1.3 JSON parse collapse and restore v1.2-level stability. The main risk is that changing too many variables simultaneously will make the next iteration's diagnosis harder if something unexpected happens. Consider the v1.4a/v1.4b split if you want cleaner attribution, but if you want to move fast, executing the plan as-is is a reasonable bet.
