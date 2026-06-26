#!/usr/bin/env python3
"""Compare pilot exact-way2 artifacts against the frozen decimal snapshot."""

from __future__ import annotations

import argparse
import csv
import time
from collections import Counter
from pathlib import Path

from common import COMPARE_SCHEMA, ROOT, compare_dyadic_to_decimal, read_json, write_csv, write_json


def load_selection(path: Path) -> tuple[list[dict[str, str]], set[tuple[int, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return rows, {(int(row["r"]), row["u"].lower()) for row in rows}


def load_snapshot_rows(path: Path, selected_keys: set[tuple[int, str]]) -> tuple[list[dict[str, str]], dict[str, int]]:
    rows: list[dict[str, str]] = []
    row_ids: set[str] = set()
    triples: set[tuple[int, str, str]] = set()
    counts = {
        "duplicate_row_id": 0,
        "duplicate_ruv": 0,
    }
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            key = (int(row["r"]), row["u"].lower())
            if key not in selected_keys:
                continue
            triple = (key[0], key[1], row["v"].lower())
            row_id = row["row_id"]
            if row_id in row_ids:
                counts["duplicate_row_id"] += 1
                continue
            if triple in triples:
                counts["duplicate_ruv"] += 1
                continue
            row_ids.add(row_id)
            triples.add(triple)
            rows.append(
                {
                    "row_id": row_id,
                    "r": str(key[0]),
                    "u": key[1],
                    "v": row["v"].lower(),
                    "frozen_way2_ve": row["frozen_way2_ve"],
                }
            )
    rows.sort(key=lambda row: (int(row["r"]), row["u"], row["v"], row["row_id"]))
    return rows, counts


def load_backend(root: Path, backend: str) -> tuple[dict[tuple[int, str], dict[str, object]], dict[tuple[int, str, str], dict[str, str]], dict[str, int]]:
    columns: dict[tuple[int, str], dict[str, object]] = {}
    endpoints: dict[tuple[int, str, str], dict[str, str]] = {}
    counts = {
        "duplicate_column_key": 0,
        "duplicate_backend_artifact": 0,
        "duplicate_row_id": 0,
        "duplicate_ruv": 0,
    }
    row_ids: set[str] = set()
    triples: set[tuple[int, str, str]] = set()
    for bundle_dir in sorted((root / "completed").glob(f"*_{backend}")):
        done = read_json(bundle_dir / "DONE.json")
        column = read_json(bundle_dir / "column.json")
        if not isinstance(done, dict) or not isinstance(column, dict):
            raise SystemExit(f"invalid bundle payload: {bundle_dir}")
        key = (int(done["r"]), str(done["u"]).lower())
        if key in columns:
            counts["duplicate_backend_artifact"] += 1
            continue
        columns[key] = {"done": done, "column": column}
        with (bundle_dir / "endpoints.csv").open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                row_id = row["row_id"]
                triple = (int(row["r"]), row["u"].lower(), row["v"].lower())
                if row_id in row_ids:
                    counts["duplicate_row_id"] += 1
                    continue
                if triple in triples:
                    counts["duplicate_ruv"] += 1
                    continue
                row_ids.add(row_id)
                triples.add(triple)
                endpoints[triple] = row
    return columns, endpoints, counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--snapshot", required=True)
    args = parser.parse_args()

    started = time.perf_counter()
    root = Path(args.artifact_root)
    selection_path = root / "PILOT_SELECTION.csv"
    selection_rows, selected_keys = load_selection(selection_path)
    snapshot_rows, snapshot_duplicates = load_snapshot_rows(Path(args.snapshot), selected_keys)
    cpp_columns, cpp_endpoints, cpp_duplicates = load_backend(root, "cpp_int")
    int_columns, int_endpoints, int_duplicates = load_backend(root, "int128_checked")

    expected_endpoint_keys = {
        (int(row["r"]), row["u"].lower(), row["v"].lower())
        for row in snapshot_rows
    }
    extra_rows = 0
    for triple in cpp_endpoints:
        if triple not in expected_endpoint_keys:
            extra_rows += 1
    for triple in int_endpoints:
        if triple not in expected_endpoint_keys:
            extra_rows += 1

    comparison_counts = Counter(
        {
            "EXACT_EQUAL": 0,
            "NOT_EQUAL": 0,
            "PARSE_ERROR": 0,
            "MISSING_ENDPOINT": 0,
        }
    )
    comparisons: list[dict[str, object]] = []
    cross_backend_digest_mismatch = 0
    cross_backend_endpoint_mismatch = 0
    cross_backend_state_count_mismatch = 0
    cross_backend_denominator_mismatch = 0
    cross_backend_parseval_mismatch = 0
    cross_backend_certificate_mismatch = 0
    cross_backend_way1_mismatch = 0
    missing_rows = 0

    for row in snapshot_rows:
        r = int(row["r"])
        u = row["u"].lower()
        v = row["v"].lower()
        key = (r, u)
        triple = (r, u, v)
        cpp_bundle = cpp_columns.get(key)
        int_bundle = int_columns.get(key)
        cpp_endpoint = cpp_endpoints.get(triple)
        int_endpoint = int_endpoints.get(triple)

        status = "EXACT_EQUAL"
        if cpp_bundle is None or int_bundle is None:
            status = "MISSING_ENDPOINT"
            missing_rows += 1
        else:
            cpp_column = cpp_bundle["column"]
            int_column = int_bundle["column"]
            if not cpp_column["certified_exact_dyadic"] or not cpp_column["parseval_pass"]:
                status = "MISSING_ENDPOINT"
                missing_rows += 1
            elif cpp_endpoint is None or int_endpoint is None:
                status = "MISSING_ENDPOINT"
                missing_rows += 1
            else:
                status = compare_dyadic_to_decimal(
                    int(cpp_endpoint["numerator"]),
                    int(cpp_endpoint["denominator_exp2"]),
                    row["frozen_way2_ve"],
                )

            digest_match = int(
                cpp_column["canonical_column_digest"] == int_column["canonical_column_digest"]
            )
            state_count_match = int(cpp_column["state_count"] == int_column["state_count"])
            denominator_match = int(
                cpp_endpoint is not None
                and int_endpoint is not None
                and cpp_endpoint["denominator_exp2"] == int_endpoint["denominator_exp2"]
            )
            parseval_match = int(cpp_column["parseval_pass"] == int_column["parseval_pass"])
            certificate_match = int(
                cpp_column["certified_exact_dyadic"] == int_column["certified_exact_dyadic"]
            )
            endpoint_match = int(
                cpp_endpoint is not None
                and int_endpoint is not None
                and cpp_endpoint["numerator"] == int_endpoint["numerator"]
            )
            way1_match = int(
                cpp_endpoint is not None
                and int_endpoint is not None
                and cpp_endpoint["way1_normalized_numerator"]
                == int_endpoint["way1_normalized_numerator"]
            )
            sum_squares_match = int(cpp_column["sum_squares"] == int_column["sum_squares"])
            expected_sum_squares_match = int(
                cpp_column["expected_sum_squares"] == int_column["expected_sum_squares"]
            )
            completed_rounds_match = int(
                cpp_column["completed_rounds"] == int_column["completed_rounds"]
            )

            cross_backend_digest_mismatch += int(not digest_match)
            cross_backend_state_count_mismatch += int(not state_count_match)
            cross_backend_denominator_mismatch += int(not denominator_match)
            cross_backend_parseval_mismatch += int(not parseval_match)
            cross_backend_certificate_mismatch += int(not certificate_match)
            cross_backend_endpoint_mismatch += int(not endpoint_match)
            cross_backend_way1_mismatch += int(not way1_match)

            comparisons.append(
                {
                    "row_id": row["row_id"],
                    "r": r,
                    "u": u,
                    "v": v,
                    "comparison_status": status,
                    "cpp_int_int128_digest_match": digest_match,
                    "cpp_int_int128_endpoint_match": endpoint_match,
                    "cpp_int_int128_state_count_match": state_count_match,
                    "cpp_int_int128_denominator_match": denominator_match,
                    "cpp_int_int128_parseval_match": parseval_match,
                    "cpp_int_int128_certificate_match": certificate_match,
                    "cpp_int_int128_way1_match": way1_match,
                    "cpp_int_int128_sum_squares_match": sum_squares_match,
                    "cpp_int_int128_expected_sum_squares_match": expected_sum_squares_match,
                    "cpp_int_int128_completed_rounds_match": completed_rounds_match,
                    "cpp_int_numerator": "" if cpp_endpoint is None else cpp_endpoint["numerator"],
                    "int128_numerator": "" if int_endpoint is None else int_endpoint["numerator"],
                    "denominator_exp2": "" if cpp_endpoint is None else cpp_endpoint["denominator_exp2"],
                }
            )
            comparison_counts[status] += 1
            continue

        comparisons.append(
            {
                "row_id": row["row_id"],
                "r": r,
                "u": u,
                "v": v,
                "comparison_status": status,
                "cpp_int_int128_digest_match": 0,
                "cpp_int_int128_endpoint_match": 0,
                "cpp_int_int128_state_count_match": 0,
                "cpp_int_int128_denominator_match": 0,
                "cpp_int_int128_parseval_match": 0,
                "cpp_int_int128_certificate_match": 0,
                "cpp_int_int128_way1_match": 0,
                "cpp_int_int128_sum_squares_match": 0,
                "cpp_int_int128_expected_sum_squares_match": 0,
                "cpp_int_int128_completed_rounds_match": 0,
                "cpp_int_numerator": "",
                "int128_numerator": "",
                "denominator_exp2": "",
            }
        )
        comparison_counts[status] += 1

    way1_rows = []
    with (ROOT / "experiments/spotcheck/exact_spotcheck.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            key = (int(row["r"]), row["u"].lower(), row["v"].lower())
            endpoint = cpp_endpoints.get(key)
            if endpoint is None:
                status = "MISSING_ENDPOINT"
            else:
                expected = int(row["numerator"])
                actual = int(endpoint["way1_normalized_numerator"])
                status = "MATCH" if expected == actual else "MISMATCH"
            way1_rows.append({**row, "status_exact_way2": status})

    comparisons.sort(key=lambda row: (int(row["r"]), str(row["u"]), str(row["v"]), str(row["row_id"])))
    comparison_fields = [
        "row_id",
        "r",
        "u",
        "v",
        "comparison_status",
        "cpp_int_int128_digest_match",
        "cpp_int_int128_endpoint_match",
        "cpp_int_int128_state_count_match",
        "cpp_int_int128_denominator_match",
        "cpp_int_int128_parseval_match",
        "cpp_int_int128_certificate_match",
        "cpp_int_int128_way1_match",
        "cpp_int_int128_sum_squares_match",
        "cpp_int_int128_expected_sum_squares_match",
        "cpp_int_int128_completed_rounds_match",
        "cpp_int_numerator",
        "int128_numerator",
        "denominator_exp2",
    ]
    write_csv(root / "COMPARISONS.csv", comparison_fields, comparisons)
    write_csv(
        root / "MISMATCHES.csv",
        comparison_fields,
        [row for row in comparisons if row["comparison_status"] != "EXACT_EQUAL"],
    )
    write_csv(
        root / "WAY1_NUMERATOR_CHECK.csv",
        list(way1_rows[0].keys()) if way1_rows else ["r", "u", "v", "status_exact_way2"],
        way1_rows,
    )
    total_selected_endpoints = len(snapshot_rows)
    if sum(comparison_counts.values()) != total_selected_endpoints:
        raise SystemExit("comparison totals do not match selected endpoint count")

    write_json(
        root / "COMPARE.json",
        {
            "schema": COMPARE_SCHEMA,
            "selected_columns": len(selection_rows),
            "selected_endpoint_rows": total_selected_endpoints,
            "frozen_comparison": {
                "EXACT_EQUAL": comparison_counts["EXACT_EQUAL"],
                "NOT_EQUAL": comparison_counts["NOT_EQUAL"],
                "PARSE_ERROR": comparison_counts["PARSE_ERROR"],
                "MISSING_ENDPOINT": comparison_counts["MISSING_ENDPOINT"],
            },
            "cpp_int_columns": len(cpp_columns),
            "int128_columns": len(int_columns),
            "cross_backend_digest_mismatch": cross_backend_digest_mismatch,
            "cross_backend_endpoint_mismatch": cross_backend_endpoint_mismatch,
            "cross_backend_state_count_mismatch": cross_backend_state_count_mismatch,
            "cross_backend_denominator_mismatch": cross_backend_denominator_mismatch,
            "cross_backend_parseval_mismatch": cross_backend_parseval_mismatch,
            "cross_backend_certificate_mismatch": cross_backend_certificate_mismatch,
            "cross_backend_way1_mismatch": cross_backend_way1_mismatch,
            "duplicate_row_id": snapshot_duplicates["duplicate_row_id"]
            + cpp_duplicates["duplicate_row_id"]
            + int_duplicates["duplicate_row_id"],
            "duplicate_ruv": snapshot_duplicates["duplicate_ruv"]
            + cpp_duplicates["duplicate_ruv"]
            + int_duplicates["duplicate_ruv"],
            "duplicate_column_key": cpp_duplicates["duplicate_column_key"] + int_duplicates["duplicate_column_key"],
            "duplicate_backend_artifact": cpp_duplicates["duplicate_backend_artifact"]
            + int_duplicates["duplicate_backend_artifact"],
            "missing_row": missing_rows,
            "extra_row": extra_rows,
            "way1_spotcheck_rows": len(way1_rows),
            "way1_spotcheck_mismatch": sum(row["status_exact_way2"] != "MATCH" for row in way1_rows),
            "comparison_elapsed_wall": time.perf_counter() - started,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
