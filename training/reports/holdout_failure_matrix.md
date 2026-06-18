# Holdout failure matrix

Row ? version: `pass` or failure mode (`parse_json`, `wrong_verdict`, etc.).

**Trust note:** v1.5 is contaminated (7 boost rows reused eval passages/excerpts) ? its `pass` cells reflect memorization. v1.6 onward are decontaminated (`scripts/check_contamination.py` gate = 0) and trustworthy.

**v1.10 A/B columns:** seed 42, Q6_K, hardened 115-row harness (`ab_e4b_q6_k_v110` / `ab_12b_q6_k_v110` combined reports). Rows **h-046..h-090** (extension holdout) are scored only in those combined reports ? not in this legacy-45 slice table.

| row | v1.0 | v1.2 | v1.3 | v1.4a | v1.4b | v1.5 | v1.6 | v1.7 | v1.8 | v1.9 | v1.10 E4B | v1.10 12B-Q6 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| h-001 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-002 | pass | pass | parse_json | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-003 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-004 | pass | pass | parse_json | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-005 | pass | pass | parse_json | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-006 | pass | pass | parse_json | wrong_verdict | pass | pass | pass | pass | pass | pass | pass | pass |
| h-007 | pass | pass | parse_json | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-008 | pass | pass | parse_json | pass | wrong_verdict | pass | pass | pass | pass | wrong_verdict | wrong_verdict | pass |
| h-009 | pass | pass | pass | pass | pass | pass | pass | pass | wrong_verdict | pass | pass | pass |
| h-010 | wrong_verdict | wrong_verdict | parse_json | wrong_verdict | wrong_verdict | pass | pass | pass | pass | pass | pass | pass |
| h-011 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | wrong_verdict | pass |
| h-012 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-013 | wrong_verdict | wrong_verdict | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-014 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-015 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-016 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-017 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-018 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-019 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-020 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-021 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-022 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-023 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-024 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-025 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-026 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-027 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-028 | pass | pass | wrong_verdict | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-029 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-030 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-031 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | wrong_verdict | pass |
| h-032 | pass | pass | pass | pass | pass | wrong_verdict | wrong_verdict | wrong_verdict | pass | pass | pass | pass |
| h-033 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-034 | pass | pass | pass | pass | wrong_verdict | wrong_verdict | wrong_verdict | wrong_verdict | pass | wrong_verdict | pass | pass |
| h-035 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-036 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-037 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-038 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-039 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-040 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| h-041 | pass | pass | pass | pass | pass | pass | pass | pass | pass | forbidden_verdict | forbidden_verdict | pass |
| h-042 | pass | pass | pass | pass | pass | pass | wrong_verdict | wrong_verdict | pass | pass | pass | pass |
| h-043 | wrong_verdict | wrong_verdict | forbidden_verdict | forbidden_verdict | wrong_verdict | forbidden_verdict | forbidden_verdict | forbidden_verdict | forbidden_verdict | forbidden_verdict | forbidden_verdict | forbidden_verdict |
| h-044 | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | wrong_verdict | wrong_verdict |
| h-045 | wrong_verdict | wrong_verdict | wrong_verdict | wrong_verdict | wrong_verdict | wrong_verdict | wrong_verdict | wrong_verdict | wrong_verdict | wrong_verdict | wrong_verdict | wrong_verdict |

**Footnote (v1.11 harness):** **h-043** gold corrected at v1.11 (Option A: `min_claims: 2`, removed forbidden `supported`). v1.10 model predictions pass on regrade; this matrix?s v1.10 columns reflect the pre-fix gold. **h-045** gains `min_claims: 2` at v1.11; fix requires prompt + v1.11 train.
