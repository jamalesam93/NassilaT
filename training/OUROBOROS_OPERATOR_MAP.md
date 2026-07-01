# Ouroboros operator map — training + product

**Status (2026-06):** v1.13 **NO-GO**; v1.14 **GO**. **Ship checkpoints:** E4B **S12** (legacy v1.12, default-tier), 12B **S14** (legacy v1.14, Tier 2 + h-045/h-088 split fix). **Laptop smoke PASS** (RTX 4060 8 GB, 2026-06-21). **HF verify PASS.** Nassila **Passage grounding + Set up Sanad guide** shipped (see § Phase checklist). 12B v1.12 remains the higher-combined fallback/reference.

**Version streams:** App semver (Nassila **1.1.x**) and Sanad checkpoint **SNN** are independent — see § Sanad checkpoint naming and § App release train.

**Agent brief:** [Nassila `docs/OUROBOROS_CONTEXT.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/OUROBOROS_CONTEXT.md)  
**Ship policy:** [`docs/DUAL_TIER_POLICY.md`](../docs/DUAL_TIER_POLICY.md)  
**Decisions log:** [`EVAL_GONOGO.md`](./EVAL_GONOGO.md)  
**Laptop acceptance:** [`LAPTOP_SMOKE_TEST.md`](./LAPTOP_SMOKE_TEST.md)

---

## What v1.13 proved

Multi-seed mean (`reports/ab_12b_q6_k_v113/`):

| Metric | v1.12 ship | v1.13 | Tier 2 bar |
|--------|------------|-------|------------|
| Combined expect | 94.20% | **88.99%** | ≥90% |
| JSON parse | 100% | **95.65%** | ≥98% |
| Quote (holdout) | 100% | **94.74%** | ≥98% |
| Tier 2 pass | 3/3 | **0/3** | all six gates |
| multi_claim | 69.23% | 64.10% | stretch ≥80% |

**Root cause (v1.14 runbook):** 12 v113 parity rows (all `weak`) merged under the **850-row cap** → `prepare_v15_train.py` trimmed **11 `supported`** rows → verdict-boundary regressions (h-038, h-051, h-082, eval-012) plus inference flakes (h-028, h-037). **h-045 / h-088** worsened from v1.12 `min_claims` failures to **`parse_json`** on all seeds.

**Rule:** Do **not** publish v1.13. Use **v1.14** (cap 874 + v114 counterbalance + prompt sync).

---

## Current ship

| HF id | Checkpoint | Gate | Role |
|-------|------------|------|------|
| `nassila-sanad-e4b` | **S12** *(legacy v1.12)* | E4B default-tier | 8 GB default |
| `nassila-sanad-12b` | **S14** *(legacy v1.14)* | Tier 2 | Quality tier; subgroup split fix |

12B S14 trades lower combined score (**90.43%**) for fixed h-045 / h-088 and higher `multi_claim` (**84.62%**). v1.12 12B remains the reference if future work prioritizes maximum combined score again.

GGUF filenames on Hub are unchanged (`nassila-sanad-*-q6_k.gguf`); **SNN** is the published checkpoint label in READMEs and model cards.

---

## Sanad checkpoint naming (`SNN`, S = Sanad)

**S** = **Sanad** (سند) — the `l3_grounding` worker / `nassila-sanad-*` model family.

| Rule | Detail |
|------|--------|
| **Format** | **SNN** — Sanad generation integer (no dots), e.g. **S15** for next train |
| **Legacy** | `v1.12` = **S12**, `v1.14` = **S14** — valid in archive walkthroughs only |
| **Speech** | App → *Nassila **1.1.2*** · Model → *Sanad **S12*** or *S12 E4B* |
| **Never bare** | Do not write `1.12` or `12` alone in mixed app/model docs |

### Legacy alias table

| Legacy | Canonical | HF repo | Role |
|--------|-----------|---------|------|
| v1.12 | **S12** | `nassila-sanad-e4b` | E4B default-tier ship (89.27%) |
| v1.13 | — | — | **NO-GO** — do not publish; no S13 on Hub |
| v1.14 | **S14** | `nassila-sanad-12b` | 12B quality Tier 2 (90.43%) |
| v1.15+ | **S15+** | TBD | Parked until Tier 3 corpus |

**SNN is not one linear counter per GGUF file.** S12 and S14 label **separate ship artifacts** (E4B default vs 12B quality) that share legacy `v1.NN` train numbering.

### Future worker prefixes (when trained facets ship)

| Worker | Prefix | Example | Note |
|--------|--------|---------|------|
| Sanad | **S** | S15 | Only family with production GGUFs today |
| Maktab | **M** | M01 | Trained `doc_extract` facet |
| Masdar | **Md** | Md01 | Trained `source_pdf_extract` — **not** app Masdar-lite (pdf.js) |

### Docs vs binaries

| Action | Do? |
|--------|-----|
| Update HF READMEs + MODEL_CARDs to **S12** / **S14** | **Yes** (README-only upload) |
| Re-upload GGUF weight files for relabel | **No** — same bytes on Hub |
| Rename GGUF filenames on Hub | **No** |

---

## v1.14 result

Full spec: [`docs/V113_12B_REGRESSION_FIX_REPORT.md`](../docs/V113_12B_REGRESSION_FIX_REPORT.md)  
Operator walkthrough: [`PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md`](./PHASE2_14_12B_MULTI_CLAIM_WALKTHROUGH.md)

Reports: `reports/ab_12b_q6_k_v114/`.

| Metric | v1.12 | v1.14 |
|--------|-------|-------|
| Combined expect | **94.20%** | **90.43%** |
| JSON parse | 100% | **100%** |
| Quote (holdout) | 100% | **100%** |
| False supported | 2.86% | **2.86%** |
| multi_claim | 69.23% | **84.62%** |
| Tier 2 pass | 3/3 | **3/3** |

**Decision:** select v1.14 because it fixes h-045 / h-088 on all seeds while keeping Tier 2. The combined-score regression is accepted as a product tradeoff for subgroup-split correctness.

**Stop publishing rule:** Any attempt with Tier 2 fail → keep **v1.12** on HF.

---

## Next: laptop smoke test — **DONE**

Local acceptance **PASS** (2026-06-21, RTX 4060 8 GB): [`outputs/LAPTOP_SMOKE_SIGNOFF.md`](./outputs/LAPTOP_SMOKE_SIGNOFF.md).

HF verify **PASS**: [`HF_RELEASE_VERIFY.md`](./HF_RELEASE_VERIFY.md) · [`outputs/hf_release_verify_report.json`](./outputs/hf_release_verify_report.json).

**Current focus:** App **1.2.0 Masdar-lite** (Nassila [`FEATURES-AND-TWEAKS.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/FEATURES-AND-TWEAKS.md) #3–4); then **1.2.1 Masdar UX**. Models remain **S12 / S14**; **S15+** parked until Tier 3 corpus. Nassila app **1.1.3 Polish** shipped.

