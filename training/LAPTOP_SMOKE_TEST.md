# Laptop smoke test — Sanad GGUF acceptance

Fast local acceptance for downloaded **`nassila-sanad-e4b-q6_k.gguf`** (v1.12) and **`nassila-sanad-12b-q6_k.gguf`** (v1.14) before marking the HF release as verified.

This is **not** the full 115-row Tier 2 eval (that ran on Vast). It confirms LM Studio loads the GGUF, returns Sanad JSON, and passes four canonical rows including the v1.14 h-045 / h-088 subgroup fix.

**Operator map:** [`POST_V114_MAP.md`](./POST_V114_MAP.md) · **LM Studio setup:** [`LM_STUDIO_INTEGRATION.md`](./LM_STUDIO_INTEGRATION.md)

---

## Prerequisites

1. **LM Studio** with llama.cpp **2.10.1+** (Gemma 4 / `gemma4_unified`).
2. GGUF downloaded from Hugging Face:
   - [`QinEmPeRoR93/nassila-sanad-e4b`](https://huggingface.co/QinEmPeRoR93/nassila-sanad-e4b)
   - [`QinEmPeRoR93/nassila-sanad-12b`](https://huggingface.co/QinEmPeRoR93/nassila-sanad-12b)
3. Python env:

```powershell
cd training
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

4. LM Studio **Local Server** on `http://localhost:1234` with the model loaded.

| Model | VRAM guidance |
|-------|---------------|
| E4B Q6_K | ~8 GB |
| 12B Q6_K | ~12 GB+ (unload E4B first) |

---

## One-command wrapper (recommended)

Copy the **exact model id** from LM Studio, then:

```powershell
cd training
.\scripts\run_laptop_smoke.ps1 -Model "PASTE_LM_STUDIO_MODEL_ID" -Arm e4b
# Unload E4B, load 12B GGUF, start server again:
.\scripts\run_laptop_smoke.ps1 -Model "PASTE_LM_STUDIO_MODEL_ID" -Arm 12b
```

**Outputs:**

- `outputs/laptop_smoke_e4b.jsonl` / `outputs/laptop_smoke_e4b_report.json`
- `outputs/laptop_smoke_12b.jsonl` / `outputs/laptop_smoke_12b_report.json`

Record results in [`outputs/LAPTOP_SMOKE_SIGNOFF.md`](./outputs/LAPTOP_SMOKE_SIGNOFF.md).

---

## Canonical 4-row smoke set

| Id | Source file | What it tests |
|----|-------------|---------------|
| `h-001` | `data/eval_holdout_90.jsonl` | Clear `supported` + quote substrings |
| `eval-004` | `data/eval_samples.jsonl` | Unrelated excerpt → no false `supported` |
| `h-045` | `data/eval_holdout_90.jsonl` | Adults/children parity split (v1.14 fix) |
| `h-088` | `data/eval_holdout_90.jsonl` | Seniors/infants parity split |

Inference flags (match Vast eval): `--chat-template --retry 1 --repair`.

---

## Pass criteria

| Check | Target |
|-------|--------|
| Ping | Response contains `ok` |
| JSON parse | **4/4** rows (repair allowed) |
| Expect checks | **4/4** rows pass `expect` blocks |
| h-045 / h-088 | ≥2 claims; no forbidden `supported` |
| Laptop stability | No OOM; no repeated HTTP 500 |

**12B** only after **E4B** passes.

---

## Manual steps (if wrapper fails)

### Ping

```powershell
python scripts/lmstudio_smoke_test.py `
  --base-url http://localhost:1234 `
  --model "PASTE_MODEL_ID" `
  --task ping
```

### Single row

```powershell
python scripts/lmstudio_smoke_test.py `
  --base-url http://localhost:1234 `
  --model "PASTE_MODEL_ID" `
  --task l3_grounding `
  --sample data/eval_holdout_90.jsonl `
  --id h-045 `
  --chat-template --retry 1 --repair
```

### Batch + score

```powershell
python scripts/run_l3_eval_batch.py `
  --base-url http://localhost:1234 `
  --model "PASTE_MODEL_ID" `
  --data data/eval_samples.jsonl data/eval_holdout_90.jsonl `
  --id h-001 eval-004 h-045 h-088 `
  --chat-template --retry 1 --repair `
  --out outputs/laptop_smoke_manual.jsonl

python scripts/score_laptop_smoke.py `
  --predictions outputs/laptop_smoke_manual.jsonl `
  --report outputs/laptop_smoke_manual_report.json
```

---

## Sign-off checklist

Fill in [`outputs/LAPTOP_SMOKE_SIGNOFF.md`](./outputs/LAPTOP_SMOKE_SIGNOFF.md) after both arms complete.

If **both pass** → proceed to HF release verification ([`HF_PUBLISH.md`](./HF_PUBLISH.md)).  
If **either fails** → record failure mode; do not mark release verified.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Connection refused | Start LM Studio local server; confirm port 1234 |
| Unknown architecture `gemma4` | Update LM Studio llama.cpp runtime |
| Empty / HTTP 500 | Restart server; retry once (`--retry 1` is default in wrapper) |
| 12B OOM | Close other GPU apps; unload E4B first; reduce context if LM Studio allows |
| h-045 parse fail (not min_claims) | Blocker for 12B v1.14 — compare raw output in `.jsonl` |
| Quotes fail on h-001 | Check `sourceQuotes` are verbatim substrings of excerpt |

---

## Related

- [`scripts/run_laptop_smoke.ps1`](./scripts/run_laptop_smoke.ps1) — Windows wrapper
- [`scripts/lmstudio_smoke_test.py`](./scripts/lmstudio_smoke_test.py) — ping + single row
- [`scripts/run_l3_eval_batch.py`](./scripts/run_l3_eval_batch.py) — batch inference
- [`EVALUATION_GUIDE.md`](./EVALUATION_GUIDE.md) — full eval harness
