#!/usr/bin/env python3
"""
Generate l3_grounding training rows from enriched paper corpus (Phase 2).

Abstract-only: source_excerpt = paper abstract (or a methods slice for
insufficient_evidence), meta.label = "abstract".

Verdicts are driven by semantic rules (quote overlap, numeric flip, hedging),
not fixed passage-prefix templates.

Usage:
  python scripts/generate_l3_from_corpus.py
  python scripts/generate_l3_from_corpus.py --target-rows 400 --export-review data/l3_review_queue.csv
"""

from __future__ import annotations

import argparse
import csv
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent
DATA_DIR = TRAINING_DIR / "data"
sys.path.insert(0, str(SCRIPT_DIR))

from corpus_utils import first_author_surname, read_jsonl, write_jsonl  # noqa: E402
from validate_dataset import validate_l3_record  # noqa: E402

MIN_ABSTRACT_CHARS = 120
HOLDOUT_PAPERS = 50
# Claim text in JSONL and review columns is compared at this prefix length.
VISIBLE_CLAIM_CHARS = 200
YEAR_BINS = [(2000, 2009), (2010, 2019), (2020, 2026)]

VERDICT_TARGETS = {
    "supported": 0.30,
    "weak": 0.18,
    "not_in_source": 0.22,
    "contradicted": 0.18,
    "insufficient_evidence": 0.12,
}

HEDGE_RE = re.compile(
    r"\b(may|might|could|suggest|suggested|possibly|appear|appears|seem|seems|"
    r"hypothesiz\w*|proposed|preliminary|limited|unclear|potential)\b",
    re.I,
)
METHODS_RE = re.compile(
    r"^(METHODS?|MATERIALS?|DESIGN|SETTING|PARTICIPANTS|OBJECTIVE|PURPOSE|BACKGROUND)\b",
    re.I,
)
RESULTS_RE = re.compile(
    r"\b(results?|found|showed|demonstrat\w*|conclud\w*|significant|increased|decreased)\b",
    re.I,
)

# Shared openers — same pool for every verdict so prefix cannot imply label.
NEUTRAL_OPENERS: list[str] = [
    "",
    "In this work, ",
    "The paper states that ",
    "Prior findings indicate ",
    "Researchers reported that ",
]

# Plausible claims unlikely to appear verbatim in unrelated abstracts.
NIS_CLAIM_POOL: list[str] = [
    "vaccination coverage reached 95% nationwide and eliminated the pathogen",
    "the intervention reduced five-year mortality by 60% in all subgroups",
    "lunar cycle phase significantly predicted weekly stock index returns",
    "gene therapy restored full organ function in every treated patient",
    "the drug combination cured the disease in a double-blind phase III trial",
    "air pollution levels were unrelated to any respiratory outcomes",
    "blockchain adoption cut administrative costs by half across hospitals",
]


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) >= 40]


def pick_claim_sentence(abstract: str, rng: random.Random) -> str | None:
    sents = split_sentences(abstract)
    if not sents:
        return abstract[:200].strip() if len(abstract) >= 40 else None
    scored: list[tuple[int, str]] = []
    for s in sents:
        score = 0
        if re.search(r"\d", s):
            score += 2
        if RESULTS_RE.search(s):
            score += 2
        if METHODS_RE.match(s):
            score -= 1
        scored.append((score, s))
    scored.sort(key=lambda x: (-x[0], rng.random()))
    return scored[0][1]


def pick_hedged_sentence(abstract: str, rng: random.Random) -> str | None:
    candidates = [s for s in split_sentences(abstract) if HEDGE_RE.search(s)]
    return rng.choice(candidates) if candidates else None


def pick_numeric_sentence(
    abstract: str, rng: random.Random, within: int = VISIBLE_CLAIM_CHARS
) -> str | None:
    candidates = [
        s
        for s in split_sentences(abstract)
        if re.search(r"\d", s) and NUMERIC_TOKEN_RE.search(s[:within])
    ]
    if not candidates:
        candidates = [s for s in split_sentences(abstract) if re.search(r"\d", s)]
    return rng.choice(candidates) if candidates else None


