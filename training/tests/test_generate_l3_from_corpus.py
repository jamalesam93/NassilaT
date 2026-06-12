"""Unit tests for l3 label generation helpers (Phase 2.1 / v1.2)."""



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

    make_supported_paraphrase,

    make_supported_paraphrase_chunked,

    make_weak,

    numeric_alignment_ok,

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



    def test_paraphrase_sensitivity(self):

        rng = random.Random(0)

        sentence = "Diagnostic sensitivity was 95% (95% CI 92-97) in the validation cohort."

        para = paraphrase_sentence_for_supported(sentence, rng)

        self.assertIsNotNone(para)

        self.assertIn("95", para)

        self.assertNotEqual(para, sentence)

    def test_h001_template_appears_in_generator(self):
        sentence = "Diagnostic sensitivity was 95% (95% CI 92-97) in the validation cohort."
        templates = {
            paraphrase_sentence_for_supported(sentence, random.Random(seed))
            for seed in range(30)
        }
        self.assertTrue(any(p and "The new test had" in p for p in templates))

    def test_paraphrase_supported_row(self):

        rng = random.Random(1)

        paper = {

            "corpus_id": "test-1",

            "abstract": "Diagnostic sensitivity was 95% (95% CI 92-97) in the validation cohort.",

            "authors": ["Lopez"],

            "year": 2022,

            "article_url": "https://example.com",

        }

        sentence = paper["abstract"]

        row = make_supported_paraphrase(paper, sentence, 0, rng)

        self.assertIsNotNone(row)

        claim = row["output"]["claims"][0]

        self.assertEqual(claim["verdict"], "supported")

        self.assertIn(claim["sourceQuotes"][0], paper["abstract"])

        self.assertTrue(numeric_alignment_ok(claim["claim"], claim["sourceQuotes"][0]))

        self.assertTrue(claim.get("rationale"))



    def test_holdout_style_sanad_row(self):

        rng = random.Random(3)

        paper = {

            "corpus_id": "test-sanad",

            "abstract": "Diagnostic sensitivity was 95% (95% CI 92-97) in the validation cohort.",

            "authors": ["Lopez"],

            "year": 2022,

        }

        sentence = paper["abstract"]

        row = make_holdout_style_supported(paper, sentence, 0, rng)

        self.assertIsNotNone(row)

        self.assertIn("-sanad-", row["id"])

        self.assertEqual(row["meta"]["excerpt_mode"], "sentence")

        self.assertEqual(row["source_excerpt"], sentence)

        self.assertNotIn("This study reports", row["passage"])

        claim = row["output"]["claims"][0]

        self.assertEqual(claim["verdict"], "supported")

        self.assertTrue(claim.get("rationale"))



    def test_chunked_excerpt_row(self):

        rng = random.Random(4)

        abstract = (

            "METHODS: We enrolled 1200 adults in a randomized trial. "

            "RESULTS: Diagnostic sensitivity was 95% (95% CI 92-97) in the validation cohort. "

            "CONCLUSIONS: The test performed well in practice."

        )

        paper = {

            "corpus_id": "test-chunk",

            "abstract": abstract,

            "authors": ["A"],

            "year": 2021,

        }

        sentence = "RESULTS: Diagnostic sensitivity was 95% (95% CI 92-97) in the validation cohort."

        row = make_supported_paraphrase_chunked(paper, sentence, 0, rng)

        self.assertIsNotNone(row)

        self.assertEqual(row["meta"]["excerpt_mode"], "chunked")

        self.assertLessEqual(len(row["source_excerpt"]), 1800)

        quote = row["output"]["claims"][0]["sourceQuotes"][0]

        self.assertIn(quote, row["source_excerpt"])



    def test_chunk_excerpt_for_grounding(self):

        abstract = "Alpha beta gamma. " * 30 + "Target sensitivity was 95% in cohort. " + "Delta epsilon. " * 30

        passage = "The new test had 95% sensitivity"

        chunk = chunk_excerpt_for_grounding(passage, abstract, max_chars=500)

        self.assertLessEqual(len(chunk), 500)

        self.assertIn("95%", chunk)



    def test_weak_skips_numeric_only_hedge_removal(self):

        rng = random.Random(2)

        paper = {

            "corpus_id": "test-2",

            "abstract": "Results may suggest efficacy was 95% in the subgroup analysis.",

            "authors": ["A"],

            "year": 2020,

        }

        sentence = paper["abstract"]

        row = make_weak(paper, sentence, 0, rng)

        self.assertIsNone(row)





if __name__ == "__main__":

    unittest.main()

