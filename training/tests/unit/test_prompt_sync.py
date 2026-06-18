"""Cross-repo guard: Python train prompt must match Nassila grounding-llm.ts golden."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TRAINING_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRAINING_ROOT / "scripts"))

from validate_dataset import build_grounding_user_prompt  # noqa: E402

FIXTURE_PASSAGE = (
    "The intervention worked equally well in adults and children (Daniels, 2024)."
)
FIXTURE_EXCERPT = (
    "Efficacy was demonstrated in adults; pediatric data were not collected."
)
FIXTURE_META = {"label": "abstract"}
GOLDEN_PATH = TRAINING_ROOT / "fixtures" / "grounding_prompt_golden.txt"
# Keep byte-identical to Nassila tests/fixtures/grounding_prompt_golden.txt


def test_grounding_user_prompt_matches_golden() -> None:
    golden = GOLDEN_PATH.read_text(encoding="utf-8")
    actual = build_grounding_user_prompt(FIXTURE_PASSAGE, FIXTURE_EXCERPT, FIXTURE_META)
    assert actual == golden, (
        "build_grounding_user_prompt drifted from fixtures/grounding_prompt_golden.txt; "
        "update both validate_dataset.py and Nassila grounding-llm.ts in lockstep."
    )


def test_scope_silence_rule_present() -> None:
    prompt = build_grounding_user_prompt(FIXTURE_PASSAGE, FIXTURE_EXCERPT, FIXTURE_META)
    assert "Scope-silence rule" in prompt
    assert "never contradicted" in prompt


def test_no_blanket_never_supported_on_compound() -> None:
    prompt = build_grounding_user_prompt(FIXTURE_PASSAGE, FIXTURE_EXCERPT, FIXTURE_META)
    assert "never supported when the passage bundles multiple claims" not in prompt