def citation_phrase(authors: list[str], year: int | None) -> str:
    surname = first_author_surname(authors)
    y = year if year else "n.d."
    if len(authors) > 2:
        return f"({surname} et al., {y})"
    if len(authors) == 2:
        s2 = first_author_surname([authors[1]])
        return f"({surname} & {s2}, {y})"
    return f"({surname}, {y})"


def neutral_passage(core: str, cite: str, rng: random.Random) -> str:
    opener = rng.choice(NEUTRAL_OPENERS)
    body = core.strip()
    if body and body[-1] in ".!?":
        body = body[:-1]
    # Lowercase only when continuing a sentence after a neutral opener (not for RESULTS:/METHODS: headers).
    if opener and body and not METHODS_RE.match(body) and body[0].isupper():
        body = body[0].lower() + body[1:] if len(body) > 1 else body.lower()
    return f"{opener}{body} {cite}."


NUMERIC_TOKEN_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(%|percent|percentage|fold|times|months|years|days|g/100 g|mg|ml|ha)?",
    re.I,
)


def flip_number_in_text(text: str, max_offset: int | None = None) -> tuple[str, str] | None:
    """Return (original_number_token, flipped_sentence) or None.

    When max_offset is set, only flip a number whose match starts at or before that index
    (so the contradiction is visible in the training claim prefix).
    """
    for m in NUMERIC_TOKEN_RE.finditer(text):
        if max_offset is not None and m.start() > max_offset:
            continue
        num = float(m.group(1))
        new_num = int(num * 1.4 + 1) if num >= 1 else round(num + 0.15, 2)
        if str(new_num) == m.group(1):
            new_num = num + 1
        flipped = text[: m.start()] + m.group(0).replace(m.group(1), str(new_num), 1) + text[m.end() :]
        if flipped != text:
            return m.group(0), flipped
    return None


def strip_hedges(text: str) -> str:
    out = HEDGE_RE.sub("", text)
    out = re.sub(r"\s{2,}", " ", out).strip()
    out = re.sub(r"\s+([,.])", r"\1", out)
    return out


