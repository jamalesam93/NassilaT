"""
Lightweight JSON repair for model outputs.

Targets the most common failure modes seen with stock Gemma 4 E4B Q6_K on the
Nassila L3 grounding task. Order of operations matters; keep transforms minimal
to avoid silently changing semantics.

Repairs covered:
1. Strip markdown code fences (```json ... ```)
2. Slice to the outermost {...} object (mirrors parseGroundingJson)
3. Remove TypeScript-style optional markers on keys ("foo"?: -> "foo":)
4. Remove trailing commas before ] or }
5. Fix brace/bracket ordering before overallVerdict (premature root close, unclosed rationale array)
6. Strip leading/trailing whitespace

Usage:
    repaired = repair_json_text(raw)
    parsed = json.loads(repaired)
"""

from __future__ import annotations

import json
import re
from typing import Any


_FENCE_RE = re.compile(r"```(?:json)?\s*", re.IGNORECASE)
_OPTIONAL_KEY_RE = re.compile(r'("\w[\w\-]*")\s*\?\s*:')
_TRAILING_COMMA_RE = re.compile(r",\s*([\]}])")
# Model closed the root object after claims: ..."]}]}, "overallVerdict"
_PREMATURE_ROOT_CLOSE_RE = re.compile(r'"\]\}\}\],\s*"overallVerdict"')
# Model closed claim before rationale array: ..."text"}], "overallVerdict"
_UNCLOSED_RATIONALE_ARRAY_RE = re.compile(r"\"\}\],\s*\"overallVerdict\"")


def strip_code_fences(text: str) -> str:
    return _FENCE_RE.sub("", text).replace("```", "")


def slice_outer_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return text
    return text[start : end + 1]


def remove_optional_key_markers(text: str) -> str:
    """Convert "foo"?: value into "foo": value."""
    return _OPTIONAL_KEY_RE.sub(r"\1:", text)


def remove_trailing_commas(text: str) -> str:
    """Strip ",]" and ",}" patterns (single or multi-line)."""
    prev = None
    out = text
    while prev != out:
        prev = out
        out = _TRAILING_COMMA_RE.sub(r"\1", out)
    return out


def fix_overall_verdict_brace_errors(text: str) -> str:
    """Fix common brace/bracket ordering mistakes before overallVerdict."""
    out = _PREMATURE_ROOT_CLOSE_RE.sub('"]}], "overallVerdict"', text)
    return _UNCLOSED_RATIONALE_ARRAY_RE.sub('"]}], "overallVerdict"', out)


def repair_json_text(raw: str) -> str:
    """Apply the full repair pipeline. Always returns a string."""
    if not raw:
        return raw
    out = raw.strip()
    out = strip_code_fences(out)
    out = slice_outer_object(out)
    out = remove_optional_key_markers(out)
    out = fix_overall_verdict_brace_errors(out)
    out = remove_trailing_commas(out)
    return out.strip()


def parse_strict_json(raw: str) -> tuple[bool, Any, str | None]:
    """Parse without repair. Validates root object and claims array."""
    sliced = slice_outer_object(strip_code_fences(raw or "").strip())
    if not sliced:
        return False, None, "No JSON object"
    try:
        parsed = json.loads(sliced)
    except json.JSONDecodeError as e:
        return False, None, e.msg
    if not isinstance(parsed, dict):
        return False, None, "JSON root not an object"
    if not isinstance(parsed.get("claims"), list):
        return False, None, "Missing claims array"
    return True, parsed, None


def try_parse_first_object(raw: str) -> tuple[bool, Any, str | None]:
    """If the model appended junk after a valid object, parse the first one only."""
    text = strip_code_fences(raw or "").strip()
    start = text.find("{")
    if start == -1:
        return False, None, "No JSON object"
    try:
        parsed, _end = json.JSONDecoder().raw_decode(text, start)
    except json.JSONDecodeError as e:
        return False, None, e.msg
    if not isinstance(parsed, dict):
        return False, None, "JSON root not an object"
    if not isinstance(parsed.get("claims"), list):
        return False, None, "Missing claims array"
    return True, parsed, None


def try_parse_with_repair(raw: str) -> tuple[bool, Any, str | None, bool]:
    """
    Returns (ok, parsed, error_message, repaired_used).

    Tries strict parse first to preserve "raw OK" stats. Falls back to repair,
    then to first-object extraction when extra trailing text breaks strict parse.
    """
    ok, parsed, err = parse_strict_json(raw)
    if ok:
        return True, parsed, None, False

    repaired = repair_json_text(raw or "")
    if repaired:
        try:
            parsed = json.loads(repaired)
            if isinstance(parsed, dict) and isinstance(parsed.get("claims"), list):
                return True, parsed, None, True
        except json.JSONDecodeError as e:
            if e.msg != "Extra data":
                err = f"Invalid JSON after repair: {e.msg}"
            # fall through for Extra data / try first object

    ok, parsed, first_err = try_parse_first_object(repair_json_text(raw or ""))
    if ok:
        return True, parsed, None, True

    if not repaired:
        return False, None, err or "Empty after repair", True
    return False, None, err or first_err or "Invalid JSON after repair", True
