#!/usr/bin/env python3
"""Summarize pilot artifacts and build manifest/SHA inventory."""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from common import SUMMARY_SCHEMA, read_json, sha256_file, write_json


def categorize(path: Path) -> str:
    relative = str(path).replace("\\", "/")
    if relative in {
        "SUMMARY.json",
        "SUMMARY.md",
        "COMPARE.json",
        "COMPARISONS.csv",
        "MISMATCHES.csv",
        "PROVENANCE.json",
        "ENVIRONMENT.json",
        "PILOT_SELECTION.csv",
        "PILOT_SELECTION.json",
        "PROTOCOL.md",
        "WAY1_NUMERATOR_CHECK.csv",
    }:
        return "REQUIRED_SUMMARY"
    if relative in {
        "MANIFEST.json",
        "SHA256SUMS.txt",
        "SELECTOR_PROVENANCE.json",
        "COMPLEXITY_INPUT.csv",
        "SPOTCHECK_COORDINATES.csv",
    }:
        return "REQUIRED_MANIFEST"
    if relative.startswith("completed/"):
        return "PILOT_RAW_EVIDENCE"
    return "EXCLUDE_FROM_SUBMISSION_PACKAGE"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True)
    args = parser.parse_args()

    started = time.perf_counter()
    root = Path(args.artifact_root)
    compare = read_json(root / "COMPARE.json")
    selection = read_json(root / "PILOT_SELECTION.json")
    provenance = read_json(root / "PROVENANCE.json")
    if not isinstance(compare, dict) or not isinstance(selection, dict) or not isinstance(provenance, dict):
        raise SystemExit("invalid summary prerequisites")

    bundles = sorted(path for path in (root / "completed").glob("*") if path.is_dir())
    cpp_columns = 0
    int_columns = 0
    exact_cert_count = 0
    parseval_count = 0
    cpp_wall_sum = 0.0
    int_wall_sum = 0.0
    peak_rss = 0
    partial_or_orphan_artifact = 0
    for bundle_dir in bundles:
        done = read_json(bundle_dir / "DONE.json")
        column = read_json(bundle_dir / "column.json")
        if not isinstance(done, dict) or not isinstance(column, dict):
            raise SystemExit(f"invalid bundle: {bundle_dir}")
        backend = str(done["backend"])
        if backend == "cpp_int":
            cpp_columns += 1
            cpp_wall_sum += float(column["wall_seconds"])
            exact_cert_count += int(bool(column["certified_exact_dyadic"]))
            parseval_count += int(bool(column["parseval_pass"]))
        elif backend == "int128_checked":
            int_columns += 1
            int_wall_sum += float(column["wall_seconds"])
        peak_rss = max(peak_rss, int(column["peak_rss_bytes"]))
        for required in ("column.json", "endpoints.csv", "DONE.json"):
            if not (bundle_dir / required).exists():
                partial_or_orphan_artifact += 1

    frozen = compare["frozen_comparison"]
    status = "PILOT_PASS_READY_FOR_FULL_EXACT_WAY2_REVIEW"
    failure_checks = [
        selection["selected_columns"] != 344,
        selection["round_distribution"] != {"r1": 120, "r2": 128, "r3": 96},
        cpp_columns != 344,
        int_columns != 344,
        compare["cross_backend_digest_mismatch"] != 0,
        compare["cross_backend_endpoint_mismatch"] != 0,
        compare["cross_backend_state_count_mismatch"] != 0,
        compare["cross_backend_denominator_mismatch"] != 0,
        compare["cross_backend_parseval_mismatch"] != 0,
        compare["cross_backend_certificate_mismatch"] != 0,
        compare["cross_backend_way1_mismatch"] != 0,
        frozen["NOT_EQUAL"] != 0,
        frozen["PARSE_ERROR"] != 0,
        frozen["MISSING_ENDPOINT"] != 0,
        compare["duplicate_row_id"] != 0,
        compare["duplicate_ruv"] != 0,
        compare["duplicate_column_key"] != 0,
        compare["duplicate_backend_artifact"] != 0,
        compare["missing_row"] != 0,
        compare["extra_row"] != 0,
        exact_cert_count != 344,
        parseval_count != 344,
        compare["way1_spotcheck_rows"] != 18,
        compare["way1_spotcheck_mismatch"] != 0,
        partial_or_orphan_artifact != 0,
    ]
    if any(failure_checks):
        status = "PILOT_FAIL"

    summarizer_elapsed = time.perf_counter() - started
    summary = {
        "schema": SUMMARY_SCHEMA,
        "status": status,
        "selected_columns": selection["selected_columns"],
        "round_distribution": selection["round_distribution"],
        "cpp_int_completed_columns": cpp_columns,
        "int128_completed_columns": int_columns,
        "frozen_comparison": {
            "EXACT_EQUAL": frozen["EXACT_EQUAL"],
            "NOT_EQUAL": frozen["NOT_EQUAL"],
            "PARSE_ERROR": frozen["PARSE_ERROR"],
            "MISSING_ENDPOINT": frozen["MISSING_ENDPOINT"],
        },
        "total_endpoint_count": compare["selected_endpoint_rows"],
        "cross_backend_digest_mismatch": compare["cross_backend_digest_mismatch"],
        "cross_backend_endpoint_mismatch": compare["cross_backend_endpoint_mismatch"],
        "cross_backend_state_count_mismatch": compare["cross_backend_state_count_mismatch"],
        "cross_backend_denominator_mismatch": compare["cross_backend_denominator_mismatch"],
        "cross_backend_parseval_mismatch": compare["cross_backend_parseval_mismatch"],
        "cross_backend_certificate_mismatch": compare["cross_backend_certificate_mismatch"],
        "cross_backend_way1_mismatch": compare["cross_backend_way1_mismatch"],
        "exact_certificate_count": exact_cert_count,
        "parseval_count": parseval_count,
        "duplicate_row_id": compare["duplicate_row_id"],
        "duplicate_ruv": compare["duplicate_ruv"],
        "duplicate_column_key": compare["duplicate_column_key"],
        "duplicate_backend_artifact": compare["duplicate_backend_artifact"],
        "missing_row": compare["missing_row"],
        "extra_row": compare["extra_row"],
        "partial_or_orphan_artifact": partial_or_orphan_artifact,
        "way1_spotcheck_rows": compare["way1_spotcheck_rows"],
        "way1_spotcheck_numerator_mismatch": compare["way1_spotcheck_mismatch"],
        "selector_elapsed_wall": 0.0,
        "cpp_int_column_wall_sum": cpp_wall_sum,
        "int128_column_wall_sum": int_wall_sum,
        "total_column_wall_sum": cpp_wall_sum + int_wall_sum,
        "orchestrator_elapsed_wall": provenance["orchestrator_elapsed_wall"],
        "comparison_elapsed_wall": compare.get("comparison_elapsed_wall", 0.0),
        "summarizer_elapsed_wall": summarizer_elapsed,
        "total_pilot_elapsed_wall": provenance["orchestrator_elapsed_wall"]
        + compare.get("comparison_elapsed_wall", 0.0)
        + summarizer_elapsed,
        "peak_process_rss": provenance["peak_process_rss"],
        "peak_total_concurrent_rss": provenance["peak_total_concurrent_rss"],
        "jobs": provenance["jobs"],
    }
    write_json(root / "SUMMARY.json", summary)

    files = sorted(path for path in root.rglob("*") if path.is_file())
    sha_lines = [f"{sha256_file(path)}  ./{path.relative_to(root)}" for path in files if path.name != "SHA256SUMS.txt"]
    (root / "SHA256SUMS.txt").write_text("\n".join(sha_lines) + "\n", encoding="utf-8")
    write_json(
        root / "MANIFEST.json",
        {
            "schema": SUMMARY_SCHEMA,
            "status": status,
            "files": [
                {
                    "path": str(path.relative_to(root)).replace("\\", "/"),
                    "sha256": sha256_file(path),
                    "category": categorize(path.relative_to(root)),
                }
                for path in files
                if path.name != "SHA256SUMS.txt"
            ],
        },
    )

    lines = [
        "# Exact Way-2 Pilot Summary",
        "",
        f"- status: `{status}`",
        f"- selected columns: `{selection['selected_columns']}`",
        f"- round distribution: `{selection['round_distribution']}`",
        f"- cpp_int completed: `{cpp_columns}`",
        f"- int128 completed: `{int_columns}`",
        f"- EXACT_EQUAL: `{frozen['EXACT_EQUAL']}`",
        f"- NOT_EQUAL: `{frozen['NOT_EQUAL']}`",
        f"- PARSE_ERROR: `{frozen['PARSE_ERROR']}`",
        f"- MISSING_ENDPOINT: `{frozen['MISSING_ENDPOINT']}`",
        f"- cross-backend digest mismatch: `{compare['cross_backend_digest_mismatch']}`",
        f"- cross-backend endpoint mismatch: `{compare['cross_backend_endpoint_mismatch']}`",
        f"- exact certificate count: `{exact_cert_count}`",
        f"- parseval count: `{parseval_count}`",
        f"- duplicate row_id: `{compare['duplicate_row_id']}`",
        f"- duplicate (r,u,v): `{compare['duplicate_ruv']}`",
        f"- missing row: `{compare['missing_row']}`",
        f"- extra row: `{compare['extra_row']}`",
        f"- partial/orphan artifacts: `{partial_or_orphan_artifact}`",
        f"- way-1 numerator mismatch: `{compare['way1_spotcheck_mismatch']}`",
        f"- cpp_int column wall sum: `{cpp_wall_sum}`",
        f"- int128 column wall sum: `{int_wall_sum}`",
        f"- peak RSS bytes: `{peak_rss}`",
    ]
    (root / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
