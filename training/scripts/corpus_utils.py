"""Shared helpers for Nassila paper corpus pipeline (Phase 1.5)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

TRAINING_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = TRAINING_DIR / "data"
CACHE_DIR = TRAINING_DIR / "cache"


def normalize_doi(raw: str | None) -> str | None:
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if s.startswith(prefix):
            s = s[len(prefix) :]
    s = s.strip()
    return s or None


def normalize_authors(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    out: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, dict):
            name = item.get("name") or item.get("display_name")
            if isinstance(name, str) and name.strip():
                out.append(name.strip())
    return out


def first_author_surname(authors: list[str]) -> str:
    if not authors:
        return "Unknown"
    first = authors[0]
    if "," in first:
        return first.split(",", 1)[0].strip()
    parts = first.split()
    return parts[-1] if parts else "Unknown"


def corpus_id_from_uid(uid: str | None, doi: str | None, source: str) -> str:
    if uid and isinstance(uid, str):
        clean = uid.replace(":", "_").lower()
        return clean
    if doi:
        return f"{source}_{hashlib.sha256(doi.encode()).hexdigest()[:12]}"
    return f"{source}_{hashlib.sha256(repr(uid).encode()).hexdigest()[:12]}"


def reconstruct_openalex_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Mirror src/engine/resolver/openalex.ts reconstructAbstract."""
    if not inverted_index:
        return None
    words: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        for pos in positions:
            if isinstance(pos, int):
                words.append((pos, word))
    if not words:
        return None
    words.sort(key=lambda x: x[0])
    return " ".join(w for _, w in words)


def crossref_abstract(message: dict[str, Any]) -> str | None:
    abstract = message.get("abstract")
    if isinstance(abstract, str) and abstract.strip():
        return re.sub(r"<[^>]+>", "", abstract).strip()
    return None


def load_json_array(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig")
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in {path}")
    return [r for r in data if isinstance(r, dict)]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def doi_cache_path(doi: str) -> Path:
    h = hashlib.sha256(doi.encode()).hexdigest()[:16]
    return CACHE_DIR / "api" / f"{h}.json"
