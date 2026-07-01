# Manuscript audit smoke — sign-off

**Date:** 2026-06-28  
**Operator:** product smoke on real thesis/manuscript DOCX  
**App:** Nassila v1.1.1 (post–v1.1.0 L1/OA/bibliography fixes)  
**Sanad:** E4B (`nassila-sanad-e4b` v1.12), passage grounding on  
**Unpaywall email:** set (Settings → General → Manuscript source fetch)

## Result: **PASS** (with workflow guidance)

| Check | Outcome |
|-------|---------|
| Manuscript upload + segmentation | Pass — references block detected (numbered / bracket styles) |
| In-text citation count | Pass — non-zero after segment fixes |
| L1 registry resolve | Pass — improved vs pre–v1.1.0; fewer false “not found” on DOI/PMID rows |
| OA / Unpaywall fetch | Pass — no main-process throw spam on marginal URLs |
| Cited sources panel | Pass at end of run — **empty during run** (known P1: stream partial findings) |
| Sanad grounding | Pass when abstract/OA text available; many rows still abstract-only or unavailable (expected Tier 2) |

## Operator conclusion (product)

**When embedded references are chaotic or unverified**, audit quality suffers (bad cite→ref mapping, weak L1, poor Sanad input). **Recommended workflow:**

1. Switch to **Bibliography** — import or paste the reference list (DOCX, `.bib`, plain text).
2. **Verify**, autocorrect, dedupe, attach missing DOIs in Raqim.
3. Return to **Manuscript** and run audit on a manuscript whose reference *section* matches the curated library (or re-paste after export).

This is **Bibliography-first**, not a model failure. Automated “export refs → Raqim” and “audit from store” are **P1** backlog ([`OUROBOROS_OPERATOR_MAP.md`](./OUROBOROS_OPERATOR_MAP.md) § D).

## Institutional access (not Unpaywall email)

**Unpaywall email** is an API contact string for **legally open** copies only. It does **not** unlock paywalled publisher PDFs via university subscription.

To boost Sanad on subscription-only papers:

- **Today:** download PDFs you can access via library browser; attach when **Masdar** ships.
- **Tier 3:** library proxy prefix or sandboxed institutional login + fetch in main process (security review).

## Next product items

- P1: Audit progress UX (partial findings + `N / M` counter)
- P1: Bibliography bridge (send refs to Raqim / audit from store)
- P1: Maktab / Masdar stubs
