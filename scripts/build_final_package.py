#!/usr/bin/env python3
"""Build the final competition package release candidate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "submission_final"
ARCHIVE_PATH = ROOT / "submission_final.zip"
FINAL_PACKAGE_READY = "FINAL_PACKAGE_RELEASE_CANDIDATE_READY"
FINAL_PACKAGE_PENDING = "FINAL_PACKAGE_PREFLIGHT_PENDING"
PACKAGE_MANIFEST = ROOT / "PACKAGE_MANIFEST.md"
ROOT_SHA256SUMS = ROOT / "SHA256SUMS.txt"
REPOSITORY = "Roki-Xing/cryptomath-2026-problem3-final-submission"
SUBMIT_SHA = "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e"
VALID_COUNT = "138338"
TOTAL_SCORE = "105843.622442471292742994"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
PDF_PREFLIGHT = ROOT / "参赛论文" / "PDF_PREFLIGHT.md"
FIGURE_PREFLIGHT = ROOT / "参赛论文" / "FIGURE_MANUSCRIPT_PREFLIGHT.md"
ROOT_EVIDENCE_SCOPE = ROOT / "docs" / "EVIDENCE_SCOPE.md"
PACKAGE_SOURCE_APP_FILES = [
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
]
EXCLUDED_SOURCE_HELPERS = [
    "source/apps/search_candidates.cpp",
    "source/apps/candidate_miner_approx.cpp",
]


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for a file.

    Args:
        path: File to hash.

    Returns:
        Hexadecimal SHA-256 digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(args: list[str]) -> str:
    """Run a git command and return stripped stdout.

    Args:
        args: Git arguments after the ``git`` executable.

    Returns:
        Stripped command stdout.
    """
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def extract_status(path: Path) -> str:
    """Extract the Markdown status token from a preflight file."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Status: `") and line.endswith("`."):
            return line[len("Status: `") : -2]
    raise SystemExit(f"missing status line in {path}")


def final_package_status() -> tuple[str, str, str]:
    """Derive package readiness from the current preflight files."""
    pdf_status = extract_status(PDF_PREFLIGHT)
    figure_status = extract_status(FIGURE_PREFLIGHT)
    if (
        pdf_status == "FINAL_PACKAGE_PREFLIGHT_PASSED"
        and figure_status == "FINAL_PACKAGE_PREFLIGHT_PASSED"
    ):
        return FINAL_PACKAGE_READY, pdf_status, figure_status
    return FINAL_PACKAGE_PENDING, pdf_status, figure_status


