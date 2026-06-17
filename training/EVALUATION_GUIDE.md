# Evaluation Guide

How to measure whether your fine-tuned **Nassila grounding** model is good enough to use — and better than stock Gemma 4 E4B Q6_K.

**Canonical go/no-go gates:** [Nassila `docs/OUROBOROS_CONTEXT.md` §10](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md) (Tier 2 model gates + Tier 2b product-safety in app). This file describes *how* to measure; §10 is the single source for *thresholds*.

---

## Evaluation philosophy

The model is **advisory**. Nassila still applies deterministic checks ([`passageVerdictFromGroundingClaims`](../src/engine/manuscript/grounding-llm.ts), lexical overlap). Your eval should mirror those failures:

- Broken JSON → user sees warnings
- Hallucinated quotes → academic trust risk
- False `supported` → worse than no LLM

Optimize for **trust**, not fluent writing.

---

## Datasets

| Set | File | Use |
|-----|------|-----|
| Public synthetic template | [`data/eval_samples.jsonl`](./data/eval_samples.jsonl) | CI-style checks, learning the pipeline |
| 45-row holdout | [`data/eval_holdout_45.jsonl`](./data/eval_holdout_45.jsonl) | Legacy regression matrix only |
| **90-row hardened holdout** | [`data/eval_holdout_90.jsonl`](./data/eval_holdout_90.jsonl) | **Canonical Tier 2 go/no-go** (build via `build_hardened_holdout.py`) |
| Private held-out | `eval_private.jsonl` (you create, do not commit) | Real manuscript snippets you care about |

Never train on eval ids you use for go/no-go decisions.

### One-shot batch run

```powershell
python scripts/run_l3_eval_batch.py --model "YOUR_MODEL_ID" \
  --data data/eval_samples.jsonl data/eval_holdout_45.jsonl \
  --retry 1 --repair --out outputs/predictions.jsonl

python scripts/evaluate_outputs.py \
  --eval data/eval_samples.jsonl \
  --predictions outputs/predictions.jsonl \
  --report outputs/eval_report.json --repair
```

The runner prints **strict** and **with-repair** parse rates plus retry recoveries; the evaluator reports both rates separately so you can decide whether to ship a parser-side repair or keep guardrails strict.

---

## Metrics

### 1. JSON parse rate

**Definition:** Fraction of model outputs where `parseGroundingJson` equivalent succeeds (valid object with `claims` array).

**Target (Tier 2, §10):** ≥ **98%** with repair on combined 70-row harness

**How to measure:**

```bash
python scripts/evaluate_outputs.py --eval data/eval_samples.jsonl --predictions outputs/baseline_predictions.jsonl
```

### 2. Quote validity rate

**Definition:** For every claim with `verdict: supported`, every `sourceQuotes[]` entry must be a substring of `source_excerpt`.

**Target (Tier 2, §10):** ≥ **98%** on **holdout** slice (report extended-core separately via `run_eval_reports.py`)

This is non-negotiable for an academic tool.

### 3. Verdict accuracy (claim-level)

**Definition:** Match gold `claims[].verdict` on eval rows (exact match per claim after alignment — use claim text similarity or id if you add claim ids in eval).

**Target v1:** ≥ **80%** on balanced eval

Harder cases (`weak` vs `not_in_source`) may stay ambiguous; track separately.

### 4. False supported rate (critical)

**Definition:** On eval rows where gold expects `contradicted`, `not_in_source`, or `forbidden_claim_verdict`, model must not emit `supported`.

**Target (Tier 2, §10):** ≤ **5%** on **holdout** slice. Monitor extended-core in `false_supported_by_slice` (not a ship gate).

### 4b. Supported h-001–h-010 (Tier 2 sub-gate)

**Definition:** Holdout rows `h-001` … `h-010` (paraphrase-supported cluster) must pass expect checks.

**Target:** ≥ **8/10** pass.

### 4c. Core legacy 5 (Tier 2 sub-gate)

**Definition:** All 5 rows in `eval_samples.jsonl` must pass.

**Target:** **5/5** pass.

### 5. Numeric mismatch detection

**Definition:** Eval rows where passage says 50% but excerpt says 30% must yield `contradicted` or at least not `supported`.

