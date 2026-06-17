# Model card — nassila-grounding-e4b-v1.4 (Sanad / Ouroboros)

**HF adapters:**
- v1.4a: [`QinEmPeRoR93/nassila-grounding-e4b-v1.4a-adapter`](https://huggingface.co/QinEmPeRoR93/nassila-grounding-e4b-v1.4a-adapter) — **SHIP** (4a gate PASS)
- v1.4b: [`QinEmPeRoR93/nassila-grounding-e4b-v1.4b-adapter`](https://huggingface.co/QinEmPeRoR93/nassila-grounding-e4b-v1.4b-adapter) — **NO-GO** (archived)

**Production pick:** **v1.4a** — best combined expect (90%), JSON parse recovered, core 5/5.

Train file for both phases: `data/l3_grounding_train_v14a.jsonl` (850 rows, seq-safe excerpts).

See [PHASE2_7_V1_4_WALKTHROUGH.md](./PHASE2_7_V1_4_WALKTHROUGH.md). Model cards live on each HF adapter repo README.

---

## v1.4 fixes vs v1.3

| Fix | Description |
|-----|-------------|
| Uniform JSON schema | `canonical_claim()` — `hasNumericClaim` always last |
| Priority balancing | Rare suffixes only (`-sanad-`, `-supp-`, etc.); not `-multi-`/`-multip-` |
| Prompt dedup | System message only in chat `system` role |
| Seq length | 2048; `prepare_v14_train.py` caps excerpts |
| Training | `save_strategy=no` (Unsloth/Gemma4 checkpoint pickle bug) |

---

## v1.4a evaluation (Vast, Q6_K, 70 rows)

| Metric | v1.2 | v1.3 | v1.4a | Target |
|--------|------|------|-------|--------|
| Combined expect | 86% | 80% | **90%** | ≥90% |
| JSON parse (repair) | 100% | 86% | **100%** | ≥98% |
| Supported h-001–h-010 | 9/10 | 3/10 | **8/10** | ≥8/10 |
| Core eval (legacy 5) | 2/5 | 5/5 | **5/5** | 5/5 |
| Quote validity (holdout) | 90.9% | 36.4% | **81.8%** | ≥98% |
| False supported (holdout) | 0% | 2.9% | **2.9%** | ≤5% |

**4a gate:** PASS — JSON + supported cluster recovered from v1.3 `parse_json` failures.

**Holdout misses:** h-006, h-010 (`wrong_verdict`); h-043 (`forbidden_verdict`); h-045 (`wrong_verdict`).

Reports: `reports/v1_4a_eval_combined_report.json`

---

## v1.4b evaluation (Vast, Q6_K, 70 rows)

| Field | v1.4a | v1.4b |
|-------|-------|-------|
| Train rows | 850 (`train_v14a.jsonl`) | same |
| Epochs | 2 | **3** |
| Learning rate | 1e-4 | **1.5e-4** |
| Combined expect | **90%** | **87.1%** |
| JSON parse (repair) | 100% | **100%** |
| Supported h-001–h-010 | 8/10 | **8/10** |
| Core eval (legacy 5) | 5/5 | **5/5** |
| Extended core (20) | 85% | **80%** |
| Holdout expect | 91.1% | **88.9%** |
| Quote validity (holdout) | 81.8% | **81.8%** (no gain) |
| False supported (holdout) | 2.9% | **0%** |

**4b verdict:** NO-GO — extra epochs did not improve quote validity or combined score; regressed h-008, h-034 vs 4a. Fixed h-006.

**Holdout misses:** h-008, h-010, h-034, h-043, h-045.

Reports: `reports/v1_4b_eval_combined_report.json`, `reports/holdout_failure_matrix.md`

---

## Holdout regression (4a vs 4b)

| Row | v1.4a | v1.4b | Notes |
|-----|-------|-------|-------|
| h-006 | wrong_verdict | **pass** | 4b win |
| h-008 | pass | **wrong_verdict** | 4b regression |
| h-010 | wrong_verdict | wrong_verdict | persistent |
| h-034 | pass | **wrong_verdict** | 4b regression |
| h-043 | forbidden_verdict | wrong_verdict | mode shift |
| h-045 | wrong_verdict | wrong_verdict | persistent |

---

## Related

- [nassila_training_diagnosis.md](../nassila_training_diagnosis.md)
- Predecessor NO-GO: v1.3 (see git history / `holdout_failure_matrix.md`)
- llama.cpp on Vast: [LLAMA_CPP_VAST.md](./LLAMA_CPP_VAST.md)
