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
    "supported": 0.40,
    "weak": 0.12,
    "not_in_source": 0.20,
    "contradicted": 0.16,
    "insufficient_evidence": 0.08,
}

MULTI_CLAIM_MIN = 100
EXCERPT_CHUNK_MAX = 1800
SUPPORTED_RATIONALE = "Numeric/factual alignment; paraphrase is supported"
SEMANTIC_SUPPORTED_RATIONALE = "Semantic/factual alignment; paraphrase is supported"

SCOPE_LIMIT_PHRASES: list[tuple[str, str, str]] = [
    (
        "Cost analyses were beyond the scope of this report.",
        "identical hospital costs",
        "Cost data are not present in the excerpt",
    ),
    (
        "Pediatric data were not collected.",
        "worked equally well in adults and children",
        "Pediatric outcomes are not described in the excerpt",
    ),
    (
        "Subgroup analyses were not prespecified.",
        "benefited all demographic subgroups equally",
        "Subgroup findings are not reported in the excerpt",
    ),
]

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


def direct_passage(core: str, cite: str) -> str:
    """Eval holdout style: direct claim + citation (no neutral opener)."""
    body = core.strip()
    if body and body[-1] in ".!?":
        body = body[:-1]
    return f"{body} {cite}."


def normalize_tokens(text: str) -> set[str]:
    parts = (
        text.lower()
        .replace(",", " ")
        .replace(".", " ")
        .replace(";", " ")
        .split()
    )
    return {t for t in parts if len(t) >= 3}


def overlap_score(passage_tokens: set[str], chunk_tokens: set[str]) -> float:
    if not passage_tokens:
        return 0.0
    hits = sum(1 for t in passage_tokens if t in chunk_tokens)
    return hits / len(passage_tokens)


def chunk_excerpt_for_grounding(passage: str, source_text: str, max_chars: int = EXCERPT_CHUNK_MAX) -> str:
    """Mirror grounding-llm.ts selectSourceChunksForGrounding."""
    cleaned = normalize_ws(source_text)
    if len(cleaned) <= max_chars:
        return cleaned

    parts = re.split(r"(?<=[.!?])\s+|[\n\r]+", cleaned)
    chunks = [p.strip() for p in parts if len(p.strip()) > 20]
    if not chunks:
        chunks = [cleaned[:2000]]

    p_tokens = normalize_tokens(passage)
    ranked = sorted(
        ((c, overlap_score(p_tokens, normalize_tokens(c))) for c in chunks),
        key=lambda x: -x[1],
    )

    out = ""
    for chunk, _score in ranked:
        sep = "\n\n" if out else ""
        if len(out) + len(sep) + len(chunk) > max_chars:
            break
        out = out + sep + chunk
    if not out:
        out = cleaned[:max_chars]
    return out[:max_chars]


