"""URL selection + manifest helpers for fetch_oa_fulltext.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from fetch_oa_fulltext import (  # noqa: E402
    apply_overrides_to_jsonl,
    best_oa_url,
    load_manifest,
    load_url_overrides,
    rank_oa_candidates,
    score_oa_location,
    upsert_manifest,
    url_embeds_doi,
    write_manifest,
)


def test_load_manifest_dedupes_by_doi(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "doi": "10.1063/1.1316015",
                        "status": "resolved",
                        "url": "https://example.com/old.pdf",
                    }
                ),
                json.dumps(
                    {
                        "doi": "10.1063/1.1316015",
                        "status": "resolved",
                        "url": "https://example.com/new.pdf",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    entries = load_manifest(manifest)
    assert len(entries) == 1
    assert entries["10.1063/1.1316015"]["url"] == "https://example.com/new.pdf"


def test_write_manifest_one_row_per_doi(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.jsonl"
    entries: dict = {}
    upsert_manifest(entries, {"doi": "10.1038/75556", "status": "resolved", "url": "https://a.example"})
    upsert_manifest(entries, {"doi": "10.1063/1.1316015", "status": "resolved", "url": "https://b.example"})
    upsert_manifest(entries, {"doi": "10.1038/75556", "status": "resolved", "url": "https://a2.example"})

    write_manifest(entries, manifest)

    lines = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 2
    dois = {line["doi"] for line in lines}
    assert dois == {"10.1038/75556", "10.1063/1.1316015"}
    by_doi = {line["doi"]: line for line in lines}
    assert by_doi["10.1038/75556"]["url"] == "https://a2.example"


def test_reject_untrusted_repo_without_doi() -> None:
    loc = {
        "host_type": "repository",
        "url": "https://repositorio.unal.edu.co/handle/unal/81108",
    }
    assert score_oa_location(loc, "10.1287/mnsc.46.2.186.11926") is None


def test_accept_pmc_without_doi_in_path() -> None:
    loc = {
        "host_type": "repository",
        "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/3037419",
    }
    scored = score_oa_location(loc, "10.1038/75556")
    assert scored is not None
    assert "pmc/articles" in scored[1]


def test_prefer_publisher_doi_url_over_mismatched_repo() -> None:
    payload = {
        "is_oa": True,
        "best_oa_location": {
            "host_type": "repository",
            "url": "https://repositorio.unal.edu.co/handle/unal/81108",
        },
        "oa_locations": [
            {
                "host_type": "repository",
                "url": "https://repositorio.unal.edu.co/handle/unal/81108",
            },
            {
                "host_type": "publisher",
                "url": "https://pubsonline.informs.org/doi/pdf/10.1287/mnsc.46.2.186.11926",
                "url_for_pdf": "https://pubsonline.informs.org/doi/pdf/10.1287/mnsc.46.2.186.11926",
            },
        ],
    }
    picked = best_oa_url(payload, "10.1287/mnsc.46.2.186.11926")
    assert picked is not None
    url, meta = picked
    assert "pubsonline.informs.org" in url
    assert meta["selection"] == "scored_oa_location"
    assert meta["rejected_mismatch_locations"] >= 1


def test_unal_only_payload_returns_none() -> None:
    payload = {
        "is_oa": True,
        "best_oa_location": {
            "host_type": "repository",
            "url": "https://repositorio.unal.edu.co/handle/unal/81108",
            "url_for_landing_page": "https://repositorio.unal.edu.co/handle/unal/81108",
        },
        "oa_locations": [
            {
                "host_type": "repository",
                "url": "https://repositorio.unal.edu.co/handle/unal/81108",
            }
        ],
    }
    assert best_oa_url(payload, "10.1287/mnsc.46.2.186.11926") is None


def test_prefer_pmc_over_publisher_when_both_present() -> None:
    payload = {
        "is_oa": True,
        "best_oa_location": {
            "host_type": "publisher",
            "url": "https://www.nature.com/articles/nature12345",
            "url_for_pdf": "https://www.nature.com/articles/nature12345.pdf",
        },
        "oa_locations": [
            {
                "host_type": "repository",
                "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1234567/",
            },
            {
                "host_type": "publisher",
                "url": "https://www.nature.com/articles/nature12345.pdf",
                "url_for_pdf": "https://www.nature.com/articles/nature12345.pdf",
            },
        ],
    }
    ranked = rank_oa_candidates(payload, "10.1038/nature12345")
    assert ranked
    top_url = ranked[0][1]
    assert "pmc/articles" in top_url


def test_operator_override_wins() -> None:
    payload = {
        "is_oa": True,
        "best_oa_location": {
            "host_type": "repository",
            "url": "https://repositorio.unal.edu.co/handle/unal/81108",
        },
        "oa_locations": [],
    }
    overrides = {
        "10.1287/mnsc.46.2.186.11926": {
            "url": "https://pubsonline.informs.org/doi/10.1287/mnsc.46.2.186.11926",
            "host_type": "publisher",
            "is_oa": False,
            "reason": "mismatched UNAL handle",
        }
    }
    picked = best_oa_url(payload, "10.1287/mnsc.46.2.186.11926", overrides=overrides)
    assert picked is not None
    url, meta = picked
    assert url.startswith("https://pubsonline.informs.org/")
    assert meta["selection"] == "operator_override"


def test_url_embeds_doi() -> None:
    doi = "10.1287/mnsc.46.2.186.11926"
    assert url_embeds_doi(
        "https://pubsonline.informs.org/doi/10.1287/mnsc.46.2.186.11926", doi
    )
    assert not url_embeds_doi("https://repositorio.unal.edu.co/handle/unal/81108", doi)


def test_apply_overrides_rewrites_pilot_row(tmp_path: Path) -> None:
    pilot = tmp_path / "pilot.jsonl"
    pilot.write_text(
        json.dumps(
            {
                "id": "oa-old",
                "doi": "10.1287/mnsc.46.2.186.11926",
                "url": "https://repositorio.unal.edu.co/handle/unal/81108",
                "meta": {"host_type": "repository", "is_oa": True},
                "output": {"notes": "old"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    overrides = {
        "10.1287/mnsc.46.2.186.11926": {
            "url": "https://pubsonline.informs.org/doi/10.1287/mnsc.46.2.186.11926",
            "host_type": "publisher",
            "is_oa": False,
            "reason": "mismatched UNAL handle",
        }
    }
    manifest: dict = {}
    n = apply_overrides_to_jsonl(pilot, overrides, manifest)
    assert n == 1
    row = json.loads(pilot.read_text(encoding="utf-8").strip())
    assert row["url"].startswith("https://pubsonline.informs.org/")
    assert row["meta"]["url_selection"] == "operator_override"
    assert row["meta"]["is_oa"] is False
    assert manifest["10.1287/mnsc.46.2.186.11926"]["url"].startswith(
        "https://pubsonline.informs.org/"
    )


def test_load_url_overrides_skips_comments(tmp_path: Path) -> None:
    path = tmp_path / "overrides.json"
    path.write_text(
        json.dumps(
            {
                "_comment": "ignore",
                "10.1287/mnsc.46.2.186.11926": {
                    "url": "https://pubsonline.informs.org/doi/10.1287/mnsc.46.2.186.11926"
                },
            }
        ),
        encoding="utf-8",
    )
    loaded = load_url_overrides(path)
    assert "10.1287/mnsc.46.2.186.11926" in loaded
    assert "_comment" not in loaded
