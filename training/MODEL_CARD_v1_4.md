# Model card — nassila-grounding-e4b-v1.4 (Sanad / Ouroboros)

**Status:** **PENDING** — v1.4a/b Vast train + eval not yet run. Update this file after `run_vast_pipeline.sh`.

**Planned HF repos:** `nassila-grounding-e4b-v1.4a-adapter`, `nassila-grounding-e4b-v1.4b-adapter` (or single v1.4 if fast path).

See [PHASE2_7_V1_4_WALKTHROUGH.md](./PHASE2_7_V1_4_WALKTHROUGH.md).

---

## v1.4 changes vs v1.3

| Fix | Description |
|-----|-------------|
| **Uniform JSON schema** | `canonical_claim()` — fixed key order; `hasNumericClaim` always last |
| **Priority balancing** | `-sanad-`, `-sanadsem-`, `-supp-`, etc. never crowded out by generic paraphrase rows |
| **Prompt dedup** | System message only in chat `system` role (NassilaT `validate_dataset.py`) |
| **Seq length** | 2048 on A6000; `--strict-length` on export |
| **Checkpoints** | `save_steps=50`, `eval_steps=50`, 5% eval holdout, `load_best_model_at_end` |
| **Two-step train** | 4a = data fix + v1.3 hyperparams; 4b = v1.2 hyperparams if 4a passes JSON gate |
| **Eval** | Legacy 5 + extended 20 core + 45 holdout; `failure_mode` per row |

## Training (planned)

| Field | v1.4a | v1.4b |
|-------|-------|-------|
| Train rows | 850 (seed **46**) | same file |
| Seq length | **2048** | **2048** |
| Epochs | **2** | **3** |
| Learning rate | **1e-4** | **1.5e-4** |
| Output dir | `nassila-grounding-e4b-v1.4a` | `nassila-grounding-e4b-v1.4b` |

## Evaluation targets

| Metric | v1.2 | v1.3 | v1.4 target |
|--------|------|------|-------------|
| Combined expect | 86% | 80% | **≥90%** |
| JSON parse (repair) | 100% | 86% | **≥98%** |
| Supported h-001–h-010 | 9/10 | 3/10 | **≥8/10** |
| Core eval (legacy 5) | 2/5 | 5/5 | **5/5** |
| Quote validity (holdout) | 90.9% | 36.4% | **≥98%** |

## v1.4a gate (minimum before hyperparam change)

- [ ] `audit_l3_labels.py` PASS
- [ ] `audit_chat_seq_lengths.py` — 0 overflows
- [ ] JSON parse ≥98%
- [ ] Supported h-001–h-010 ≥8/10

## Results (fill after Vast)

```
v1.4a combined:     PENDING
v1.4a JSON parse:   PENDING
v1.4a supported:    PENDING
v1.4b combined:     PENDING
GO/NO-GO:           PENDING
```

Reports: `reports/v1_4a_eval_combined_report.json`, `reports/holdout_failure_matrix.md`

## Related

- Diagnosis: [nassila_training_diagnosis.md](../nassila_training_diagnosis.md)
- Predecessor NO-GO: [MODEL_CARD_v1_3.md](./MODEL_CARD_v1_3.md)
- llama.cpp on Vast: [LLAMA_CPP_VAST.md](./LLAMA_CPP_VAST.md)
