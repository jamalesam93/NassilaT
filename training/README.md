# Nassila — Gemma 4 training pack

Fine-tune **Nassila Sanad** (`l3_grounding`) on Gemma 4 E4B / 12B; export Q6_K GGUF for LM Studio.

**Strategy:** [Ouroboros](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS.md) — seven workers, one facet at a time. **Agent brief:** [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md).

**Current work:** [`POST_V113_MAP.md`](./POST_V113_MAP.md) · [`PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md`](./PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md)

Documentation-first: schemas, scripts, eval harnesses. No model weights in git.

---

## Quick start (read in this order)

| Step | Document | What you do |
|------|----------|-------------|
| 0 | [Nassila `OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md) | Workers, tiers, eval gates |
| 1 | [POST_V113_MAP.md](./POST_V113_MAP.md) | Where we are after v1.13 NO-GO |
| 2 | [PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md](./PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md) | Next 12B Vast run |
| 3 | [PHASE2_9_AB_PILOT_WALKTHROUGH.md](./PHASE2_9_AB_PILOT_WALKTHROUGH.md) | A/B pipeline + HF publish |
| 4 | [`docs/DUAL_TIER_POLICY.md`](../docs/DUAL_TIER_POLICY.md) | Ship gates |
| 5 | [EVAL_GONOGO.md](./EVAL_GONOGO.md) | GO/NO-GO log |
| 6 | [MODEL_CARD.md](./MODEL_CARD.md) | HF card index |
| 7 | [DATASET_SCHEMA.md](./DATASET_SCHEMA.md) | JSONL contracts |
| 8 | [EVALUATION_GUIDE.md](./EVALUATION_GUIDE.md) | How to score |

Historical: [`archive/`](./archive/).

---

## Folder layout (active)

```
training/
  README.md
  POST_V113_MAP.md              ← operator map
  ROADMAP.md
  PHASE2_9_AB_PILOT_WALKTHROUGH.md
  PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md
  PHASE2_12_31B_PREMIUM_WALKTHROUGH.md   ← optional
  EVAL_GONOGO.md
  EVALUATION_GUIDE.md
  MODEL_CARD.md
  MODEL_CARD_sanad_e4b.md
  MODEL_CARD_sanad_12b.md
  MODEL_CARD_sanad_31b.md
  DATASET_SCHEMA.md
  CORPUS_PIPELINE.md
  LM_STUDIO_INTEGRATION.md
  LLAMA_CPP_VAST.md
  HF_PUBLISH.md
  archive/                      ← v1.4–v1.13 completed walkthroughs
  scripts/
  data/
  reports/
```

---

## Ship checkpoints

| HF id | Checkpoint | Role |
|-------|------------|------|
| `nassila-sanad-e4b` | **v1.12** | Default ~8 GB |
| `nassila-sanad-12b` | **v1.12** | Quality Tier 2 |

v1.13 **NO-GO** — keep v1.12 on HF until v1.14+ passes.

---

## Helper commands

```bash
cd training
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

python scripts/validate_dataset.py data/l3_grounding_samples.jsonl
python scripts/lmstudio_smoke_test.py --base-url http://localhost:1234 --model "nassila-sanad-e4b"
```

See [EVALUATION_GUIDE.md](./EVALUATION_GUIDE.md) for full eval flow.

---

## Principles

1. **Deterministic code stays authoritative** — registries, parse repair, quote checks in the app.
2. **Never reward hallucinated quotes** — `sourceQuotes` must be substrings of the excerpt.
3. **Keep train and eval separate** — no holdout ids in train merges.
4. **Do not chase Tier 2 on E4B** — v1.11 lesson; E4B ships on default-tier only.

Product branding: [Nassila `docs/BRAND.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/BRAND.md).
