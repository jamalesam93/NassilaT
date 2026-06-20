# Phase 2.13 — 12B v1.13 multi_claim boost (h-045 / h-088)

**12B only** — adds targeted parity subgroup-split rows on top of v1.12. No E4B train. No prompt change (v1.12 prompt stays).

## Problem

12B v1.12 passes Tier 2 but still bundles h-045 / h-088 into a single `weak` claim (`multi_claim` 69.23%). Gold requires **2 claims**: studied subgroup `weak`, unstudied subgroup `not_in_source`.

## Boost

`data/l3_grounding_v113_boost.jsonl` — **12 rows**, `v113_parity_subgroup_split`:

- Adults/children, seniors/infants, and 10 parallel patterns
- Always: claim 1 = studied arm `weak` + quote; claim 2 = parity arm `not_in_source`, no quote
- Never `supported` on parity passages (matches eval gold)

Train merge: v14a + v16/v18/v110/v112 boosts + **v113** → `l3_grounding_train_v113.jsonl` (**850 rows**, contamination 0).

## Vast (A100)

```bash
cd training
git pull
python scripts/check_contamination.py data/l3_grounding_train_v113.jsonl
ARM=12b PHASE=13 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

Reports: `reports/ab_12b_q6_k_v113/`.

## Success criteria

| Check | Target |
|-------|--------|
| `tier2_gates.model_gates_passed` | **true** (must not regress) |
| **h-045, h-088** | **pass** on all seeds |
| `multi_claim_pass` | **≥80%** (stretch; was 69.23% at v1.12) |
| Combined expect (mean) | ≥ v1.12 mean (94.20%) |

**Ship when:** Tier 2 holds **and** h-045 + h-088 pass. Publish `exports/nassila-sanad-12b-q6_k.gguf` over v1.12.

## Rsync

```powershell
scp -r -P <PORT> root@<host>:/root/nassila/training/reports/ab_12b_q6_k_v113 "E:\Cursor Projects\NassilaT\training\reports\"
```

## If v1.13 fails

Keep shipping **12B v1.12** (Tier 2 PASS). Do not publish v1.13 unless gates improve on the target rows.
