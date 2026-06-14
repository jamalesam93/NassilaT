# Model card — nassila-grounding-e4b-v1.4 (Sanad / Ouroboros)

**HF adapters:**
- v1.4a: [`QinEmPeRoR93/nassila-grounding-e4b-v1.4a-adapter`](https://huggingface.co/QinEmPeRoR93/nassila-grounding-e4b-v1.4a-adapter) — **4a GATE PASS**
- v1.4b: `QinEmPeRoR93/nassila-grounding-e4b-v1.4b-adapter` — **PENDING**

Train file for both phases: `data/l3_grounding_train_v14a.jsonl` (seq-safe excerpts).

See [PHASE2_7_V1_4_WALKTHROUGH.md](./PHASE2_7_V1_4_WALKTHROUGH.md).

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

**4a gate:** PASS (JSON + supported cluster recovered from v1.3 `parse_json` failures).

**Remaining misses:** h-006, h-010 (`wrong_verdict`); h-043, h-045 (holdout edge cases).

Reports: `reports/v1_4a_eval_combined_report.json`, `reports/holdout_failure_matrix.md`

---

## v1.4b (planned)

| Field | v1.4a | v1.4b |
|-------|-------|-------|
| Train rows | 850 (`train_v14a.jsonl`) | same |
| Epochs | 2 | **3** |
| Learning rate | 1e-4 | **1.5e-4** |
| Output dir | `nassila-grounding-e4b-v1.4a` | `nassila-grounding-e4b-v1.4b` |

**Ship bar:** hold quote validity ≥98%, keep JSON 100%, core 5/5, improve h-006/h-010 if possible.

## v1.4b results

```
PENDING — run PHASE=4b on Vast after git pull
```

---

## Related

- [nassila_training_diagnosis.md](../nassila_training_diagnosis.md)
- Predecessor NO-GO: [MODEL_CARD_v1_3.md](./MODEL_CARD_v1_3.md)
- llama.cpp on Vast: [LLAMA_CPP_VAST.md](./LLAMA_CPP_VAST.md)
