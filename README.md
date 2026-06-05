# NassilaT — training repository

Training data, scripts, and guides for fine-tuning Nassila local models (One Ring / `l3_grounding` first).

The desktop app lives in a separate repo. This repo is **only** for GPU training on Vast (or similar) and publishing adapters/GGUF to Hugging Face.

## Start here

1. Open [`training/README.md`](training/README.md) for the training pack overview.
2. Follow [`training/PHASE1_VAST_4090_WALKTHROUGH.md`](training/PHASE1_VAST_4090_WALKTHROUGH.md) for Phase 1 (Vast + RTX 4090 smoke QLoRA).

## Clone on Vast

```bash
git clone https://github.com/jamalesam93/NassilaT.git ~/nassila
cd ~/nassila/training
```
