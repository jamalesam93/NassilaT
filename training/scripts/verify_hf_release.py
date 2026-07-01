#!/usr/bin/env python3
"""Compare local Sanad GGUFs to Hugging Face repos (size + SHA256, README checks)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    from huggingface_hub import HfApi
    from huggingface_hub.utils import EntryNotFoundError
except ImportError:
    print("Install huggingface_hub: pip install -r requirements.txt", file=sys.stderr)
    raise SystemExit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_DIR = SCRIPT_DIR.parent

ARMS = {
    "e4b": {
        "repo_id": "QinEmPeRoR93/nassila-sanad-e4b",
        "gguf_name": "nassila-sanad-e4b-q6_k.gguf",
        "checkpoint": "S12",
        "readme_source": TRAINING_DIR / "hf_readmes" / "nassila-sanad-e4b" / "README.md",
        "metrics": ("89.27%", "92.98%", "3.81%"),
        "forbidden_gguf_substrings": ("v1.13",),
    },
    "12b": {
        "repo_id": "QinEmPeRoR93/nassila-sanad-12b",
        "gguf_name": "nassila-sanad-12b-q6_k.gguf",
        "checkpoint": "S14",
        "readme_source": TRAINING_DIR / "hf_readmes" / "nassila-sanad-12b" / "README.md",
        "metrics": ("90.43%", "100%", "2.86%"),
        "forbidden_gguf_substrings": ("v1.13",),
    },
}

FORBIDDEN_GGUF_PATTERNS = ("v1.13",)


def sha256_file(path: Path, chunk: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def resolve_gguf(local_path: Path, expected_name: str) -> Path:
    if local_path.is_file():
        return local_path
    if local_path.is_dir():
        direct = local_path / expected_name
        if direct.is_file():
            return direct
        matches = list(local_path.glob("*.gguf"))
        if len(matches) == 1:
            return matches[0]
        if matches:
            names = ", ".join(m.name for m in matches)
            raise FileNotFoundError(f"Ambiguous GGUF in {local_path}: {names}")
    raise FileNotFoundError(f"Local path not found: {local_path}")


def readme_checks(local_readme: Path, hf_readme: str, metrics: tuple[str, ...]) -> list[str]:
    failures: list[str] = []
    if not local_readme.is_file():
        failures.append(f"missing_local_readme:{local_readme}")
        return failures
    local_text = local_readme.read_text(encoding="utf-8")
    for metric in metrics:
        if metric not in local_text:
            failures.append(f"local_readme_missing_metric:{metric}")
        if metric not in hf_readme:
            failures.append(f"hf_readme_missing_metric:{metric}")
    return failures


def verify_arm(api: HfApi, arm: str, local_path: Path, hash_local: bool) -> dict:
    spec = ARMS[arm]
    gguf_name = spec["gguf_name"]
    repo_id = spec["repo_id"]
    result: dict = {"arm": arm, "repo_id": repo_id, "checkpoint": spec["checkpoint"], "checks": []}

    try:
        gguf = resolve_gguf(local_path, gguf_name)
    except FileNotFoundError as e:
        result["error"] = str(e)
        result["passed"] = False
        return result

    result["local_gguf"] = str(gguf)
    result["local_size"] = gguf.stat().st_size

    info = api.repo_info(repo_id, repo_type="model", files_metadata=True)
    siblings = {s.rfilename: s for s in info.siblings}
    result["remote_files"] = sorted(siblings.keys())

    forbidden_remote = [
        name
        for name in siblings
        if name.endswith(".gguf")
        and name != gguf_name
        and any(p in name.lower() for p in FORBIDDEN_GGUF_PATTERNS)
    ]
    if forbidden_remote:
        result["checks"].append({"check": "no_extra_forbidden_gguf", "passed": False, "detail": forbidden_remote})
    else:
        result["checks"].append({"check": "no_extra_forbidden_gguf", "passed": True})

    if gguf_name not in siblings:
        result["checks"].append({"check": "expected_gguf_on_hf", "passed": False, "detail": gguf_name})
        result["passed"] = False
        return result

    remote = siblings[gguf_name]
    remote_size = remote.size or 0
    remote_sha = None
    if remote.lfs is not None:
        remote_sha = getattr(remote.lfs, "sha256", None)

    size_match = result["local_size"] == remote_size
    result["remote_size"] = remote_size
    result["remote_sha256"] = remote_sha
    result["checks"].append(
        {
            "check": "size_match",
            "passed": size_match,
            "local": result["local_size"],
            "remote": remote_size,
        }
    )

    local_sha = None
    if hash_local:
        print(f"  Hashing {gguf.name} ({result['local_size']:,} bytes)...", flush=True)
        local_sha = sha256_file(gguf)
        result["local_sha256"] = local_sha
        sha_match = remote_sha is not None and local_sha == remote_sha
        result["checks"].append(
            {
                "check": "sha256_match",
                "passed": sha_match,
                "local": local_sha,
                "remote": remote_sha,
            }
        )
    elif remote_sha:
        result["checks"].append(
            {
                "check": "sha256_match",
                "passed": None,
                "detail": "skipped (--no-hash); use default to verify SHA256",
                "remote": remote_sha,
            }
        )

    try:
        hf_readme = api.hf_hub_download(repo_id, "README.md", repo_type="model")
        hf_readme_text = Path(hf_readme).read_text(encoding="utf-8")
    except EntryNotFoundError:
        hf_readme_text = ""
        result["checks"].append({"check": "hf_readme_exists", "passed": False})

    readme_fails = readme_checks(spec["readme_source"], hf_readme_text, spec["metrics"])
    result["checks"].append(
        {
            "check": "readme_metrics",
            "passed": len(readme_fails) == 0,
            "failures": readme_fails,
        }
    )

    result["passed"] = all(
        c.get("passed") is True for c in result["checks"] if c.get("passed") is not None
    ) and not any(c.get("passed") is False for c in result["checks"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify local Sanad GGUFs against Hugging Face")
    parser.add_argument(
        "--e4b-path",
        type=Path,
        default=Path(r"D:\LM_Studio_Models\lmstudio-community\nassila-sanad-e4b-q6_k"),
    )
    parser.add_argument(
        "--path-12b",
        dest="path_12b",
        type=Path,
        default=Path(r"D:\LM_Studio_Models\lmstudio-community\nassila-sanad-12b-q6_k"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=TRAINING_DIR / "outputs" / "hf_release_verify_report.json",
    )
    parser.add_argument(
        "--no-hash",
        action="store_true",
        help="Skip local SHA256 (faster; size-only check)",
    )
    args = parser.parse_args()

    api = HfApi()
    arms = [("e4b", args.e4b_path), ("12b", args.path_12b)]
    results: list[dict] = []

    print("HF release verification")
    for arm, path in arms:
        print(f"\n=== {arm.upper()} ===")
        print(f"  Local: {path}")
        print(f"  Repo:  {ARMS[arm]['repo_id']}")
        row = verify_arm(api, arm, path, hash_local=not args.no_hash)
        results.append(row)
        status = "PASS" if row.get("passed") else "FAIL"
        print(f"  Result: {status}")
        for check in row.get("checks", []):
            mark = "ok" if check.get("passed") is True else ("skip" if check.get("passed") is None else "FAIL")
            print(f"    {check['check']}: {mark}")

    report = {
        "all_passed": all(r.get("passed") for r in results),
        "arms": results,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nReport: {args.report}")
    print("Overall:", "PASS" if report["all_passed"] else "FAIL")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
