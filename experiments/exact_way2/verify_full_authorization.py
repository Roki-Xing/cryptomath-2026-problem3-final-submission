#!/usr/bin/env python3
"""Fail-closed validation for full exact-way2 authorization."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    FULL_AUTHORIZATION_SCHEMA,
    FULL_EXPECTED_ROUND_DISTRIBUTION_JSON,
    FULL_EXPECTED_RU_COUNT,
    ROOT,
    current_source_commit,
    current_source_tree_sha,
    sibling_json_path,
    read_json,
    require_clean_worktree,
    sha256_file,
    validate_full_selection_csv,
    validate_full_selection_json,
)

SUBMIT_SHA256 = "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e"


def require_match(name: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise SystemExit(f"authorization mismatch for {name}: actual={actual!r} expected={expected!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--binary", required=True)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--queries", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--jobs", required=True, type=int)
    args = parser.parse_args()

    payload = read_json(Path(args.authorization))
    if not isinstance(payload, dict):
        raise SystemExit("authorization must be a JSON object")
    require_clean_worktree(cwd=ROOT)

    require_match("schema", payload.get("schema"), FULL_AUTHORIZATION_SCHEMA)
    require_match("authorized", payload.get("authorized"), True)
    require_match("source_commit", payload.get("source_commit"), current_source_commit(cwd=ROOT))
    require_match("source_tree_sha", payload.get("source_tree_sha"), current_source_tree_sha(cwd=ROOT))
    require_match("source_tree_dirty", payload.get("source_tree_dirty"), False)
    require_match("binary_sha256", payload.get("binary_sha256"), sha256_file(Path(args.binary)))
    require_match("final_ru_sha256", payload.get("final_ru_sha256"), sha256_file(ROOT / "experiments/frozen/final_ru.csv"))
    require_match("final_queries_sha256", payload.get("final_queries_sha256"), sha256_file(ROOT / args.queries))
    require_match("frozen_snapshot_sha256", payload.get("frozen_snapshot_sha256"), sha256_file(ROOT / args.snapshot))
    selection_path = Path(args.selection)
    selection_summary = validate_full_selection_csv(selection_path, ROOT / "experiments/frozen/final_ru.csv")
    validate_full_selection_json(
        sibling_json_path(selection_path),
        expected_csv_sha256=str(selection_summary["selection_sha256"]),
        expected_row_count=int(selection_summary["row_count"]),
        expected_unique_ru_count=int(selection_summary["unique_ru_count"]),
        expected_round_distribution_json=dict(selection_summary["round_distribution_json"]),
        expected_rows=list(selection_summary["rows"]),
    )
    selection_sha = str(selection_summary["selection_sha256"])
    require_match("cpp_int_selection_sha256", payload.get("cpp_int_selection_sha256"), selection_sha)
    require_match("int128_crosscheck_selection_sha256", payload.get("int128_crosscheck_selection_sha256"), selection_sha)
    require_match("full_selection_sha256", payload.get("full_selection_sha256"), selection_sha)
    require_match("full_selection_row_count", int(payload.get("full_selection_row_count", -1)), FULL_EXPECTED_RU_COUNT)
    require_match("unique_ru_count", int(payload.get("unique_ru_count", -1)), FULL_EXPECTED_RU_COUNT)
    require_match("round_distribution", payload.get("round_distribution"), FULL_EXPECTED_ROUND_DISTRIBUTION_JSON)
    require_match("jobs", int(payload.get("jobs", -1)), args.jobs)
    require_match("submit_sha256", payload.get("submit_sha256"), SUBMIT_SHA256)
    require_match("full_4760_scope", payload.get("full_4760_scope"), True)
    require_match("stage_b_authorized", payload.get("stage_b_authorized"), False)
    require_match("new_way1_run_started", payload.get("new_way1_run_started"), False)
    print("full exact authorization verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