def capped_abstract_excerpt(passage: str, abstract: str, max_chars: int = EXCERPT_CHUNK_MAX) -> str:
    """Chunk long corpus abstracts so chat rows fit MAX_SEQ_LENGTH (2048 tokens)."""
    return chunk_excerpt_for_grounding(passage, abstract, max_chars=max_chars)


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


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def extract_key_numbers(text: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?", text)


def numeric_alignment_ok(claim: str, source_sentence: str) -> bool:
    """True when every number in claim appears in the source sentence."""
    claim_nums = extract_key_numbers(claim)
    if not claim_nums:
        return False
    source_nums = set(extract_key_numbers(source_sentence))
    return all(n in source_nums for n in claim_nums)


def semantic_overlap_ok(claim: str, source_sentence: str) -> bool:
    """Non-numeric paraphrase: enough content-word overlap with source sentence."""
    claim_words = {w.lower() for w in re.findall(r"[a-zA-Z]{5,}", claim)}
    source_words = {w.lower() for w in re.findall(r"[a-zA-Z]{5,}", source_sentence)}
    if len(claim_words) < 2:
        return False
    hits = len(claim_words & source_words)
    return hits >= max(2, len(claim_words) // 3)


def supported_alignment_ok(claim: str, source_sentence: str) -> bool:
    if extract_key_numbers(claim):
        return numeric_alignment_ok(claim, source_sentence)
    return semantic_overlap_ok(claim, source_sentence)


def paraphrase_sentence_for_supported(sentence: str, rng: random.Random) -> str | None:
    """Manuscript-style paraphrase preserving key numbers (eval holdout style)."""
    s = sentence.strip()
    if len(s) < 30:
        return None

    patterns: list[tuple[re.Pattern[str], list[str]]] = [
        (
            re.compile(r"sensitivity was (\d+(?:\.\d+)?)\s*%", re.I),
            [
                "The new test had {n}% sensitivity",
                "Diagnostic sensitivity reached {n}%",
            ],
        ),
        (
            re.compile(r"followed for (?:a )?mean of (\d+(?:\.\d+)?) months", re.I),
            ["Mean follow-up was {n} months"],
        ),
        (
            re.compile(r"(?:reached|achieved) an AUC of (\d+(?:\.\d+)?)", re.I),
            ["The model achieved an AUC of {n}"],
        ),
        (
            re.compile(r"(\d+(?:\.\d+)?)\s*% of (?:patients|participants)", re.I),
            ["Around {n}% of patients reported the outcome"],
        ),
        (
            re.compile(r"enrolled (\d[\d,]*) (?:adults|patients|participants)", re.I),
            ["The cohort included {n} participants"],
        ),
        (
            re.compile(r"efficacy (?:was |of )?(\d+(?:\.\d+)?)\s*%", re.I),
            ["Vaccine efficacy was {n}% in the trial"],
        ),
        (
            re.compile(r"efficacy against .+ was (\d+(?:\.\d+)?)\s*%", re.I),
            ["Efficacy was {n}% against the primary endpoint"],
        ),
        (
            re.compile(r"(\d+(?:\.\d+)?)\s*% \(95% CI", re.I),
            ["The rate was {n}% in the primary analysis"],
        ),
        (
            re.compile(r"increased by (\d+(?:\.\d+)?)\s*%", re.I),
            ["The measure rose by {n}% compared with baseline"],
        ),
    ]

    for pat, templates in patterns:
        m = pat.search(s)
        if m:
            n = m.group(1).replace(",", "")
            tpl = rng.choice(templates)
            return tpl.format(n=n)

    semantic: list[tuple[re.Pattern[str], str]] = [
        (
            re.compile(r"was associated with improved (.+?)[\.,]", re.I),
            r"\1 improved with treatment",
        ),
        (
            re.compile(r"decreased significantly in the (.+?) (?:arm|group)", re.I),
            r"Treatment reduced outcomes in the \1 group",
        ),
        (
            re.compile(r"did not differ between (.+?) groups", re.I),
            r"Rates were similar between groups",
        ),
        (
            re.compile(r"protocol compliance was high", re.I),
            r"Compliance with the protocol was high",
        ),
        (
            re.compile(r"were significantly elevated", re.I),
            r"Both biomarkers were elevated",
        ),
    ]
    for pat, repl in semantic:
        m = pat.search(s)
        if m:
            out = pat.sub(repl, s, count=1)
            if "{n}" in out and m.lastindex:
                out = out.format(n=m.group(1))
            out = normalize_ws(out)
            if 20 <= len(out) <= VISIBLE_CLAIM_CHARS and out.lower() != s.lower():
                return out[:VISIBLE_CLAIM_CHARS]

    return None


def paraphrase_semantic_for_supported(sentence: str, rng: random.Random) -> str | None:
    """Non-numeric paraphrase (h-010 style)."""
    if re.search(r"\d", sentence):
        return None
    s = sentence.strip()
    semantic_templates: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"protocol compliance was high", re.I), "Compliance with the protocol was high"),
        (re.compile(r"compliance was high", re.I), "Compliance with the protocol was high"),
        (re.compile(r"adherence to (?:the )?protocol was high", re.I), "Compliance with the protocol was high"),
        (re.compile(r"were similar between groups", re.I), "Rates were similar between groups"),
        (re.compile(r"did not differ between", re.I), "Outcomes did not differ between groups"),
        (re.compile(r"were significantly elevated", re.I), "Both biomarkers were elevated"),
        (re.compile(r"was associated with improved", re.I), "Outcomes improved with treatment"),
    ]
    for pat, repl in semantic_templates:
        if pat.search(s):
            return repl
    return paraphrase_sentence_for_supported(sentence, rng)


