#!/usr/bin/env python3
"""Validate compact Strategy-B Stage-A artifacts and bounded-scope status."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "artifacts" / "strategy_b" / "stage_a"
BENCH_ROOT = ROOT / "bench" / "way1"
SCRIPT = ROOT / "scripts" / "build_strategy_b_stage_a_artifacts.py"
QUERY_HEADER = ["row_id", "r", "u", "v"]


def sha256(path: Path) -> str:
    return subprocess.check_output(["sha256sum", str(path)], text=True).split()[0]


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def query_header(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        return next(csv.reader(handle))


def main() -> None:
    required = [
        ROOT / "docs" / "STRATEGY_B_STAGE_A_PROTOCOL.md",
        ARTIFACT_ROOT / "STAGE_A_SUMMARY.json",
        ARTIFACT_ROOT / "QUERY_FAMILY_SUMMARY.json",
        ARTIFACT_ROOT / "MISMATCH_SUMMARY.json",
        ARTIFACT_ROOT / "REDUCER_NEGATIVE_TEST_SUMMARY.json",
        ARTIFACT_ROOT / "MANIFEST.json",
        ARTIFACT_ROOT / "SHA256SUMS.txt",
    ]
    if not all(path.exists() for path in required):
        print("strategy-b Stage-A artifact test skipped")
        return

    subprocess.run(
        ["python3", "-X", "utf8", str(SCRIPT), "--check"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    summary = read_json(ARTIFACT_ROOT / "STAGE_A_SUMMARY.json")
    families = read_json(ARTIFACT_ROOT / "QUERY_FAMILY_SUMMARY.json")
    mismatches = read_json(ARTIFACT_ROOT / "MISMATCH_SUMMARY.json")
    reducer = read_json(ARTIFACT_ROOT / "REDUCER_NEGATIVE_TEST_SUMMARY.json")
    manifest = read_json(ARTIFACT_ROOT / "MANIFEST.json")
    bench_summary = read_json(BENCH_ROOT / "STAGE_A_SUMMARY.json")

    assert summary["stage"] == "STRATEGY_B_STAGE_A"
    assert summary["decision"] == "STAGE_A_PASS"
    assert summary["next_state"] == "STRATEGY_B_STAGE_A_REVIEW"
    assert summary["submission"] == {
        "sha256": "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e",
        "valid_count": 138338,
        "total_score": "105843.622442471292742994",
    }
    assert summary["implementations_tested"] == ["current", "grouped_u", "grouped_uv"]
    assert summary["status_flags"] == {
        "stage_b_authorized": False,
        "full_2_32_run_started": False,
        "full_138338_way1_started": False,
        "new_way1_run_started": False,
        "strategy_b_final_file_generated": False,
        "submit_txt_modified": False,
        "vt_provenance_closed": False,
    }
    assert summary["matrices"]["a0"]["run_case_count"] == 68
    assert summary["matrices"]["a1"]["run_case_count"] == 50
    assert summary["matrices"]["a2"]["matrix_case_count"] == 31
    assert summary["matrices"]["toolchain"]["matrix_case_count"] == 69
    assert summary["gates"]["numerator_mismatch_count"] == 0
    assert summary["gates"]["shard_negative_test_pass_count"] == 12

    assert families["query_csv_header"] == QUERY_HEADER
    assert families["query_csv_header_only_row_id_r_u_v"] is True
    assert families["a0_available_counts"] == {
        "frozen-subset": 5,
        "synthetic-frozen-shaped": 6,
        "uniform": 6,
    }
    assert families["a1_available_counts"] == {
        "frozen-subset": 12,
        "synthetic-frozen-shaped": 15,
        "uniform": 15,
    }
    assert families["a2_anchor_counts"] == {
        "frozen-subset": 2,
        "synthetic-frozen-shaped": 1,
    }

    assert mismatches["numerator_mismatch_count"] == 0
    assert mismatches["semantic_mismatch_count_a0"] == 0
    assert mismatches["semantic_mismatch_count_a1"] == 0
    assert mismatches["semantic_mismatch_count_a2"] == 0
    assert mismatches["semantic_mismatch_count_toolchain"] == 0
    assert mismatches["sanitizer_diagnostic_count"] == 0
    assert mismatches["timeout_count"] == 0
    assert mismatches["oom_count"] == 0
    assert mismatches["nonzero_exit_count"] == 0

    assert reducer["total_cases"] == 12
    assert reducer["passed_cases"] == 12
    assert reducer["all_cases_passed"] is True

    file_entries = manifest["files"]
    assert file_entries
    assert all(
        entry["path"]
        not in {
            "artifacts/strategy_b/stage_a/MANIFEST.json",
            "artifacts/strategy_b/stage_a/SHA256SUMS.txt",
        }
        for entry in file_entries
    )
    counts: dict[str, int] = {}
    for entry in file_entries:
        counts[entry["category"]] = counts.get(entry["category"], 0) + 1
        path = ROOT / entry["path"]
        assert path.exists()
        assert sha256(path) == entry["sha256"]
        assert path.stat().st_size == entry["size"]
    assert manifest["category_counts"] == counts
    assert counts == {"REQUIRED_SUMMARY": 5}

    source_paths = {entry["path"] for entry in manifest["source_evidence"]}
    assert "bench/way1/STAGE_A_SUMMARY.json" in source_paths
    assert "bench/way1/stage_toolchain/SUMMARY.json" in source_paths
    assert summary["source_benchmark_summary_sha256"] == sha256(
        BENCH_ROOT / "STAGE_A_SUMMARY.json"
    )
    assert summary["protocol_doc_sha256"] == sha256(
        ROOT / "docs" / "STRATEGY_B_STAGE_A_PROTOCOL.md"
    )
    assert bench_summary["decision"] == "STAGE_A_PASS"
    assert bench_summary["submission"] == summary["submission"]

    for query_path in sorted((BENCH_ROOT / "stage_a0" / "queries").glob("*.csv")):
        assert query_header(query_path) == QUERY_HEADER
    for query_path in sorted((BENCH_ROOT / "stage_a1" / "queries").glob("*.csv")):
        assert query_header(query_path) == QUERY_HEADER

    subprocess.run(
        ["sha256sum", "-c", str(ARTIFACT_ROOT / "SHA256SUMS.txt")],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    print("strategy-b Stage-A artifact tests passed")


if __name__ == "__main__":
    main()