def package_source_makefile() -> str:
    """Return the package-safe Makefile content for ``submission_final/source``."""
    return "\n".join(
        [
            "CXX ?= g++",
            "CXXFLAGS ?= -O3 -std=c++17 -Wall -Wextra -pedantic -pthread",
            "CPPFLAGS := -Iinclude $(EXTRA_CPPFLAGS)",
            "",
            "BUILD_DIR := build",
            "APPROX_OBJS := $(BUILD_DIR)/sbox_corr.o $(BUILD_DIR)/linear_layer.o $(BUILD_DIR)/beam_search.o",
            "EXACT_OBJS := $(APPROX_OBJS) $(BUILD_DIR)/exact.o",
            "EXACT_DYADIC_OBJS := $(BUILD_DIR)/sbox_corr.o $(BUILD_DIR)/linear_layer.o \\",
            "\t$(BUILD_DIR)/exact_cartesian.o $(BUILD_DIR)/exact_dyadic.o",
            "",
            ".PHONY: all clean test",
            "",
            "# Package-safe target set: final rebuild, scoring, exact-way2, and bounded way-1 validation tools only.",
            "# Historical candidate-discovery helpers are intentionally excluded from the final competition package.",
            "all: estimator estimator_exact recompute_frozen_exact exact_oracle exact_batch_mt exact_batch_current exact_batch_grouped_u exact_batch_grouped_uv reduce_exact_parts enumerate_r1_positive score",
            "",
            "$(BUILD_DIR):",
            "\tmkdir -p $(BUILD_DIR)",
            "",
            "$(BUILD_DIR)/%.o: src/%.cpp | $(BUILD_DIR)",
            "\t$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c -o $@ $<",
            "",
            "estimator: apps/estimator.cpp $(APPROX_OBJS)",
            "\t$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^",
            "",
            "estimator_exact: apps/estimator_exact.cpp $(EXACT_DYADIC_OBJS)",
            "\t$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^",
            "",
            "recompute_frozen_exact: apps/recompute_frozen_exact.cpp $(EXACT_DYADIC_OBJS)",
            "\t$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^",
            "",
            "exact_oracle: apps/exact_oracle.cpp $(EXACT_OBJS)",
            "\t$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^",
            "",
            "exact_batch_mt: apps/exact_batch_mt.cpp $(EXACT_OBJS)",
            "\t$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^",
            "",
            "exact_batch_current: apps/exact_batch_current.cpp $(EXACT_OBJS)",
            "\t$(CXX) $(CPPFLAGS) $(CXXFLAGS) -Iapps -o $@ $^",
            "",
            "exact_batch_grouped_u: apps/exact_batch_grouped_u.cpp $(EXACT_OBJS)",
            "\t$(CXX) $(CPPFLAGS) $(CXXFLAGS) -Iapps -o $@ $^",
            "",
            "exact_batch_grouped_uv: apps/exact_batch_grouped_uv.cpp $(EXACT_OBJS)",
            "\t$(CXX) $(CPPFLAGS) $(CXXFLAGS) -Iapps -o $@ $^",
            "",
            "reduce_exact_parts: apps/reduce_exact_parts.cpp",
            "\t$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^",
            "",
            "enumerate_r1_positive: apps/enumerate_r1_positive.cpp $(BUILD_DIR)/sbox_corr.o $(BUILD_DIR)/linear_layer.o",
            "\t$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^",
            "",
            "score: apps/score.cpp $(APPROX_OBJS)",
            "\t$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^",
            "",
            "test: all",
            "\t@test \"$$(sha256sum ../submit.txt | cut -d' ' -f1)\" = \"" + SUBMIT_SHA + "\"",
            "",
            "clean:",
            "\trm -rf $(BUILD_DIR)",
            "\trm -f estimator estimator_exact recompute_frozen_exact exact_oracle exact_batch_mt exact_batch_current exact_batch_grouped_u exact_batch_grouped_uv reduce_exact_parts enumerate_r1_positive score",
            "",
        ]
    )


def copy_file(src: str | Path, dst: str | Path) -> None:
    """Copy one repository file into the package.

    Args:
        src: Repository-relative or absolute source path.
        dst: Package-relative destination path.
    """
    src_path = src if isinstance(src, Path) and src.is_absolute() else ROOT / src
    dst_path = PACKAGE_DIR / dst
    if not src_path.is_file():
        raise SystemExit(f"missing required package input: {src_path}")
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dst_path)


def copy_tree(src: str | Path, dst: str | Path) -> None:
    """Copy a repository directory into the package.

    Args:
        src: Repository-relative or absolute source directory.
        dst: Package-relative destination directory.
    """
    src_path = src if isinstance(src, Path) and src.is_absolute() else ROOT / src
    dst_path = PACKAGE_DIR / dst
    if not src_path.is_dir():
        raise SystemExit(f"missing required package input directory: {src_path}")
    shutil.copytree(
        src_path,
        dst_path,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "build", ".staging", "locks"),
    )


