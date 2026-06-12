# Ouroboros (training pack pointer)

**Canonical doc:** [docs/OUROBOROS.md](https://github.com/jamalesam93/citations-style/blob/main/docs/OUROBOROS.md) in the Nassila app repo.

This training pack implements **forge one worker at a time**:

1. **Now:** **Sanad** (`l3_grounding`) → `nassila-grounding-e4b-v1.2`
2. **Later:** `doc_extract`, `source_pdf_extract`, `table_figure_grounding`, `webpage_*`
3. **Merge:** multi-task JSONL → `nassila-agent-*` GGUF

## Training-specific notes

| Topic | Doc |
|-------|-----|
| Phases | [`ROADMAP.md`](./ROADMAP.md) |
| v1.2 plan | [`PHASE2_3_V1_2_PLAN.md`](./PHASE2_3_V1_2_PLAN.md) |
| JSONL `task` field | [`DATASET_SCHEMA.md`](./DATASET_SCHEMA.md) |
| Eval gates | [`EVALUATION_GUIDE.md`](./EVALUATION_GUIDE.md) |
| Workers (app) | [`nassila-agent-tasks.ts`](https://github.com/jamalesam93/citations-style/blob/main/src/shared/nassila-agent-tasks.ts) |

**One Ring** was renamed to **Ouroboros**. See stub [`ONE_RING.md`](./ONE_RING.md).
