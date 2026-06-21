# Phase 2.14 — 12B v1.14 recovery (GO)

**12B only.** Follow-up after **v1.13 NO-GO**.

**Canonical runbook:** [`docs/V113_12B_REGRESSION_FIX_REPORT.md`](../docs/V113_12B_REGRESSION_FIX_REPORT.md)  
**Context:** [`POST_V114_MAP.md`](./POST_V114_MAP.md), [`EVAL_GONOGO.md`](./EVAL_GONOGO.md)

**Ship decision:** select **12B v1.14** for `nassila-sanad-12b`. v1.12 remains the higher-combined fallback/reference.

---

## Problem summary

v1.13 added 12 v113 parity rows under the 850-row cap → 11 `supported` rows trimmed → boundary regressions + JSON parse drop. v1.14 fixes:

| Lever | Change |
|-------|--------|
| Prompt | Full TS↔Python v1.12 sync + approximation clause |
| Boost | Keep v113 + new `l3_grounding_v114_boost.jsonl` (12 rows) |
| Cap | **874** rows (no trim) |
| Train | `PHASE=14`, hyperparameters frozen (2 ep, lr=1e-4) |

---

## v1.14 prep (local)

### 1. Prompt sync (both repos)

- Nassila: `src/engine/manuscript/grounding-llm.ts`
- NassilaT: `training/scripts/validate_dataset.py`
- Golden: `tests/fixtures/grounding_prompt_golden.txt` (both repos)

```bash
# Nassila
cd "E:/Cursor Projects/Nassila"
npm test -- tests/unit/grounding-llm.test.ts

# NassilaT
cd training
python tests/unit/test_prompt_sync.py
```

### 2. Build train + chat files

```bash
cd training
python scripts/prepare_v15_train.py \
  --base data/l3_grounding_train_v14a.jsonl \
  --boost data/l3_grounding_v16_boost.jsonl data/l3_grounding_v18_boost.jsonl \
          data/l3_grounding_v110_boost.jsonl data/l3_grounding_v112_boost.jsonl \
          data/l3_grounding_v113_boost.jsonl data/l3_grounding_v114_boost.jsonl \
  --out data/l3_grounding_train_v114.jsonl

python scripts/check_contamination.py data/l3_grounding_train_v114.jsonl
python scripts/validate_dataset.py data/l3_grounding_train_v114.jsonl \
  --export-chat data/l3_grounding_chat_v114.jsonl --strict-length 2048
```

**Expect:** 874 rows, contamination 0, first-claim supported ≥281, insufficient_evidence ≥84.

### 3. Optional — re-run v1.13 inference for h-028 / h-037

Before retraining, confirm server-error rows pass with clean llama.cpp (see runbook Step 5).

---

## Vast (A100)

```bash
cd training
git pull
python scripts/check_contamination.py data/l3_grounding_train_v114.jsonl
ARM=12b PHASE=14 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

Reports: `reports/ab_12b_q6_k_v114/`.

---

## Result

Reports: `reports/ab_12b_q6_k_v114/`.

| Check | Result |
|-------|--------|
| `tier2_gates.model_gates_passed` | **true** on all seeds |
| Combined expect (mean) | **90.43%** (below v1.12 94.20%; accepted tradeoff) |
| JSON parse (with repair) | **100%** |
| Quote validity (holdout) | **100%** |
| False supported (holdout) | **2.86%** |
| h-045, h-088 | **pass all seeds** |
| `multi_claim_pass` | **84.62%** |

**Ship:** publish `exports/nassila-sanad-12b-q6_k.gguf` from v1.14 over v1.12. Future v1.15+ can try to recover v1.12-level combined score without losing h-045 / h-088.

---

## Rsync

```powershell
scp -r -P <PORT> root@<host>:/root/nassila/training/reports/ab_12b_q6_k_v114 "E:\Cursor Projects\NassilaT\training\reports\"
```

---

## Archive reference

- v1.14 runbook: [`docs/V113_12B_REGRESSION_FIX_REPORT.md`](../docs/V113_12B_REGRESSION_FIX_REPORT.md)
- Failed attempt: [`archive/PHASE2_13_12B_MULTI_CLAIM_WALKTHROUGH.md`](./archive/PHASE2_13_12B_MULTI_CLAIM_WALKTHROUGH.md)
- v1.12 quality baseline: [`archive/PHASE2_12_12B_QUALITY_WALKTHROUGH.md`](./archive/PHASE2_12_12B_QUALITY_WALKTHROUGH.md)
