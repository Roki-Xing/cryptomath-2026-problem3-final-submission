#!/usr/bin/env python3
"""Fail-closed validation for full exact-way2 authorization."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    FULL_AUTHORIZATION_SCHEMA,
    ROOT,
    current_source_commit,
    current_source_tree_sha,
    read_json,
    require_clean_worktree,
    sha256_file,
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
    require_match("final_queries_sha256", payload.get("final_queries_sha256"), sha256_file(ROOT / args.queries))
    require_match("frozen_snapshot_sha256", payload.get("frozen_snapshot_sha256"), sha256_file(ROOT / args.snapshot))
    selection_sha = sha256_file(Path(args.selection))
    require_match("cpp_int_selection_sha256", payload.get("cpp_int_selection_sha256"), selection_sha)
    require_match("int128_crosscheck_selection_sha256", payload.get("int128_crosscheck_selection_sha256"), selection_sha)
    require_match("jobs", int(payload.get("jobs", -1)), args.jobs)
    require_match("submit_sha256", payload.get("submit_sha256"), SUBMIT_SHA256)
    require_match("full_4760_scope", payload.get("full_4760_scope"), True)
    require_match("stage_b_authorized", payload.get("stage_b_authorized"), False)
    require_match("new_way1_run_started", payload.get("new_way1_run_started"), False)
    print("full exact authorization verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