def pick_semantic_sentence(abstract: str, rng: random.Random) -> str | None:
    candidates = [
        s
        for s in split_sentences(abstract)
        if not re.search(r"\d", s) and RESULTS_RE.search(s) and len(s) >= 40
    ]
    return rng.choice(candidates) if candidates else None


def pick_polarity_source_sentence(abstract: str, rng: random.Random) -> str | None:
    patterns = [
        re.compile(r"significant association", re.I),
        re.compile(r"statistically significant", re.I),
        re.compile(r"was associated with", re.I),
        re.compile(r"significantly (?:increased|decreased|reduced)", re.I),
    ]
    candidates = [s for s in split_sentences(abstract) if any(p.search(s) for p in patterns)]
    return rng.choice(candidates) if candidates else None


def pick_partial_response_sentence(abstract: str, rng: random.Random) -> str | None:
    patterns = [
        re.compile(r"\d+\s+of\s+\d+", re.I),
        re.compile(r"partial response", re.I),
        re.compile(r"\d+\s+participants", re.I),
        re.compile(r"showed (?:a )?response", re.I),
    ]
    candidates = [s for s in split_sentences(abstract) if any(p.search(s) for p in patterns)]
    return rng.choice(candidates) if candidates else None


def pick_two_numeric_sentences(abstract: str, rng: random.Random) -> tuple[str, str] | None:
    candidates = [s for s in split_sentences(abstract) if re.search(r"\d", s) and len(s) >= 30]
    if len(candidates) < 2:
        return None
    pair = rng.sample(candidates, 2)
    return pair[0], pair[1]


def short_claim_from_sentence(sentence: str, max_len: int = 80) -> str:
    s = normalize_ws(sentence)
    if len(s) <= max_len:
        return s
    m = re.search(r"\d+(?:\.\d+)?\s*%?", s)
    if m:
        start = max(0, m.start() - 30)
        return s[start : start + max_len].strip()
    return s[:max_len].strip()


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


def row_meta(paper: dict[str, Any], excerpt_mode: str = "full") -> dict[str, Any]:
    return {
        "label": "abstract",
        "url": paper.get("article_url") or paper.get("doi"),
        "excerpt_mode": excerpt_mode,
    }


CANONICAL_CLAIM_KEYS = ("claim", "verdict", "sourceQuotes", "rationale", "hasNumericClaim")

PRIORITY_SUFFIXES = (
    "-sanad-",
    "-sanadsem-",
    "-supp-",
    "-chunk-",
    "-pol-",
    "-over-",
    # -multi- and -multip- intentionally excluded: too abundant (~700 candidates),
    # would flood the 850-row budget before verdict quotas can fill.
    # Protected by MULTI_CLAIM_MIN = 100 floor in balance_rows instead.
)


def is_priority_row(row_id: str) -> bool:
    return any(s in row_id for s in PRIORITY_SUFFIXES)


def canonical_claim(
    *,
    claim: str,
    verdict: str,
    source_quotes: list[str] | None = None,
    rationale: list[str] | None = None,
    has_numeric: bool | None = None,
) -> dict[str, Any]:
    """Fixed key order; hasNumericClaim is always last (scalar JSON terminator)."""
    quotes = list(source_quotes or [])
    if verdict == "supported" and not quotes:
        raise ValueError(f"supported claim must have sourceQuotes: {claim[:60]!r}")
    return {
        "claim": claim,
        "verdict": verdict,
        "sourceQuotes": quotes,
        "rationale": list(rationale or []),
        "hasNumericClaim": has_numeric
        if has_numeric is not None
        else bool(re.search(r"\d", claim)),
    }


