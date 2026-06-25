#!/usr/bin/env python3
"""Verify package source metadata generation."""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_package_source_commit.py"
CURRENT_REPOSITORY = "Roki-Xing/cryptomath-2026-problem3-final-submission"
RELEASE_COMMIT = "0123456789abcdef0123456789abcdef01234567"
SUBMIT_SOURCE_COMMIT = "fedcba9876543210fedcba9876543210fedcba98"


def parse_metadata(text: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        key, value = line.split(":", 1)
        rows[key.strip()] = value.strip()
    return rows


def test_generator_schema_and_values() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "PACKAGE_SOURCE_COMMIT.txt"
        subprocess.run(
            [
                "python3",
                "-X",
                "utf8",
                str(SCRIPT),
                "--release-ref",
                "test-release",
                "--release-commit",
                RELEASE_COMMIT,
                "--package-generated-at-utc",
                "2026-06-25T00:00:00Z",
                "--submit-source-commit",
                SUBMIT_SOURCE_COMMIT,
                "--out",
                str(out),
            ],
            cwd=ROOT,
            check=True,
        )
        rows = parse_metadata(out.read_text(encoding="utf-8"))

    assert rows == {
        "repository": CURRENT_REPOSITORY,
        "release_ref": "test-release",
        "release_commit": RELEASE_COMMIT,
        "package_generated_at_utc": "2026-06-25T00:00:00Z",
        "submit_source_commit": SUBMIT_SOURCE_COMMIT,
        "submit_sha256": hashlib.sha256((ROOT / "submit.txt").read_bytes()).hexdigest(),
    }


def test_generator_rejects_old_repository() -> None:
    result = subprocess.run(
        [
            "python3",
            "-X",
            "utf8",
            str(SCRIPT),
            "--repository",
            "Roki-Xing/password-final-submit-20260506_e38b20a_professional",
            "--release-commit",
            RELEASE_COMMIT,
            "--submit-source-commit",
            SUBMIT_SOURCE_COMMIT,
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode != 0
    assert "repository must be" in result.stderr


if __name__ == "__main__":
    test_generator_schema_and_values()
    test_generator_rejects_old_repository()
    print("package source commit generator tests passed")
