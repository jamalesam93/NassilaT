# S15 un-park criteria

**Status:** UNPARKED & GO · **Prompt contract:** `sanad-grounding-v1` · **Base model:** `Qwen/Qwen3.5-4B`

## Data gates (NassilaT)

1. **Field-note boosts** — human-adjudicated rows exported (`export_field_note_boost_jsonl.py`).
2. **Body holdout** — contrastive v2 (308 rows) scored: S14 false-supported **4.22%**; S15 combined **94.48%**, quote validity **100%**, false-supported **4.87%**.
3. **Schemas locked** — `doc_extract` + `source_pdf_extract` v1 in [`DATASET_SCHEMA.md`](./DATASET_SCHEMA.md).

## Model gates (preserve S14 lessons)

On body holdout (and abstract harness when running W9 recovery):

| Check | Target | Achieved S15 (Qwen 3.5 4B) |
|-------|--------|----------------------------|
| Quote validity (holdout) | ≥98% | **100.0%** ✅ |
| False supported (holdout) | ≤5% | **4.87%** ✅ |
| **h-045 / h-088** | No `parse_json` regression | Preserved ✅ |
| Combined expect | ≥90% | **94.48%** ✅ |

## Product gates (Nassila)

After app **1.5.0** measurements:
- Tier A Rust WASM engine (`@firecrawl/pdf-inspector-wasm`) integrated into Maktab ingest.
- Passage windows + Masdar chunking feeding full-text excerpts directly into LM Studio runner.

## Un-park checklist

- [x] Boost JSONL exported from field notes (**49/49** masdar-lite-jul13)
- [x] Body holdout **draft** scored (PDF-body 84 rows)
- [x] Body holdout **frozen_v1** scored (2026-07-23): S12 + S14 Ollama **100%** parse / expect / quote
- [x] Product-scale freeze (≥100 docs / 400–500 claims) — **contrastive v2** (308 rows): S14 false-supported **4.22%** (**passes Tier-2 ≤5% gate!**)
- [x] **S15 Trained & Merged** — `nassila-sanad-4b-q6_k.gguf` based on `Qwen/Qwen3.5-4B` (**94.48% combined, 100% quote, 4.87% false-supported**)
- [x] Released on Hugging Face as default laptop tier GGUF.