def make_supported_paraphrase(
    paper: dict[str, Any], sentence: str, idx: int, rng: random.Random
) -> dict[str, Any] | None:
    """Supported when passage paraphrases the abstract but numbers/facts align."""
    if sentence not in paper["abstract"]:
        return None
    paraphrase = paraphrase_sentence_for_supported(sentence, rng)
    if not paraphrase:
        return None
    if normalize_ws(paraphrase) == normalize_ws(sentence):
        return None
    if not supported_alignment_ok(paraphrase, sentence):
        return None
    cite = citation_phrase(paper.get("authors", []), paper.get("year"))
    return {
        "id": f"l3-{paper['corpus_id']}-supp-{idx}",
        "task": "l3_grounding",
        "version": 1,
        "passage": neutral_passage(paraphrase, cite, rng),
        "source_excerpt": capped_abstract_excerpt(paraphrase, paper["abstract"]),
        "meta": row_meta(paper, "full"),
        "output": {
            "claims": [
                canonical_claim(
                    claim=paraphrase[:VISIBLE_CLAIM_CHARS],
                    verdict="supported",
                    source_quotes=[sentence],
                    rationale=[SUPPORTED_RATIONALE],
                    has_numeric=bool(re.search(r"\d", paraphrase)),
                )
            ],
            "overallVerdict": "support",
        },
    }


def make_holdout_style_supported(
    paper: dict[str, Any], sentence: str, idx: int, rng: random.Random
) -> dict[str, Any] | None:
    """Holdout-shaped: direct passage + single-sentence excerpt (eval alignment)."""
    if sentence not in paper["abstract"]:
        return None
    paraphrase = paraphrase_sentence_for_supported(sentence, rng)
    if not paraphrase:
        return None
    if not supported_alignment_ok(paraphrase, sentence):
        return None
    cite = citation_phrase(paper.get("authors", []), paper.get("year"))
    return {
        "id": f"l3-{paper['corpus_id']}-sanad-{idx}",
        "task": "l3_grounding",
        "version": 1,
        "passage": direct_passage(paraphrase, cite),
        "source_excerpt": sentence,
        "meta": row_meta(paper, "sentence"),
        "output": {
            "claims": [
                canonical_claim(
                    claim=paraphrase[:VISIBLE_CLAIM_CHARS],
                    verdict="supported",
                    source_quotes=[sentence],
                    rationale=[SUPPORTED_RATIONALE],
                    has_numeric=bool(re.search(r"\d", paraphrase)),
                )
            ],
            "overallVerdict": "support",
        },
    }


def make_supported_paraphrase_chunked(
    paper: dict[str, Any], sentence: str, idx: int, rng: random.Random
) -> dict[str, Any] | None:
    """Production-shaped: paraphrase claim + token-overlap chunked excerpt."""
    abstract = paper["abstract"]
    if sentence not in abstract:
        return None
    paraphrase = paraphrase_sentence_for_supported(sentence, rng)
    if not paraphrase or not supported_alignment_ok(paraphrase, sentence):
        return None
    cite = citation_phrase(paper.get("authors", []), paper.get("year"))
    chunk = chunk_excerpt_for_grounding(paraphrase, abstract)
    if not is_substring_quote(sentence, chunk):
        if len(sentence) + len(chunk) + 2 <= EXCERPT_CHUNK_MAX:
            chunk = f"{sentence}\n\n{chunk}"[:EXCERPT_CHUNK_MAX]
        elif not is_substring_quote(sentence, chunk):
            return None
    return {
        "id": f"l3-{paper['corpus_id']}-chunk-{idx}",
        "task": "l3_grounding",
        "version": 1,
        "passage": neutral_passage(paraphrase, cite, rng),
        "source_excerpt": chunk,
        "meta": row_meta(paper, "chunked"),
        "output": {
            "claims": [
                canonical_claim(
                    claim=paraphrase[:VISIBLE_CLAIM_CHARS],
                    verdict="supported",
                    source_quotes=[sentence],
                    rationale=[SUPPORTED_RATIONALE],
                    has_numeric=bool(re.search(r"\d", paraphrase)),
                )
            ],
            "overallVerdict": "support",
        },
    }


