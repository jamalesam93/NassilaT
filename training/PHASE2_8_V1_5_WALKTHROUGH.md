# Phase 2.8 — v1.5 / v1.6 / v1.7 on Vast (quote validity + contrastive data)

**Checkpoint to beat:** `nassila-grounding-e4b-v1.4a` — combined 90%, quote validity **81.8%** (target **≥98%**).  
**v1.4b lesson:** More epochs (3 @ 1.5e-4) did **not** improve quotes. Fixes are **data / contrastive**, not hyperparams.

**Agent brief:** [Nassila `docs/OUROBOROS_CONTEXT.md` §7–§12](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md)

---

## ⚠️ v1.5 result — NO-GO and contaminated (do not ship, do not trust)

`reports/v1_5_eval_combined_report.json`: combined expect **88.57%** (< 90% → **FAIL**, down from v1.4a 90.0%).

Two problems, both fixed in **v1.6**:

1. **Train/eval contamination.** 7 of 27 v1.5 boost rows reused **verbatim** eval passages/excerpts (h-006, h-010, h-043, h-045, eval-007/021). The h-006/h-010 "fix" and most of the quote-validity 81.8%→100% jump are **memorization**, not learning. Run `python scripts/check_contamination.py data/l3_grounding_train_v15.jsonl` to see all 7.
2. **Eroded hedge middle.** The v1.5 boost had 0 `weak` and 0 `insufficient_evidence` rows → regressed h-032, h-034 (weak→not_in_source) and eval-012 (insufficient→decisive).

**Use v1.6 below.** `prepare_v15_train.py` now hard-fails on contamination, so a contaminated train file cannot be built again.

### v1.6 train file (decontaminated + rebalanced)

```bash
python scripts/prepare_v15_train.py \
  --base data/l3_grounding_train_v14a.jsonl \
  --boost data/l3_grounding_v16_boost.jsonl \
  --out data/l3_grounding_train_v16.jsonl
python scripts/validate_dataset.py data/l3_grounding_train_v16.jsonl \
  --export-chat data/l3_grounding_chat_v16.jsonl --strict-length 2048
python scripts/audit_l3_labels.py data/l3_grounding_train_v16.jsonl --json reports/v1_6_audit_summary.json
python scripts/check_contamination.py data/l3_grounding_train_v16.jsonl   # must print 0
```

850 rows; verdict mix contradicted 142 / supported 343 / weak 108 / not_in_source 185 / insufficient 72. Boost `data/l3_grounding_v16_boost.jsonl` = 32 rows: 8 paraphrase, 6 quote-fidelity, 5 contrastive not_in_source, **6 weak**, **4 insufficient**, 3 multi-partial. Train with the **same v1.4a recipe** (2 epochs, LR 1e-4), then eval with `--prefix v1_6_`.

### v1.6 on Vast (current — Tier 2 go/no-go)

| Setting | Value |
|---------|--------|
| Train file | `data/l3_grounding_train_v16.jsonl` |
| Hyperparams | **2 epochs**, LR **1e-4** (v1.4a recipe) |
| `save_strategy` | **`no`** (Unsloth pickle crash on checkpoint save) |
| Output | `outputs/nassila-grounding-e4b-v1.6/` |
| Ship bar | [OUROBOROS_CONTEXT §10](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md) Tier 2 model gates |

```bash
cd ~/nassila/training
source ~/nassila/.venv/bin/activate
chmod +x scripts/run_vast_pipeline.sh

PHASE=6 bash scripts/run_vast_pipeline.sh
```

Resume merge + eval only (adapter already trained):

```bash
SKIP_TRAIN=1 PHASE=6 bash scripts/run_vast_pipeline.sh
```

---

## v1.6 result — clean NO-GO (trustworthy), and the v1.7 fix

`reports/v1_6_eval_combined_report.json`: combined expect **88.57%** (< 90% → **FAIL**), but **contamination = 0** — so unlike v1.5 the result is trustworthy. Quote validity holdout **100%**, supported h-001–h-010 10/10, JSON 100% all genuine. The 8 combined misses cluster into:

