# NassilaT — training repository

Training data, scripts, and guides for fine-tuning Nassila **Ouroboros** workers. **Sanad** (`l3_grounding`) first.

The desktop app lives in [Nassila](https://github.com/jamalesam93/Nassila). This repo is for GPU training on Vast (or similar) and publishing GGUF to Hugging Face.

## Start here

1. [`training/README.md`](training/README.md) — training pack overview  
2. [`training/POST_V113_MAP.md`](training/POST_V113_MAP.md) — **current arc** (v1.13 failed → v1.14+)  
3. [`docs/DUAL_TIER_POLICY.md`](docs/DUAL_TIER_POLICY.md) — E4B default-tier vs Tier 2  
4. [`training/PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md`](training/PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md) — next 12B Vast run  
5. [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md) — agents: workers + tiers  

Historical walkthroughs (v1.4–v1.13): [`training/archive/`](training/archive/).

## Clone on Vast

```bash
git clone https://github.com/jamalesam93/NassilaT.git ~/nassila
cd ~/nassila/training
```

## Ship checkpoints (frozen)

| Model | Checkpoint | Gate |
|-------|------------|------|
| `nassila-sanad-e4b` | v1.12 | E4B default-tier |
| `nassila-sanad-12b` | v1.12 | Tier 2 |

Do **not** publish v1.13. See [`training/EVAL_GONOGO.md`](training/EVAL_GONOGO.md).
