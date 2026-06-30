#!/usr/bin/env python3
"""Package-safe submission checker for submission_final/source."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path


EXPECTED_SUBMIT_SHA256 = "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e"
EXPECTED_VALID_COUNT = 138338
EXPECTED_TOTAL_SCORE = "105843.622442471292742994"
MANIFEST_FIELDS = [
    "path",
    "round",
    "active_nibbles",
    "generation_command",
    "beam",
    "trans",
    "branch",
    "certified_only",
    "row_count",
    "sha256",
    "used_in_final_submit",
]
REQUIRED_SOURCE_FILES = [
    "Makefile",
    "include/sbox_corr.hpp",
    "include/beam_search.hpp",
    "include/exact.hpp",
    "include/exact_dyadic.hpp",
    "src/sbox_corr.cpp",
    "src/beam_search.cpp",
    "src/exact.cpp",
    "src/exact_cartesian.cpp",
    "src/exact_dyadic.cpp",
    "src/linear_layer.cpp",
    "apps/enumerate_r1_positive.cpp",
    "apps/estimator.cpp",
    "apps/estimator_exact.cpp",
    "apps/exact_batch_current.cpp",
    "apps/exact_batch_grouped_u.cpp",
    "apps/exact_batch_grouped_uv.cpp",
    "apps/exact_batch_mt.cpp",
    "apps/exact_batch_variant_app.hpp",
    "apps/exact_oracle.cpp",
    "apps/recompute_frozen_exact.cpp",
    "apps/reduce_exact_parts.cpp",
    "apps/score.cpp",
    "experiments/build_submit_from_sources.py",
    "experiments/SOURCE_MANIFEST.csv",
]


def require(condition: bool, message: str) -> None:
    """Raise an assertion-style error for package-safe checks."""
    if not condition:
        raise AssertionError(message)


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], cwd: Path) -> str:
    """Run a subprocess and return stdout, failing closed on error."""
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def parse_args() -> argparse.Namespace:
    """Parse package-safe checker arguments."""
    parser = argparse.ArgumentParser(
        description="Check only the runnable final-package submission boundary."
    )
    parser.add_argument("--submit", default="../submit.txt", help="Package-local submit.txt path.")
    parser.add_argument(
        "--source-root",
        default=".",
        help="Package source root that contains Makefile, apps/, include/, src/, and experiments/.",
    )
    parser.add_argument("--expected-submit-sha256", default=EXPECTED_SUBMIT_SHA256)
    parser.add_argument("--expected-valid-count", type=int, default=EXPECTED_VALID_COUNT)
    parser.add_argument("--expected-total-score", default=EXPECTED_TOTAL_SCORE)
    return parser.parse_args()


def verify_required_files(source_root: Path, submit_path: Path) -> None:
    """Verify only the files that are supposed to exist inside final package."""
    require(submit_path.is_file(), f"missing frozen submit file: {submit_path}")
    for rel in REQUIRED_SOURCE_FILES:
        require((source_root / rel).is_file(), f"missing required final-package source file: {rel}")
    for rel in ["include", "src", "apps", "experiments"]:
        require((source_root / rel).is_dir(), f"missing required final-package directory: {rel}")


def load_source_manifest(path: Path) -> list[dict[str, str]]:
    """Load the final-package SOURCE_MANIFEST rows used by rebuild."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        require(
            reader.fieldnames == MANIFEST_FIELDS,
            f"unexpected SOURCE_MANIFEST schema: {reader.fieldnames}",
        )
        rows = [row for row in reader if row.get("used_in_final_submit") == "1"]
    require(rows, "SOURCE_MANIFEST.csv listed no final-submit source CSVs")
    return rows


def verify_source_manifest(source_root: Path) -> None:
    """Check source-manifest paths and recorded SHAs within final package."""
    manifest_path = source_root / "experiments" / "SOURCE_MANIFEST.csv"
    rows = load_source_manifest(manifest_path)
    source_root_resolved = source_root.resolve()
    seen: set[str] = set()
    for row in rows:
        rel = row["path"]
        require(rel not in seen, f"duplicate SOURCE_MANIFEST path: {rel}")
        seen.add(rel)
        require(not os.path.isabs(rel), f"SOURCE_MANIFEST path must be relative: {rel}")
        path = source_root / rel
        require(
            path.resolve().is_relative_to(source_root_resolved),
            f"SOURCE_MANIFEST path escapes source root: {rel}",
        )
        require(path.is_file(), f"SOURCE_MANIFEST target missing: {rel}")
        require(sha256_file(path) == row["sha256"], f"SOURCE_MANIFEST SHA mismatch: {rel}")


def verify_submit_rebuild(
    source_root: Path,
    submit_path: Path,
    expected_submit_sha256: str,
) -> None:
    """Byte-rebuild submit.txt from saved certified source CSVs."""
    with tempfile.TemporaryDirectory() as tmp:
        rebuilt = Path(tmp) / "rebuilt_submission_final.txt"
        run(
            [
                sys.executable,
                "-X",
                "utf8",
                "experiments/build_submit_from_sources.py",
                "--source-submit",
                str(submit_path),
                "--out",
                str(rebuilt),
            ],
            cwd=source_root,
        )
        require(
            rebuilt.read_bytes() == submit_path.read_bytes(),
            "build_submit_from_sources.py did not reproduce submit.txt",
        )
    require(
        sha256_file(submit_path) == expected_submit_sha256,
        "submit.txt SHA no longer matches the frozen final package",
    )


def verify_score_output(
    source_root: Path,
    submit_path: Path,
    expected_valid_count: int,
    expected_total_score: str,
) -> None:
    """Verify score output for the frozen final submit."""
    score_bin = source_root / "score"
    require(score_bin.is_file(), "score executable is missing; build the package source first")
    output = run(
        [str(score_bin), "--dedup", "uv", "--positive-only", str(submit_path)],
        cwd=source_root,
    )
    require(f"valid_count={expected_valid_count}" in output, "score valid_count mismatch")
    require(f"total_score={expected_total_score}" in output, "score total_score mismatch")


def main() -> int:
    """Run the package-safe final submission checks."""
    args = parse_args()
    source_root = Path(args.source_root).resolve()
    submit_arg = Path(args.submit)
    submit_path = submit_arg if submit_arg.is_absolute() else (source_root / submit_arg).resolve()

    verify_required_files(source_root, submit_path)
    verify_source_manifest(source_root)
    verify_submit_rebuild(source_root, submit_path, args.expected_submit_sha256)
    verify_score_output(
        source_root,
        submit_path,
        args.expected_valid_count,
        args.expected_total_score,
    )
    print("submission_final package checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
