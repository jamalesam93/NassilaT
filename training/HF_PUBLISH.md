# Hugging Face publish — `nassila-sanad-*`

**Current HF repos:** `QinEmPeRoR93/nassila-sanad-e4b`, `QinEmPeRoR93/nassila-sanad-12b` (see [`MODEL_CARD_sanad_e4b.md`](./MODEL_CARD_sanad_e4b.md), [`MODEL_CARD_sanad_12b.md`](./MODEL_CARD_sanad_12b.md)). Pipeline: [`PHASE2_9_AB_PILOT_WALKTHROUGH.md`](./PHASE2_9_AB_PILOT_WALKTHROUGH.md).

**HF README sources (upload these):**

| Repo | README on disk | GGUF file |
|------|----------------|-----------|
| `nassila-sanad-e4b` | [`hf_readmes/nassila-sanad-e4b/README.md`](./hf_readmes/nassila-sanad-e4b/README.md) | `nassila-sanad-e4b-q6_k.gguf` (v1.12) |
| `nassila-sanad-12b` | [`hf_readmes/nassila-sanad-12b/README.md`](./hf_readmes/nassila-sanad-12b/README.md) | `nassila-sanad-12b-q6_k.gguf` (v1.14) |

One repo per tier — do not mix E4B and 12B GGUFs in the same repo.

One repo per tier — do not mix E4B and 12B GGUFs in the same repo.

After laptop smoke pass, verify release with [`HF_RELEASE_VERIFY.md`](./HF_RELEASE_VERIFY.md).

Legacy naming below (`nassila-grounding-e4b-v1`) — replace with worker ids above.

## Repositories (legacy example)

| Repo | Contents |
|------|----------|
| `YOUR_USER/nassila-grounding-e4b-v1-adapter` | LoRA `lora_adapter/` (private until go/no-go) |
| `YOUR_USER/nassila-grounding-e4b-v1` | GGUF Q6_K (user-facing) |

## Model card (README.md on HF)

```markdown
---
license: apache-2.0
base_model: google/gemma-4-E4B-it
tags:
  - lora
  - gemma
  - nassila
  - l3-grounding
  - academic
---

# Nassila grounding E4B v1

Fine-tuned Gemma 4 E4B for **l3_grounding** — manuscript passage vs **abstract** excerpt → JSON claims.

## Training

- **Task:** `l3_grounding` only (abstract-only excerpts)
- **Base:** `google/gemma-4-E4B-it`
- **Method:** QLoRA (Unsloth) on Vast RTX 4090
- **Train rows:** SEE_TRAIN_JSONL_COUNT
- **Corpus:** OpenAlex + Semantic Scholar exports (2000–2026), abstract backfill via OpenAlex/Crossref APIs
- **Not bundled** in Nassila installer — bring your own GGUF for LM Studio

## Eval (vs stock Gemma 4 E4B Q6_K)

| Metric | Baseline | Tuned v1 |
|--------|----------|----------|
| JSON parse (repair) | | |
| Expect pass rate | | |
| False supported | | |

## Usage

Load GGUF in LM Studio. Point Nassila manuscript audit preset at `http://localhost:1234` with model id from server UI.

## Limitations

- Trained on **abstracts**, not full PDF text
- Advisory only — use with Nassila deterministic guardrails
```

Replace `SEE_TRAIN_JSONL_COUNT` and eval table after Phase 2.4.

## Upload commands

**README only (write token required):**

```bash
hf upload QinEmPeRoR93/nassila-sanad-e4b \
  training/hf_readmes/nassila-sanad-e4b/README.md README.md \
  --repo-type model --commit-message "v1.12 E4B default tier model card"

hf upload QinEmPeRoR93/nassila-sanad-12b \
  training/hf_readmes/nassila-sanad-12b/README.md README.md \
  --repo-type model --commit-message "v1.14 12B quality tier model card"
```

**GGUF + adapter (legacy example):**

```bash
export HF_TOKEN="hf_..."
hf upload YOUR_USER/nassila-grounding-e4b-v1-adapter . . --repo-type model
hf upload YOUR_USER/nassila-grounding-e4b-v1 . . --repo-type model
```
