# Phase 2.11 — E4B v1.12 recovery (default-tier ship)

Recovers from v1.11 regression. Spec: [`V112_RECOVERY_PLAN.md`](../V112_RECOVERY_PLAN.md). Policy: [`docs/DUAL_TIER_POLICY.md`](../docs/DUAL_TIER_POLICY.md).

## What changed vs v1.11

1. **Prompt v1.12** — passage-number discipline + parity compound guardrail; scope rows use `weak` only.
2. **Boost** — `l3_grounding_v112_boost.jsonl` (23 rows, 6 scope, all `weak` on studied subgroup).
3. **Gates** — ship E4B on **E4B default-tier**, not Tier 2. Tier 2 remains for 12B/31B.

## Local prep (done in repo)

- `data/l3_grounding_train_v112.jsonl` (850 rows, contamination 0)
- `fixtures/grounding_prompt_golden.txt` (v1.12 prompt)

## Vast

```bash
cd training
git pull
python scripts/check_contamination.py data/l3_grounding_train_v112.jsonl
ARM=e4b PHASE=12 MULTI_SEED=1 bash scripts/run_ab_pilot_pipeline.sh
```

## Success criteria

| Check | Target |
|-------|--------|
| `e4b_default_gates.model_gates_passed` | **true** (all seeds or mean) |
| `v110_baseline_beat.all_met` | **true** — must beat v1.10 (88.12% / 89.47% quote / 6.57% false-sup) |
| `tier2_gates.model_gates_passed` | nice-to-have; **not** E4B ship requirement |
| h-043, h-045 | pass |
| eval-002, eval-017, h-012 | back to `contradicted` (no `supported` spam) |

**Publish E4B when default-tier passes:** `exports/nassila-sanad-e4b-q6_k.gguf` → `QinEmPeRoR93/nassila-sanad-e4b`.

If v1.12 fails baseline beat, **keep shipping v1.10 E4B** — do not publish v1.11.

## Rsync before destroy

```bash
scp -r root@<host>:/root/nassila/training/reports/ab_e4b_q6_k_v112 ./training/reports/
```

Include `seed_*_predictions.jsonl` for forensics.
