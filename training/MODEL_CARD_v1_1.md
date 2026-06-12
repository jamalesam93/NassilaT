# Model card — `nassila-grounding-e4b-v1.1-adapter` (NO-GO)

**Hugging Face:** `QinEmPeRoR93/nassila-grounding-e4b-v1.1-adapter`  
**Status:** evaluation **NO-GO** — not for production. Slight improvement over v1; same supported-paraphrase blocker.

Copy the body below into the HF repo README.

---

```markdown
---
license: apache-2.0
base_model: google/gemma-4-E4B-it
tags:
  - lora
  - gemma
  - gemma4
  - nassila
  - l3-grounding
  - academic
  - peft
library_name: peft
pipeline_tag: text-generation
---

# Nassila grounding E4B v1.1 — LoRA adapter (NO-GO)

Second QLoRA iteration after v1 failure. Adds **eval-style supported paraphrase** rows (passage paraphrases abstract; `sourceQuotes` = verbatim source sentence).

**Status: evaluation NO-GO — not recommended for production use.**

## Why v1.1

v1 over-called **`weak`** on numeric paraphrase (0/10 supported holdout). v1.1 dataset: **700** rows, **266** supported (262 paraphrase `-supp-`), human spot-check 99.05% on 105-row sample.

## Training

| Field | Value |
|-------|--------|
| Base model | `google/gemma-4-E4B-it` |
| Method | QLoRA (Unsloth), Vast RTX A6000 |
| Train rows | 700 (seed 43) |
| Seq length | 1536 |
| LoRA r / α | 16 / 32 |
| Epochs | 2 |
| Code | [NassilaT](https://github.com/jamalesam93/NassilaT) Phase 2.1 |

## Evaluation (Vast, llama-server + Q6_K, 50 rows)

| Metric | v1 | v1.1 | Target |
|--------|-----|------|--------|
| JSON parse (with repair) | 100% | **100%** | ≥95% |
| Expect pass rate | ~62% | **66%** | ≥90% |
| Quote validity (holdout) | ~0% | **9.1%** | ≥98% |
| False supported | 0% | **0%** | ≤5% |

### Holdout by category (v1.1)

| Category | Pass rate |
|----------|-----------|
| supported (h-001–h-010) | **10%** (1/10) |
| contradicted | 100% |
| weak | 100% |
| insufficient_evidence | 100% |
| not_in_source | 67% |
| multi_claim | 50% |

### Documented failure (h-001)

- **Verdict:** `weak` (expected `supported`)
- **sourceQuotes:** correct verbatim substring from excerpt
- **Rationale:** “Passage uses more hedged wording than the abstract” — incorrect; paraphrase with same numbers should be **supported**.

GGUF was **not** published (eval NO-GO; eval-on-Vast workflow).

## Related

- Predecessor: `nassila-grounding-e4b-v1-adapter`
- Next: v1.2 plan in NassilaT `training/PHASE2_3_V1_2_PLAN.md`
```
