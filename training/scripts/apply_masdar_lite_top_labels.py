#!/usr/bin/env python3
"""Apply human adjudication labels for masdar-lite top-priority review rows."""
from __future__ import annotations

import csv
from pathlib import Path

DIR = Path(__file__).resolve().parents[1] / "field-notes" / "masdar-lite-jul13-2026-07-13"
CALLS = DIR / "grounding-calls.csv"
QUEUE = DIR / "review-queue.csv"

# expected_overall_verdict must be one of: support | weak | unrelated | insufficient_evidence
LABELS: dict[str, tuple[str, str]] = {
    "field-masdar-lite-jul13-012": (
        "unrelated",
        "parse_error/no_claims; source is Yemeni MSc-interest survey, not SA/Yemen clinical-training comparison — discard or re-run L3",
    ),
    "field-masdar-lite-jul13-001": (
        "insufficient_evidence",
        "echo_false_positive: supported quotes copied from manuscript, not ESCP abstract; related topic but cited definition sentences absent from excerpt",
    ),
    "field-masdar-lite-jul13-006": (
        "unrelated",
        "Masdar mismatch: model answered SCFHS CPD source content; passage is Vision 2030 / comparative CPE objectives (not in excerpt)",
    ),
    "field-masdar-lite-jul13-008": (
        "unrelated",
        "echo quotes from methods/framework passage; source is accreditation-attitude survey tables, not lit-review methods",
    ),
    "field-masdar-lite-jul13-010": (
        "unrelated",
        "echo quotes; accreditation survey source does not support SA vs Yemen regulatory/licensure comparison claims",
    ),
    "field-masdar-lite-jul13-011": (
        "unrelated",
        "echo quotes; Yemeni MSc-interest abstract does not support methods/data-extraction passage",
    ),
    "field-masdar-lite-jul13-015": (
        "unrelated",
        "echo quotes; CME/Asir pharmacist source does not support methods/data-extraction passage",
    ),
    "field-masdar-lite-jul13-024": (
        "weak",
        "partial: 30% ward-round participation is in source; 120-pharmacist framing, 83.1% physician barriers, and CPS-nascent claim0 were echo/unsupported",
    ),
    "field-masdar-lite-jul13-027": (
        "insufficient_evidence",
        "source discusses MTM attitudes generally; passage 11%/461 Sana'a utilization stats not in excerpt — model treated attitude text as support",
    ),
    "field-masdar-lite-jul13-033": (
        "insufficient_evidence",
        "source only ~83-char newsletter title; all supported claims were manuscript echoes",
    ),
    "field-masdar-lite-jul13-034": (
        "support",
        "ETEC/ACPE/national accreditation claims present in source; overall support OK but quotes were passage echoes — fix at claim level",
    ),
    "field-masdar-lite-jul13-035": (
        "weak",
        "ACPE/CCAPP/SPLE content in source; Vision 2030 claim not evidenced; supported rows used echo quotes",
    ),
    "field-masdar-lite-jul13-041": (
        "weak",
        "Al-Qassim / pharmaceutical-care knowledge gap (~45%/93.9%) in source; Toolkit absent; model also marked unrelated Jordan/quality digressions as supported",
    ),
    "field-masdar-lite-jul13-043": (
        "unrelated",
        "echo quotes; DHT/digital-health Yemen source does not support faculty-qualification disparity passage",
    ),
    # echo_other bucket (2026-07-21)
    "field-masdar-lite-jul13-007": (
        "weak",
        "HCDP/Vision 2030 partially in SCFHS CPD source; 2 supported claims used echo quotes; comparative investment claims not_in_source",
    ),
    "field-masdar-lite-jul13-013": (
        "insufficient_evidence",
        "Yemeni MSc-interest abstract; SA/Yemen clinical-training comparison claims not_in_source; echo on 'two countries'",
    ),
    "field-masdar-lite-jul13-025": (
        "weak",
        "ward-round/AST gaps partially in Hatem source but supported rows echo manuscript/figure caption text — not verbatim source quotes",
    ),
    "field-masdar-lite-jul13-036": (
        "weak",
        "ACPE/CCAPP accreditation linkage in source; echo quotes; unrelated not_in_source tail",
    ),
    "field-masdar-lite-jul13-037": (
        "unrelated",
        "regulatory-enforcement SA vs Yemen comparison not in Frontiers accreditation article; echo_false_positive pattern",
    ),
    "field-masdar-lite-jul13-046": (
        "insufficient_evidence",
        "truncated abstract-only excerpt; Vision 2030 pharmacy support claim not evidenced in short window",
    ),
    # support_review
    "field-masdar-lite-jul13-049": (
        "support",
        "antimicrobial stewardship / OTC antibiotic sales claim supported in medRxiv excerpt; passage ADR sentence out of scope for this cite site",
    ),
    # truncated bucket (2026-07-21) — short/wrong Masdar windows; defer re-ground after 1.6 chunking
    "field-masdar-lite-jul13-003": (
        "unrelated",
        "passage states Yemen/SA review objectives; excerpt is ESCP clinical-pharmacy definition abstract — wrong source",
    ),
    "field-masdar-lite-jul13-004": (
        "insufficient_evidence",
        "generic clinical-pharmacy symposium abstract; passage claims not evidenced in truncated excerpt",
    ),
    "field-masdar-lite-jul13-005": (
        "unrelated",
        "passage lists review aims; excerpt is unrelated symposium abstract",
    ),
    "field-masdar-lite-jul13-016": (
        "unrelated",
        "passage SCFHS/HCDP/Vision 2030; excerpt is Saudi pharmacist CME study — source mismatch",
    ),
    "field-masdar-lite-jul13-017": (
        "unrelated",
        "passage SA vs Yemen governance; excerpt CME pharmacist abstract — wrong source",
    ),
    "field-masdar-lite-jul13-018": (
        "unrelated",
        "methods/data-extraction passage; excerpt YSMC DataFlow marketing snippet",
    ),
    "field-masdar-lite-jul13-019": (
        "insufficient_evidence",
        "national clinical pharmacy guideline claim; excerpt only YSMC portal tagline",
    ),
    "field-masdar-lite-jul13-020": (
        "insufficient_evidence",
        "methods passage; excerpt Arabic program boilerplate only (~15 chars useful)",
    ),
    "field-masdar-lite-jul13-021": (
        "insufficient_evidence",
        "Yemen Pharm.D. curriculum claim; excerpt unusable program stub",
    ),
    "field-masdar-lite-jul13-022": (
        "insufficient_evidence",
        "methods passage; excerpt faculty dean greeting page not curricular content",
    ),
    "field-masdar-lite-jul13-023": (
        "insufficient_evidence",
        "methods passage; excerpt corporate tagline only",
    ),
    "field-masdar-lite-jul13-026": (
        "unrelated",
        "MTM/ADR practice-gap passage; excerpt author-affiliation block — Masdar window failure",
    ),
    "field-masdar-lite-jul13-028": (
        "unrelated",
        "education–practice alignment passage; excerpt affiliations not results text",
    ),
    "field-masdar-lite-jul13-029": (
        "weak",
        "MTM attitudes partially in abstract; passage cites southern Yemen dispensers with thin excerpt",
    ),
    "field-masdar-lite-jul13-030": (
        "insufficient_evidence",
        "King Saud 1959 pharmacy history; excerpt ~83-char newsletter title only",
    ),
    "field-masdar-lite-jul13-031": (
        "insufficient_evidence",
        "pharmacy college expansion claim; excerpt title stub only",
    ),
    "field-masdar-lite-jul13-032": (
        "unrelated",
        "KFSH clinical pharmacy history; excerpt title stub — cannot ground",
    ),
    "field-masdar-lite-jul13-038": (
        "weak",
        "pharmacist shortage/residency initiatives may be in full abstract; truncated window insufficient",
    ),
    "field-masdar-lite-jul13-039": (
        "unrelated",
        "PGY-1 US scholarship passage not in excerpt window",
    ),
    "field-masdar-lite-jul13-040": (
        "unrelated",
        "specialty evolution passage not evidenced in truncated abstract window",
    ),
    "field-masdar-lite-jul13-042": (
        "weak",
        "45% disease-state knowledge gap may be in Cureus source; passage window truncated",
    ),
    "field-masdar-lite-jul13-044": (
        "unrelated",
        "faculty-qualification disparity passage; excerpt too short/wrong section",
    ),
    "field-masdar-lite-jul13-045": (
        "insufficient_evidence",
        "graduate workforce disparity claims; truncated abstract cannot support",
    ),
    "field-masdar-lite-jul13-047": (
        "weak",
        "Yemen conflict context partially inferable; passage comparative claims mostly unsupported in excerpt",
    ),
    "field-masdar-lite-jul13-048": (
        "unrelated",
        "graduate outcome disparity passage; excerpt does not contain comparative evidence",
    ),
    # other bucket
    "field-masdar-lite-jul13-002": (
        "unrelated",
        "global clinical pharmacy education intro; generic abstract unrelated to Yemen/SA comparison",
    ),
    "field-masdar-lite-jul13-009": (
        "unrelated",
        "data-sources methods list; excerpt FIP accreditation survey not methods bibliography",
    ),
    "field-masdar-lite-jul13-014": (
        "insufficient_evidence",
        "professional-growth comparison; truncated abstract-only excerpt",
    ),
}


def apply(path: Path) -> int:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    if not rows:
        raise SystemExit(f"empty {path}")
    fieldnames = list(rows[0].keys())
    n = 0
    for r in rows:
        rid = r.get("id") or ""
        if rid not in LABELS:
            continue
        verdict, notes = LABELS[rid]
        r["expected_overall_verdict"] = verdict
        r["reviewer_notes"] = notes
        n += 1
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return n


def main() -> None:
    n1 = apply(CALLS)
    n2 = apply(QUEUE) if QUEUE.exists() else 0
    labeled = sum(
        1
        for r in csv.DictReader(CALLS.open(encoding="utf-8"))
        if (r.get("expected_overall_verdict") or "").strip()
    )
    print(f"updated grounding-calls.csv rows={n1}")
    print(f"updated review-queue.csv rows={n2}")
    print(f"human_labels now={labeled}/{sum(1 for _ in csv.DictReader(CALLS.open(encoding='utf-8')))}")


if __name__ == "__main__":
    main()
