# Model card — nassila-grounding-e4b-v1.3 (Sanad / Ouroboros)

**Hugging Face:** `QinEmPeRoR93/nassila-grounding-e4b-v1.3-adapter`  
**Status:** evaluation **NO-GO** — adapter archived; GGUF not published.

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
  - sanad
  - ouroboros
  - academic
  - peft
library_name: peft
pipeline_tag: text-generation
---

# Nassila grounding E4B v1.3 — LoRA adapter (NO-GO)

Third QLoRA iteration (**Sanad** worker, Nassila Ouroboros). Targets multi-claim decomposition, polarity contradicted, semantic Sanad, and overclaim contradicted on top of v1.2’s holdout-shaped Sanad rows.

**Status: evaluation NO-GO — not recommended for production use.**  
Adapter archived for training history and merge/export experiments. **GGUF was not published.**

## Why v1.3

v1.2 fixed supported holdout (9/10) but failed combined go/no-go (86%) due to **core eval collapse** (2/5) and quote validity (90.9%). v1.3 added ~207 multi-claim rows, polarity (`-pol-`), semantic Sanad (`-sanadsem-`), and overclaim (`-over-`) labels; **2 epochs** @ **1e-4**.

## Training

| Field | Value |
|-------|--------|
| Task | `l3_grounding` (abstract-only excerpts) |
| Worker | **Sanad** (`l3_grounding`) |
| Base model | [`google/gemma-4-E4B-it`](https://huggingface.co/google/gemma-4-E4B-it) |
| Method | QLoRA (Unsloth), Vast RTX A6000 48 GB |
| Train rows | 850 (seed 45) |
| Seq length | 1536 |
| LoRA r / α | 16 / 32 |
| Epochs | 2 |
| Learning rate | 1e-4 |
| Eval | `--chat-template` (matches train) |
| Export | Merge via `merge_adapter_gemma4.py` → llama.cpp **b9608** → Q6_K |
| Code | [NassilaT](https://github.com/jamalesam93/NassilaT) — `training/PHASE2_5_V1_3_PLAN.md` |

## Evaluation (Vast, llama-server + Q6_K, 50 rows)

| Metric | Stock baseline | v1.2 | v1.3 | Target |
|--------|----------------|------|------|--------|
| Combined expect pass | 86% | 86% | **80%** | ≥90% |
| Core eval (5 rows) | 100% | 40% | **100%** | — |
| Holdout expect pass | 84.4% | 91.1% | **77.8%** | — |
| JSON parse (combined, repair) | 100% | 100% | **86%** | ≥95% |
| Quote validity (holdout) | 100% | 90.9% | **36.4%** | ≥98% |
| False supported (holdout) | 11.8% | 0% | **2.9%** | ≤5% |
| Supported h-001–h-010 | 10/10 | 9/10 | **3/10** | ≥8/10 |

### Holdout by category (v1.3)

| Category | Pass rate |
|----------|-----------|
| supported (h-001–h-010) | **30%** (3/10) |
| contradicted | **100%** (9/9) |
| weak | 100% |
| insufficient_evidence | 100% |
| not_in_source | 89% |
| multi_claim | 67% (4/6) |

### What improved vs v1.2

- **Core eval 5/5** — eval-001, eval-003, eval-005 all pass.
- **Contradicted holdout 100%** — including h-013 (polarity).

### What regressed vs v1.2

- **Supported holdout 3/10** — seven rows fail with **`must_parse_json`** (`Expecting ',' delimiter` after repair).
- **Combined expect 80%** (down from 86%).
- **Quote validity 36.4%** (down from 90.9%).

## Usage (research / re-export only)

LoRA weights only. Merge with base via `scripts/merge_adapter_gemma4.py`; GGUF via llama.cpp — see NassilaT `training/LLAMA_CPP_VAST.md` (pinned tag **b9608**).

## Related

- Predecessor: [`nassila-grounding-e4b-v1.2-adapter`](https://huggingface.co/QinEmPeRoR93/nassila-grounding-e4b-v1.2-adapter)
- Eval: [reports/v1_3_eval_combined_report.json](./reports/v1_3_eval_combined_report.json)
```

## Evaluation summary (repo copy)

Reports: [reports/v1_3_eval_combined_report.json](./reports/v1_3_eval_combined_report.json)

**Next:** v1.4 should target JSON output stability on supported holdout while preserving core eval gains.
