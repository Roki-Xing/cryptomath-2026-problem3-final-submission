#!/usr/bin/env python3
"""Verify release-staging metadata generation and staged no-git behavior."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_release_package.py"
HEAD = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
SUBMIT_SHA = hashlib.sha256((ROOT / "submit.txt").read_bytes()).hexdigest()
SUBMIT_SOURCE_COMMIT = "b4fd4061877660a4eefbd2ea88e8170a708e2da1"


def restore_post_release_targets() -> None:
    subprocess.run(
        [
            "make",
            "-j2",
            "estimator_exact",
            "enumerate_r1_positive",
            "exact_batch_current",
            "exact_batch_grouped_u",
            "exact_batch_grouped_uv",
            "score",
        ],
        cwd=ROOT,
        check=True,
    )


def test_release_staging_builds_metadata_and_binary() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "staging"
        env = dict(os.environ)
        env["SOURCE_DATE_EPOCH"] = "1760000000"
        subprocess.run(
            [
                "python3",
                "-X",
                "utf8",
                str(SCRIPT),
                "--out-dir",
                str(out),
                "--repository",
                "Roki-Xing/cryptomath-2026-problem3-final-submission",
                "--release-ref",
                "refs/tags/test-release",
                "--release-commit",
                HEAD,
                "--submit-source-commit",
                SUBMIT_SOURCE_COMMIT,
                "--submit-sha256",
                SUBMIT_SHA,
            ],
            cwd=ROOT,
            env=env,
            check=True,
        )
        manifest = json.loads((out / "RELEASE_STAGING_MANIFEST.json").read_text(encoding="utf-8"))
        metadata = (out / "PACKAGE_SOURCE_COMMIT.txt").read_text(encoding="utf-8")
        assert manifest["release_commit"] == HEAD
        assert "schema: package-source-metadata-v1" in metadata
        assert f"release_commit: {HEAD}" in metadata
        assert (out / "estimator_exact").exists()


def test_nonempty_release_staging_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "staging"
        out.mkdir()
        (out / "placeholder.txt").write_text("x", encoding="utf-8")
        result = subprocess.run(
            [
                "python3",
                "-X",
                "utf8",
                str(SCRIPT),
                "--out-dir",
                str(out),
                "--repository",
                "Roki-Xing/cryptomath-2026-problem3-final-submission",
                "--release-ref",
                "refs/tags/test-release",
                "--release-commit",
                HEAD,
                "--package-generated-at-utc",
                "2026-06-25T00:00:00Z",
                "--submit-source-commit",
                SUBMIT_SOURCE_COMMIT,
                "--submit-sha256",
                SUBMIT_SHA,
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        assert result.returncode != 0
        assert "out-dir must be empty" in result.stderr


def test_mismatched_staged_metadata_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "staging"
        env = dict(os.environ)
        env["SOURCE_DATE_EPOCH"] = "1760000000"
        subprocess.run(
            [
                "python3",
                "-X",
                "utf8",
                str(SCRIPT),
                "--out-dir",
                str(out),
                "--repository",
                "Roki-Xing/cryptomath-2026-problem3-final-submission",
                "--release-ref",
                "refs/tags/test-release",
                "--release-commit",
                HEAD,
                "--submit-source-commit",
                SUBMIT_SOURCE_COMMIT,
                "--submit-sha256",
                SUBMIT_SHA,
            ],
            cwd=ROOT,
            env=env,
            check=True,
        )
        tampered = (out / "PACKAGE_SOURCE_COMMIT.txt").read_text(encoding="utf-8").replace(
            f"release_commit: {HEAD}",
            "release_commit: 0123456789abcdef0123456789abcdef01234567",
        )
        (out / "PACKAGE_SOURCE_COMMIT.txt").write_text(tampered, encoding="utf-8")
        result = subprocess.run(
            [
                str(out / "estimator_exact"),
                "--r",
                "1",
                "--u",
                "0x00000001",
                "--v",
                "0x70070000",
                "--backend",
                "cpp_int",
                "--out",
                str(out / "artifact.json"),
            ],
            cwd=out,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        assert result.returncode != 0
        assert "mismatch" in result.stderr


if __name__ == "__main__":
    try:
        test_release_staging_builds_metadata_and_binary()
        test_nonempty_release_staging_rejected()
        test_mismatched_staged_metadata_is_rejected()
    finally:
        restore_post_release_targets()
    print("release package metadata tests passed")
