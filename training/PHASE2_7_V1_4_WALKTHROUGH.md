# Phase 2.7 — v1.4 on Vast (training diagnosis fix)

Act on [nassila_training_diagnosis.md](../nassila_training_diagnosis.md) and [v1_4_plan_review.md](../v1_4_plan_review.md).

**Prerequisite:** `l3_grounding_train.jsonl` = **850** rows, **seed 46**, canonical claim schema + priority balancing.

**Baseline to beat:** v1.2 combined 86%, supported 9/10; v1.3 core 5/5 but JSON parse 86%, supported 3/10.

---

## Two-step Vast runs (recommended)

| Phase | Data / code | Hyperparams | Gate |
|-------|-------------|-------------|------|
| **v1.4a** | `canonical_claim`, priority balance, prompt dedup, seq 2048 | **v1.3** (2 ep, 1e-4) | JSON parse ≥98%, supported h-001–h-010 ≥8/10 |
| **v1.4b** | Same train file as 4a | **v1.2** (3 ep, 1.5e-4) | Full go/no-go ≥90% combined |

If **4a fails JSON**, fix schema/balance — do **not** run 4b yet.

Output dirs: `outputs/nassila-grounding-e4b-v1.4a`, `outputs/nassila-grounding-e4b-v1.4b`.

---

## PC prep (before Vast)

```powershell
cd training

# Regenerate train data (seed 46)
python scripts/generate_l3_from_corpus.py --seed 46

python scripts/audit_l3_labels.py data/l3_grounding_train.jsonl
python scripts/validate_dataset.py data/l3_grounding_train.jsonl `
  --export-chat data/l3_grounding_chat.jsonl --strict-length 2048
python scripts/audit_chat_seq_lengths.py data/l3_grounding_chat.jsonl --max-length 2048

python -m unittest discover -s tests -p "test_*.py"
```

Commit/push `l3_grounding_train.jsonl` + scripts before renting Vast.

---

## Vast — single pipeline script

After clone + venv + [LLAMA_CPP_VAST.md](./LLAMA_CPP_VAST.md) (branch **b9608**):

```bash
cd training
chmod +x scripts/run_vast_pipeline.sh

# v1.4a (schema fix attribution)
PHASE=4a bash scripts/run_vast_pipeline.sh

# After 4a JSON gate passes:
PHASE=4b bash scripts/run_vast_pipeline.sh
```

### Optional: alternate checkpoint

If final checkpoint fails JSON parse, retry merge/GGUF/eval on other saved checkpoints (~30 min each):

```bash
CHECKPOINT=checkpoint-100 PHASE=4a bash scripts/run_vast_pipeline.sh
```

`save_total_limit=3` keeps the last three step checkpoints under `outputs/nassila-grounding-e4b-v1.4a/`.

---

## Manual steps (if not using pipeline script)

### Train v1.4a

```bash
python scripts/train_qlora_gemma4_e4b.py \
  --train-file data/l3_grounding_train.jsonl \
  --phase 4a \
  --chat-file data/l3_grounding_chat.jsonl
```

### Eval

```bash
python scripts/run_l3_eval_batch.py \
  --base-url http://127.0.0.1:8080 \
  --model nassila-grounding \
  --data data/eval_samples.jsonl data/eval_samples_extended.jsonl data/eval_holdout_45.jsonl \
  --chat-template --retry 1 --repair \
  --out reports/v1_4a_predictions.jsonl

python scripts/run_eval_reports.py \
  --predictions reports/v1_4a_predictions.jsonl \
  --out-dir reports --prefix v1_4a_ --repair

python scripts/compare_eval_versions.py
```

---

## Go/no-go (v1.4b / ship)

| Metric | v1.2 | v1.3 | v1.4 target |
|--------|------|------|-------------|
| Combined expect | 86% | 80% | **≥90%** |
| JSON parse (repair) | 100% | 86% | **≥98%** |
| Supported h-001–h-010 | 9/10 | 3/10 | **≥8/10** |
| Core eval (legacy 5) | 2/5 | 5/5 | **5/5** |
| Extended core (20) | — | — | stable category metrics |
| Quote validity (holdout) | 90.9% | 36.4% | **≥98%** |

Primary: holdout n=45. Extended core n=20 for category stability.

---

## Nassila app merge checklist (later)

When merging NassilaT → [Nassila](https://github.com/jamalesam93/Nassila):

- [ ] Align `build_grounding_user_prompt` / schema line in `src/engine/manuscript/grounding-llm.ts` (remove duplicate system line; `hasNumericClaim` last in schema hint)
- [ ] Ship GGUF + adapter only after v1.4b GO
- [ ] Update `llm-presets.ts` model id

---

## Reports to archive after eval

| File | Purpose |
|------|---------|
| `reports/v1_4a_eval_combined_report.json` | 4a gate |
| `reports/v1_4b_eval_combined_report.json` | Full go/no-go |
| `reports/holdout_failure_matrix.md` | Cross-version regression |
| `reports/v1_4a_predictions.jsonl` | Debug parse failures |

Update [MODEL_CARD_v1_4.md](./MODEL_CARD_v1_4.md) with GO/NO-GO.
