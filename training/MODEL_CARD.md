# Model card — `nassila-grounding-e4b-v1` (draft)

Status: **pre-train** — `data/l3_grounding_train.jsonl` ready; Vast QLoRA pending.

## Identity

| Field | Value |
|-------|-------|
| Artifact | `nassila-grounding-e4b-v1` |
| Task | `l3_grounding` only |
| Base model | `google/gemma-4-E4B-it` |
| Export quant | Q6_K GGUF |
| Excerpt type | **Abstract only** (`meta.label: abstract`) |

## Training data

| Metric | Value |
|--------|-------|
| Train rows | 400 (`l3_grounding_train.jsonl`) |
| Corpus papers | 5,997 merged (OpenAlex 1000 + Semantic 5000 exports) |
| Papers with abstract ≥120 chars | 2,519+ (grows with API backfill) |
| Holdout papers | 50 (`eval_corpus_holdout_papers.jsonl`) |
| Generation | Rule-based variants + `validate_dataset.py` |

## Corpus provenance

- Publish-or-Perish-style JSON exports (2000–2026)
- Optional abstract backfill: OpenAlex API, Crossref (see `training/cache/api/`)

## Eval targets ([EVALUATION_GUIDE.md](./EVALUATION_GUIDE.md))

| Metric | Baseline (ref) | Tuned target |
|--------|----------------|--------------|
| JSON parse (repair) | 100% | ≥ 95–99% |
| Expect pass | 82% | ≥ 90% |
| False supported | — | ≤ 5% |

Fill tuned column after Phase 2.4 on LM Studio.

## Ship checklist

- [ ] Vast QLoRA ([PHASE2_VAST_WALKTHROUGH.md](./PHASE2_VAST_WALKTHROUGH.md))
- [ ] GGUF export (`scripts/export_gguf.py`)
- [ ] HF upload ([HF_PUBLISH.md](./HF_PUBLISH.md))
- [ ] Go/no-go vs baseline
