---
license: apache-2.0
base_model: google/gemma-4-12B-it
tags:
  - gguf
  - gemma
  - gemma4
  - nassila
  - sanad
  - l3-grounding
  - ouroboros
  - academic
  - text-generation
language:
  - en
  - ar
library_name: llama.cpp
---

# Nassila Sanad 12B (quality tier)

**Checkpoint:** **S14** *(legacy train label v1.14)*

Local GGUF for **Sanad** in [Nassila](https://github.com/jamalesam93/Nassila) — checks manuscript claims against source excerpts and returns structured JSON with verdicts and verbatim quotes.

**File:** `nassila-sanad-12b-q6_k.gguf` · Q6_K · ~9.1 GB  
**Default tier:** [`nassila-sanad-e4b`](https://huggingface.co/QinEmPeRoR93/nassila-sanad-e4b)

Part of [Nassila Ouroboros](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS.md) — see the E4B model card for the seven-worker overview.

**Sanad today:** validated on abstract excerpts (Tier 2). Full paper body text is planned (Tier 3).

| Combined | Quote validity | False-supported |
|----------|----------------|-----------------|
| **90.43%** | **100%** | **2.86%** |

Quality-tier validation: **PASS**

## Usage

### Quick start (Nassila + LM Studio)

**Recommended** — download this GGUF, load it in [LM Studio](https://lmstudio.ai/), and start the Local Server at `http://localhost:1234`. **~12 GB+ VRAM** recommended.

In Nassila: **Settings → Passage grounding** → runner **LM Studio** → model `nassila-sanad-12b` (or the id LM Studio shows).

### Ollama

Requires Ollama 0.5+ and a **public** Hugging Face repo.

**Pull from Hub:**

```bash
ollama pull huggingface.co/QinEmPeRoR93/nassila-sanad-12b:Q6_K
```

In Nassila: runner **Ollama** → base URL `http://localhost:11434` → model name from `ollama list` (often `nassila-sanad-12b:Q6_K`).

<details>
<summary>Modelfile fallback (private repo or pull tag not indexed)</summary>

```
FROM https://huggingface.co/QinEmPeRoR93/nassila-sanad-12b/resolve/main/nassila-sanad-12b-q6_k.gguf
PARAMETER num_ctx 4096
```

```bash
ollama create nassila-sanad-12b -f Modelfile
```

</details>

### Advanced (llama.cpp / vLLM)

Serve the GGUF with any OpenAI-compatible server (`ctx-size` 4096; requires a recent llama.cpp build with `gemma4_unified` support). Point Nassila at your base URL and exposed model id.

```bash
llama-server -m nassila-sanad-12b-q6_k.gguf \
  --host 127.0.0.1 --port 1234 --ctx-size 4096 --n-gpu-layers 99
```

## Limitations

- Trained on **abstract excerpts** (Tier 2); full paper body (Tier 3) planned.
- **Advisory only** — use with Nassila deterministic guardrails.
- Not bundled in the Nassila installer.

## Base model

[`google/gemma-4-12B-it`](https://huggingface.co/google/gemma-4-12B-it) · [Gemma Terms of Use](https://ai.google.dev/gemma/terms)

**HF README source:** [`hf_readmes/nassila-sanad-12b/README.md`](./hf_readmes/nassila-sanad-12b/README.md)
