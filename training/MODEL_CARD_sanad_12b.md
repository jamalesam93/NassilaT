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

Local GGUF for **Sanad** in [Nassila](https://github.com/jamalesam93/Nassila) — checks manuscript claims against source excerpts and returns structured JSON with verdicts and verbatim quotes.

**File:** `nassila-sanad-12b-q6_k.gguf` · Q6_K · ~9.1 GB  
**Default tier:** [`nassila-sanad-e4b`](https://huggingface.co/QinEmPeRoR93/nassila-sanad-e4b)

Part of [Nassila Ouroboros](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS.md) — see the E4B model card for the seven-worker overview.

**Sanad today:** validated on abstract excerpts (Tier 2). Full paper body text is planned (Tier 3) for both E4B and 12B. Needs ~12 GB+ VRAM for comfortable local use.

| Combined | Quote validity | False-supported |
|----------|----------------|-----------------|
| **90.43%** | **100%** | **2.86%** |

Quality-tier validation: **PASS**

## Usage

1. Load `nassila-sanad-12b-q6_k.gguf` in [LM Studio](https://lmstudio.ai/) and start the server on `http://localhost:1234`.
2. Point Nassila's Sanad preset at that server.

```bash
llama-server -m nassila-sanad-12b-q6_k.gguf \
  --host 127.0.0.1 --port 1234 --ctx-size 4096 --n-gpu-layers 99
```

Requires a recent llama.cpp build with `gemma4_unified` support.

## Ollama

Pull directly from Hugging Face (requires Ollama 0.5+; repos must be **public**):

```bash
ollama pull huggingface.co/QinEmPeRoR93/nassila-sanad-12b:Q6_K
```

Then use `nassila-sanad-12b:Q6_K` as the model name in Nassila's Ollama preset.

**Modelfile fallback** (if the pull tag is not yet indexed, or for private repos with `HF_TOKEN` set):

```
FROM https://huggingface.co/QinEmPeRoR93/nassila-sanad-12b/resolve/main/nassila-sanad-12b-q6_k.gguf
PARAMETER num_ctx 4096
```

Save as `Modelfile` and run `ollama create nassila-sanad-12b -f Modelfile`.

Needs ~12 GB+ VRAM for comfortable local use.

- Trained on abstracts, not full paper body text yet.
- Advisory only; not bundled in the Nassila installer.

Base: [`google/gemma-4-12B-it`](https://huggingface.co/google/gemma-4-12B-it) · [Gemma Terms of Use](https://ai.google.dev/gemma/terms)

**HF README source:** [`hf_readmes/nassila-sanad-12b/README.md`](./hf_readmes/nassila-sanad-12b/README.md)
