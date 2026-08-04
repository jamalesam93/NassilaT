# Shahid (Tier 3+) gate

**App target:** Nassila **1.8.0 · Shahid**  
**Depends on:** Tier 3 full-text holdout pilot → product gate (see [`TIER3_EVAL_SUITES.md`](./TIER3_EVAL_SUITES.md))

## In scope for 1.8.0 (bounded slice)

- Table/figure evidence path (today disabled in product).
- Model-assisted grey-literature field suggestions — **user confirms before apply**.
- Platform typing via deterministic host parsers first (`webpage-hosts.ts` in Nassila).

## Out of scope (long-term)

- Full multimodal Shahid without separate multimodal holdout.
- Institutional login webview (SEC-06).
- Cloud-default LLM.

## Gate before ship

1. `evaluate_tier3_body_gates` **PASS** on product-scale holdout (not pilot-only).
2. Retrieval vs grounding vs e2e suites documented with no conflated metrics.
3. S15 train only if §6 go/no-go shows a **model** gap after Nassila **1.4–1.7**.

## Eval artifacts (future)

| Task | Schema |
|------|--------|
| `table_figure_grounding` | `DATASET_SCHEMA.md` (stub) |
| `webpage_metadata` / `webpage_classify` | Phase 2+ grey-web |

Do not start Shahid training until Tier 3 body Sanad is stable or deterministic paths suffice.
