# NassilaT — training repository

Training data, scripts, and guides for fine-tuning Nassila **Ouroboros** workers. **Sanad** (`l3_grounding`) first.

The desktop app lives in [Nassila](https://github.com/jamalesam93/Nassila). This repo is for GPU training on Vast (or similar) and publishing GGUF to Hugging Face.

## Start here

1. [`training/README.md`](training/README.md) — training pack overview  
2. [`training/OUROBOROS_OPERATOR_MAP.md`](training/OUROBOROS_OPERATOR_MAP.md) — **current arc** (S15/S14 selected)  
3. [`training/LAPTOP_SMOKE_TEST.md`](training/LAPTOP_SMOKE_TEST.md) — local GGUF acceptance  
4. [`docs/DUAL_TIER_POLICY.md`](docs/DUAL_TIER_POLICY.md) — 4B default-tier vs Tier 2  
5. [`training/EVAL_GONOGO.md`](training/EVAL_GONOGO.md) — GO/NO-GO history (S15 ship)  
6. [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md) — agents: workers + tiers

Historical walkthroughs (v1.4–v1.13): [`training/archive/`](training/archive/).

## Clone on Vast

```bash
git clone https://github.com/jamalesam93/NassilaT.git ~/nassila
cd ~/nassila/training
```

## Ship checkpoints

| Model | Checkpoint | Gate |
|-------|------------|------|
| `nassila-sanad-4b` | S15 (Qwen 3.5 4B) | Default-tier |
| `nassila-sanad-12b` | v1.14 (S14) | Tier 2 |

E4B S12 is **retired** as default (legacy HF download only). Do **not** publish v1.13. See [`training/EVAL_GONOGO.md`](training/EVAL_GONOGO.md).