**Target v1:** ≥ **90%** correct on numeric mismatch subset

### 6. Latency (operational)

**Definition:** Seconds per L3 call on your hardware (passage + ~4k excerpt).

**Guideline:**

| Hardware | Acceptable per call |
|----------|---------------------|
| Laptop GPU Q6_K | ≤ 15–30 s |
| CPU-only | Often too slow for batch audit |

Track p50 and p95 if auditing full manuscripts.

### 7. Overall rollup alignment (optional)

Simulate [`passageVerdictFromGroundingClaims`](../src/engine/manuscript/grounding-llm.ts) with deterministic bucket from eval context. Compare final `pass` vs `warn` vs `insufficient_evidence`.

---

## Eval record `expect` block

See [DATASET_SCHEMA.md](./DATASET_SCHEMA.md). Supported checks in [`scripts/evaluate_outputs.py`](./scripts/evaluate_outputs.py):

| Key | Meaning |
|-----|---------|
| `must_parse_json` | Output must parse |
| `any_claim_verdict` | At least one claim has one of these verdicts |
| `all_claim_verdicts_in` | Every claim verdict must be in list |
| `forbidden_claim_verdict` | Must not appear |
| `quotes_must_be_substrings` | Validate supported quotes |
| `min_claims` | Minimum claim count |

---

## Baseline vs fine-tuned comparison

Run the **same** eval set twice:

1. **Baseline** — stock LM Studio Gemma 4 E4B Q6_K
2. **Tuned** — `nassila-grounding-e4b-v1` GGUF

Record a table:

| Metric | Baseline | Tuned v1 | Delta |
|--------|----------|----------|-------|
| JSON parse rate | | | |
| Quote validity | | | |
| False supported | | | |
| Verdict accuracy | | | |
| p50 latency | | | |

Ship tuned model only if critical metrics improve without latency regression you cannot accept.

---

## Regression checklist (manual)

For 10 random eval rows, human review:

- [ ] Claims are atomic (not one giant claim)
- [ ] Rationale is not copied from passage as if it were source
- [ ] `insufficient_evidence` used when excerpt is too thin
- [ ] Abstract-only cases not over-confident
- [ ] No invented DOI or author in JSON

---

## Webpage task metrics (phase 2)

When training [`webpage_citation_samples.jsonl`](./data/webpage_citation_samples.jsonl):

| Metric | Target |
|--------|--------|
| CSL type accuracy | ≥ 85% on eval |
| Required field presence (title, URL) | ≥ 95% |
| Wrong author type (person vs org) | ≤ 10% |
| Harmful auto-fix suggestions | 0 in manual review |

---

## When to stop training

Stop (or roll back) if:

- Eval JSON parse rate drops vs earlier checkpoint
- False supported rate rises
- Quote validity drops below 95%
- Model collapses to always `insufficient_evidence`

Use **early checkpoint** with best eval, not last epoch.

---

## Automation sketch

```bash
# 1. Generate predictions (your inference loop or LM Studio batch)
# 2. Evaluate
python scripts/evaluate_outputs.py \
  --eval data/eval_samples.jsonl \
  --predictions outputs/nassila-v1_predictions.jsonl \
  --report outputs/eval_report.json

# 3. Compare reports
python -c "import json; print(json.load(open('outputs/eval_report.json')))"
```

Commit **reports** only if they contain no private text; keep private eval local.

---

## Go / no-go for Nassila grounding (Tier 2)

**Canonical checklist:** [Nassila `docs/OUROBOROS_CONTEXT.md` §10](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md).

After Vast eval, run:

```bash
python scripts/run_eval_reports.py --predictions reports/v1_5_predictions.jsonl --repair --prefix v1_5_
```

Inspect `tier2_gates` in `*_eval_combined_report.json`. **Go** when `model_gates_passed` is true **and** manual review of 20 hard holdout rows is acceptable.

**Combined expect:** minimum ≥90%; operator target ≥92% (margin buffer).

**Product safety:** app quote-substring guardrail in `grounding-llm.ts` (Tier 2b) — not scored in NassilaT; verify in Nassila unit tests.

**No-go** if any Tier 2 model gate fails — keep v1.4a checkpoint, expand v1.5 dataset (`prepare_v15_train.py`), retrain before ship.
