#!/usr/bin/env python3
"""Verify strict package-source metadata generation and parser behavior."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts" / "generate_package_source_commit.py"
ESTIMATOR_EXACT = ROOT / "estimator_exact"
CURRENT_REPOSITORY = "Roki-Xing/cryptomath-2026-problem3-final-submission"
VALID_RELEASE_COMMIT = "0123456789abcdef0123456789abcdef01234567"
VALID_SUBMIT_SOURCE_COMMIT = "fedcba9876543210fedcba9876543210fedcba98"
VALID_SUBMIT_SHA = "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e"
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
ROOT_HEAD = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def parse_metadata(text: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        key, value = line.split(":", 1)
        rows[key.strip()] = value.strip()
    return rows


def run_generator(
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "-X", "utf8", str(GENERATOR), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )


def run_estimator(cwd: Path, binary: Path | None = None) -> subprocess.CompletedProcess[str]:
    binary = binary or ESTIMATOR_EXACT
    return subprocess.run(
        [str(binary), *QUERY[1:], "--out", str(cwd / "artifact.json")],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def build_estimator_with_macro(value: str) -> None:
    env = dict(os.environ)
    env["EXTRA_CPPFLAGS"] = f"-DHS_SOURCE_COMMIT=\\\"{value}\\\""
    subprocess.run(["make", "-B", "estimator_exact"], cwd=ROOT, env=env, check=True)


def restore_default_estimator() -> None:
    subprocess.run(["make", "-B", "estimator_exact"], cwd=ROOT, check=True)


def legal_metadata() -> str:
    return "\n".join(
        [
            "schema: package-source-metadata-v1",
            f"repository: {CURRENT_REPOSITORY}",
            "release_ref: release/test",
            f"release_commit: {VALID_RELEASE_COMMIT}",
            "package_generated_at_utc: 2026-06-25T00:00:00Z",
            f"submit_source_commit: {VALID_SUBMIT_SOURCE_COMMIT}",
            f"submit_sha256: {VALID_SUBMIT_SHA}",
            "",
        ]
    )


def assert_failure(text: str, expected: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        (cwd / "PACKAGE_SOURCE_COMMIT.txt").write_text(text, encoding="utf-8")
        result = run_estimator(cwd)
        assert result.returncode != 0
        assert expected in result.stderr


def test_generator_requires_explicit_fields() -> None:
    result = run_generator("--repository", CURRENT_REPOSITORY)
    assert result.returncode != 0


def test_generator_uses_explicit_time_or_source_date_epoch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "PACKAGE_SOURCE_COMMIT.txt"
        env = dict(os.environ)
        env.pop("SOURCE_DATE_EPOCH", None)
        result = run_generator(
            "--repository",
            CURRENT_REPOSITORY,
            "--release-ref",
            "release/test",
            "--release-commit",
            VALID_RELEASE_COMMIT,
            "--submit-source-commit",
            VALID_SUBMIT_SOURCE_COMMIT,
            "--submit-sha256",
            VALID_SUBMIT_SHA,
            "--out",
            str(out),
            env=env,
        )
        assert result.returncode != 0
        assert "package_generated_at_utc" in result.stderr

        env["SOURCE_DATE_EPOCH"] = "1760000000"
        result = run_generator(
            "--repository",
            CURRENT_REPOSITORY,
            "--release-ref",
            "release/test",
            "--release-commit",
            VALID_RELEASE_COMMIT,
            "--submit-source-commit",
            VALID_SUBMIT_SOURCE_COMMIT,
            "--submit-sha256",
            VALID_SUBMIT_SHA,
            "--out",
            str(out),
            env=env,
        )
        assert result.returncode == 0, result.stderr
        rows = parse_metadata(out.read_text(encoding="utf-8"))
        assert rows["schema"] == "package-source-metadata-v1"
        assert rows["repository"] == CURRENT_REPOSITORY


def test_generator_schema_and_values() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "PACKAGE_SOURCE_COMMIT.txt"
        result = run_generator(
            "--repository",
            CURRENT_REPOSITORY,
            "--release-ref",
            "release/test",
            "--release-commit",
            VALID_RELEASE_COMMIT,
            "--package-generated-at-utc",
            "2026-06-25T00:00:00Z",
            "--submit-source-commit",
            VALID_SUBMIT_SOURCE_COMMIT,
            "--submit-sha256",
            VALID_SUBMIT_SHA,
            "--out",
            str(out),
        )
        assert result.returncode == 0, result.stderr
        assert parse_metadata(out.read_text(encoding="utf-8")) == {
            "schema": "package-source-metadata-v1",
            "repository": CURRENT_REPOSITORY,
            "release_ref": "release/test",
            "release_commit": VALID_RELEASE_COMMIT,
            "package_generated_at_utc": "2026-06-25T00:00:00Z",
            "submit_source_commit": VALID_SUBMIT_SOURCE_COMMIT,
            "submit_sha256": VALID_SUBMIT_SHA,
        }


def test_generator_rejects_old_repository() -> None:
    result = run_generator(
        "--repository",
        "Roki-Xing/password-final-submit-20260506_e38b20a_professional",
        "--release-ref",
        "release/test",
        "--release-commit",
        VALID_RELEASE_COMMIT,
        "--package-generated-at-utc",
        "2026-06-25T00:00:00Z",
        "--submit-source-commit",
        VALID_SUBMIT_SOURCE_COMMIT,
        "--submit-sha256",
        VALID_SUBMIT_SHA,
        "--out",
        "/tmp/unused_package_source.txt",
    )
    assert result.returncode != 0
    assert "repository must be exactly" in result.stderr


def test_parser_strict_negative_cases() -> None:
    assert_failure(legal_metadata().replace(f"repository: {CURRENT_REPOSITORY}\n", ""), "invalid PACKAGE_SOURCE_COMMIT")
    assert_failure(legal_metadata().replace(CURRENT_REPOSITORY, ""), "invalid PACKAGE_SOURCE_COMMIT")
    assert_failure(legal_metadata().replace("schema: package-source-metadata-v1\n", ""), "invalid PACKAGE_SOURCE_COMMIT")
    assert_failure(legal_metadata().replace("package-source-metadata-v1", "package-source-metadata-v0"), "invalid PACKAGE_SOURCE_COMMIT")
    assert_failure(legal_metadata().replace("release_ref: release/test", "release_ref: "), "invalid PACKAGE_SOURCE_COMMIT")
    assert_failure(legal_metadata().replace(VALID_RELEASE_COMMIT, "not-a-commit", 1), "invalid PACKAGE_SOURCE_COMMIT")
    assert_failure(legal_metadata().replace(VALID_SUBMIT_SOURCE_COMMIT, "not-a-commit", 1), "invalid PACKAGE_SOURCE_COMMIT")
    assert_failure(legal_metadata().replace("package_generated_at_utc: 2026-06-25T00:00:00Z", "package_generated_at_utc: 2026-06-25 00:00:00"), "invalid PACKAGE_SOURCE_COMMIT")
    assert_failure(legal_metadata().replace(VALID_SUBMIT_SHA, "deadbeef"), "invalid PACKAGE_SOURCE_COMMIT")
    assert_failure(legal_metadata() + "unknown_key: value\n", "invalid PACKAGE_SOURCE_COMMIT")
    assert_failure(
        legal_metadata() + f"release_commit: {VALID_RELEASE_COMMIT}\n",
        "invalid PACKAGE_SOURCE_COMMIT",
    )
    assert_failure(
        "\n".join(
            [
                "Repository:",
                CURRENT_REPOSITORY,
                "",
                "Source commit:",
                VALID_RELEASE_COMMIT,
                "",
            ]
        ),
        "invalid PACKAGE_SOURCE_COMMIT",
    )
    assert_failure(
        "\n".join(
            [
                "schema: package-source-metadata-v1",
                f"repository: {CURRENT_REPOSITORY}",
                f"release_commit: {VALID_RELEASE_COMMIT}",
                "",
            ]
        ),
        "invalid PACKAGE_SOURCE_COMMIT",
    )


def test_git_checkout_uses_git_head() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result = subprocess.run(
        [*QUERY, "--out", str(ROOT / "artifact.json")],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads((ROOT / "artifact.json").read_text(encoding="utf-8"))["source_commit"] == head
    (ROOT / "artifact.json").unlink()


def test_no_git_uses_structured_package_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        shutil.copy2(ESTIMATOR_EXACT, cwd / "estimator_exact")
        (cwd / "PACKAGE_SOURCE_COMMIT.txt").write_text(legal_metadata(), encoding="utf-8")
        result = run_estimator(cwd, cwd / "estimator_exact")
        assert result.returncode == 0, result.stderr
        assert json.loads((cwd / "artifact.json").read_text(encoding="utf-8"))["source_commit"] == VALID_RELEASE_COMMIT


def test_no_git_and_missing_metadata_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        shutil.copy2(ESTIMATOR_EXACT, cwd / "estimator_exact")
        result = run_estimator(cwd, cwd / "estimator_exact")
        assert result.returncode != 0
        assert "cannot determine source commit" in result.stderr


def test_git_and_metadata_mismatch_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        shutil.copy2(ESTIMATOR_EXACT, cwd / "estimator_exact")
        shutil.copy2(ROOT / ".git", cwd / ".git")
        (cwd / "PACKAGE_SOURCE_COMMIT.txt").write_text(legal_metadata(), encoding="utf-8")
        result = run_estimator(cwd, cwd / "estimator_exact")
        assert result.returncode != 0
        assert "git HEAD mismatch with PACKAGE_SOURCE_COMMIT" in result.stderr


def test_valid_build_time_macro_has_priority() -> None:
    build_estimator_with_macro(VALID_RELEASE_COMMIT)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            shutil.copy2(ESTIMATOR_EXACT, cwd / "estimator_exact")
            (cwd / "PACKAGE_SOURCE_COMMIT.txt").write_text(legal_metadata(), encoding="utf-8")
            result = run_estimator(cwd, cwd / "estimator_exact")
            assert result.returncode == 0, result.stderr
            payload = json.loads((cwd / "artifact.json").read_text(encoding="utf-8"))
            assert payload["source_commit"] == VALID_RELEASE_COMMIT
    finally:
        restore_default_estimator()


def test_invalid_build_time_macro_fails_closed() -> None:
    build_estimator_with_macro("not-a-commit")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            shutil.copy2(ESTIMATOR_EXACT, cwd / "estimator_exact")
            result = run_estimator(cwd, cwd / "estimator_exact")
            assert result.returncode != 0
            assert "invalid build-time HS_SOURCE_COMMIT" in result.stderr
    finally:
        restore_default_estimator()


def test_macro_and_metadata_mismatch_is_rejected() -> None:
    build_estimator_with_macro(ROOT_HEAD)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            shutil.copy2(ESTIMATOR_EXACT, cwd / "estimator_exact")
            (cwd / "PACKAGE_SOURCE_COMMIT.txt").write_text(legal_metadata(), encoding="utf-8")
            result = run_estimator(cwd, cwd / "estimator_exact")
            assert result.returncode != 0
            assert "build-time HS_SOURCE_COMMIT mismatch with PACKAGE_SOURCE_COMMIT" in result.stderr
    finally:
        restore_default_estimator()


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    restore_default_estimator()
    test_generator_requires_explicit_fields()
    test_generator_uses_explicit_time_or_source_date_epoch()
    test_generator_schema_and_values()
    test_generator_rejects_old_repository()
    test_parser_strict_negative_cases()
    test_git_checkout_uses_git_head()
    test_no_git_uses_structured_package_metadata()
    test_no_git_and_missing_metadata_fails_closed()
    test_valid_build_time_macro_has_priority()
    test_invalid_build_time_macro_fails_closed()
    test_macro_and_metadata_mismatch_is_rejected()
    print("package source metadata tests passed")
