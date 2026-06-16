# Phase 2.8 — v1.5 on Vast (quote validity + contrastive data)

**Checkpoint to beat:** `nassila-grounding-e4b-v1.4a` — combined 90%, quote validity **81.8%** (target **≥98%**).  
**v1.4b lesson:** More epochs (3 @ 1.5e-4) did **not** improve quotes. v1.5 fixes are **data / contrastive**, not hyperparams.

**Agent brief:** [Nassila `docs/OUROBOROS_CONTEXT.md` §7–§12](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md)

---

## Train file

Use **`data/l3_grounding_train_v15.jsonl`** — v1.4a base + `l3_grounding_v15_boost.jsonl` (~850 rows, seq-safe).

Build on **PC** (commit + `git push` so Vast can `git pull`) or on Vast:

```bash
python scripts/prepare_v15_train.py --base data/l3_grounding_train_v14a.jsonl
python scripts/validate_dataset.py data/l3_grounding_train_v15.jsonl \
  --export-chat data/l3_grounding_chat_v15.jsonl --strict-length 2048
python scripts/audit_chat_seq_lengths.py data/l3_grounding_chat_v15.jsonl --max-length 2048
```

Boost rows: paraphrase-supported (`-para-`), multi-claim (`-multi-`), quote-fidelity (`-quote-`). See `nassila_training_diagnosis.md` §6.2.

---

## v1.5 on Vast (Tier 2 go/no-go)

| Setting | Value |
|---------|--------|
| Train file | `data/l3_grounding_train_v15.jsonl` |
| Hyperparams | **2 epochs**, LR **1e-4** (v1.4a recipe — **not** 4b) |
| `save_strategy` | **`no`** (Unsloth pickle crash on checkpoint save) |
| Output | `outputs/nassila-grounding-e4b-v1.5/` |
| Ship bar | [OUROBOROS_CONTEXT §10](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md) Tier 2 model gates |

### Quick path (pipeline script)

After `git pull`, llama.cpp **b9608** built ([LLAMA_CPP_VAST.md](./LLAMA_CPP_VAST.md)):

```bash
cd ~/nassila/training
source ~/nassila/.venv/bin/activate
chmod +x scripts/run_vast_pipeline.sh

PHASE=5 bash scripts/run_vast_pipeline.sh
```

Resume merge + eval only (adapter already trained):

```bash
SKIP_TRAIN=1 PHASE=5 bash scripts/run_vast_pipeline.sh
```

### Manual path

```bash
cd ~/nassila/training
source ~/nassila/.venv/bin/activate

python scripts/prepare_v15_train.py --base data/l3_grounding_train_v14a.jsonl
python scripts/validate_dataset.py data/l3_grounding_train_v15.jsonl \
  --export-chat data/l3_grounding_chat_v15.jsonl --strict-length 2048

python scripts/train_qlora_gemma4_e4b.py \
  --phase 5 \
  --train-file data/l3_grounding_train_v15.jsonl \
  --chat-file data/l3_grounding_chat_v15.jsonl

python scripts/merge_adapter_gemma4.py \
  --adapter-dir outputs/nassila-grounding-e4b-v1.5/lora_adapter \
  --out-dir exports/hf-merged-v1.5-bf16 \
  --max-seq-length 2048

python ~/llama.cpp/convert_hf_to_gguf.py exports/hf-merged-v1.5-bf16 \
  --outfile exports/nassila-grounding-e4b-v1.5-f16.gguf --outtype f16

~/llama.cpp/build/bin/llama-quantize \
  exports/nassila-grounding-e4b-v1.5-f16.gguf \
  exports/nassila-grounding-e4b-v1.5-q6_k.gguf Q6_K
```

**Eval** (llama-server port **1234**):

```bash
python scripts/run_l3_eval_batch.py \
  --base-url http://127.0.0.1:1234 \
  --model nassila-grounding \
  --data data/eval_samples.jsonl data/eval_samples_extended.jsonl data/eval_holdout_45.jsonl \
  --chat-template --retry 1 --repair \
  --out reports/v1_5_predictions.jsonl

python scripts/run_eval_reports.py \
  --predictions reports/v1_5_predictions.jsonl \
  --out-dir reports --prefix v1_5_ --repair

python scripts/compare_eval_versions.py
```

Read `reports/v1_5_eval_combined_report.json` → `tier2_gates.model_gates_passed`.

---

## v1.5 go/no-go (Tier 2 ship bar)

All gates in [OUROBOROS_CONTEXT §10](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md). Summary:

| Metric | v1.4a | v1.5 target | Slice |
|--------|-------|-------------|-------|
| Combined expect | 90% | **≥90%** (target ≥92%) | Combined 70 rows |
| JSON parse (repair) | 100% | **≥98%** | Combined |
| Supported h-001–h-010 | 8/10 | **≥8/10** | Holdout |
| Core eval (legacy 5) | 5/5 | **5/5** | Legacy |
| Quote validity | 81.8% | **≥98%** | Holdout |
| False supported | 2.9% | **≤5%** | Holdout |

**Primary v1.5 goal:** quote validity on holdout (h-006, h-010, h-043, h-045 persistent misses at v1.4a).

**No-go:** Keep v1.4a adapter; expand `l3_grounding_v15_boost.jsonl` + re-run `prepare_v15_train.py` before another Vast cycle.

---

## PC preflight (before `git push`)

From `E:\Cursor Projects\NassilaT\training`:

```powershell
python scripts/prepare_v15_train.py --base data/l3_grounding_train_v14a.jsonl
python scripts/validate_dataset.py data/l3_grounding_train_v15.jsonl
python scripts/audit_l3_labels.py data/l3_grounding_train_v15.jsonl --json reports/v1_5_audit_summary.json
```

Commit and push train data + scripts so Vast can `git pull`:

```powershell
cd "E:\Cursor Projects\NassilaT"
git add training/data/l3_grounding_train_v15.jsonl training/data/l3_grounding_v15_boost.jsonl training/scripts/
git commit -m "Add v1.5 train set and Vast pipeline phase 5."
git push origin main
```

---

## Lessons carried from v1.4

1. **`save_strategy="no"`** — mid-training checkpoints crash Unsloth/Gemma4 on Vast.
2. **Merge/GGUF** — llama.cpp `convert_hf_to_gguf` + `llama-quantize` (not broken Unsloth `export_gguf`).
3. **llama.cpp pin** — tag **b9608**, `LLAMA_BUILD_UI=OFF` ([LLAMA_CPP_VAST.md](./LLAMA_CPP_VAST.md)).
4. **Row budget** — ~850 rows; boost trims over-represented `supported` from base, keeps all boost rows.

---

## Archive after eval

| File | Purpose |
|------|---------|
| `reports/v1_5_eval_combined_report.json` | Tier 2 go/no-go |
| `reports/v1_5_predictions.jsonl` | Debug |
| `reports/holdout_failure_matrix.md` | v1.0–v1.5 regression |

Upload adapter (if Tier 2 passes):

```bash
cd outputs/nassila-grounding-e4b-v1.5/lora_adapter
hf upload QinEmPeRoR93/nassila-grounding-e4b-v1.5-adapter . . --repo-type model
```

See [EVAL_GONOGO.md](./EVAL_GONOGO.md), [MODEL_CARD_v1_4.md](./MODEL_CARD_v1_4.md) (v1.4 baseline), prior walkthrough [PHASE2_7_V1_4_WALKTHROUGH.md](./PHASE2_7_V1_4_WALKTHROUGH.md).
