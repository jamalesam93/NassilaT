# Nassila training roadmap — One Ring

**North star:** one local model identity (**One Ring**) for all Nassila AI tasks, forged **one facet at a time**. Canonical vision: [`docs/ONE_RING.md`](../docs/ONE_RING.md).

**v1 ships only** `l3_grounding` → **`nassila-grounding-e4b-v1`** (Gemma 4 E4B). Later facets merge into **`nassila-agent-*`**.

---

## One Ring phases (product + training)

| Phase | Facet | Task id(s) | Artifact | Base model |
|-------|-------|------------|----------|------------|
| **0** | Baseline eval | `l3_grounding` | Stock Gemma 4 E4B Q6_K | E4B |
| **0.5** | App guardrails | — | JSON repair, retry, caps | — (app code) |
| **1** | Cloud QLoRA setup | `l3_grounding` | Smoke LoRA on Vast | E4B |
| **2** | L3 dataset + train | `l3_grounding` | `nassila-grounding-e4b-v1` | E4B |
| **3** | Manuscript ingest | `doc_extract` | Facet or agent merge | E4B → 12B |
| **3b** | Cited PDF text | `source_pdf_extract` | Same | E4B |
| **4** | Tables / figures | `table_figure_grounding` | `nassila-agent-e12b-v1` | 12B multimodal |
| **5** | Webpage AI | `webpage_*`, `issue_explain` | Merge into agent | E4B / 12B |
| **6** | Multi-task merge | All | Single `nassila-agent-*` GGUF | Best fit |

**Not in the Ring:** Crossref/PubMed/OpenAlex, citeproc, predatory lists, Marker (optional GPL ingest only).

---

## Phase 0 — Baseline (complete)

- Stock **Gemma 4 E4B Q6_K** in LM Studio
- 50-row eval harness → **100% JSON with repair**, **82% expect pass**, ~**9.8 s/row**
- **Go** for Phase 0.5 / Phase 1

---

## Phase 0.5 — App guardrails (complete)

Implemented in Nassila engine/renderer:

- [`grounding-json-repair.ts`](../src/engine/manuscript/grounding-json-repair.ts)
- Passage/excerpt caps (1500 / 4200 chars)
- One LLM retry on parse failure
- LM Studio preset (port 1234)

---

## Phase 1 — Environment + smoke QLoRA (next)

**Goal:** Prove 4-bit load + one training step on cloud GPU.

| Step | Doc |
|------|-----|
| Vast + RTX 4090 + WSL2 | [`PHASE1_VAST_4090_WALKTHROUGH.md`](./PHASE1_VAST_4090_WALKTHROUGH.md) |
| Full phase guide | [`TRAINING_GUIDE.md`](./TRAINING_GUIDE.md) §3 |
| Checklist | [`PHASE1_CHECKLIST.md`](./PHASE1_CHECKLIST.md) |

**Exit:** `train_lora.py --max_steps 1` succeeds; adapter saved.

---

## Phase 2 — L3 production model (v1 ship)

**Goal:** `nassila-grounding-e4b-v1` beats baseline on eval harness.

| Step | Action |
|------|--------|
| Dataset | Expand `data/l3_grounding_samples.jsonl` (target 200–500 rows) |
| Train | QLoRA on Vast; export GGUF Q6_K |
| Eval | [`EVALUATION_GUIDE.md`](./EVALUATION_GUIDE.md) — JSON ≥99%, expect ≥90% |
| Publish | HF repo; app preset + version bump **1.2.0** |

---

## Phase 3+ — More facets → One Ring merge

Train each task with its JSONL ([`DATASET_SCHEMA.md`](./DATASET_SCHEMA.md)), eval independently, then **multi-task merge** into one GGUF.

| Task | Unblocks in app |
|------|-----------------|
| `doc_extract` | Better PDF/DOCX than pdfjs-only |
| `source_pdf_extract` | `pdf_pending` rows in manuscript audit |
| `table_figure_grounding` | Figure/table claims |
| `webpage_metadata` / `webpage_classify` | [`docs/WEBPAGE_ROADMAP.md`](../docs/WEBPAGE_ROADMAP.md) |

**12B pivot:** When multimodal ingest/grounding facets ship; E4B remains valid for text-only L3 tier.

---

## App integration status

| Component | Status |
|-----------|--------|
| L3 engine (`grounding-llm.ts`) | Ready |
| Manuscript audit UI | **Not mounted** in shipping app |
| Task router (multi-task) | **Future** — constants in [`nassila-agent-tasks.ts`](../src/shared/nassila-agent-tasks.ts) |
| Model download UX | Planned (HF URL, resumable) |

---

## Publishing this pack

`training/` is **gitignored** locally until L3 is production-ready. When publishing:

1. Remove `/training/` from `.gitignore` (or use separate repo per [`docs/NEW_REPOSITORY.md`](../docs/NEW_REPOSITORY.md))
2. Ship eval reports + GGUF on Hugging Face
3. Link [`docs/ONE_RING.md`](../docs/ONE_RING.md) from README

---

## Quick links

| Doc | Purpose |
|-----|---------|
| [`docs/ONE_RING.md`](../docs/ONE_RING.md) | Product vision + task registry |
| [`README.md`](./README.md) | Training pack index |
| [`DATASET_SCHEMA.md`](./DATASET_SCHEMA.md) | JSONL per task |
| [`LM_STUDIO_INTEGRATION.md`](./LM_STUDIO_INTEGRATION.md) | Inference + presets |
| [`PHASE1_VAST_4090_WALKTHROUGH.md`](./PHASE1_VAST_4090_WALKTHROUGH.md) | Vast walkthrough |
