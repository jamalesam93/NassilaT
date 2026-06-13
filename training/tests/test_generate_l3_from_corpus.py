"""Unit tests for l3 label generation (v1.2 / v1.3)."""

from __future__ import annotations

import random
import sys
from pathlib import Path

import unittest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from generate_l3_from_corpus import (  # noqa: E402
    chunk_excerpt_for_grounding,
    make_holdout_style_supported,
    make_multi_claim_partial,
    make_multi_claim_supported,
    make_polarity_contradicted,
    make_semantic_sanad_supported,
    make_supported_paraphrase,
    make_weak,
    numeric_alignment_ok,
    paraphrase_semantic_for_supported,
    paraphrase_sentence_for_supported,
)


class TestGenerateL3(unittest.TestCase):
    def test_numeric_alignment_ok(self):
        self.assertTrue(
            numeric_alignment_ok(
                "The new test had 95% sensitivity",
                "Diagnostic sensitivity was 95% (95% CI 92-97)",
            )
        )
        self.assertFalse(numeric_alignment_ok("Mortality halved", "Mortality decreased by 12%"))

    def test_h001_template_appears_in_generator(self):
        sentence = "Diagnostic sensitivity was 95% (95% CI 92-97) in the validation cohort."
        templates = {
            paraphrase_sentence_for_supported(sentence, random.Random(seed))
            for seed in range(30)
        }
        self.assertTrue(any(p and "The new test had" in p for p in templates))

    def test_semantic_paraphrase_compliance(self):
        sentence = "Protocol compliance was high across all study sites."
        para = paraphrase_semantic_for_supported(sentence, random.Random(0))
        self.assertIsNotNone(para)
        self.assertIn("Compliance", para)

    def test_semantic_sanad_row(self):
        rng = random.Random(5)
        paper = {
            "corpus_id": "test-sem",
            "abstract": "Protocol compliance was high across all study sites.",
            "authors": ["Davies"],
            "year": 2018,
        }
        sentence = paper["abstract"]
        row = make_semantic_sanad_supported(paper, sentence, 0, rng)
        self.assertIsNotNone(row)
        self.assertIn("-sanadsem-", row["id"])
        self.assertEqual(row["output"]["claims"][0]["verdict"], "supported")

    def test_polarity_contradicted_row(self):
        rng = random.Random(6)
        sentence = (
            "A statistically significant association was observed between "
            "dietary pattern and the primary outcome."
        )
        paper = {
            "corpus_id": "test-pol",
            "abstract": sentence,
            "authors": ["Mehta"],
            "year": 2020,
        }
        row = make_polarity_contradicted(paper, sentence, 0, rng)
        self.assertIsNotNone(row)
        self.assertEqual(row["output"]["claims"][0]["verdict"], "contradicted")
        self.assertIn("no association", row["output"]["claims"][0]["claim"].lower())

    def test_multi_claim_supported_row(self):
        rng = random.Random(7)
        abstract = (
            "We enrolled 500 participants in the trial. "
            "Power calculations assumed 80% power for the primary endpoint."
        )
        paper = {"corpus_id": "test-mc", "abstract": abstract, "authors": ["Torres"], "year": 2020}
        row = make_multi_claim_supported(paper, 0, rng)
        self.assertIsNotNone(row)
        self.assertGreaterEqual(len(row["output"]["claims"]), 2)
        self.assertTrue(all(c["verdict"] == "supported" for c in row["output"]["claims"]))

    def test_multi_claim_partial_row(self):
        rng = random.Random(8)
        abstract = "Results showed pain scores were similar between groups in the primary analysis."
        paper = {"corpus_id": "test-mp", "abstract": abstract, "authors": ["Park"], "year": 2020}
        row = make_multi_claim_partial(paper, 0, rng)
        self.assertIsNotNone(row)
        verdicts = [c["verdict"] for c in row["output"]["claims"]]
        self.assertIn("supported", verdicts)
        self.assertIn("not_in_source", verdicts)

    def test_holdout_style_sanad_row(self):
        rng = random.Random(3)
        paper = {
            "corpus_id": "test-sanad",
            "abstract": "Diagnostic sensitivity was 95% (95% CI 92-97) in the validation cohort.",
            "authors": ["Lopez"],
            "year": 2022,
        }
        row = make_holdout_style_supported(paper, paper["abstract"], 0, rng)
        self.assertIsNotNone(row)
        self.assertIn("-sanad-", row["id"])

    def test_weak_skips_numeric_only_hedge_removal(self):
        rng = random.Random(2)
        paper = {
            "corpus_id": "test-2",
            "abstract": "Results may suggest efficacy was 95% in the subgroup analysis.",
            "authors": ["A"],
            "year": 2020,
        }
        self.assertIsNone(make_weak(paper, paper["abstract"], 0, rng))


if __name__ == "__main__":
    unittest.main()