def claim_absent_from_text(claim: str, text: str) -> bool:
    words = [w.lower() for w in re.findall(r"[a-zA-Z]{5,}", claim)]
    if len(words) < 3:
        return True
    hay = text.lower()
    hits = sum(1 for w in words if w in hay)
    return hits < max(2, len(words) // 2)


def pick_not_in_source_claim(abstract: str, rng: random.Random) -> str:
    rng.shuffle(NIS_CLAIM_POOL)
    for claim in NIS_CLAIM_POOL:
        if claim_absent_from_text(claim, abstract):
            return claim
    return NIS_CLAIM_POOL[0]


def methods_excerpt(abstract: str) -> str | None:
    sents = split_sentences(abstract)
    methods = [s for s in sents if METHODS_RE.match(s) or re.match(r"^We (surveyed|conducted|enrolled|randomized)", s, re.I)]
    if len(methods) < 1:
        return None
    chunk = " ".join(methods[:3])
    return chunk if len(chunk) >= 80 else None


def pick_results_sentence(abstract: str, rng: random.Random) -> str | None:
    candidates = [s for s in split_sentences(abstract) if RESULTS_RE.search(s) and not METHODS_RE.match(s)]
    return rng.choice(candidates) if candidates else None


def excerpt_preview(excerpt: str, anchor: str | None, width: int = 180) -> str:
    if not excerpt:
        return ""
    needle = (anchor or "")[:80].strip()
    if needle and needle in excerpt:
        i = excerpt.index(needle)
        start = max(0, i - 50)
        end = min(len(excerpt), i + width)
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(excerpt) else ""
        return prefix + excerpt[start:end] + suffix
    if len(excerpt) <= width:
        return excerpt
    return excerpt[:width] + "..."


def row_meta(paper: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": "abstract",
        "url": paper.get("article_url") or paper.get("doi"),
    }


def make_supported(
    paper: dict[str, Any], sentence: str, idx: int, rng: random.Random
) -> dict[str, Any] | None:
    if sentence not in paper["abstract"]:
        return None
    cite = citation_phrase(paper.get("authors", []), paper.get("year"))
    return {
        "id": f"l3-{paper['corpus_id']}-sup-{idx}",
        "task": "l3_grounding",
        "version": 1,
        "passage": neutral_passage(sentence, cite, rng),
        "source_excerpt": paper["abstract"],
        "meta": row_meta(paper),
        "output": {
            "claims": [
                {
                    "claim": sentence[:VISIBLE_CLAIM_CHARS],
                    "verdict": "supported",
                    "sourceQuotes": [sentence],
                    "hasNumericClaim": bool(re.search(r"\d", sentence)),
                }
            ],
            "overallVerdict": "support",
        },
    }


def make_contradicted(
    paper: dict[str, Any], sentence: str, idx: int, rng: random.Random
) -> dict[str, Any] | None:
    if sentence not in paper["abstract"]:
        return None
    flip = flip_number_in_text(sentence, max_offset=VISIBLE_CLAIM_CHARS - 1)
    if not flip:
        return None
    _orig_num, flipped = flip
    if flipped in paper["abstract"]:
        return None
    if flipped[:VISIBLE_CLAIM_CHARS] == sentence[:VISIBLE_CLAIM_CHARS]:
        return None
    cite = citation_phrase(paper.get("authors", []), paper.get("year"))
    return {
        "id": f"l3-{paper['corpus_id']}-con-{idx}",
        "task": "l3_grounding",
        "version": 1,
        "passage": neutral_passage(flipped, cite, rng),
        "source_excerpt": paper["abstract"],
        "meta": row_meta(paper),
        "output": {
            "claims": [
                {
                    "claim": flipped[:VISIBLE_CLAIM_CHARS],
                    "verdict": "contradicted",
                    "sourceQuotes": [sentence],
                    "hasNumericClaim": True,
                    "rationale": ["Passage numeric value conflicts with abstract wording"],
                }
            ],
            "overallVerdict": "weak",
        },
    }


def make_weak(
    paper: dict[str, Any], sentence: str, idx: int, rng: random.Random
) -> dict[str, Any] | None:
    if not HEDGE_RE.search(sentence) or sentence not in paper["abstract"]:
        return None
    strengthened = strip_hedges(sentence)
    if strengthened == sentence or len(strengthened) < 30:
        return None
    # Hedges must change the claim text we train on (first 200 chars), not only the tail.
    if strengthened[:VISIBLE_CLAIM_CHARS] == sentence[:VISIBLE_CLAIM_CHARS]:
        return None
    cite = citation_phrase(paper.get("authors", []), paper.get("year"))
    return {
        "id": f"l3-{paper['corpus_id']}-weak-{idx}",
        "task": "l3_grounding",
        "version": 1,
        "passage": neutral_passage(strengthened, cite, rng),
        "source_excerpt": paper["abstract"],
        "meta": row_meta(paper),
        "output": {
            "claims": [
                {
                    "claim": strengthened[:VISIBLE_CLAIM_CHARS],
                    "verdict": "weak",
                    "sourceQuotes": [sentence],
                    "rationale": ["Abstract uses more hedged wording than the passage"],
                }
            ],
            "overallVerdict": "weak",
        },
    }


def make_not_in_source(paper: dict[str, Any], idx: int, rng: random.Random) -> dict[str, Any]:
    cite = citation_phrase(paper.get("authors", []), paper.get("year"))
    claim = pick_not_in_source_claim(paper["abstract"], rng)
    passage = neutral_passage(claim, cite, rng)
    return {
        "id": f"l3-{paper['corpus_id']}-nis-{idx}",
        "task": "l3_grounding",
        "version": 1,
        "passage": passage,
        "source_excerpt": paper["abstract"],
        "meta": row_meta(paper),
        "output": {
            "claims": [
                {
                    "claim": claim[:200],
                    "verdict": "not_in_source",
                    "rationale": ["Claim content is not supported by the abstract excerpt"],
                }
            ],
            "overallVerdict": "unrelated",
        },
    }


def make_insufficient_evidence(
    paper: dict[str, Any], idx: int, rng: random.Random
) -> dict[str, Any] | None:
    abstract = paper["abstract"]
    thin = methods_excerpt(abstract)
    result_sent = pick_results_sentence(abstract, rng)
    if not thin or not result_sent or result_sent in thin:
        return None
    cite = citation_phrase(paper.get("authors", []), paper.get("year"))
    return {
        "id": f"l3-{paper['corpus_id']}-ins-{idx}",
        "task": "l3_grounding",
        "version": 1,
        "passage": neutral_passage(result_sent, cite, rng),
        "source_excerpt": thin,
        "meta": row_meta(paper),
        "output": {
            "claims": [
                {
                    "claim": result_sent[:200],
                    "verdict": "insufficient_evidence",
                    "rationale": [
                        "Excerpt covers methods/design only; results claim cannot be verified from it"
                    ],
                }
            ],
            "overallVerdict": "insufficient_evidence",
        },
    }


def year_bin(year: int | None) -> str:
    if not isinstance(year, int):
        return "unknown"
    for lo, hi in YEAR_BINS:
        if lo <= year <= hi:
            return f"{lo}-{hi}"
    return "other"


def validate_row(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    validate_l3_record(record, 0, errors)
    return errors


def select_papers(
    pool: list[dict[str, Any]], target_papers: int, seed: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(seed)
    by_bin: dict[str, list[dict[str, Any]]] = {}
    for p in pool:
        by_bin.setdefault(year_bin(p.get("year")), []).append(p)

    holdout_list: list[dict[str, Any]] = []
    holdout: set[str] = set()
    if len(pool) > HOLDOUT_PAPERS + target_papers:
        holdout_candidates = rng.sample(pool, HOLDOUT_PAPERS)
        holdout_list = holdout_candidates
        holdout = {p["corpus_id"] for p in holdout_candidates}

    train_pool = [p for p in pool if p["corpus_id"] not in holdout]
    selected: list[dict[str, Any]] = []
    bins = sorted(by_bin.keys())
    per_bin = max(1, target_papers // max(1, len(bins)))
    for b in bins:
        candidates = [p for p in by_bin[b] if p["corpus_id"] not in holdout]
        rng.shuffle(candidates)
        selected.extend(candidates[:per_bin])

    if len(selected) < target_papers:
        rest = [p for p in train_pool if p not in selected]
        rng.shuffle(rest)
        selected.extend(rest[: target_papers - len(selected)])

    return selected[:target_papers], holdout_list


def generate_for_paper(paper: dict[str, Any], rng: random.Random) -> list[dict[str, Any]]:
    abstract = paper.get("abstract") or ""
    rows: list[dict[str, Any]] = []
    idx = 0

    sentence = pick_claim_sentence(abstract, rng)
    if sentence:
        sup = make_supported(paper, sentence, idx, rng)
        if sup and not validate_row(sup):
            rows.append(sup)
            idx += 1

    num_sent = pick_numeric_sentence(abstract, rng)
    if num_sent:
        con = make_contradicted(paper, num_sent, idx, rng)
        if con and not validate_row(con):
            rows.append(con)
            idx += 1

    hedged = pick_hedged_sentence(abstract, rng)
    if hedged:
        weak = make_weak(paper, hedged, idx, rng)
        if weak and not validate_row(weak):
            rows.append(weak)
            idx += 1

    nis = make_not_in_source(paper, idx, rng)
    if not validate_row(nis):
        rows.append(nis)
        idx += 1

    if rng.random() < 0.45:
        ins = make_insufficient_evidence(paper, idx, rng)
        if ins and not validate_row(ins):
            rows.append(ins)

    return rows


def balance_rows(rows: list[dict[str, Any]], target: int, rng: random.Random) -> list[dict[str, Any]]:
    by_verdict: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        for c in r.get("output", {}).get("claims", []):
            v = c.get("verdict", "supported")
            by_verdict.setdefault(v, []).append(r)
            break

    if not rows:
        return []

    picked: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    quotas = {v: max(1, int(target * frac)) for v, frac in VERDICT_TARGETS.items()}

    for verdict, quota in quotas.items():
        pool = by_verdict.get(verdict, [])
        rng.shuffle(pool)
        count = 0
        for r in pool:
            if r["id"] in seen_ids:
                continue
            picked.append(r)
            seen_ids.add(r["id"])
            count += 1
            if count >= quota:
                break

    rest = [r for r in rows if r["id"] not in seen_ids]
    rng.shuffle(rest)
    for r in rest:
        if len(picked) >= target:
            break
        picked.append(r)
        seen_ids.add(r["id"])

    return picked[:target]


def export_review_csv(
    train_rows: list[dict[str, Any]], path: Path, rng: random.Random, fraction: float
) -> None:
    sample = rng.sample(train_rows, max(1, int(len(train_rows) * fraction)))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "passage",
                "claim",
                "verdict",
                "source_quote",
                "source_excerpt_preview",
                "approve",
            ],
        )
        w.writeheader()
        for r in sample:
            claim_obj = r["output"]["claims"][0]
            quote = ""
            quotes = claim_obj.get("sourceQuotes") or []
            if quotes and isinstance(quotes[0], str):
                quote = quotes[0]
            anchor = quote or claim_obj.get("claim", "")
            claim_text = str(claim_obj.get("claim", ""))
            preview_len = max(VISIBLE_CLAIM_CHARS + 80, 320)
            w.writerow(
                {
                    "id": r["id"],
                    "passage": r["passage"][:preview_len],
                    "claim": claim_text[:preview_len],
                    "verdict": claim_obj.get("verdict", ""),
                    "source_quote": quote[:preview_len] if quote else "",
                    "source_excerpt_preview": excerpt_preview(r["source_excerpt"], anchor),
                    "approve": "",
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate l3_grounding train JSONL from corpus")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=DATA_DIR / "paper_corpus_enriched.jsonl",
    )
    parser.add_argument(
        "--out-candidates",
        type=Path,
        default=DATA_DIR / "l3_grounding_candidates.jsonl",
    )
    parser.add_argument(
        "--out-train",
        type=Path,
        default=DATA_DIR / "l3_grounding_train.jsonl",
    )
    parser.add_argument(
        "--holdout-out",
        type=Path,
        default=DATA_DIR / "eval_corpus_holdout_papers.jsonl",
    )
    parser.add_argument("--target-rows", type=int, default=400)
    parser.add_argument("--target-papers", type=int, default=0, help="0 = auto from target-rows")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--export-review", type=Path, default=None)
    parser.add_argument("--review-fraction", type=float, default=0.15)
    args = parser.parse_args()

    corpus = read_jsonl(args.corpus)
    pool = [
        p
        for p in corpus
        if p.get("abstract") and len(p["abstract"]) >= MIN_ABSTRACT_CHARS
    ]
    if not pool:
        print(f"No papers with abstract >= {MIN_ABSTRACT_CHARS} in {args.corpus}", file=sys.stderr)
        return 1

    target_papers = args.target_papers or max(150, args.target_rows // 2)
    rng = random.Random(args.seed)
    papers, holdout_papers = select_papers(pool, target_papers, args.seed)

    all_rows: list[dict[str, Any]] = []
    for paper in papers:
        all_rows.extend(generate_for_paper(paper, rng))

    train_rows = balance_rows(all_rows, args.target_rows, rng)
    write_jsonl(args.out_candidates, all_rows)
    write_jsonl(args.out_train, train_rows)
    write_jsonl(args.holdout_out, holdout_papers)

    verdict_counts = Counter()
    for r in train_rows:
        for c in r.get("output", {}).get("claims", []):
            verdict_counts[c.get("verdict", "?")] += 1

    errors = 0
    for r in train_rows:
        errs = validate_row(r)
        if errs:
            errors += 1
            print(f"Validation error row {r['id']}: {errs}", file=sys.stderr)

    if args.export_review:
        export_review_csv(train_rows, args.export_review, rng, args.review_fraction)

    print(f"Papers used: {len(papers)}, holdout papers: {len(holdout_papers)}")
    print(f"Candidates: {len(all_rows)} -> {args.out_candidates}")
    print(f"Train rows: {len(train_rows)} -> {args.out_train}")
    print(f"Verdict mix: {dict(verdict_counts)}")
    print(f"Validation errors: {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