- **Compound / multi-claim** (h-042, h-043, h-045, eval-018): model grants blanket `supported` on two-part claims; eval-018 didn't split (`min_claims:2`). Causes the holdout false-supported overflow (5.88% > 5%).
- **Evidential weak/insufficient** (h-032, h-034, eval-012/013): v1.6 taught modal hedges (`may/could`); misses use evidential hedging (`suggested … causality unclear`, `mixed`).

### v1.7 train file (compound + evidential boost)

```bash
python scripts/prepare_v15_train.py \
  --base data/l3_grounding_train_v14a.jsonl \
  --boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v17_boost.jsonl \
  --out data/l3_grounding_train_v17.jsonl
python scripts/check_contamination.py data/l3_grounding_train_v17.jsonl   # must print 0
python scripts/validate_dataset.py data/l3_grounding_train_v17.jsonl \
  --export-chat data/l3_grounding_chat_v17.jsonl --strict-length 2048
python scripts/audit_l3_labels.py data/l3_grounding_train_v17.jsonl --json reports/v1_7_audit_summary.json
```

850 rows; verdict mix contradicted 145 / supported 330 / weak 114 / not_in_source 185 / insufficient 76. `data/l3_grounding_v17_boost.jsonl` = 17 new rows: **8 hard compound** (split + contradicted/out-of-scope, forbids blanket supported), **6 evidential weak**, **3 insufficient**. Merged with the 32 v1.6 boost rows (49 boost total). Same v1.4a recipe (2 epochs, LR 1e-4).

### v1.7 on Vast (current — Tier 2 go/no-go)

| Setting | Value |
|---------|--------|
| Train file | `data/l3_grounding_train_v17.jsonl` |
| Hyperparams | **2 epochs**, LR **1e-4** (v1.4a recipe) |
| Output | `outputs/nassila-grounding-e4b-v1.7/` |

```bash
cd ~/nassila/training
source ~/nassila/.venv/bin/activate
chmod +x scripts/run_vast_pipeline.sh

PHASE=7 bash scripts/run_vast_pipeline.sh
```

Resume merge + eval only:

```bash
SKIP_TRAIN=1 PHASE=7 bash scripts/run_vast_pipeline.sh
```

(`PHASE` defaults to **7** if omitted. The pipeline runs `check_contamination.py` before training on every phase.)

---

## v1.7 result — zero delta vs v1.6 (do not rerun v1.7)

`reports/v1_7_eval_combined_report.json` matches v1.6 exactly (**88.57%**, same 8 failures). The v1.7 boost did not change model behavior — root cause was **claims copied from SOURCE_EXCERPT** instead of PASSAGE (see `nassila_training_diagnosis.md`). v1.7 boost is **archived**; use v1.8 below.

---

## v1.8 train file (passage-claim prompt + v18 boost)

Prompt update (train + Nassila `grounding-llm.ts`): claims must restate PASSAGE assertions. Eval fix: `eval-018` → `contradicted` + `not_in_source`, `min_claims: 2`.

```bash
python scripts/prepare_v15_train.py \
  --base data/l3_grounding_train_v14a.jsonl \
  --boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v18_boost.jsonl \
  --out data/l3_grounding_train_v18.jsonl
python scripts/check_contamination.py data/l3_grounding_train_v18.jsonl
python scripts/validate_dataset.py data/l3_grounding_train_v18.jsonl \
  --export-chat data/l3_grounding_chat_v18.jsonl --strict-length 2048
```

850 rows; **67 boost rows** (32 v1.6 + 35 v1.8): passage-number compound, no-`supported` multi, subgroup scope, weak-when-topic-in-excerpt, insufficient design-only, hedge-in-passage.

### v1.8 on Vast (current — Tier 2 go/no-go)

```bash
PHASE=8 bash scripts/run_vast_pipeline.sh
```

(`PHASE` defaults to **8**.)

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
