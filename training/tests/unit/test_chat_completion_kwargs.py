"""Unit tests for OpenAI chat payload helpers (Nanbeige probe)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lmstudio_smoke_test import chat_completion  # noqa: E402


def test_chat_completion_includes_template_kwargs() -> None:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": '{"claims":[]}'}}]
    }

    with patch("lmstudio_smoke_test.requests.post", return_value=mock_resp) as post:
        chat_completion(
            "http://127.0.0.1:8000",
            "Nanbeige/Nanbeige4.2-3B",
            [{"role": "user", "content": "hi"}],
            chat_template_kwargs={"enable_thinking": False},
        )

    payload = post.call_args.kwargs["json"]
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}


def test_chat_completion_omits_template_kwargs_by_default() -> None:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "ok"}}]
    }

    with patch("lmstudio_smoke_test.requests.post", return_value=mock_resp) as post:
        chat_completion(
            "http://127.0.0.1:1234",
            "google/gemma-4-e4b",
            [{"role": "user", "content": "hi"}],
        )

    payload = post.call_args.kwargs["json"]
    assert "chat_template_kwargs" not in payload
