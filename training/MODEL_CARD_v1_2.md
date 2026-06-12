# Model card — nassila-grounding-e4b-v1.2 (Sanad / Ouroboros)

**Status:** Template — fill after Vast train + eval.

| Field | Value |
|-------|-------|
| Worker | **Sanad** (`l3_grounding`) |
| Base | `google/gemma-4-E4B-it` |
| Method | QLoRA (Unsloth), 3 epochs, LR 1.5e-4 |
| Train rows | 850 (seed 44) |
| Quant (ship) | Q6_K GGUF |
| Artifact | `nassila-grounding-e4b-v1.2-q6_k.gguf` |

## Intended use

Offline manuscript claim grounding: passage vs source excerpt → structured JSON (`supported`, `weak`, `contradicted`, `not_in_source`, `insufficient_evidence`).

## Training data (v1.2)

- Holdout-shaped rows (`-sanad-`): direct passage + single-sentence excerpt
- Chunked excerpts (`excerpt_mode=chunked`) mirroring app `selectSourceChunksForGrounding`
- Full-abstract rows retained for production shape
- Rebalanced verdicts: supported ≥45%, weak ≤12%

## Eval (fill in)

| Metric | Target | v1.2 result |
|--------|--------|-------------|
| Expect pass | ≥90% | |
| Quote validity (holdout) | ≥98% | |
| False supported | ≤5% | |
| Supported holdout h-001–h-010 | ≥8/10 | |

**Eval command:** `run_l3_eval_batch.py --chat-template` (matches train system+user layout).

## Comparison

| Version | Expect pass | Quote validity | Notes |
|---------|-------------|----------------|-------|
| v1 | 62% | 0% holdout supported | NO-GO |
| v1.1 | 66% | 9.1% | NO-GO, false weak on paraphrase |
| v1.2 | | | Multi-scale excerpts + chat-template eval |

## Links

- [PHASE2_4_V1_2_WALKTHROUGH.md](./PHASE2_4_V1_2_WALKTHROUGH.md)
- [OUROBOROS.md](./OUROBOROS.md)
- Prior: [MODEL_CARD_v1_1.md](./MODEL_CARD_v1_1.md)
