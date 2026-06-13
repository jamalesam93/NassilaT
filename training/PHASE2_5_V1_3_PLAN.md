# Phase 2.5 — v1.3 plan (dataset + train)

**Prerequisite:** v1.2 NO-GO documented ([MODEL_CARD_v1_2.md](./MODEL_CARD_v1_2.md), [reports/v1_2_eval_combined_report.json](./reports/v1_2_eval_combined_report.json)).

**Goal:** Pass go/no-go on E4B: combined expect ≥90%, quote validity ≥98%, false supported ≤5%, supported holdout ≥8/10 — without regressing v1.2 holdout gains.

---

## v1.2 diagnosis

| Works (v1.2) | Still fails |
|--------------|-------------|
| Supported holdout **9/10** (fixed v1.1) | Combined **86%** (core eval **40%**) |
| Weak **100%**, false supported **0%** | Quote validity **90.9%** (target 98%) |
| Holdout expect **91.1%** | h-010, h-013, h-043, h-045 |

**Core eval failures:** eval-001 (supported), eval-003 (contradicted/overclaim), eval-005 (`min_claims` 2).

---

## v1.3 dataset changes

| Bucket | Id suffix | Target |
|--------|-----------|--------|
| Semantic Sanad (h-010) | `-sanadsem-` | Non-numeric paraphrase supported |
| Polarity contradicted (h-013) | `-pol-` | Negation vs significant association |
| Overclaim contradicted (eval-003) | `-over-` | “All cured” vs partial response |
| Multi-claim supported (eval-005) | `-multi-` | ≥2 atomic supported claims |
| Multi-claim partial (h-043/h-045) | `-multip-` | Supported + `not_in_source` in one passage |

**Rebalance:** supported **40%**, weak ≤12%, **≥100** multi-claim rows (2+ claims).

**Defaults:** 850 rows, seed **45**.

**Keep from v1.2:** `-sanad-`, chunked excerpts, anti-false-weak.

---

## v1.3 training

| Constant | v1.2 | v1.3 |
|----------|------|------|
| Epochs | 3 | **2** |
| LR | 1.5e-4 | **1e-4** |
| Output | `nassila-grounding-e4b-v1.2` | `nassila-grounding-e4b-v1.3` |

Eval: **`--chat-template`** + `run_eval_reports.py`.

---

## Go/no-go

| Metric | Target |
|--------|--------|
| Combined expect pass | ≥90% |
| Core eval (5 rows) | **5/5** stretch |
| Quote validity (holdout) | ≥98% |
| False supported | ≤5% |
| Supported h-001–h-010 | ≥8/10 |

---

## Walkthrough

[PHASE2_6_V1_3_WALKTHROUGH.md](./PHASE2_6_V1_3_WALKTHROUGH.md)  
**llama.cpp on Vast:** [LLAMA_CPP_VAST.md](./LLAMA_CPP_VAST.md) — pinned **`b9608`**, never floating `main`.
