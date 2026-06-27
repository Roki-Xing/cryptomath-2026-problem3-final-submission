#!/usr/bin/env python3
"""Summarize the full exact-way2 recompute artifacts."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from common import FULL_SUMMARY_SCHEMA, read_json, write_json, write_text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True)
    args = parser.parse_args()

    started = time.perf_counter()
    root = Path(args.artifact_root)
    compare = read_json(root / "COMPARE.json")
    selection = read_json(root / "FULL_SELECTION.json")
    runner = read_json(root / "RUNNER.json")
    pipeline = read_json(root / "PIPELINE.json")
    if not all(isinstance(payload, dict) for payload in (compare, selection, runner, pipeline)):
        raise SystemExit("invalid summary prerequisites")

    bundles = sorted(path for path in (root / "completed").glob("*") if path.is_dir())
    cpp_columns = 0
    int_columns = 0
    cert_cpp = 0
    cert_int = 0
    parseval_cpp = 0
    parseval_int = 0
    partial_or_orphan_artifact = 0
    for bundle_dir in bundles:
        done = read_json(bundle_dir / "DONE.json")
        column = read_json(bundle_dir / "column.json")
        if not isinstance(done, dict) or not isinstance(column, dict):
            raise SystemExit(f"invalid bundle: {bundle_dir}")
        backend = str(done["backend"])
        if backend == "cpp_int":
            cpp_columns += 1
            cert_cpp += int(bool(column["certified_exact_dyadic"]))
            parseval_cpp += int(bool(column["parseval_pass"]))
        elif backend == "int128_checked":
            int_columns += 1
            cert_int += int(bool(column["certified_exact_dyadic"]))
            parseval_int += int(bool(column["parseval_pass"]))
        for required in ("column.json", "endpoints.csv", "DONE.json"):
            if not (bundle_dir / required).exists():
                partial_or_orphan_artifact += 1

    frozen = compare["frozen_comparison"]
    selected_columns = int(selection["selected_columns"])
    distribution = selection["round_distribution"]
    status = "FULL_EXACT_WAY2_REVIEW"
    failure_checks = [
        selected_columns != 4760,
        distribution != {"r1": 120, "r2": 4544, "r3": 96},
        cpp_columns != 4760,
        int_columns != 4760,
        compare["cross_backend_canonical_column_digest_mismatch"] != 0,
        compare["cross_backend_state_count_mismatch"] != 0,
        compare["cross_backend_denominator_exp2_mismatch"] != 0,
        compare["cross_backend_sum_squares_mismatch"] != 0,
        compare["cross_backend_expected_sum_squares_mismatch"] != 0,
        compare["cross_backend_completed_rounds_mismatch"] != 0,
        compare["cross_backend_certified_no_truncation_mismatch"] != 0,
        compare["cross_backend_certified_exact_dyadic_mismatch"] != 0,
        compare["cross_backend_parseval_pass_mismatch"] != 0,
        compare["cross_backend_endpoint_numerator_mismatch"] != 0,
        compare["cross_backend_way1_normalized_numerator_mismatch"] != 0,
        frozen["EXACT_EQUAL"] != 138338,
        frozen["NOT_EQUAL"] != 0,
        frozen["PARSE_ERROR"] != 0,
        frozen["MISSING_ENDPOINT"] != 0,
        compare["duplicate_row_id"] != 0,
        compare["duplicate_ruv"] != 0,
        compare["duplicate_column_key"] != 0,
        compare["duplicate_backend_artifact"] != 0,
        compare["missing_row"] != 0,
        compare["extra_row"] != 0,
        cert_cpp != 4760,
        cert_int != 4760,
        parseval_cpp != 4760,
        parseval_int != 4760,
        compare["way1_spotcheck_rows"] != 18,
        compare["way1_spotcheck_mismatch"] != 0,
        partial_or_orphan_artifact != 0,
    ]
    if any(failure_checks):
        status = "FULL_EXACT_WAY2_FAIL"

    summarizer_elapsed = time.perf_counter() - started
    summary = {
        "schema": FULL_SUMMARY_SCHEMA,
        "status": status,
        "selected_columns": selected_columns,
        "round_distribution": distribution,
        "cpp_int_completed_columns": cpp_columns,
        "int128_completed_columns": int_columns,
        "frozen_comparison": {
            "EXACT_EQUAL": frozen["EXACT_EQUAL"],
            "NOT_EQUAL": frozen["NOT_EQUAL"],
            "PARSE_ERROR": frozen["PARSE_ERROR"],
            "MISSING_ENDPOINT": frozen["MISSING_ENDPOINT"],
        },
        "total_endpoint_count": compare["selected_endpoint_rows"],
        "cross_backend_canonical_column_digest_mismatch": compare["cross_backend_canonical_column_digest_mismatch"],
        "cross_backend_state_count_mismatch": compare["cross_backend_state_count_mismatch"],
        "cross_backend_denominator_exp2_mismatch": compare["cross_backend_denominator_exp2_mismatch"],
        "cross_backend_sum_squares_mismatch": compare["cross_backend_sum_squares_mismatch"],
        "cross_backend_expected_sum_squares_mismatch": compare["cross_backend_expected_sum_squares_mismatch"],
        "cross_backend_completed_rounds_mismatch": compare["cross_backend_completed_rounds_mismatch"],
        "cross_backend_certified_no_truncation_mismatch": compare["cross_backend_certified_no_truncation_mismatch"],
        "cross_backend_certified_exact_dyadic_mismatch": compare["cross_backend_certified_exact_dyadic_mismatch"],
        "cross_backend_parseval_pass_mismatch": compare["cross_backend_parseval_pass_mismatch"],
        "cross_backend_endpoint_numerator_mismatch": compare["cross_backend_endpoint_numerator_mismatch"],
        "cross_backend_way1_normalized_numerator_mismatch": compare["cross_backend_way1_normalized_numerator_mismatch"],
        "certified_exact_dyadic_cpp_int": cert_cpp,
        "certified_exact_dyadic_int128_checked": cert_int,
        "parseval_cpp_int": parseval_cpp,
        "parseval_int128_checked": parseval_int,
        "duplicate_row_id": compare["duplicate_row_id"],
        "duplicate_ruv": compare["duplicate_ruv"],
        "duplicate_column_key": compare["duplicate_column_key"],
        "duplicate_backend_artifact": compare["duplicate_backend_artifact"],
        "missing_row": compare["missing_row"],
        "extra_row": compare["extra_row"],
        "partial_or_orphan_artifact": partial_or_orphan_artifact,
        "way1_spotcheck_rows": compare["way1_spotcheck_rows"],
        "way1_spotcheck_numerator_mismatch": compare["way1_spotcheck_mismatch"],
        "selector_elapsed_wall": pipeline["selector_elapsed_wall"],
        "cpp_int_column_wall_sum": runner["cpp_int_column_wall_sum"],
        "int128_column_wall_sum": runner["int128_column_wall_sum"],
        "total_column_wall_sum": runner["cpp_int_column_wall_sum"] + runner["int128_column_wall_sum"],
        "orchestrator_elapsed_wall": pipeline["orchestrator_elapsed_wall"],
        "comparison_elapsed_wall": compare.get("comparison_elapsed_wall", 0.0),
        "summarizer_elapsed_wall": summarizer_elapsed,
        "total_full_elapsed_wall": pipeline["total_full_elapsed_wall"],
        "peak_process_rss": pipeline["peak_process_rss"],
        "peak_total_concurrent_rss": pipeline["peak_total_concurrent_rss"],
        "jobs": runner["jobs"],
    }
    write_json(root / "SUMMARY.json", summary)
    lines = [
        "# Exact Way-2 Full Summary",
        "",
        f"- status: `{status}`",
        f"- selected columns: `{selected_columns}`",
        f"- round distribution: `{distribution}`",
        f"- cpp_int completed: `{cpp_columns}`",
        f"- int128 completed: `{int_columns}`",
        f"- EXACT_EQUAL: `{frozen['EXACT_EQUAL']}`",
        f"- NOT_EQUAL: `{frozen['NOT_EQUAL']}`",
        f"- PARSE_ERROR: `{frozen['PARSE_ERROR']}`",
        f"- MISSING_ENDPOINT: `{frozen['MISSING_ENDPOINT']}`",
        f"- certified_exact_dyadic cpp_int/int128: `{cert_cpp}/{cert_int}`",
        f"- parseval cpp_int/int128: `{parseval_cpp}/{parseval_int}`",
        f"- total full elapsed wall: `{pipeline['total_full_elapsed_wall']}`",
        f"- peak RSS bytes: `{pipeline['peak_process_rss']}`",
    ]
    write_text(root / "SUMMARY.md", "\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
