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
HEAD = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip().lower()
OTHER_40 = "0123456789abcdef0123456789abcdef01234567"
OTHER_64 = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
SUBMIT_SHA = hashlib.sha256((ROOT / "submit.txt").read_bytes()).hexdigest()
SUBMIT_SOURCE_COMMIT = "b4fd4061877660a4eefbd2ea88e8170a708e2da1"
VALID_TIMESTAMPS = [
    "2026-06-25T00:00:00Z",
    "2026-12-31T23:59:59Z",
    "2024-02-29T23:59:59Z",
    "2000-02-29T00:00:00Z",
    "0001-01-01T00:00:00Z",
    "9999-12-31T23:59:59Z",
]
INVALID_TIMESTAMPS = [
    "2026-13-01T00:00:00Z",
    "2026-00-01T00:00:00Z",
    "2026-02-30T00:00:00Z",
    "2026-04-31T00:00:00Z",
    "2026-06-25T24:00:00Z",
    "2026-06-25T23:60:00Z",
    "2026-06-25T23:59:60Z",
    "2026-06-25T23:59:59",
    "2026-06-25 23:59:59Z",
    "0000-01-01T00:00:00Z",
    "2100-02-29T00:00:00Z",
    "2026-06-25T23:59:59+00:00",
    "2026-06-25T23:59:59.000Z",
]


def restore_post_release_targets() -> None:
    subprocess.run(
        [
            "make",
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


def run_builder(
    out_dir: Path,
    *,
    release_commit: str,
    package_generated_at_utc: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    if package_generated_at_utc is None:
        env["SOURCE_DATE_EPOCH"] = "1760000000"
    command = [
        "python3",
        "-X",
        "utf8",
        str(SCRIPT),
        "--out-dir",
        str(out_dir),
        "--repository",
        "Roki-Xing/cryptomath-2026-problem3-final-submission",
        "--release-ref",
        "refs/tags/test-release",
        "--release-commit",
        release_commit,
        "--submit-source-commit",
        SUBMIT_SOURCE_COMMIT,
        "--submit-sha256",
        SUBMIT_SHA,
    ]
    if package_generated_at_utc is not None:
        command.extend(["--package-generated-at-utc", package_generated_at_utc])
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_release_staging_builds_metadata_and_binary() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "staging"
        result = run_builder(out, release_commit=HEAD)
        assert result.returncode == 0, result.stderr
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
        result = run_builder(out, release_commit=HEAD, package_generated_at_utc="2026-06-25T00:00:00Z")
        assert result.returncode != 0
        assert "out-dir must be empty" in result.stderr


def test_release_commit_must_match_checkout_head_40() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "staging"
        result = run_builder(out, release_commit=OTHER_40)
        assert result.returncode != 0
        assert f"requested={OTHER_40}" in result.stderr
        assert f"actual_head={HEAD}" in result.stderr
        assert not out.exists()


def test_release_commit_must_match_checkout_head_64() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "staging"
        result = run_builder(out, release_commit=OTHER_64)
        assert result.returncode != 0
        assert f"requested={OTHER_64}" in result.stderr
        assert f"actual_head={HEAD}" in result.stderr
        assert not out.exists()


def test_invalid_rfc3339_timestamps_rejected_by_builder() -> None:
    for timestamp in INVALID_TIMESTAMPS:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "staging"
            result = run_builder(out, release_commit=HEAD, package_generated_at_utc=timestamp)
            assert result.returncode != 0, timestamp
            assert "package_generated_at_utc" in result.stderr


def test_valid_rfc3339_timestamps_accepted_by_builder() -> None:
    for timestamp in VALID_TIMESTAMPS:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "staging"
            result = run_builder(out, release_commit=HEAD, package_generated_at_utc=timestamp)
            assert result.returncode == 0, (timestamp, result.stderr)
            metadata = (out / "PACKAGE_SOURCE_COMMIT.txt").read_text(encoding="utf-8")
            assert f"package_generated_at_utc: {timestamp}" in metadata


def test_mismatched_staged_metadata_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "staging"
        result = run_builder(out, release_commit=HEAD)
        assert result.returncode == 0, result.stderr
        tampered = (out / "PACKAGE_SOURCE_COMMIT.txt").read_text(encoding="utf-8").replace(
            f"release_commit: {HEAD}",
            f"release_commit: {OTHER_40}",
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
        test_release_commit_must_match_checkout_head_40()
        test_release_commit_must_match_checkout_head_64()
        test_invalid_rfc3339_timestamps_rejected_by_builder()
        test_valid_rfc3339_timestamps_accepted_by_builder()
        test_mismatched_staged_metadata_is_rejected()
    finally:
        restore_post_release_targets()
    print("release package metadata tests passed")
