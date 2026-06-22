#!/usr/bin/env python3
"""Check the repository state expected for the submission package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from freeze_baseline import load_queries


REQUIRED_FILES = [
    "Makefile",
    "README.md",
    "REPORT.md",
    "submit.txt",
    "include/sbox_corr.hpp",
    "include/beam_search.hpp",
    "include/exact.hpp",
    "src/sbox_corr.cpp",
    "src/beam_search.cpp",
    "src/exact.cpp",
    "apps/estimator.cpp",
    "apps/candidate_miner_approx.cpp",
    "apps/enumerate_r1_positive.cpp",
    "apps/exact_oracle.cpp",
    "apps/exact_batch_mt.cpp",
    "apps/reduce_exact_parts.cpp",
    "apps/score.cpp",
    "tests/test_audit_schema.py",
    "tests/test_core.cpp",
    "tests/test_freeze_baseline.py",
    "tests/test_score.py",
    "tests/test_submission_integrity.py",
    "experiments/audit_submit.py",
    "experiments/freeze_baseline.py",
    "experiments/frozen/BASELINE.json",
    "experiments/frozen/SHA256SUMS.txt",
    "experiments/frozen/final_queries.csv",
    "experiments/frozen/final_ru.csv",
    "experiments/build_submit_from_sources.py",
    "experiments/build_submit_with_certified_r2.py",
    "experiments/run_ablation.py",
    "experiments/submit_audit.csv",
    "experiments/r2_active1_emit_all.csv",
    "experiments/r3_active1_emit_all.csv",
    "experiments/r2_active2_batch_1000_0100.csv",
    "experiments/r2_active2_batch_1100_0100.csv",
    "experiments/r2_active2_batch_1200_0100.csv",
    "experiments/r2_active2_batch_1300_0100.csv",
    "experiments/r2_active2_batch_1400_0100.csv",
    "experiments/r2_active2_batch_1500_0100.csv",
    "experiments/r2_active2_batch_1600_0100.csv",
    "experiments/r2_active2_batch_1700_0100.csv",
    "experiments/r2_active2_batch_1800_0100.csv",
    "experiments/r2_active2_batch_1900_0100.csv",
    "experiments/r2_active2_batch_200_0100.csv",
    "experiments/r2_active2_batch_2100_0100.csv",
    "experiments/r2_active2_batch_2200_0100.csv",
    "experiments/r2_active2_batch_2300_0100.csv",
    "experiments/r2_active2_batch_2400_0100.csv",
    "experiments/r2_active2_batch_2500_0100.csv",
    "experiments/r2_active2_batch_2600_0100.csv",
    "experiments/r2_active2_batch_2700_0100.csv",
    "experiments/r2_active2_batch_2800_0100.csv",
    "experiments/r2_active2_batch_2900_0100.csv",
    "experiments/r2_active2_batch_3000_0100.csv",
    "experiments/r2_active2_batch_300_0100.csv",
    "experiments/r2_active2_batch_3100_0100.csv",
    "experiments/r2_active2_batch_3200_0100.csv",
    "experiments/r2_active2_batch_3300_0100.csv",
    "experiments/r2_active2_batch_3400_0100.csv",
    "experiments/r2_active2_batch_3500_0100.csv",
    "experiments/r2_active2_batch_3600_0100.csv",
    "experiments/r2_active2_batch_3700_0100.csv",
    "experiments/r2_active2_batch_3800_0100.csv",
    "experiments/r2_active2_batch_3900_0100.csv",
    "experiments/r2_active2_batch_4000_0100.csv",
    "experiments/r2_active2_batch_400_0100.csv",
    "experiments/r2_active2_batch_4100_0100.csv",
    "experiments/r2_active2_batch_4200_0100.csv",
    "experiments/r2_active2_batch_4300_0100.csv",
    "experiments/r2_active2_batch_4400_0100.csv",
    "experiments/r2_active2_batch_4500_0100.csv",
    "experiments/r2_active2_batch_4600_0100.csv",
    "experiments/r2_active2_batch_4700_0100.csv",
    "experiments/r2_active2_batch_4800_0100.csv",
    "experiments/r2_active2_batch_4900_0100.csv",
    "experiments/r2_active2_batch_5000_0100.csv",
    "experiments/r2_active2_batch_500_0100.csv",
    "experiments/r2_active2_batch_5100_0100.csv",
    "experiments/r2_active2_batch_5200_0100.csv",
    "experiments/r2_active2_batch_5300_0100.csv",
    "experiments/r2_active2_batch_5400_0100.csv",
    "experiments/r2_active2_batch_5500_0100.csv",
    "experiments/r2_active2_batch_5600_0100.csv",
    "experiments/r2_active2_batch_5700_0100.csv",
    "experiments/r2_active2_batch_5800_0100.csv",
    "experiments/r2_active2_batch_5900_0100.csv",
    "experiments/r2_active2_batch_6000_0100.csv",
    "experiments/r2_active2_batch_6100_0100.csv",
    "experiments/r2_active2_batch_6200_0100.csv",
    "experiments/r2_active2_batch_6300_0100.csv",
    "experiments/r2_active2_batch_700_0100.csv",
    "experiments/r2_active2_batch_800_0100.csv",
    "experiments/r2_active2_batch_900_0100.csv",
    "experiments/r2_active2_edge120.csv",
    "experiments/r2_active2_edge6400.csv",
    "experiments/r2_active3_a3_15020.csv",
    "experiments/r2_active3_a3_50020.csv",
    "experiments/r2_active3_a3_100020.csv",
    "experiments/r2_active3_a3_190020.csv",
    "experiments/r2_active3_near_100010_0020.csv",
    "experiments/r2_active3_near_100030_0020.csv",
    "experiments/r2_active3_near_100050_0020.csv",
    "experiments/r2_active3_near_100070_0020.csv",
    "experiments/r2_active3_near_100090_0020.csv",
    "experiments/r2_active3_near_100110_0020.csv",
    "experiments/r2_active3_near_100130_0020.csv",
    "experiments/r2_active3_near_100150_0020.csv",
    "experiments/r2_active3_near_100170_0020.csv",
    "experiments/r2_active3_near_100190_0020.csv",
    "experiments/r2_active3_near_100230_0020.csv",
    "experiments/r2_active3_near_100270_0020.csv",
    "experiments/r2_active3_near_100290_0020.csv",
    "experiments/r2_active3_near_14950_0020.csv",
    "experiments/r2_active3_near_14970_0020.csv",
    "experiments/r2_active3_near_15010_0020.csv",
    "experiments/r2_active3_near_15030_0020.csv",
    "experiments/r2_active3_near_15050_0020.csv",
    "experiments/r2_active3_near_15070_0020.csv",
    "experiments/r2_active3_near_15090_0020.csv",
    "experiments/r2_active3_near_189970_0020.csv",
    "experiments/r2_active3_near_189990_0020.csv",
    "experiments/r2_active3_near_190010_0020.csv",
    "experiments/r2_active3_near_190030_0020.csv",
    "experiments/r2_active3_near_190050_0020.csv",
    "experiments/r2_active3_near_190070_0020.csv",
    "experiments/r2_active3_near_190090_0020.csv",
    "experiments/r2_active3_near_190110_0020.csv",
    "experiments/r2_active3_near_190130_0020.csv",
    "experiments/r2_active3_near_190150_0020.csv",
    "experiments/r2_active3_near_190170_0020.csv",
    "experiments/r2_active3_near_190190_0020.csv",
    "experiments/r2_active3_near_190210_0020.csv",
    "experiments/r2_active3_near_190230_0020.csv",
    "experiments/r2_active3_near_190250_0020.csv",
    "experiments/r2_active3_near_190270_0020.csv",
    "experiments/r2_active3_near_190290_0020.csv",
    "experiments/r2_active3_near_190310_0020.csv",
    "experiments/r2_active3_near_190330_0020.csv",
    "experiments/r2_active3_near_49590_0020.csv",
    "experiments/r2_active3_near_49610_0020.csv",
    "experiments/r2_active3_near_49630_0020.csv",
    "experiments/r2_active3_near_49650_0020.csv",
    "experiments/r2_active3_near_49670_0020.csv",
    "experiments/r2_active3_near_49690_0020.csv",
    "experiments/r2_active3_near_49710_0020.csv",
    "experiments/r2_active3_near_49730_0020.csv",
    "experiments/r2_active3_near_49750_0020.csv",
    "experiments/r2_active3_near_49770_0020.csv",
    "experiments/r2_active3_near_49790_0020.csv",
    "experiments/r2_active3_near_49810_0020.csv",
    "experiments/r2_active3_near_49830_0020.csv",
    "experiments/r2_active3_near_49850_0020.csv",
    "experiments/r2_active3_near_49870_0020.csv",
    "experiments/r2_active3_near_49890_0020.csv",
    "experiments/r2_active3_near_49910_0020.csv",
    "experiments/r2_active3_near_49930_0020.csv",
    "experiments/r2_active3_near_49950_0020.csv",
    "experiments/r2_active3_near_49970_0020.csv",
    "experiments/r2_active3_near_49990_0020.csv",
    "experiments/r2_active3_near_50000_0020.csv",
    "experiments/r2_active3_near_50010_0020.csv",
    "experiments/r2_active3_near_50020_0020.csv",
    "experiments/r2_active3_near_50030_0020.csv",
    "experiments/r2_active3_near_50040_0020.csv",
    "experiments/r2_active3_near_50050_0020.csv",
    "experiments/r2_active3_near_50060_0020.csv",
    "experiments/r2_active3_near_50070_0020.csv",
    "experiments/r2_active3_near_50090_0020.csv",
    "experiments/r2_active3_near_50110_0020.csv",
    "experiments/r2_active3_near_50130_0020.csv",
    "experiments/r2_active3_near_50150_0020.csv",
    "experiments/r2_active3_near_50170_0020.csv",
    "experiments/r2_active3_near_50190_0020.csv",
    "experiments/r2_active3_near_50210_0020.csv",
    "experiments/r2_active3_near_50230_0020.csv",
    "experiments/r2_active3_near_50250_0020.csv",
    "experiments/r2_active3_near_50270_0020.csv",
    "experiments/r2_active3_near_50290_0020.csv",
    "experiments/r2_active3_near_50310_0020.csv",
    "experiments/r2_active3_near_50330_0020.csv",
    "experiments/r2_active3_near_50350_0020.csv",
    "experiments/r2_active3_near_50370_0020.csv",
    "experiments/r2_active3_near_50390_0020.csv",
    "experiments/r2_active3_near_50410_0020.csv",
    "experiments/r2_active3_near_50430_0020.csv",
    "experiments/r2_active3_near_50450_0020.csv",
    "experiments/r2_active3_near_50470_0020.csv",
    "experiments/r2_active3_near_50490_0020.csv",
    "experiments/r2_active3_near_50510_0020.csv",
    "experiments/r2_active3_near_50530_0020.csv",
    "experiments/r2_active3_near_50550_0020.csv",
    "experiments/r2_active3_near_50570_0020.csv",
    "experiments/r2_active3_near_50590_0020.csv",
    "experiments/r2_active3_near_50610_0020.csv",
    "experiments/r2_active3_near_50630_0020.csv",
    "experiments/r2_active3_near_50650_0020.csv",
    "experiments/r2_active3_near_50670_0020.csv",
    "experiments/r2_active3_near_50690_0020.csv",
    "experiments/r2_active3_near_50710_0020.csv",
    "experiments/r2_active3_near_50730_0020.csv",
    "experiments/r2_active3_near_50750_0020.csv",
    "experiments/r2_active3_near_50770_0020.csv",
    "experiments/r2_active3_near_50790_0020.csv",
    "experiments/r2_active3_near_50810_0020.csv",
    "experiments/r2_active3_near_99710_0020.csv",
    "experiments/r2_active3_near_99730_0020.csv",
    "experiments/r2_active3_near_99770_0020.csv",
    "experiments/r2_active3_near_99810_0020.csv",
    "experiments/r2_active3_near_99830_0020.csv",
    "experiments/r2_active3_near_99850_0020.csv",
    "experiments/r2_active3_near_99870_0020.csv",
    "experiments/r2_active3_near_99890_0020.csv",
    "experiments/r2_active3_near_99910_0020.csv",
    "experiments/r2_active3_near_99930_0020.csv",
    "experiments/r2_active3_near_99950_0020.csv",
    "experiments/r2_active3_near_99970_0020.csv",
    "experiments/r2_active3_near_99990_0020.csv",
    "experiments/ablation_results.csv",
    "experiments/ablation_summary.md",
]

FORBIDDEN_TRACKED = {
    "estimator",
    "exact_oracle",
    "exact_batch_mt",
    "reduce_exact_parts",
    "search_candidates",
    "candidate_miner_approx",
    "enumerate_r1_positive",
    "score",
    "test_core",
    "autoresearch-state.json",
    "research-results.tsv",
    "autoresearch-lessons.md",
    "autoresearch-hook-context.json",
}

REQUIRED_FINAL_FILES = [
    "docs/REPRODUCIBILITY.md",
    "docs/VT_VE_COMPLIANCE.md",
    "docs/EXPERIMENTS.md",
    "experiments/manifests/E13_final_integration.md",
]

EXPECTED_VALID_COUNT = 138338
EXPECTED_TOTAL_SCORE = "105843.622442471292742994"
EXPECTED_UNIQUE_RU = 4760
EXPECTED_MAX_TRANSITIONS = 7578152
EXPECTED_TRANSITIONS_RATIO = 0.00176443
EXPECTED_SUBMIT_SHA256 = "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e"
EXPECTED_CERTIFIED_ROWS = 138338
EXPECTED_WAY2_MISMATCH = 0
EXPECTED_SPOTCHECK_COUNT = 18
EXPECTED_SPOTCHECK_MISMATCH = 0

EXPECTED_AUDIT_FIELDS = [
    "r",
    "u",
    "v",
    "VT",
    "VE",
    "valid",
    "score",
    "beam",
    "trans",
    "branch",
    "mode",
    "expanded_states",
    "generated_transitions",
    "final_beam_size",
    "certified_no_truncation",
    "estimator_ve",
    "ve_matches_submit",
    "way2_executed",
    "way2_value_source",
    "submitted_vt_field_source",
    "exact_executed",
    "exact_command",
    "exact_result_available",
    "estimator_command",
    "round_stats",
]


def run(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return completed.stdout


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check the final submission package without running full audit by default.")
    parser.add_argument("--submit", default="submit.txt", help="Submit file to score.")
    parser.add_argument(
        "--run-full-audit",
        action="store_true",
        help="Explicitly run the slow full way-2 audit. Disabled by default.",
    )
    parser.add_argument(
        "--audit-out",
        default="/tmp/check_submission_audit.csv",
        help="Output CSV used only with --run-full-audit.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_data_rows(path: Path, expected_header: list[str]) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        require(header == expected_header, f"unexpected header in {path}: {header}")
        return sum(1 for _ in reader)


def load_csv_rows(path: Path, expected_header: list[str]) -> list[list[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        require(header == expected_header, f"unexpected header in {path}: {header}")
        return list(reader)


def verify_sha256_manifest(root: Path, manifest_path: Path) -> None:
    entries: set[str] = set()
    for line_number, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), start=1):
        parts = line.split("  ", 1)
        require(len(parts) == 2 and len(parts[0]) == 64, f"bad SHA256 line {line_number}: {line}")
        expected, rel = parts
        require(rel not in entries, f"duplicate SHA256 entry: {rel}")
        entries.add(rel)
        target = (root / rel).resolve()
        require(target.is_relative_to(root.resolve()), f"SHA256 path escapes root: {rel}")
        require(target.is_file(), f"SHA256 target missing: {rel}")
        require(sha256(target) == expected, f"SHA256 mismatch: {rel}")
    require(bool(entries), f"empty SHA256 manifest: {manifest_path}")


def verify_frozen_baseline(root: Path, submit_path: Path) -> list[tuple[int, int, int]]:
    frozen_dir = root / "experiments/frozen"
    baseline = load_json(frozen_dir / "BASELINE.json")
    expected_numbers = {
        "certified_rows": EXPECTED_CERTIFIED_ROWS,
        "exact_spotcheck_count": EXPECTED_SPOTCHECK_COUNT,
        "exact_spotcheck_mismatch": EXPECTED_SPOTCHECK_MISMATCH,
        "max_generated_transitions_per_ru": EXPECTED_MAX_TRANSITIONS,
        "total_score": EXPECTED_TOTAL_SCORE,
        "unique_ru": EXPECTED_UNIQUE_RU,
        "valid_count": EXPECTED_VALID_COUNT,
        "way2_mismatch": EXPECTED_WAY2_MISMATCH,
    }
    require(baseline["schema_version"] == 1, "unexpected frozen baseline schema")
    require(baseline["source"]["path"] == "submit.txt", "unexpected frozen submit source path")
    require(baseline["source"]["sha256"] == EXPECTED_SUBMIT_SHA256, "unexpected frozen submit SHA-256")
    require(sha256(submit_path) == EXPECTED_SUBMIT_SHA256, "submit.txt differs from the frozen baseline")
    require(baseline["frozen_numbers"] == expected_numbers, "unexpected frozen baseline numbers")

    queries = load_queries(submit_path)
    expected_queries = [(query.r, query.u, query.v) for query in queries]
    expected_query_rows = [
        [str(r), f"0x{u:08x}", f"0x{v:08x}"]
        for r, u, v in expected_queries
    ]
    frozen_query_rows = load_csv_rows(frozen_dir / "final_queries.csv", ["r", "u", "v"])
    require(frozen_query_rows == expected_query_rows, "frozen queries do not match submit.txt")

    expected_ru = sorted({(r, u) for r, u, _ in expected_queries})
    expected_ru_rows = [[str(r), f"0x{u:08x}"] for r, u in expected_ru]
    frozen_ru_rows = load_csv_rows(frozen_dir / "final_ru.csv", ["r", "u"])
    require(frozen_ru_rows == expected_ru_rows, "frozen (r,u) rows do not match submit.txt")

    for name, columns, data_rows in (
        ("final_queries.csv", ["r", "u", "v"], EXPECTED_VALID_COUNT),
        ("final_ru.csv", ["r", "u"], EXPECTED_UNIQUE_RU),
    ):
        metadata = baseline["artifacts"][name]
        require(metadata["columns"] == columns, f"unexpected frozen columns: {name}")
        require(metadata["data_rows"] == data_rows, f"unexpected frozen row count: {name}")
        require(metadata["sha256"] == sha256(frozen_dir / name), f"frozen artifact hash mismatch: {name}")

    verify_sha256_manifest(frozen_dir, frozen_dir / "SHA256SUMS.txt")
    return expected_queries


def verify_audit_provenance(path: Path, expected_queries: list[tuple[int, int, int]]) -> None:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames == EXPECTED_AUDIT_FIELDS, f"unexpected audit schema: {reader.fieldnames}")
        rows = list(reader)
    require(len(rows) == EXPECTED_VALID_COUNT, "unexpected audit CSV row count")
    audit_queries = [(int(row["r"]), int(row["u"], 0), int(row["v"], 0)) for row in rows]
    require(audit_queries == expected_queries, "audit coordinates do not match frozen queries")
    for line_number, row in enumerate(rows, start=2):
        require(row["way2_executed"] == "1", f"way-2 not executed at audit line {line_number}")
        require(row["way2_value_source"] == "estimator", f"unexpected way-2 source at audit line {line_number}")
        require(
            row["submitted_vt_field_source"] == "submit.txt",
            f"unexpected submitted VT source at audit line {line_number}",
        )
        require(row["exact_executed"] == "0", f"unexpected exact execution at audit line {line_number}")
        require(row["exact_command"] == "", f"unexpected exact command at audit line {line_number}")
        require(row["exact_result_available"] == "0", f"unexpected exact result at audit line {line_number}")


def require_file(root: Path, rel: str, tracked: set[str], have_git: bool) -> None:
    path = root / rel
    require(path.exists(), f"missing required file: {rel}")
    if have_git:
        require(rel in tracked, f"required file is not tracked: {rel}")


def require_close(value: float, expected: float, message: str) -> None:
    require(abs(value - expected) <= 5e-9, message)


def tracked_files() -> tuple[set[str], bool]:
    """Return repository-tracked files when available.

    Submission zips normally do not contain a .git directory. In that case we
    fall back to the files present in the package and skip tracked-only checks.
    """
    root = Path.cwd()
    if (root / ".git").exists():
        return set(run(["git", "ls-files"]).splitlines()), True
    present = {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
    }
    return present, False


def main() -> int:
    args = parse_args()
    root = Path.cwd()
    tracked, have_git = tracked_files()

    for rel in REQUIRED_FILES:
        require_file(root, rel, tracked, have_git)
    for rel in REQUIRED_FINAL_FILES:
        require_file(root, rel, tracked, have_git)

    if have_git:
        forbidden = sorted(FORBIDDEN_TRACKED.intersection(tracked))
        require(not forbidden, "forbidden generated files are tracked: " + ", ".join(forbidden))

    score_output = run(["./score", "--dedup", "uv", "--positive-only", args.submit])
    require(f"valid_count={EXPECTED_VALID_COUNT}" in score_output, "unexpected valid_count in score output")
    require(f"total_score={EXPECTED_TOTAL_SCORE}" in score_output, "unexpected total_score in score output")

    expected_queries = verify_frozen_baseline(root, root / args.submit)
    verify_audit_provenance(root / "experiments/submit_audit.csv", expected_queries)

    audit_summary = load_json(root / "experiments/audit/submit_audit_summary.json")
    require(audit_summary["submit_rows"] == EXPECTED_VALID_COUNT, "unexpected submit_rows in audit summary")
    require(audit_summary["audit_rows"] == EXPECTED_VALID_COUNT, "unexpected audit_rows in audit summary")
    require(audit_summary["certified_no_truncation_rows"] == EXPECTED_VALID_COUNT, "unexpected certified rows")
    require(audit_summary["ve_mismatch_rows"] == 0, "audit summary has VE mismatches")
    require(audit_summary["duplicate_uv_rows"] == 0, "audit summary has duplicate (u,v) rows")
    require(audit_summary["zero_u_rows"] == 0, "audit summary has zero u rows")
    require(audit_summary["zero_v_rows"] == 0, "audit summary has zero v rows")
    require(audit_summary["zero_vt_rows"] == 0, "audit summary has zero VT rows")
    require(audit_summary["zero_ve_rows"] == 0, "audit summary has zero VE rows")
    require(audit_summary["unique_ru"] == EXPECTED_UNIQUE_RU, "unexpected unique_ru in audit summary")

    complexity_summary = load_json(root / "experiments/complexity/complexity_summary.json")
    require(complexity_summary["unique_ru"] == EXPECTED_UNIQUE_RU, "unexpected unique_ru in complexity summary")
    require(
        complexity_summary["max_generated_transitions_per_ru"] == EXPECTED_MAX_TRANSITIONS,
        "unexpected max_generated_transitions_per_ru",
    )
    require_close(
        float(complexity_summary["generated_transitions_ratio_to_2_32_max"]),
        EXPECTED_TRANSITIONS_RATIO,
        "unexpected generated transition ratio",
    )
    require(complexity_summary["ru_generated_transitions_ge_2_32"] == 0, "generated transitions exceeded way-1 scale")
    require(complexity_summary["ru_expanded_states_ge_2_32"] == 0, "expanded states exceeded way-1 scale")

    spotcheck_summary = root / "experiments/spotcheck/exact_spotcheck_summary.json"
    if spotcheck_summary.exists():
        spotcheck = load_json(spotcheck_summary)
        require(spotcheck["mismatch_count"] == EXPECTED_SPOTCHECK_MISMATCH, "exact spotcheck has mismatches")
        require(int(spotcheck["count"]) == EXPECTED_SPOTCHECK_COUNT, "unexpected exact spotcheck count")

    verify_sha256_manifest(root, root / "SHA256SUMS.txt")

    if args.run_full_audit:
        audit_output = run(
            [
                "python3",
                "experiments/audit_submit.py",
                "--submit",
                args.submit,
                "--out",
                args.audit_out,
                "--beam",
                "1000000",
                "--trans",
                "100000",
                "--branch",
                "16",
            ]
        )
        require(f"audit_rows={EXPECTED_VALID_COUNT}" in audit_output, "unexpected full audit row count")
        require("ve_mismatch_count=0" in audit_output, "full audit mismatch")

    print("submission package checks passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"submission check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
