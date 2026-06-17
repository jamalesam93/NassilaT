---
license: apache-2.0
base_model: google/gemma-4-12B-it
tags:
  - gguf
  - gemma
  - gemma4
  - nassila
  - sanad
  - l3-grounding
  - ouroboros
  - academic
  - text-generation
language:
  - en
  - ar
library_name: llama.cpp
---

# Nassila Sanad 12B

*Train checkpoint v1.10 · optional quality tier*

A local GGUF fine-tune of **Gemma 4 12B** for **Sanad** (سند) — Nassila's Ouroboros worker that grounds manuscript passages against **abstract** excerpts and returns structured JSON claims with verbatim `sourceQuotes` when supported.

Runs fully offline in LM Studio or llama.cpp. This is the **optional high-accuracy tier**; the default 8 GB-friendly tier is [`nassila-sanad-e4b`](https://huggingface.co/QinEmPeRoR93/nassila-sanad-e4b) (when published).

## What it is

Sanad compares a passage you wrote to a source excerpt (typically an abstract) and emits claims labeled `supported`, `weak`, `contradicted`, `not_in_source`, or `insufficient_evidence`. Supported claims must include quotes copied verbatim from the excerpt.

Part of [Nassila](https://github.com/jamalesam93/Nassila) — a desktop bibliography and source-grounding tool.

## Pick your quant

| Quant | File | Size | Notes |
|-------|------|------|-------|
| **Q6_K** | `nassila-sanad-12b-q6_k.gguf` | ~9.1 GB | **Shipped** — best balance on our eval ladder |

## Will it fit?

Rough context estimates for **12B Q6_K** (weights ~9 GB + KV cache; use `q4_0` KV in llama.cpp for roughly 2× more context):

| VRAM / unified memory | Approx max context |
|-----------------------|-------------------|
| 12 GB | ~12K |
| 16 GB | ~44K |
| 24 GB | ~110K |
| 32 GB | ~230K |

Context 4096 is enough for typical Sanad calls (passage + abstract excerpt).

## How to run

### LM Studio

1. Download `nassila-sanad-12b-q6_k.gguf`.
2. Load in [LM Studio](https://lmstudio.ai/) (llama.cpp backend, Gemma chat template).
3. Set context ≥4096.

### llama.cpp

```bash
llama-server -m nassila-sanad-12b-q6_k.gguf \
  --host 127.0.0.1 --port 1234 --ctx-size 4096 \
  --n-gpu-layers 99
```

Requires a **recent llama.cpp** build with `gemma4_unified` support.

## Evaluation snapshot

*Checkpoint v1.10 · 115-row hardened harness · multi-seed mean (seeds 42/43/44)*

| Gate | Result | Target |
|------|--------|--------|
| Combined expect pass | **94.79%** | ≥90% |
| JSON parse (with repair) | **100%** | ≥98% |
| Supported h-001–h-010 | **10/10** | ≥8/10 |
| Core legacy 5 | **5/5** | 5/5 |
| Quote validity (holdout) | **100%** | ≥98% |
| False supported (holdout) | **2.82%** | ≤5% |
| **Tier 2 (abstract Sanad ship)** | **PASS** | all six |

Trained with the same recipe as E4B v1.10 (850 rows, QLoRA r=16, 2 epochs). Training details: [NassilaT](https://github.com/jamalesam93/NassilaT).

## Dual-tier policy

| Tier | Model | Role |
|------|-------|------|
| Default | `nassila-sanad-e4b` Q6_K | ~8 GB; all text workers |
| **Optional quality** | **`nassila-sanad-12b` Q6_K** | Max Sanad grounding quality |

## Good to know

- Trained on **abstracts**, not full paper body text.
- **Advisory only** — pair with Nassila's deterministic JSON repair and quote-substring guardrails.
- **Not bundled** in the Nassila installer — bring your own GGUF.
- English-centric training mix; Arabic passages supported at inference.
- Tables and figures are **Shahid** worker scope, not this text-only Sanad facet.

## Base and license

- **Base model:** [`google/gemma-4-12B-it`](https://huggingface.co/google/gemma-4-12B-it)
- Subject to the [Gemma Terms of Use](https://ai.google.dev/gemma/terms).
