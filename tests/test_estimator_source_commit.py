#!/usr/bin/env python3
"""Regression tests for estimator_exact source-commit provenance fallback."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ESTIMATOR_EXACT = ROOT / "estimator_exact"
QUERY = [
    str(ESTIMATOR_EXACT),
    "--r",
    "1",
    "--u",
    "0x00000001",
    "--v",
    "0x70070000",
    "--backend",
    "cpp_int",
]
CURRENT_REPOSITORY = "Roki-Xing/cryptomath-2026-problem3-final-submission"
VALID_COMMIT = "0123456789abcdef0123456789abcdef01234567"
VALID_SUBMIT_SHA = "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e"


def run_estimator(cwd: Path, out: Path | None = None) -> subprocess.CompletedProcess[str]:
    if out is None:
        out = cwd / "artifact.json"
    return subprocess.run(
        [*QUERY, "--out", str(out)],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def read_artifact(cwd: Path) -> dict[str, object]:
    return json.loads((cwd / "artifact.json").read_text(encoding="utf-8"))


def legal_metadata(commit: str = VALID_COMMIT) -> str:
    return "\n".join(
        [
            f"repository: {CURRENT_REPOSITORY}",
            "release_ref: test-package",
            f"release_commit: {commit}",
            "package_generated_at_utc: 2026-06-25T00:00:00Z",
            "submit_source_commit: fedcba9876543210fedcba9876543210fedcba98",
            f"submit_sha256: {VALID_SUBMIT_SHA}",
            "",
        ]
    )


def test_git_checkout_uses_git_head() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "artifact.json"
        result = run_estimator(ROOT, out)
        assert result.returncode == 0, result.stderr
        assert json.loads(out.read_text(encoding="utf-8"))["source_commit"] == head


def test_no_git_uses_structured_package_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        (cwd / "PACKAGE_SOURCE_COMMIT.txt").write_text(legal_metadata(), encoding="utf-8")
        result = run_estimator(cwd)
        assert result.returncode == 0, result.stderr
        assert read_artifact(cwd)["source_commit"] == VALID_COMMIT


def test_malformed_package_metadata_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        (cwd / "PACKAGE_SOURCE_COMMIT.txt").write_text(
            legal_metadata("not-a-commit"),
            encoding="utf-8",
        )
        result = run_estimator(cwd)
        assert result.returncode != 0
        assert "source commit is unavailable" in result.stderr
        assert not (cwd / "artifact.json").exists()


def test_stale_old_repository_metadata_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        (cwd / "PACKAGE_SOURCE_COMMIT.txt").write_text(
            "\n".join(
                [
                    "Repository:",
                    "Roki-Xing/password-final-submit-20260506_e38b20a_professional",
                    "",
                    "Source commit:",
                    VALID_COMMIT,
                    "",
                ]
            ),
            encoding="utf-8",
        )
        result = run_estimator(cwd)
        assert result.returncode != 0
        assert "source commit is unavailable" in result.stderr
        assert not (cwd / "artifact.json").exists()


def test_missing_package_metadata_rejected_without_git() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        result = run_estimator(cwd)
        assert result.returncode != 0
        assert "source commit is unavailable" in result.stderr
        assert not (cwd / "artifact.json").exists()


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    test_git_checkout_uses_git_head()
    test_no_git_uses_structured_package_metadata()
    test_malformed_package_metadata_rejected()
    test_stale_old_repository_metadata_rejected()
    test_missing_package_metadata_rejected_without_git()
    print("estimator source commit tests passed")