---

## App release train (Nassila semver)

**Spec:** [Nassila `docs/FEATURES-AND-TWEAKS.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/FEATURES-AND-TWEAKS.md) (detailed acceptance). This file is the **operator schedule**. Codename in release title; semver in `package.json` and git tags.

### Shipped

| Version | Codename | Summary |
|---------|----------|---------|
| **1.1.0** | **Sanad** | Ouroboros loop, L3 grounding, Sanad setup, Unpaywall, SEC-01–07 |
| **1.1.1** | **Bibliography-first** | Loop hint, DOCX import parity, journal search IPC |
| **1.1.2** | **Raqim Bridge** | Send refs → Raqim, audit from library, PDF import + verify IPC |

Shipped with models **S12** (E4B) + **S14** (12B) — independent of app patch numbers.

### Planned (FEATURES backlog)

| Version | Codename | FEATURES # | Summary |
|---------|----------|------------|---------|
| **1.1.3** | **Polish** | #1, #2 | **Shipped** — notifications + Sanad modal → website docs |
| **1.1.3 stretch** | *(optional)* | — | SourceFetchSettings troubleshooting link; AboutModal docs link |
| **1.2.0** | **Masdar-lite** | #3, #4, #6? | OA PDF grounding + incremental audit progress; quote chip if ready |
| **1.2.1** | **Masdar UX** | #5, #6, #8 | Attach PDF, quote chip (if not in 1.2.0), shortcuts |
| **1.2.2** | **Throughput** | #7 | Bounded concurrency; split registry vs LLM pools |
| **1.3.0** | **Sharh-lite** | #9, #10, #11 | Deterministic summaries, Help → website, cancel granularity |

Cross-repo optional: **#12** Sanad metrics on `nassila-web` `local-models` page (anytime after 1.1.3).

---

## S15+ future refinement

Optional later work: recover v1.12-level combined score while preserving S14 (v1.14) h-045 / h-088 behavior. Start from S14 as the selected checkpoint; hyperparameter escalation remains last resort. *(Legacy train label: v1.15+.)*

---

## Parallel tracks (after laptop smoke + HF verify)

| Track | Repo | When |
|-------|------|------|
| **UI reform** | Nassila `docs/DESIGN.md`, `docs/PRODUCT.md` | After E4B v1.12 + 12B v1.14 laptop smoke pass |
| **HF / model cards** | `MODEL_CARD_sanad_*.md`, lean HF READMEs | After smoke pass; see [`HF_PUBLISH.md`](./HF_PUBLISH.md) |
| **Maktab / Masdar corpus** | [`PHASE3_TIER3_GROUNDWORK.md`](./PHASE3_TIER3_GROUNDWORK.md), [`CORPUS_PIPELINE.md`](./CORPUS_PIPELINE.md) | After Tier 2 stable; unblocks Tier 3 |

---

## Phase checklist — done vs left

**Last updated:** 2026-06-29 (release train + SNN naming; FEATURES backlog in § G)

Use this as the operator map after v1.14 ship. Detail lives in linked docs; check boxes here only.

### A. Training & eval (NassilaT)

- [x] v1.13 declared **NO-GO** (Tier 2 fail, parse/quote regressions)
- [x] v1.14 12B trained + selected (h-045 / h-088 fix, multi_claim 84.62%)
- [x] v1.12 E4B remains **default-tier ship** (89.27% combined)
- [x] Tier 2 §10 pass on selected 12B (v1.14)
- [x] Dual-tier policy recorded ([`DUAL_TIER_POLICY.md`](../docs/DUAL_TIER_POLICY.md))
- [x] GO/NO-GO log updated ([`EVAL_GONOGO.md`](./EVAL_GONOGO.md))
- [ ] **S15+** optional refinement (recover v1.12 combined while keeping S14 subgroup fix)

### B. Release & Hugging Face (NassilaT)

- [x] Laptop smoke **PASS** E4B + 12B ([`outputs/LAPTOP_SMOKE_SIGNOFF.md`](./outputs/LAPTOP_SMOKE_SIGNOFF.md))
- [x] HF verify **PASS** — local GGUF byte-identical to Hub ([`outputs/hf_release_verify_report.json`](./outputs/hf_release_verify_report.json))
- [x] Model cards + HF READMEs match ship metrics ([`HF_RELEASE_VERIFY.md`](./HF_RELEASE_VERIFY.md))
- [x] Public repos: `QinEmPeRoR93/nassila-sanad-e4b` (S12), `nassila-sanad-12b` (S14)
- [x] v1.13 GGUF **not** published
- [x] HF README **Ollama** section — **live on Hub** (uploaded 2026-06-22; `hf.co/...` pull + Modelfile fallback)
- [x] Ollama `hf.co/QinEmPeRoR93/nassila-sanad-e4b:Q6_K` smoke on a second machine (confirm quant tag) — procedure recorded in [`LAPTOP_SMOKE_TEST.md`](./LAPTOP_SMOKE_TEST.md)
- [x] Machine-local `training/fixtures/Modelfile.*` **gitignored** (portable templates stay in HF READMEs)

### C. Nassila app — Passage grounding (Sanad UX)

*Repo: [Nassila](https://github.com/jamalesam93/Nassila)*

- [x] Hydra-style worker tabs / Debug Model Sandbox **removed**
- [x] **Settings → Passage grounding** — local runners (LM Studio, Ollama, vLLM, Custom) + universal **Cloud API** (key-inferred endpoint)
- [x] Nassila tier chips (E4B / 12B) on **all local runners**; defaults to `nassila-sanad-e4b` / `nassila-sanad-12b`
- [x] No generic Qwen / Together / DashScope cloud presets; no maintainer wall-of-text in Settings
- [x] `ensureLlmKeyReady` before audit LLM calls; localhost placeholder key auto-save
- [x] **Set up Sanad** modal — HF links, runner links, Ollama copy command ([`src/shared/sanad-setup-links.ts`](https://github.com/jamalesam93/Nassila/blob/main/src/shared/sanad-setup-links.ts))
- [x] Auto-prompt once (Passage grounding tab or enable Sanad); dismiss + test-connection suppress
- [x] Manuscript **Sanad bar** — toggle, tier, Setup / Configure links
- [x] **Settings → General → Manuscript source fetch** — one-time **Unpaywall email** (saved locally in `manuscript-audit-preferences.json`; used only for `api.unpaywall.org` DOI OA lookups from the desktop app, not Nassila servers)
- [x] Loop hint + **Open Settings** when Unpaywall email unset (unlocks OA full-text path alongside Europe PMC / registry abstract)
- [x] External **Marker** PDF CLI import **removed** — manuscript PDF ingest uses bundled pdf.js only ([Nassila `55a88ec`](https://github.com/jamalesam93/Nassila/commit/55a88ec))
- [x] EN + AR i18n for grounding UI + source-fetch strings
- [ ] End-user **Help → full reference** — target **1.3.0** (#11); website docs canonical (see § G)
- [x] Refresh [`USER_GUIDE.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/USER_GUIDE.md) — Unpaywall one-time setup, loop evidence panels, coverage labels

