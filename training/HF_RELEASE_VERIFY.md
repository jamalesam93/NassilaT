# HF release verification — Sanad S12 / S14

Checklist after **laptop smoke pass** ([`LAPTOP_SMOKE_TEST.md`](./LAPTOP_SMOKE_TEST.md), [`outputs/LAPTOP_SMOKE_SIGNOFF.md`](./outputs/LAPTOP_SMOKE_SIGNOFF.md)).

Upload commands: [`HF_PUBLISH.md`](./HF_PUBLISH.md). Checkpoint naming: [`OUROBOROS_OPERATOR_MAP.md`](./OUROBOROS_OPERATOR_MAP.md) § Sanad checkpoint naming.

---

## Ship checkpoints (must match everywhere)

| HF repo | GGUF file | Checkpoint | Gate | Combined | Quote (holdout) | False-supported |
|---------|-----------|------------|------|----------|-----------------|-----------------|
| `QinEmPeRoR93/nassila-sanad-e4b` | `nassila-sanad-e4b-q6_k.gguf` | **S12** *(legacy v1.12)* | E4B default-tier | **89.27%** | **92.98%** | **3.81%** |
| `QinEmPeRoR93/nassila-sanad-12b` | `nassila-sanad-12b-q6_k.gguf` | **S14** *(legacy v1.14)* | Tier 2 | **90.43%** | **100%** | **2.86%** |

**Do not publish** v1.13 / S13 12B. v1.12 12B remains higher-combined fallback/reference only.

---

## Files to keep in sync

| Artifact | Path |
|----------|------|
| E4B model card | [`MODEL_CARD_sanad_e4b.md`](./MODEL_CARD_sanad_e4b.md) |
| 12B model card | [`MODEL_CARD_sanad_12b.md`](./MODEL_CARD_sanad_12b.md) |
| E4B HF README | [`hf_readmes/nassila-sanad-e4b/README.md`](./hf_readmes/nassila-sanad-e4b/README.md) |
| 12B HF README | [`hf_readmes/nassila-sanad-12b/README.md`](./hf_readmes/nassila-sanad-12b/README.md) |
| GO/NO-GO log | [`EVAL_GONOGO.md`](./EVAL_GONOGO.md) |
| Vast reports | `reports/ab_e4b_q6_k_v112/`, `reports/ab_12b_q6_k_v114/` |

---

## Automated verify (recommended)

From `training/` with venv active:

```powershell
.\scripts\verify_hf_release.ps1
```

Defaults to your LM Studio paths:

- `D:\LM_Studio_Models\lmstudio-community\nassila-sanad-e4b-q6_k`
- `D:\LM_Studio_Models\lmstudio-community\nassila-sanad-12b-q6_k`

Checks: HF file list, size match, SHA256 match (LFS), README metrics vs repo sources.  
Report: `outputs/hf_release_verify_report.json`

Fast size-only (skip hashing ~16 GB):

```powershell
.\scripts\verify_hf_release.ps1 -NoHash
```

---

## Verification checklist

- [x] Laptop smoke **PASS** for E4B and 12B (sign-off filled — RTX 4060 8 GB, 2026-06-21)
- [x] E4B metrics in model card + HF README match table above
- [x] 12B metrics in model card + HF README match table above (S14, not S12 12B)
- [x] HF README `base_model` correct (`google/gemma-4-E4B-it` / `google/gemma-4-12B-it`)
- [x] GGUF filenames on HF match ship table
- [x] v1.13 GGUF **not** uploaded under any tag
- [x] Nassila `OUROBOROS_CONTEXT.md` / `PRODUCT.md` reference S12 E4B + S14 12B
- [x] Local GGUFs match HF (size + SHA256) — `outputs/hf_release_verify_report.json` (2026-06-21)

---

## Upload (if needed)

```bash
# README only (checkpoint label update — no GGUF re-upload)
hf upload QinEmPeRoR93/nassila-sanad-e4b \
  training/hf_readmes/nassila-sanad-e4b/README.md README.md \
  --repo-type model --commit-message "Sanad S12 (legacy v1.12) — checkpoint label"

hf upload QinEmPeRoR93/nassila-sanad-12b \
  training/hf_readmes/nassila-sanad-12b/README.md README.md \
  --repo-type model --commit-message "Sanad S14 (legacy v1.14) — checkpoint label"
```

GGUF upload: see [`PHASE2_9_AB_PILOT_WALKTHROUGH.md`](./PHASE2_9_AB_PILOT_WALKTHROUGH.md) Part 9.

---

## Status (repo docs)

**Last verified:** 2026-06-21 — laptop smoke **PASS** + HF verify **PASS** (RTX 4060 8 GB). Local GGUFs byte-identical to Hub (SHA256). Report: [`outputs/hf_release_verify_report.json`](./outputs/hf_release_verify_report.json).
