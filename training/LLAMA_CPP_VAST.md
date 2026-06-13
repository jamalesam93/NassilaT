# llama.cpp on Vast — pinned build (GGUF + eval)

One-time setup per fresh GPU instance. Used after `merge_adapter_gemma4.py` for F16 GGUF conversion, `llama-quantize`, and `llama-server` eval.

**Do not** `git clone` floating `main` without a release tag. Recent `main` pulls a web UI that downloads assets from Hugging Face; failed or partial downloads produce `zero-size array 'asset_60_data'` and break the build even when `LLAMA_BUILD_UI=OFF`.

---

## Canonical recipe (verified 2026-06-09)

**Pinned tag:** `b9608` — update only after a successful full train→eval cycle on Vast.

```bash
cd ~
rm -rf llama.cpp

git clone --depth 1 --branch b9608 https://github.com/ggerganov/llama.cpp.git
cd llama.cpp

cmake -B build -DGGML_CUDA=ON -DLLAMA_BUILD_UI=OFF
grep LLAMA_BUILD_UI build/CMakeCache.txt   # must show BOOL=OFF before building

cmake --build build --target llama-server llama-quantize -j

ls -la build/bin/llama-server build/bin/llama-quantize
```

After success, record the exact commit (for bug reports / pin updates):

```bash
git -C ~/llama.cpp rev-parse HEAD
git -C ~/llama.cpp describe --tags --always
```

---

## Rules

| Do | Don't |
|----|--------|
| Clone **`--branch b9608`** (or newer tested tag) | `git clone` without branch → floating `main` |
| `-DLLAMA_BUILD_UI=OFF` | Full `cmake --build build -j` (builds `llama-ui`) |
| Build **only** `llama-server` and `llama-quantize` | Rely on HF UI bucket download on Vast |
| `rm -rf build` (and `tools/ui/dist` if present) before reconfigure after any UI failure | Retry `cmake --build` on a poisoned `build/` |
| `grep LLAMA_BUILD_UI build/CMakeCache.txt` before compile | Assume configure worked from a warning alone |

`LLAMA_BUILD_WEBUI` is deprecated on newer trees; `LLAMA_BUILD_UI=OFF` is sufficient when using a pinned release.

---

## Skip if already built

If both binaries exist on this instance:

```bash
test -x ~/llama.cpp/build/bin/llama-server && test -x ~/llama.cpp/build/bin/llama-quantize && echo OK
```

---

## Rebuild after failure

```bash
cd ~/llama.cpp
rm -rf build tools/ui/dist

cmake -B build -DGGML_CUDA=ON -DLLAMA_BUILD_UI=OFF
grep LLAMA_BUILD_UI build/CMakeCache.txt
cmake --build build --target llama-server llama-quantize -j
```

If UI still compiles (`tools/ui/CMakeFiles/llama-ui`) despite `LLAMA_BUILD_UI:BOOL=OFF`, **delete the tree** and re-clone with `--branch b9608` — do not fight `main`.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `UI: provisioning failed; embedding stale assets` | `rm -rf ~/llama.cpp/build ~/llama.cpp/tools/ui/dist`; re-clone pinned tag |
| `zero-size array 'asset_60_data'` | Same — UI asset embed failed; use pinned tag + UI OFF + targeted build |
| `HTTP response code said error` / HF download failed | Expected on broken `main` path; use **b9608** clone above |
| `llama-ui` compiles while `LLAMA_BUILD_UI=OFF` | Buggy `main` commit; switch to **b9608** |
| `llama-quantize` not found | You built wrong targets; rerun `--target llama-server llama-quantize` |
| Eval very slow / GPU idle | Rebuild with `-DGGML_CUDA=ON`; start server with `-ngl 99` if needed |
| `cmake` not found | `apt-get update && apt-get install -y cmake build-essential` |

---

## Used by

- [PHASE2_2_V1_1_WALKTHROUGH.md](./PHASE2_2_V1_1_WALKTHROUGH.md)
- [PHASE2_4_V1_2_WALKTHROUGH.md](./PHASE2_4_V1_2_WALKTHROUGH.md)
- [PHASE2_6_V1_3_WALKTHROUGH.md](./PHASE2_6_V1_3_WALKTHROUGH.md)

Convert + quantize (example v1.3 paths):

```bash
cd ~/nassila/training

python ~/llama.cpp/convert_hf_to_gguf.py exports/hf-merged-v1.3-bf16 \
  --outfile exports/nassila-grounding-e4b-v1.3-f16.gguf \
  --outtype f16

~/llama.cpp/build/bin/llama-quantize \
  exports/nassila-grounding-e4b-v1.3-f16.gguf \
  exports/nassila-grounding-e4b-v1.3-q6_k.gguf \
  Q6_K
```