def is_substring_quote(quote: str, excerpt: str) -> bool:
    if quote in excerpt:
        return True
    return normalize_ws(quote) in normalize_ws(excerpt)


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
        "source_excerpt": capped_abstract_excerpt(sentence, paper["abstract"]),
        "meta": row_meta(paper, "full"),
        "output": {
            "claims": [
                canonical_claim(
                    claim=sentence[:VISIBLE_CLAIM_CHARS],
                    verdict="supported",
                    source_quotes=[sentence],
                    has_numeric=bool(re.search(r"\d", sentence)),
                )
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
        "source_excerpt": capped_abstract_excerpt(flipped, paper["abstract"]),
        "meta": row_meta(paper, "full"),
        "output": {
            "claims": [
                canonical_claim(
                    claim=flipped[:VISIBLE_CLAIM_CHARS],
                    verdict="contradicted",
                    source_quotes=[sentence],
                    rationale=["Passage numeric value conflicts with abstract wording"],
                    has_numeric=True,
                )
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
    # Same numbers with only hedging removed → supported pattern, not weak.
    if extract_key_numbers(strengthened) and numeric_alignment_ok(strengthened, sentence):
        return None
    cite = citation_phrase(paper.get("authors", []), paper.get("year"))
    return {
        "id": f"l3-{paper['corpus_id']}-weak-{idx}",
        "task": "l3_grounding",
        "version": 1,
        "passage": neutral_passage(strengthened, cite, rng),
        "source_excerpt": capped_abstract_excerpt(strengthened, paper["abstract"]),
        "meta": row_meta(paper, "full"),
        "output": {
            "claims": [
                canonical_claim(
                    claim=strengthened[:VISIBLE_CLAIM_CHARS],
                    verdict="weak",
                    source_quotes=[sentence],
                    rationale=["Abstract uses more hedged wording than the passage"],
                    has_numeric=bool(re.search(r"\d", strengthened)),
                )
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
        "source_excerpt": capped_abstract_excerpt(passage, paper["abstract"]),
        "meta": row_meta(paper, "full"),
        "output": {
            "claims": [
                canonical_claim(
                    claim=claim[:200],
                    verdict="not_in_source",
                    rationale=["Claim content is not supported by the abstract excerpt"],
                )
            ],
            "overallVerdict": "unrelated",
        },
    }


def make_not_in_source_thin_excerpt(
    paper: dict[str, Any], idx: int, rng: random.Random
) -> dict[str, Any] | None:
    """Claim topic absent from a thin methods/design excerpt (h-021 style)."""
    abstract = paper["abstract"]
    thin = methods_excerpt(abstract)
    if not thin:
        sents = split_sentences(abstract)
        thin = " ".join(sents[:2]) if len(sents) >= 2 else None
    if not thin or len(thin) < 80:
        return None
    claim = pick_not_in_source_claim(thin, rng)
    if not claim_absent_from_text(claim, thin):
        return None
    cite = citation_phrase(paper.get("authors", []), paper.get("year"))
    return {
        "id": f"l3-{paper['corpus_id']}-nisthin-{idx}",
        "task": "l3_grounding",
        "version": 1,
        "passage": direct_passage(claim, cite),
        "source_excerpt": thin,
        "meta": row_meta(paper, "sentence"),
        "output": {
            "claims": [
                canonical_claim(
                    claim=claim[:200],
                    verdict="not_in_source",
                    rationale=["Claim topic is absent from the provided excerpt"],
                )
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
        "meta": row_meta(paper, "sentence"),
        "output": {
            "claims": [
                canonical_claim(
                    claim=result_sent[:200],
                    verdict="insufficient_evidence",
                    rationale=[
                        "Excerpt covers methods/design only; results claim cannot be verified from it"
                    ],
                )
            ],
            "overallVerdict": "insufficient_evidence",
        },
    }


def make_semantic_sanad_supported(
    paper: dict[str, Any], sentence: str, idx: int, rng: random.Random
) -> dict[str, Any] | None:
    """Holdout-shaped semantic supported (h-010; no numbers)."""
    if sentence not in paper["abstract"] or re.search(r"\d", sentence):
        return None
    paraphrase = paraphrase_semantic_for_supported(sentence, rng)
    if not paraphrase or not semantic_overlap_ok(paraphrase, sentence):
        return None
    cite = citation_phrase(paper.get("authors", []), paper.get("year"))
    return {
        "id": f"l3-{paper['corpus_id']}-sanadsem-{idx}",
        "task": "l3_grounding",
        "version": 1,
        "passage": direct_passage(paraphrase, cite),
        "source_excerpt": sentence,
        "meta": {**row_meta(paper, "sentence"), "row_type": "semantic_sanad"},
        "output": {
            "claims": [
                canonical_claim(
                    claim=paraphrase[:VISIBLE_CLAIM_CHARS],
                    verdict="supported",
                    source_quotes=[sentence],
                    rationale=[SEMANTIC_SUPPORTED_RATIONALE],
                    has_numeric=False,
                )
            ],
            "overallVerdict": "support",
        },
    }


def make_polarity_contradicted(
    paper: dict[str, Any], sentence: str, idx: int, rng: random.Random
) -> dict[str, Any] | None:
    """Negation/polarity flip (h-013 style)."""
    if sentence not in paper["abstract"]:
        return None
    lowered = sentence.lower()
    if "association" not in lowered and "associated" not in lowered:
        return None
    topic_m = re.search(
        r"association (?:was observed )?between (.+?) and (.+?)[\.,]",
        sentence,
        re.I,
    )
    if topic_m:
        neg_claim = (
            f"There was no association between {topic_m.group(1).strip()} "
            f"and {topic_m.group(2).strip()}"
        )
    else:
        neg_claim = "There was no association between the factors studied and the outcome"
    cite = citation_phrase(paper.get("authors", []), paper.get("year"))
    return {
        "id": f"l3-{paper['corpus_id']}-pol-{idx}",
        "task": "l3_grounding",
        "version": 1,
        "passage": direct_passage(neg_claim, cite),
        "source_excerpt": sentence,
        "meta": {**row_meta(paper, "sentence"), "row_type": "polarity"},
        "output": {
            "claims": [
                canonical_claim(
                    claim=neg_claim[:VISIBLE_CLAIM_CHARS],
                    verdict="contradicted",
                    source_quotes=[sentence],
                    rationale=["Passage denies an association the excerpt reports"],
                )
            ],
            "overallVerdict": "weak",
        },
    }


def make_overclaim_contradicted(
    paper: dict[str, Any], sentence: str, idx: int, rng: random.Random
) -> dict[str, Any] | None:
    """Overstated passage vs partial counts (eval-003 style)."""
    if sentence not in paper["abstract"]:
        return None
    overclaims = [
        "The treatment cured all patients in the cohort",
        "CRISPR editing cured the disorder in all patients",
        "Every participant achieved complete remission",
        "All patients recovered fully",
    ]
    cite = citation_phrase(paper.get("authors", []), paper.get("year"))
    claim = rng.choice(overclaims)
    return {
        "id": f"l3-{paper['corpus_id']}-over-{idx}",
        "task": "l3_grounding",
        "version": 1,
        "passage": direct_passage(claim, cite),
        "source_excerpt": sentence,
        "meta": {**row_meta(paper, "sentence"), "row_type": "overclaim"},
        "output": {
            "claims": [
                canonical_claim(
                    claim=claim[:VISIBLE_CLAIM_CHARS],
                    verdict="contradicted",
                    source_quotes=[sentence],
                    rationale=["Excerpt reports partial or limited response, not universal cure"],
                )
            ],
            "overallVerdict": "weak",
        },
    }


def make_multi_claim_supported(
    paper: dict[str, Any], idx: int, rng: random.Random
) -> dict[str, Any] | None:
    """Two atomic supported claims in one passage (eval-005 style)."""
    pair = pick_two_numeric_sentences(paper["abstract"], rng)
    if not pair:
        return None
    sent_a, sent_b = pair
    quote_a = short_claim_from_sentence(sent_a, 60)
    quote_b = short_claim_from_sentence(sent_b, 60)
    nums_a = extract_key_numbers(sent_a)
    nums_b = extract_key_numbers(sent_b)
    claim_a = f"Sample size n={nums_a[0]}" if nums_a else quote_a[:60]
    claim_b = f"{nums_b[0]}% power" if nums_b and "%" in sent_b.lower() else quote_b[:60]
    if "%" in sent_b and nums_b:
        claim_b = f"{nums_b[0]}% power"
    passage_core = f"{claim_a} with {claim_b}"
    cite = citation_phrase(paper.get("authors", []), paper.get("year"))
    excerpt = f"{sent_a} {sent_b}"
    if len(excerpt) > EXCERPT_CHUNK_MAX:
        excerpt = excerpt[:EXCERPT_CHUNK_MAX]
    return {
        "id": f"l3-{paper['corpus_id']}-multi-{idx}",
        "task": "l3_grounding",
        "version": 1,
        "passage": direct_passage(passage_core, cite),
        "source_excerpt": excerpt,
        "meta": {**row_meta(paper, "sentence"), "row_type": "multi_claim"},
        "output": {
            "claims": [
                canonical_claim(
                    claim=claim_a[:VISIBLE_CLAIM_CHARS],
                    verdict="supported",
                    source_quotes=[sent_a if len(sent_a) <= 200 else quote_a],
                    has_numeric=True,
                ),
                canonical_claim(
                    claim=claim_b[:VISIBLE_CLAIM_CHARS],
                    verdict="supported",
                    source_quotes=[sent_b if len(sent_b) <= 200 else quote_b],
                    has_numeric=bool(nums_b),
                ),
            ],
            "overallVerdict": "support",
        },
    }


def make_multi_claim_partial(
    paper: dict[str, Any], idx: int, rng: random.Random
) -> dict[str, Any] | None:
    """Compound passage: one supported claim + one absent from excerpt (h-043/h-045)."""
    sent_a = pick_results_sentence(paper["abstract"], rng)
    if not sent_a:
        sent_a = pick_claim_sentence(paper["abstract"], rng)
    if not sent_a or sent_a not in paper["abstract"]:
        return None
    scope_sent, claim_b_phrase, rationale_b = rng.choice(SCOPE_LIMIT_PHRASES)
    para_a = paraphrase_semantic_for_supported(sent_a, rng) or short_claim_from_sentence(sent_a, 90)
    if not para_a:
        return None
    cite = citation_phrase(paper.get("authors", []), paper.get("year"))
    passage_core = f"{para_a.rstrip('.')}, and {claim_b_phrase}"
    excerpt = f"{sent_a} {scope_sent}"
    quote_a = sent_a
    return {
        "id": f"l3-{paper['corpus_id']}-multip-{idx}",
        "task": "l3_grounding",
        "version": 1,
        "passage": direct_passage(passage_core, cite),
        "source_excerpt": excerpt,
        "meta": {**row_meta(paper, "sentence"), "row_type": "multi_claim"},
        "output": {
            "claims": [
                canonical_claim(
                    claim=para_a[:VISIBLE_CLAIM_CHARS],
                    verdict="supported",
                    source_quotes=[quote_a],
                    rationale=[SEMANTIC_SUPPORTED_RATIONALE],
                ),
                canonical_claim(
                    claim=claim_b_phrase[:VISIBLE_CLAIM_CHARS],
                    verdict="not_in_source",
                    rationale=[rationale_b],
                ),
            ],
            "overallVerdict": "weak",
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
        sup_para = make_supported_paraphrase(paper, sentence, idx, rng)
        if sup_para and not validate_row(sup_para):
            rows.append(sup_para)
            idx += 1
        sanad = make_holdout_style_supported(paper, sentence, idx, rng)
        if sanad and not validate_row(sanad):
            rows.append(sanad)
            idx += 1
        chunked = make_supported_paraphrase_chunked(paper, sentence, idx, rng)
        if chunked and not validate_row(chunked):
            rows.append(chunked)
            idx += 1

    num_sent = pick_numeric_sentence(abstract, rng)
    if num_sent:
        con = make_contradicted(paper, num_sent, idx, rng)
        if con and not validate_row(con):
            rows.append(con)
            idx += 1
        if num_sent != sentence:
            sup_num = make_supported_paraphrase(paper, num_sent, idx, rng)
            if sup_num and not validate_row(sup_num):
                rows.append(sup_num)
                idx += 1
            sanad_num = make_holdout_style_supported(paper, num_sent, idx, rng)
            if sanad_num and not validate_row(sanad_num):
                rows.append(sanad_num)
                idx += 1
            chunk_num = make_supported_paraphrase_chunked(paper, num_sent, idx, rng)
            if chunk_num and not validate_row(chunk_num):
                rows.append(chunk_num)
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

    nis_thin = make_not_in_source_thin_excerpt(paper, idx, rng)
    if nis_thin and not validate_row(nis_thin):
        rows.append(nis_thin)
        idx += 1

    semantic = pick_semantic_sentence(abstract, rng)
    if semantic:
        sem_sanad = make_semantic_sanad_supported(paper, semantic, idx, rng)
        if sem_sanad and not validate_row(sem_sanad):
            rows.append(sem_sanad)
            idx += 1

    polarity = pick_polarity_source_sentence(abstract, rng)
    if polarity:
        pol = make_polarity_contradicted(paper, polarity, idx, rng)
        if pol and not validate_row(pol):
            rows.append(pol)
            idx += 1

    partial = pick_partial_response_sentence(abstract, rng)
    if partial:
        over = make_overclaim_contradicted(paper, partial, idx, rng)
        if over and not validate_row(over):
            rows.append(over)
            idx += 1

    multi_sup = make_multi_claim_supported(paper, idx, rng)
    if multi_sup and not validate_row(multi_sup):
        rows.append(multi_sup)
        idx += 1

    multi_part = make_multi_claim_partial(paper, idx, rng)
    if multi_part and not validate_row(multi_part):
        rows.append(multi_part)
        idx += 1

    if rng.random() < 0.45:
        ins = make_insufficient_evidence(paper, idx, rng)
        if ins and not validate_row(ins):
            rows.append(ins)

    return rows


def balance_rows(rows: list[dict[str, Any]], target: int, rng: random.Random) -> list[dict[str, Any]]:
    """Include all priority (specialized) rows first, then fill verdict quotas from generic pool."""
    if not rows:
        return []

    priority = [r for r in rows if is_priority_row(r["id"])]
    generic = [r for r in rows if not is_priority_row(r["id"])]

    picked: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    rng.shuffle(priority)
    for r in priority:
        if r["id"] in seen_ids:
            continue
        picked.append(r)
        seen_ids.add(r["id"])

    def primary_verdict(row: dict[str, Any]) -> str:
        claims = row.get("output", {}).get("claims", [])
        if claims and isinstance(claims[0], dict):
            return str(claims[0].get("verdict", "supported"))
        return "supported"

    verdict_in_picked: Counter[str] = Counter(primary_verdict(r) for r in picked)
    quotas = {v: max(1, int(target * frac)) for v, frac in VERDICT_TARGETS.items()}

    by_verdict: dict[str, list[dict[str, Any]]] = {}
    for r in generic:
        if r["id"] in seen_ids:
            continue
        by_verdict.setdefault(primary_verdict(r), []).append(r)

    for verdict, quota in quotas.items():
        needed = max(0, quota - verdict_in_picked.get(verdict, 0))
        pool = by_verdict.get(verdict, [])
        rng.shuffle(pool)
        added = 0
        for r in pool:
            if len(picked) >= target:
                break
            if r["id"] in seen_ids:
                continue
            picked.append(r)
            seen_ids.add(r["id"])
            verdict_in_picked[verdict] += 1
            added += 1
            if added >= needed:
                break

    multi_pool = [
        r
        for r in rows
        if len(r.get("output", {}).get("claims", [])) >= 2 and r["id"] not in seen_ids
    ]
    rng.shuffle(multi_pool)
    multi_count = sum(1 for r in picked if len(r.get("output", {}).get("claims", [])) >= 2)
    for r in multi_pool:
        if multi_count >= MULTI_CLAIM_MIN:
            break
        if len(picked) >= target:
            break
        picked.append(r)
        seen_ids.add(r["id"])
        multi_count += 1

    rest = [r for r in generic if r["id"] not in seen_ids]
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
    parser.add_argument("--target-rows", type=int, default=850)
    parser.add_argument("--target-papers", type=int, default=0, help="0 = auto from target-rows")
    parser.add_argument("--seed", type=int, default=46)
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