### D. Nassila app — Ouroboros loop & workers

- [x] Primary surfaces: **Manuscript loop** + **Bibliography** (no seven peer worker destinations)
- [x] Single header upload; export audit from header when report exists
- [x] Tasnif / Sharh integrated inline (bibliography drawer + loop detail) — not separate tabs
- [x] Manuscript audit engine + L3 grounding wired when user runs loop audit
- [x] Raqim + Tasnif live in bibliography mode
- [x] **Loop evidence UX** — passage window, source excerpt, verbatim quotes, and OA link in `LoopAuditDetail`; `sourceExcerpt` stored per cite site in audit engine
- [x] **DOCX references fallback** — numbered bibliography block detected when no `References` / `Bibliography` heading ([`segments.ts`](https://github.com/jamalesam93/Nassila/blob/main/src/engine/manuscript/segments.ts); `tests/unit/manuscript-segments.test.ts`)
- [x] **L1 multi-registry fallback** — DOI: Crossref/DataCite → OpenAlex → PubMed-by-DOI; PMID: PubMed → OpenAlex; DOI+PMID cross-fallback; identifier normalization (`verify.ts`, `tests/unit/manuscript-verify-registry.test.ts`)
- [x] **OA fetch hardening** — `oa:fetchOaUrl` allows public `http://` Unpaywall links, soft-fails invalid URLs (no main-process throw spam), tries PDF → URL → landing-page candidates (`ipc-oa.ts`, `use-manuscript-audit.ts`)
- [x] **Real manuscript audit smoke** — full run on operator DOCX (~76 cites, Sanad E4B on); sign-off [`MANUSCRIPT_AUDIT_SMOKE_SIGNOFF.md`](./MANUSCRIPT_AUDIT_SMOKE_SIGNOFF.md). **Operator rule:** chaotic or unverified embedded references → **Bibliography first** (import, verify, dedupe, attach DOIs), then re-audit.
- [x] **Bibliography-first workflow** — documented in Nassila `PRODUCT.md` / `USER_GUIDE.md`; loop UI hint + switch to Bibliography (v1.1.1).
- [x] **Send references to Bibliography** — one-click export of manuscript `referencesText` → Raqim (`bibliography-bridge.ts`, `use-bibliography-bridge.ts`; `manuscript-ref:N` ids preserve numeric cite keys).
- [x] **Audit from Bibliography store** — optional loop toggle uses curated Raqim rows instead of re-parsing embedded refs; preview allows body + library when enabled (`manuscript-preview.ts`, `use-manuscript-audit.ts`).
- [ ] **Audit progress UX** — partial findings + `N / M` counter during long runs → **1.2.0** (#4)
- [x] **PDF IMRAD References heading** — `9. References` detected on PDF export (`segments.ts` numbered header).
- [x] **Loop audit detail UX** — deduped L3 rollup reasons; compact layer summary + cite-site list (`LoopAuditDetail.tsx`, `grounding-llm.ts`).
- [x] **Cited-sources table header** — opaque sticky header (no bleed-through on scroll).
- [x] **Bibliography PDF import** — Raqim import uses manuscript-grade PDF extractor (`extractManuscriptFromPdf`); numbered entries split at DOCX parity ([`document.ts`](https://github.com/jamalesam93/Nassila/blob/main/src/engine/parser/document.ts); v1.1.2).
- [x] **Bibliography verify references** — unified L1+L2 runs in main process via `registry:verifyUnified` IPC so **Verify references** works in packaged builds (production CSP blocks renderer registry fetch; v1.1.2).
- [x] **Nassila v1.1.2 release** — Windows installer on GitHub Releases (`Nassila Setup 1.1.2.exe`); supersedes v1.1.0/v1.1.1 for new installs.
- [x] Debug instrumentation removed (`agent-debug-log`, ingest fetch logs) — v1.1.0 ship prep
- [ ] **Maktab** — manuscript ingest LLM facet (stub → loop-fed structure)
- [ ] **Masdar** — cited source PDF / OA fetch chunks for Sanad (stub → loop-fed excerpts); **institutional access** (library proxy / login session) is **not** Unpaywall email — Tier 3; see sign-off § institutional access
- [ ] Sanad **without** manual copy-paste between modules (requires Maktab + Masdar)
- [ ] **Shahid** — table/figure evidence (Tier 3+, disabled)
- [ ] **Sharh** — richer LLM explanations (deterministic copy only today)
- [ ] Loop UI gaps shown as honest pipeline stages, not fake worker apps

### E. Documentation sync (cross-repo)

- [x] Nassila `OUROBOROS.md` / `OUROBOROS_CONTEXT.md` / `PRODUCT.md` — S12 E4B + S14 12B tiers
- [x] Nassila `AGENTS.md` — Ouroboros rules, Sanad checkpoints
- [x] This file (`OUROBOROS_OPERATOR_MAP.md`) as operator map
- [x] NassilaT HF READMEs mention Ollama path (see B)
- [x] Nassila [`docs/SECURITY-FIX-PLAN.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/SECURITY-FIX-PLAN.md) — SEC-01–07 implemented (v1.1.1)
- [x] Nassila `README.md` + `CHANGELOG.md` — v1.1.2 ship (bibliography bridge, PDF import, verify IPC)
- [ ] In-app Help mirrors user-facing truth (see C) — **1.3.0**

### G. App polish & Masdar-lite (FEATURES-AND-TWEAKS)

*Repo: [Nassila](https://github.com/jamalesam93/Nassila) · Spec: [`docs/FEATURES-AND-TWEAKS.md`](https://github.com/jamalesam93/Nassila/blob/main/docs/FEATURES-AND-TWEAKS.md)*

- [x] **1.1.3 Polish** — notifications (#1) + Sanad modal → website (#2)
- [ ] **1.1.3 stretch (optional)** — SourceFetchSettings troubleshooting link; AboutModal docs link
- [ ] **1.2.0 Masdar-lite** — OA PDF grounding (#3) + incremental audit progress (#4); quote chip (#6) if ready
- [ ] **1.2.1 Masdar UX** — attach PDF (#5), quote chip (#6) if not in 1.2.0, shortcuts (#8)
- [ ] **1.2.2 Throughput** — bounded concurrency (#7); split registry vs LLM pools
- [ ] **1.3.0 Sharh-lite** — deterministic summaries (#9), Help deep links (#11), cancel granularity (#10)

### F. Tier 3+ (future — after Tier 2 product stable)

- [ ] **Institutional full-text access** — library proxy prefix or sandboxed publisher/login session for paywalled DOIs (separate from Unpaywall email; boosts Sanad when OA APIs have no copy). Security review required (SEC-06).
- [ ] Maktab / Masdar training corpus ([`PHASE3_TIER3_GROUNDWORK.md`](./PHASE3_TIER3_GROUNDWORK.md))
- [ ] Full-text excerpt eval (not abstract-only)
- [ ] Merged Ouroboros model (`nassila-agent-e12b-v1`) — research track only

---

**Suggested next actions (ordered):**

1. **App (P0):** **1.2.0 Masdar-lite** — OA PDF grounding + incremental audit (#3–4).
2. **App (P1):** **1.2.0 Masdar-lite** — OA PDF grounding + incremental audit (#3–4).
3. **App (P1):** **1.2.1 Masdar UX** — attach PDF, quote chip, shortcuts (#5–6, #8).
4. **Product (Tier 3):** **Institutional access** design — proxy prefix or login webview for paywalled full text (not Unpaywall email).
5. **Training (P2):** Park **S15+** until Tier 3 corpus.

---

## Doc map (minimal reading)

| Read | Purpose |
|------|---------|
| This file | Where you are; **done vs left checklist** |
| [`LAPTOP_SMOKE_TEST.md`](./LAPTOP_SMOKE_TEST.md) | Local GGUF acceptance |
| `docs/V113_12B_REGRESSION_FIX_REPORT.md` | v1.14 RCA + implementation checklist |
| `PHASE2_14_…` | Vast commands |
| `DUAL_TIER_POLICY.md` | E4B vs 12B gates |
| `EVAL_GONOGO.md` | GO/NO-GO history |
| `MODEL_CARD_sanad_12b.md` | HF-facing 12B truth |
| Nassila `OUROBOROS_CONTEXT.md` | Workers + tiers |

Historical walkthroughs: [`archive/`](./archive/).
