"""Unit tests for corpus pipeline helpers."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from corpus_utils import (  # noqa: E402
    normalize_doi,
    reconstruct_openalex_abstract,
)


def test_normalize_doi():
    assert normalize_doi("https://doi.org/10.1234/ABC") == "10.1234/abc"
    assert normalize_doi("DOI:10.1/x") == "10.1/x"
    assert normalize_doi("") is None


def test_reconstruct_openalex_abstract():
    inv = {"Hello": [0], "world": [1]}
    assert reconstruct_openalex_abstract(inv) == "Hello world"
    assert reconstruct_openalex_abstract({}) is None
    assert reconstruct_openalex_abstract(None) is None


if __name__ == "__main__":
    test_normalize_doi()
    test_reconstruct_openalex_abstract()
    print("OK: corpus_utils tests passed")
