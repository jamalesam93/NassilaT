# Phase 2.3 — v1.2 plan (dataset + train)

**Prerequisite:** v1.1 NO-GO documented ([MODEL_CARD_v1_1.md](./MODEL_CARD_v1_1.md), [reports/v1_1_eval_combined_report.json](./reports/v1_1_eval_combined_report.json)).

**Goal:** Pass go/no-go on E4B before considering a larger base model.

| Metric | Target |
|--------|--------|
| Expect pass | ≥90% |
| Quote validity (holdout) | ≥98% |
| False supported | ≤5% |

---

## Diagnosis (v1 → v1.1)

| Works | Fails |
|-------|--------|
| JSON schema (100%) | Supported paraphrase → **`weak`** instead of **`supported`** |
| contradicted / weak / insufficient_evidence holdout | not_in_source (67%), multi_claim (50%) |
| False supported (0%) | Quote validity low because few `supported` claims |

**h-001 smoking gun:** correct `sourceQuotes`, wrong verdict, bogus hedge rationale.

This is **verdict calibration**, not JSON or quote extraction.

---

## Is the problem the model size (E4B vs 12B)?

**Short answer: try v1.2 on E4B first.** Evidence does not yet justify jumping to `google/gemma-4-12B-it`.

| Observation | Implication |
|-------------|-------------|
| Stock **E4B** baseline ~**82%** expect pass | E4B can do the task without fine-tuning |
| Tuned v1/v1.1 **worse** on supported than baseline | Fine-tuning **introduced** a conservative `weak` bias — data/signal issue |
| h-001 has **correct quotes**, wrong label | Model understood excerpt; failed a **classification** step |
| contradicted / weak / IE at **100%** on holdout | Capacity exists for other verdicts |
| One Ring v1 ships **E4B** for local LM Studio | 12B ≈ 2× VRAM/RAM; breaks current Q6_K deployment tier |

**When 12B might help:** after E4B plateaus with better labels, aligned eval, and 3 epochs — if supported paraphrase still fails while baseline 12B stock clearly wins on the same harness.

**12B costs:** slower train, larger GGUF, harder Vast/PC inference; defer until E4B path is exhausted.

---

## v1.2 dataset changes (Phase 2.3.1)

### A. Holdout-shaped supported rows (h-001 pattern)

Generate rows that mirror eval structure **without copying holdout text**:

- Short passage paraphrase (“The new test had 95% sensitivity”)
- `sourceQuotes` = full abstract sentence with same numbers
- Verdict **`supported`**, rationale: numeric/factual alignment (not hedging)

Target: **+80–120** new `-supp-holdout-style-` rows from corpus.

### B. Anti–false-weak pairs

For same source sentence, emit **two** training rows:

1. Paraphrase, same numbers → **`supported`**
2. Hedge stripped incorrectly → only **`weak`** when a hedge word was removed from source wording

Reinforces: *wording difference ≠ weak* unless modality was dropped.

### C. Oversample supported paraphrase

Shift `VERDICT_TARGETS` or post-balance:

- supported **≥45%** of train rows (up from ~38%)
- weak **≤12%**

Or duplicate hard supported-paraphrase ids in JSONL (cheap oversampling).

### D. Fix not_in_source misses

Review h-021, h-026, h-028, h-043, h-045 failures; add rows where claim topic ≠ excerpt topic → `not_in_source` / `insufficient_evidence`.

### E. Row count

Target **800–900** rows after generation; audit + 15% spot-check.

**Scripts to touch:** `generate_l3_from_corpus.py`, `audit_l3_labels.py`, tests.

---

## v1.2 training changes (Phase 2.3.2)

| Knob | v1.1 | v1.2 proposal |
|------|------|----------------|
| Epochs | 2 | **3** |
| Learning rate | 2e-4 | **1.5e-4** (optional) |
| Train rows | 700 | 800–900 |
| Output dir | `nassila-grounding-e4b-v1.1` | `nassila-grounding-e4b-v1.2` |

Same QLoRA recipe otherwise (1536 seq, r=16, A6000, Unsloth checkpointing).

---

## v1.2 eval alignment (Phase 2.3.3)

**Hypothesis:** Batch eval sends a **single user message**; training uses **system + user + assistant** chat. Mismatch may hurt supported calibration.

Before next Vast train:

1. Add `run_l3_eval_batch.py --chat-template` (or eval through same `records_to_chat_jsonl` path as train).
2. Re-run **stock E4B** with aligned prompt — confirm baseline still ~82%.

---

## v1.2 Vast workflow

Same as [PHASE2_2_V1_1_WALKTHROUGH.md](./PHASE2_2_V1_1_WALKTHROUGH.md):

- Train → merge → GGUF → **eval on Vast** → upload adapter only if NO-GO; GGUF + PC download only if GO.
- llama.cpp **must** be built with `-DGGML_CUDA=ON`.

---

## Checklist

### Phase 2.3.1 — Labels (PC)

- [ ] Implement holdout-style supported generator
- [ ] Anti–false-weak pairs
- [ ] Rebalance supported ≥45%
- [ ] Regenerate `l3_grounding_train.jsonl` (800–900 rows)
- [ ] `validate_dataset.py` + `audit_l3_labels.py` PASS
- [ ] Spot-check review CSV

### Phase 2.3.2 — Eval alignment (PC)

- [ ] Chat-template eval option
- [ ] Baseline re-check with aligned prompt

### Phase 2.3.3 — Train (Vast)

- [ ] QLoRA → `outputs/nassila-grounding-e4b-v1.2`
- [ ] Merge + Q6_K GGUF
- [ ] Eval on Vast → `reports/v1_2_eval_combined_report.json`
- [ ] HF: `nassila-grounding-e4b-v1.2-adapter`

### Go / no-go

- [ ] Expect ≥90%, quotes ≥98%, false supported ≤5%
- [ ] If GO: download GGUF, LM Studio, update Nassila preset

---

## HF artifacts

| Version | Adapter repo | Status |
|---------|--------------|--------|
| v1 | `QinEmPeRoR93/nassila-grounding-e4b-v1-adapter` | NO-GO |
| v1.1 | `QinEmPeRoR93/nassila-grounding-e4b-v1.1-adapter` | NO-GO |
| v1.2 | `QinEmPeRoR93/nassila-grounding-e4b-v1.2-adapter` | planned |

Cards: [MODEL_CARD_v1.md](./MODEL_CARD_v1.md), [MODEL_CARD_v1_1.md](./MODEL_CARD_v1_1.md).
