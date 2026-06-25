#!/usr/bin/env python3
"""Generate structured package source metadata for repository archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CURRENT_REPOSITORY = "Roki-Xing/cryptomath-2026-problem3-final-submission"
COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}([0-9a-fA-F]{24})?$")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def git_text(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def default_release_ref() -> str:
    ref = git_text("rev-parse", "--abbrev-ref", "HEAD")
    return "HEAD" if ref == "HEAD" else ref


def default_release_commit() -> str:
    return git_text("rev-parse", "HEAD")


def submit_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def default_submit_source_commit() -> str:
    baseline = ROOT / "experiments" / "frozen" / "BASELINE.json"
    if baseline.exists():
        data = json.loads(baseline.read_text(encoding="utf-8"))
        value = data.get("source", {}).get("submit_source_commit", "")
        if value:
            return str(value)
    return default_release_commit()


def require_commit(value: str, field: str) -> str:
    if not COMMIT_RE.fullmatch(value):
        raise SystemExit(f"{field} must be a 40- or 64-hex commit/hash")
    return value.lower()


def require_sha256(value: str, field: str) -> str:
    if not SHA256_RE.fullmatch(value):
        raise SystemExit(f"{field} must be a 64-hex SHA-256 digest")
    return value.lower()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=CURRENT_REPOSITORY)
    parser.add_argument("--release-ref", default=None)
    parser.add_argument("--release-commit", default=None)
    parser.add_argument("--package-generated-at-utc", default=None)
    parser.add_argument("--submit-source-commit", default=None)
    parser.add_argument("--submit", default=str(ROOT / "submit.txt"))
    parser.add_argument("--out", default="-")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    submit_path = Path(args.submit)
    if not submit_path.is_absolute():
        submit_path = ROOT / submit_path

    repository = args.repository.strip()
    if repository != CURRENT_REPOSITORY and repository != f"https://github.com/{CURRENT_REPOSITORY}":
        raise SystemExit(f"repository must be {CURRENT_REPOSITORY}")

    release_ref = args.release_ref or default_release_ref()
    release_commit = require_commit(args.release_commit or default_release_commit(), "release_commit")
    generated_at = args.package_generated_at_utc or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    submit_source_commit = require_commit(
        args.submit_source_commit or default_submit_source_commit(),
        "submit_source_commit",
    )
    submit_digest = require_sha256(submit_sha256(submit_path), "submit_sha256")

    output = "\n".join(
        [
            f"repository: {repository}",
            f"release_ref: {release_ref}",
            f"release_commit: {release_commit}",
            f"package_generated_at_utc: {generated_at}",
            f"submit_source_commit: {submit_source_commit}",
            f"submit_sha256: {submit_digest}",
            "",
        ]
    )

    if args.out == "-":
        print(output, end="")
    else:
        Path(args.out).write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
