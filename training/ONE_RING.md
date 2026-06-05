# One Ring (training pack pointer)

The **canonical** One Ring vision lives in the main repo:

**→ [`docs/ONE_RING.md`](../docs/ONE_RING.md)**

This training pack implements **forge one facet at a time**:

1. **Now:** `l3_grounding` → `nassila-grounding-e4b-v1`
2. **Later:** `doc_extract`, `source_pdf_extract`, `table_figure_grounding`, `webpage_*`
3. **Merge:** multi-task JSONL → `nassila-agent-*` GGUF

## Training-specific notes

| Topic | Doc |
|-------|-----|
| Phases | [`ROADMAP.md`](./ROADMAP.md) |
| JSONL `task` field | [`DATASET_SCHEMA.md`](./DATASET_SCHEMA.md) |
| Eval gates | [`EVALUATION_GUIDE.md`](./EVALUATION_GUIDE.md) |
| Task constants (app) | [`src/shared/nassila-agent-tasks.ts`](../src/shared/nassila-agent-tasks.ts) |

## Merge checklist (future)

- [ ] Each facet passes eval harness independently
- [ ] Mixed JSONL balanced per task (avoid one task dominating)
- [ ] Single system prompt convention (`TASK:` line)
- [ ] One GGUF quant target (Q6_K for 8GB tier)
- [ ] Update `MODEL_ARTIFACT_TASKS` in `nassila-agent-tasks.ts`
- [ ] LM Studio preset → `nassila-agent-*` with task list in notes
