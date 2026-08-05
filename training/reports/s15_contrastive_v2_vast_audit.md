# S15 contrastive-v2 Vast audit (2026-08-05)

**Model:** [QinEmPeRoR93/nassila-sanad-4b](https://huggingface.co/QinEmPeRoR93/nassila-sanad-4b) `nassila-sanad-4b-q6_k.gguf`
**Harness:** `sanad-grounding-v1` · contrastive-v2 · 308 rows (`eval_holdout_body_contrastive_frozen_v2.jsonl`)
**Runner:** Vast RTX 4090 (CUDA 13.1, driver 610.57) + `llama.cpp@master` llama-server · `--reasoning-format none --skip-chat-parsing`
**Branches:** seed 42, temp 0.2, retry 1, repair on — same GGUF both branches.

| Branch | Prompt path |
|--------|-------------|
| A (fast) | `--disable-thinking` → `/no_think` appended to user turn |
| B (claim) | no flag → "keep reasoning concise" note (matches original 94.48% claim run) |

## Verdict

**The claimed 94.48% / 4.87% numbers are real for the intended (thinking-off) harness.** Batch A reproduces them within noise on the same GGUF via llama.cpp. The laptop's 75% / 13.31% was a **harness artifact** (LM Studio partial thinking suppression + schema echo), not a model weakness.

## Metrics (this run)

| Metric | **Vast A** (fast) | **Vast B** (claim) | **Laptop** (LM Studio) | Claimed |
|--------|------------------:|-------------------:|-----------------------:|--------:|
| JSON parse (strict/repair) | **99.35%** | 20.45% / 35.71% | 82.47% / 88.31% | ~99%+ |
| Expect checks pass | **94.16%** | 31.49% | 75.00% | 94.48% |
| False supported | **5.19%** | 3.57% | 13.31% | 4.87% |
| Contradicted pass | **85.83%** | 20.00% | 50.83% | — |
| Not-in-source pass | **99.47%** | 38.83% | 90.43% | — |

## Failure-mode breakdown (308 rows)

**Batch A (fast):** 290 pass · 14 wrong_verdict · 2 parse_json · 2 forbidden_verdict.
- 16 of 18 failures pick `supported` on contradicted rows → false-supported is concentrated in the contradicted category (17/18 failures are contradicted).

**Batch B (claim):** 97 pass · 198 parse_json · 9 forbidden_verdict · 2 wrong_verdict · 2 min_claims.
- Reasoning left on → long think blocks pollute the JSON. Confirms the laptop failure mechanism.

**Cross-branch:** 17 rows fail in both (genuinely hard) · 1 fails only in A · 194 fail only in B (almost all `must_parse_json`).

## Interpretation

- Same GGUF + tight harness on a clean CUDA 13.1 box → **expect 94.16%, false-supported 5.19%** ≈ claimed **94.48% / 4.87%**.
- Batch B proves the failure driver: un-suppressed reasoning breaks JSON, so the laptop's low numbers came from LM Studio not fully applying `/no_think`, plus the schema-echo footgun (`?: string[]` TS annotations in `validate_dataset.py` ground-truth schema echoed verbatim).
- With thinking suppressed, S15 is a solid default-tier model; false-supported stays at ~5% (worst on contradicted rows).

## Artifacts

- `training/reports/s15_contrastive_v2_vast_fast_predictions.jsonl` · `s15_contrastive_v2_vast_fast_eval.json`
- `training/reports/s15_contrastive_v2_vast_claim_predictions.jsonl` · `s15_contrastive_v2_vast_claim_eval.json`
- Laptop baseline: `training/reports/laptop_s15_quoteeval/cv2_eval_holdout_report.json`

## Notes

- Runner script: `training/scripts/run_s15_contrastive_vast.sh` (builds llama.cpp CUDA, installs CUDA 13 toolkit if nvcc<12, downloads GGUF, runs both branches; idempotent per branch).
- Quote validity is `null` in this harness (not a quote-eval split).
- Batch B is an artifact demonstration, not a candidate path — always run S15 with thinking off.
- Vast instance destroyed after download; all artifacts local.