def source_manifest_paths() -> list[str]:
    """Return final-submit source CSV paths from SOURCE_MANIFEST.

    Returns:
        Sorted repository-relative source paths.
    """
    rows: list[str] = []
    with (ROOT / "experiments" / "SOURCE_MANIFEST.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("used_in_final_submit") == "1":
                rows.append(row["path"])
    if not rows:
        raise SystemExit("experiments/SOURCE_MANIFEST.csv did not list final-submit sources")
    return sorted(set(rows))


def copy_submission_artifacts() -> None:
    """Copy required paper, submit, figure manuscript, docs, and compact evidence."""
    copy_file("submit.txt", "submit.txt")
    copy_file("参赛论文/参赛论文_赛题三_稳稳接住.pdf", "paper/参赛论文_赛题三_稳稳接住.pdf")
    copy_file("参赛论文/参赛论文_赛题三_稳稳接住.tex", "paper/参赛论文_赛题三_稳稳接住.tex")
    copy_tree("参赛论文/figures", "paper/figures")
    copy_tree("第十一届0000002243图稿", "figure_manuscript")

    copy_file("docs/OFFICIAL_SPEC_INTERPRETATION.md", "docs/OFFICIAL_SPEC_INTERPRETATION.md")
    copy_file("docs/EVIDENCE_SCOPE.md", "docs/EVIDENCE_SCOPE.md")
    for path in [
        "experiments/manifests/E13_final_integration.md",
        "experiments/audit/submit_audit_summary.json",
        "experiments/audit/submit_audit_summary.md",
        "experiments/complexity/complexity_summary.json",
        "experiments/complexity/complexity_summary.md",
        "experiments/spotcheck/exact_spotcheck_summary.json",
        "experiments/spotcheck/exact_spotcheck_summary.md",
    ]:
        copy_file(path, f"evidence_compact/final_check/{path}")

    for path in [
        "artifacts/way2_exact/full/SUMMARY.json",
        "artifacts/way2_exact/full/SUMMARY.md",
        "artifacts/way2_exact/full/COMPARE.json",
        "artifacts/way2_exact/full/MISMATCHES.csv",
        "artifacts/way2_exact/full/FULL_RUN_AUTHORIZATION.json",
        "artifacts/way2_exact/full/PROVENANCE.json",
        "artifacts/way2_exact/full/MANIFEST.json",
        "artifacts/way2_exact/full/SHA256SUMS.txt",
        "artifacts/way2_exact/full/RAW_EVIDENCE_INDEX.json",
        "artifacts/way2_exact/full/RAW_EVIDENCE_MANIFEST.json",
    ]:
        copy_file(path, f"evidence_compact/way2_exact_full/{Path(path).name}")

    for path in sorted((ROOT / "artifacts" / "strategy_b" / "stage_a").glob("*")):
        if path.is_file():
            copy_file(path, f"evidence_compact/strategy_b_stage_a/{path.name}")
    copy_file("docs/STRATEGY_B_STAGE_A_PROTOCOL.md", "evidence_compact/strategy_b_stage_a/STRATEGY_B_STAGE_A_PROTOCOL.md")
    copy_file("docs/CLAIMS_AND_EVIDENCE.md", "evidence_compact/claims_and_evidence/CLAIMS_AND_EVIDENCE.md")


def copy_source_tree() -> None:
    """Copy runnable submit rebuild source into the package."""
    copy_file("requirements-dev.txt", "source/requirements-dev.txt")
    copy_tree("include", "source/include")
    copy_tree("src", "source/src")
    for path in PACKAGE_SOURCE_APP_FILES:
        copy_file(path, f"source/{path}")
    for path in [
        "experiments/build_submit_from_sources.py",
        "experiments/SOURCE_MANIFEST.csv",
        "experiments/check_submission_package.py",
    ]:
        copy_file(path, f"source/{path}")
    for path in source_manifest_paths():
        copy_file(path, f"source/{path}")
    (PACKAGE_DIR / "source" / "Makefile").write_text(package_source_makefile(), encoding="utf-8")


def write_package_submission_manifest(
    package_status: str,
    pdf_preflight_status: str,
    figure_preflight_status: str,
) -> str:
    """Return the package-internal submission manifest content."""
    return "\n".join(
        [
            "# Submission Package Manifest",
            "",
            f"Status: `{package_status}`.",
            f"PDF preflight status: `{pdf_preflight_status}`.",
            f"Figure-manuscript preflight status: `{figure_preflight_status}`.",
            "Way-2 exact compact summary artifact status: `FULL_EXACT_WAY2_REVIEW`.",
            "Strategy-B Stage-A compact artifact status: `STAGE_A_PASS`.",
            "Evidence scope is summarized in `EVIDENCE_SCOPE.md`.",
            "",
            "## Included package structure",
            "",
            "- `README_FIRST.md`: package entry and frozen result summary.",
            "- `PACKAGE_SOURCE_COMMIT.txt` / `PACKAGE_SOURCE_TREE.txt`: clean committed source provenance for this package build.",
            "- `submit.txt`: unchanged frozen final submit file.",
            "- `score_report.txt`: frozen self-score summary.",
            "- `paper/`: final PDF, TeX, and figure assets used by the paper build.",
            "- `figure_manuscript/`: Word figure manuscript plus figure source exports.",
            "- `source/`: package-safe rebuild source tree and saved certified source CSV inputs.",
            "- `docs/EVIDENCE_SCOPE.md`: single authority for the way-1 / way-2 boundary statement.",
            "- `evidence_compact/`: compact way-2 exact evidence, Strategy-B Stage-A evidence, and final integration summaries.",
            "- `SHA256SUMS.txt`: package-local SHA-256 manifest.",
            "",
            "## Runnable package rebuild chain",
            "",
            "```bash",
            "cd source",
            "make clean && make -j2",
            "python3 -X utf8 experiments/build_submit_from_sources.py --source-submit ../submit.txt --out /tmp/rebuilt_submission_final.txt",
            "cmp ../submit.txt /tmp/rebuilt_submission_final.txt",
            "./score --dedup uv --positive-only ../submit.txt",
            "python3 -X utf8 experiments/check_submission_package.py --submit ../submit.txt",
            "```",
            "",
            "Expected frozen result:",
            "",
            "```text",
            f"valid_count={VALID_COUNT}",
            f"total_score={TOTAL_SCORE}",
            f"submit_sha256={SUBMIT_SHA}",
            "```",
            "",
            "## SOURCE_MANIFEST boundary",
            "",
            "- `source/experiments/SOURCE_MANIFEST.csv` records saved certified source CSV inputs used by the final rebuild chain.",
            "- Its `generation_command` field is a historical discovery label, not a runnable final-package command.",
            "- `candidate_miner_approx` is a repository-only historical discovery helper and is excluded from this package.",
            "- `search_candidates` is a legacy helper and is excluded from this package.",
            "- The final package rebuild path is `source/experiments/build_submit_from_sources.py` consuming the saved certified CSVs.",
            "",
            "## Evidence boundaries",
            "",
            "- The full exact-way2 rerun closes the way-2 mathematical and numerical evidence only.",
            "- `evidence_compact/way2_exact_full/` contains compact summaries, compare outputs, provenance, and manifest files for the completed full exact-way2 rerun.",
            "- `evidence_compact/strategy_b_stage_a/` contains bounded way-1 batch toolchain evidence only; it is not full way-1 `VT` provenance.",
            "- Raw full exact-way2 archives, CI artifacts, benchmark logs, temporary logs, build outputs, `__pycache__`, fonts, and repository-only discovery helpers are excluded from this package.",
            "",
            "```text",
            "stage_b_authorized=false",
            "full_2_32_run_started=false",
            "full_138338_way1_started=false",
            "new_way1_run_started=false",
            "strategy_b_final_file_generated=false",
            "submit_txt_modified=false",
            "vt_provenance_closed=false",
            "```",
            "",
        ]
    )


def write_package_reproducibility() -> str:
    """Return the package-internal reproducibility guide."""
    return "\n".join(
        [
            "# Final Package Reproducibility",
            "",
            "This document applies only to the extracted `submission_final/` package.",
            "It does not claim that repository-only discovery helpers or raw exact-way2",
            "archives are present inside the package.",
            "Evidence scope is summarized in `EVIDENCE_SCOPE.md`.",
            "",
            "## Requirements",
            "",
            "- Linux / WSL2",
            "- `make` and a C++17 compiler",
            "- `python3`",
            "- `python3 -m pip install -r source/requirements-dev.txt` if additional Python helpers are needed",
            "",
            "## Package-safe validation commands",
            "",
            "```bash",
            "sha256sum -c SHA256SUMS.txt",
            "cd source",
            "make clean && make -j2",
            "python3 -X utf8 experiments/build_submit_from_sources.py --source-submit ../submit.txt --out /tmp/rebuilt_submission_final.txt",
            "cmp ../submit.txt /tmp/rebuilt_submission_final.txt",
            "./score --dedup uv --positive-only ../submit.txt",
            "python3 -X utf8 experiments/check_submission_package.py --submit ../submit.txt",
            "```",
            "",
            "The package-safe checker validates only files that actually exist in the final",
            "package. It does not require repository-only tests, CI workflows,",
            "`freeze_baseline.py`, `audit_submit.py`, `candidate_miner_approx.cpp`, or",
            "`search_candidates.cpp`.",
            "",
            "## SOURCE_MANIFEST semantics",
            "",
            "- `source/experiments/SOURCE_MANIFEST.csv` lists saved certified source CSV inputs used by the final package rebuild chain.",
            "- `generation_command` records a historical discovery label for provenance; it is not a command that the final package promises to rerun.",
            "- `source/experiments/build_submit_from_sources.py` is the runnable final-package generator.",
            "",
            "## Evidence included vs excluded",
            "",
            "- Included compact evidence: `evidence_compact/way2_exact_full/`, `evidence_compact/strategy_b_stage_a/`, `evidence_compact/final_check/`, and `evidence_compact/claims_and_evidence/`.",
            "- Excluded repository-only evidence: full exact-way2 raw archives, CI artifacts, benchmark raw logs, temporary logs, build outputs, and fonts.",
            "",
        ]
    )


def write_package_evidence_scope() -> str:
    """Return the package-local evidence-scope statement."""
    return ROOT_EVIDENCE_SCOPE.read_text(encoding="utf-8")


def rewrite_markdown_for_package(relative_target: str, text: str) -> str:
    """Adjust root-relative docs links for package-local copies."""
    return text.replace("`docs/EVIDENCE_SCOPE.md`", f"`{relative_target}`")


def write_text_files(
    generated_at: str,
    source_commit: str,
    source_tree: str,
    package_status: str,
    pdf_preflight_status: str,
    figure_preflight_status: str,
) -> None:
    """Write package-local README, score report, and source metadata.

    Args:
        generated_at: RFC3339 UTC generation time.
        source_commit: Source commit used for the package.
        source_tree: Git tree SHA for the source commit.
        package_status: Release-candidate readiness status for the package.
        pdf_preflight_status: Current PDF preflight status.
        figure_preflight_status: Current figure-manuscript preflight status.
    """
    (PACKAGE_DIR / "README_FIRST.md").write_text(
        "\n".join(
            [
                "# Final Submission Package Release Candidate",
                "",
                f"Status: `{package_status}`.",
                "",
                "This package contains the frozen final submission file, the paper, the",
                "package-level rebuild source tree, and compact evidence.",
                "The way-2 mathematical and numerical evidence chain is closed.",
                "Way-1 evidence is included only as bounded tooling validation and",
                "spotcheck validation; full way-1 `VT` provenance is not claimed.",
                "See `docs/EVIDENCE_SCOPE.md`.",
                f"PDF preflight status: `{pdf_preflight_status}`.",
                f"Figure-manuscript preflight status: `{figure_preflight_status}`.",
                "See `docs/SUBMISSION_MANIFEST.md` for the recorded package state.",
                "",
                "## Required Checks",
                "",
                "```bash",
                "sha256sum -c SHA256SUMS.txt",
                "cd source",
                "make clean && make -j2",
                "python3 -X utf8 experiments/build_submit_from_sources.py --source-submit ../submit.txt --out /tmp/rebuilt_submission_final.txt",
                "cmp ../submit.txt /tmp/rebuilt_submission_final.txt",
                "./score --dedup uv --positive-only ../submit.txt",
                "python3 -X utf8 experiments/check_submission_package.py --submit ../submit.txt",
                "```",
                "",
                "## Frozen Result",
                "",
                f"- `valid_count = {VALID_COUNT}`",
                f"- `total_score = {TOTAL_SCORE}`",
                f"- `submit_sha256 = {SUBMIT_SHA}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    package_submission_manifest = write_package_submission_manifest(
        package_status,
        pdf_preflight_status,
        figure_preflight_status,
    )
    (PACKAGE_DIR / "docs" / "SUBMISSION_MANIFEST.md").write_text(
        package_submission_manifest,
        encoding="utf-8",
    )
    (PACKAGE_DIR / "evidence_compact" / "final_check" / "SUBMISSION_MANIFEST.md").write_text(
        package_submission_manifest,
        encoding="utf-8",
    )
    (PACKAGE_DIR / "docs" / "REPRODUCIBILITY.md").write_text(
        write_package_reproducibility(),
        encoding="utf-8",
    )
    (PACKAGE_DIR / "docs" / "EVIDENCE_SCOPE.md").write_text(
        write_package_evidence_scope(),
        encoding="utf-8",
    )
    final_check_root = (ROOT / "FINAL_CHECK.md").read_text(encoding="utf-8")
    (PACKAGE_DIR / "docs" / "FINAL_CHECK.md").write_text(
        rewrite_markdown_for_package("EVIDENCE_SCOPE.md", final_check_root),
        encoding="utf-8",
    )
    (PACKAGE_DIR / "evidence_compact" / "final_check" / "FINAL_CHECK.md").write_text(
        rewrite_markdown_for_package("../../docs/EVIDENCE_SCOPE.md", final_check_root),
        encoding="utf-8",
    )
    (PACKAGE_DIR / "score_report.txt").write_text(
        "\n".join(
            [
                f"valid_count = {VALID_COUNT}",
                f"total_score = {TOTAL_SCORE}",
                f"submit_sha256 = {SUBMIT_SHA}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (PACKAGE_DIR / "PACKAGE_SOURCE_COMMIT.txt").write_text(
        "\n".join(
            [
                "schema: package-source-metadata-v1",
                f"repository: {REPOSITORY}",
                "release_ref: hardening/final-package-release-candidate",
                f"release_commit: {source_commit}",
                f"package_generated_at_utc: {generated_at}",
                f"submit_source_commit: {source_commit}",
                f"submit_sha256: {SUBMIT_SHA}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    copy_file("PACKAGE_SOURCE_COMMIT.template", "PACKAGE_SOURCE_COMMIT.template")
    (PACKAGE_DIR / "PACKAGE_SOURCE_TREE.txt").write_text(
        f"source_commit = {source_commit}\nsource_tree_sha = {source_tree}\n",
        encoding="utf-8",
    )


def write_package_sha256s() -> list[Path]:
    """Write the package-local SHA256SUMS file.

    Returns:
        Sorted package file paths relative to ``submission_final``.
    """
    files = sorted(path for path in PACKAGE_DIR.rglob("*") if path.is_file() and path != PACKAGE_DIR / "SHA256SUMS.txt")
    rows = [f"{sha256_file(path)}  submission_final/{path.relative_to(PACKAGE_DIR).as_posix()}" for path in files]
    (PACKAGE_DIR / "SHA256SUMS.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return [path.relative_to(PACKAGE_DIR) for path in files] + [Path("SHA256SUMS.txt")]


def build_archive() -> tuple[str, int]:
    """Build a deterministic zip archive for ``submission_final``.

    Returns:
        Archive SHA-256 and byte size.
    """
    if ARCHIVE_PATH.exists():
        ARCHIVE_PATH.unlink()
    paths = sorted(path for path in PACKAGE_DIR.rglob("*") if path.is_file())
    with zipfile.ZipFile(ARCHIVE_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in paths:
            rel = Path("submission_final") / path.relative_to(PACKAGE_DIR)
            info = zipfile.ZipInfo(rel.as_posix(), ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    return sha256_file(ARCHIVE_PATH), ARCHIVE_PATH.stat().st_size


def write_manifest(
    generated_at: str,
    source_commit: str,
    source_tree: str,
    package_files: list[Path],
    archive_sha: str,
    archive_size: int,
    package_status: str,
    pdf_preflight_status: str,
    figure_preflight_status: str,
) -> None:
    """Write the root package manifest.

    Args:
        generated_at: RFC3339 UTC generation time.
        source_commit: Source commit used for the package.
        source_tree: Git tree SHA for the source commit.
        package_files: Package file list relative to ``submission_final``.
        archive_sha: SHA-256 of the generated archive.
        archive_size: Archive byte size.
        package_status: Release-candidate readiness status for the package.
        pdf_preflight_status: Current PDF preflight status.
        figure_preflight_status: Current figure-manuscript preflight status.
    """
    package_sha = sha256_file(PACKAGE_DIR / "SHA256SUMS.txt")
    PACKAGE_MANIFEST.write_text(
        "\n".join(
            [
                "# Final Package Manifest",
                "",
                f"Status: `{package_status}`.",
                "",
                "| field | value |",
                "|---|---|",
                f"| repository | `{REPOSITORY}` |",
                f"| source_commit | `{source_commit}` |",
                f"| source_tree_sha | `{source_tree}` |",
                f"| generated_at_utc | `{generated_at}` |",
                f"| pdf_preflight_status | `{pdf_preflight_status}` |",
                f"| figure_preflight_status | `{figure_preflight_status}` |",
                f"| submit_sha256 | `{SUBMIT_SHA}` |",
                f"| valid_count | `{VALID_COUNT}` |",
                f"| total_score | `{TOTAL_SCORE}` |",
                f"| package_dir | `submission_final/` |",
                f"| package_file_count | `{len(package_files)}` |",
                f"| package_sha256s | `submission_final/SHA256SUMS.txt` |",
                f"| package_sha256s_sha256 | `{package_sha}` |",
                f"| archive | `{ARCHIVE_PATH.name}` |",
                f"| archive_bytes | `{archive_size}` |",
                f"| archive_sha256 | `{archive_sha}` |",
                f"| archive_command | `python3 -X utf8 scripts/build_final_package.py --clean` |",
                "",
                "## Inclusion Boundary",
                "",
                "| category | package treatment |",
                "|---|---|",
                "| required submission artifacts | included: paper PDF/TeX, figure manuscript, `submit.txt`, score report, README |",
                "| runnable submit rebuild source | included under `source/` with core C++/Python programs and final source CSVs |",
                "| way-2 exact evidence | compact summaries/manifests included under `evidence_compact/way2_exact_full/` |",
                "| Strategy-B Stage-A evidence | bounded toolchain summaries/manifests included under `evidence_compact/strategy_b_stage_a/` |",
                "| repository-only raw evidence | excluded: full raw archives, CI artifacts, diagnostic logs |",
                "| excluded artifacts | excluded: build outputs, `__pycache__`, temporary logs, fonts, superseded snapshots, legacy helpers |",
                "",
                "## Source Boundary Notes",
                "",
                "- Legacy and discovery-only helper programs are excluded from the final competition package and are not part of the final rebuild chain.",
                "- The frozen final `submit.txt` is rebuilt from saved certified CSV sources, not by rerunning historical candidate discovery.",
                "- The final package does not rerun Strategy-B, does not run new way-1 computation, and does not regenerate `submit.txt` from excluded helper utilities.",
                "- The compact full exact-way2 summary bundled under `submission_final/evidence_compact/way2_exact_full/SUMMARY.json` retains its artifact status code `FULL_EXACT_WAY2_REVIEW`; this package uses that completed dual-backend run only to describe closure of the way-2 mathematical and numerical evidence.",
                "",
                "## Evidence State",
                "",
                "```text",
                "stage_b_authorized=false",
                "full_2_32_run_started=false",
                "full_138338_way1_started=false",
                "new_way1_run_started=false",
                "strategy_b_final_file_generated=false",
                "submit_txt_modified=false",
                "vt_provenance_closed=false",
                "```",
                "",
                "## Package Files",
                "",
                *[f"- `{path.as_posix()}`" for path in package_files],
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_root_sha256s() -> None:
    """Write the repository-root SHA256SUMS manifest for tracked files."""
    tracked = subprocess.check_output(
        ["git", "-c", "core.quotePath=false", "ls-files", "-z"],
        cwd=ROOT,
        text=True,
    )
    tracked_paths = {
        Path(raw)
        for raw in tracked.split("\0")
        if raw and raw != "SHA256SUMS.txt" and (ROOT / raw).is_file()
    }
    generated_paths = {
        path.relative_to(ROOT)
        for path in PACKAGE_DIR.rglob("*")
        if path.is_file()
    }
    if ARCHIVE_PATH.is_file():
        generated_paths.add(ARCHIVE_PATH.relative_to(ROOT))
    paths = sorted(tracked_paths | generated_paths, key=lambda path: path.as_posix())
    rows = [f"{sha256_file(ROOT / path)}  {path.as_posix()}" for path in paths]
    ROOT_SHA256SUMS.write_text("\n".join(rows) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Remove existing submission_final and archive first.")
    parser.add_argument("--generated-at-utc", help="RFC3339 UTC timestamp. Defaults to current UTC.")
    return parser.parse_args()


def main() -> None:
    """Build the final package release candidate."""
    args = parse_args()
    if args.clean:
        if PACKAGE_DIR.exists():
            shutil.rmtree(PACKAGE_DIR)
        if ARCHIVE_PATH.exists():
            ARCHIVE_PATH.unlink()
    if PACKAGE_DIR.exists() and any(PACKAGE_DIR.iterdir()):
        raise SystemExit("submission_final exists and is not empty; use --clean to rebuild")
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)

    generated_at = args.generated_at_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    source_commit = git_output(["rev-parse", "HEAD"])
    source_tree = git_output(["rev-parse", "HEAD^{tree}"])
    package_status, pdf_preflight_status, figure_preflight_status = final_package_status()

    copy_submission_artifacts()
    copy_source_tree()
    write_text_files(
        generated_at,
        source_commit,
        source_tree,
        package_status,
        pdf_preflight_status,
        figure_preflight_status,
    )
    package_files = write_package_sha256s()
    archive_sha, archive_size = build_archive()
    write_manifest(
        generated_at,
        source_commit,
        source_tree,
        package_files,
        archive_sha,
        archive_size,
        package_status,
        pdf_preflight_status,
        figure_preflight_status,
    )
    write_root_sha256s()

    print(f"package_dir={PACKAGE_DIR.relative_to(ROOT)}")
    print(f"package_files={len(package_files)}")
    print(f"archive={ARCHIVE_PATH.name}")
    print(f"archive_sha256={archive_sha}")


if __name__ == "__main__":
    main()
