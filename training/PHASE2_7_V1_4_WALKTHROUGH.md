# Phase 2.7 — v1.4 on Vast (training diagnosis fix)

**v1.4a result (GATE PASS):** JSON parse 100%, supported 8/10, combined 90%.  
**HF adapter:** `QinEmPeRoR93/nassila-grounding-e4b-v1.4a-adapter`

---

## Train file (both 4a and 4b)

Use **`data/l3_grounding_train_v14a.jsonl`** — seq-safe excerpts (capped at 1800 chars).  
Build on Vast or PC:

```bash
python scripts/prepare_v14_train.py
python scripts/validate_dataset.py data/l3_grounding_train_v14a.jsonl \
  --export-chat data/l3_grounding_chat.jsonl --strict-length 2048
python scripts/audit_chat_seq_lengths.py data/l3_grounding_chat.jsonl --max-length 2048
```

---

## v1.4b on Vast (full go/no-go)

| Setting | Value |
|---------|--------|
| Train file | `data/l3_grounding_train_v14a.jsonl` |
| Hyperparams | **3 epochs**, LR **1.5e-4** (v1.2 recipe) |
| `save_strategy` | **`no`** (Unsloth pickle crash on checkpoint save) |
| Output | `outputs/nassila-grounding-e4b-v1.4b/` |

### Quick path (pipeline script)

After `git pull`, llama.cpp **b9608** built ([LLAMA_CPP_VAST.md](./LLAMA_CPP_VAST.md)):

```bash
cd ~/nassila/training
source ~/nassila/.venv/bin/activate
chmod +x scripts/run_vast_pipeline.sh

PHASE=4b bash scripts/run_vast_pipeline.sh
```

### Manual path (proven v1.3 recipe)

```bash
cd ~/nassila/training
source ~/nassila/.venv/bin/activate

python scripts/prepare_v14_train.py
python scripts/validate_dataset.py data/l3_grounding_train_v14a.jsonl \
  --export-chat data/l3_grounding_chat.jsonl --strict-length 2048

python scripts/train_qlora_gemma4_e4b.py \
  --phase 4b \
  --train-file data/l3_grounding_train_v14a.jsonl \
  --chat-file data/l3_grounding_chat.jsonl

python scripts/merge_adapter_gemma4.py \
  --adapter-dir outputs/nassila-grounding-e4b-v1.4b/lora_adapter \
  --out-dir exports/hf-merged-v1.4b-bf16 \
  --max-seq-length 2048

python ~/llama.cpp/convert_hf_to_gguf.py exports/hf-merged-v1.4b-bf16 \
  --outfile exports/nassila-grounding-e4b-v1.4b-f16.gguf --outtype f16

~/llama.cpp/build/bin/llama-quantize \
  exports/nassila-grounding-e4b-v1.4b-f16.gguf \
  exports/nassila-grounding-e4b-v1.4b-q6_k.gguf Q6_K
```

**Eval** (llama-server port **1234**):

```bash
python scripts/run_l3_eval_batch.py \
  --base-url http://127.0.0.1:1234 \
  --model nassila-grounding \
  --data data/eval_samples.jsonl data/eval_samples_extended.jsonl data/eval_holdout_45.jsonl \
  --chat-template --retry 1 --repair \
  --out reports/v1_4b_predictions.jsonl

python scripts/run_eval_reports.py \
  --predictions reports/v1_4b_predictions.jsonl \
  --out-dir reports --prefix v1_4b_ --repair

python scripts/compare_eval_versions.py
```

---

## v1.4b go/no-go (ship bar)

| Metric | v1.4a | v1.4 target |
|--------|-------|-------------|
| Combined expect | 90% | **≥90%** ✓ (hold) |
| JSON parse (repair) | 100% | **≥98%** |
| Supported h-001–h-010 | 8/10 | **≥8/10** |
| Core eval (legacy 5) | 5/5 | **5/5** |
| Quote validity (holdout) | 81.8% | **≥98%** |
| False supported (holdout) | 2.9% | **≤5%** |

4b goal: improve **h-006/h-010** (semantic supported), **quote validity**, **multi_claim** without regressing JSON parse.

---

## Lessons learned (v1.4a Vast)

1. **`PRIORITY_SUFFIXES`** — do not include `-multi-`/`-multip-` (floods 850-row budget).
2. **Seq overflows** — cap excerpts via `prepare_v14_train.py` / `capped_abstract_excerpt()`.
3. **Checkpoints** — `save_strategy="steps"` pickles `SFTConfig` and crashes on Gemma4+Unsloth; use **`save_strategy="no"`** + final `lora_adapter/` save.
4. **Pipeline** — merge/GGUF via llama.cpp convert+quantize (not broken `export_gguf` adapter path).

---

## Archive after eval

| File | Purpose |
|------|---------|
| `reports/v1_4b_eval_combined_report.json` | Full go/no-go |
| `reports/v1_4b_predictions.jsonl` | Debug |
| `reports/holdout_failure_matrix.md` | v1.0–v1.4b regression |

Upload adapter: `hf upload QinEmPeRoR93/nassila-grounding-e4b-v1.4b-adapter . . --repo-type model`

See [MODEL_CARD_v1_4.md](./MODEL_CARD_v1_4.md).
