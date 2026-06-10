# NassilaT — training repository

Training data, scripts, and guides for fine-tuning Nassila local models (One Ring / `l3_grounding` first).

The desktop app lives in a separate repo. This repo is **only** for GPU training on Vast (or similar) and publishing adapters/GGUF to Hugging Face.

## Start here

1. Open [`training/README.md`](training/README.md) for the training pack overview.
2. **Phase 1.5 (PC):** [`training/CORPUS_PIPELINE.md`](training/CORPUS_PIPELINE.md) — merge JSON exports, backfill abstracts.
3. **Phase 2 (Vast):** [`training/PHASE2_VAST_WALKTHROUGH.md`](training/PHASE2_VAST_WALKTHROUGH.md) — train `nassila-grounding-e4b-v1`.
4. **Your checklist:** [`training/PHASE2_USER_STEPS.md`](training/PHASE2_USER_STEPS.md).
5. Phase 1 smoke: [`training/PHASE1_VAST_4090_WALKTHROUGH.md`](training/PHASE1_VAST_4090_WALKTHROUGH.md).

## Clone on Vast

```bash
git clone https://github.com/jamalesam93/NassilaT.git ~/nassila
cd ~/nassila/training
```
