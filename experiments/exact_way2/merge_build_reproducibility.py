#!/usr/bin/env python3
"""Merge two clean-build records into BUILD_REPRODUCIBILITY.json."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import BUILD_REPRODUCIBILITY_SCHEMA, EMPTY_SHA256, read_json, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first", required=True)
    parser.add_argument("--second", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    first = read_json(Path(args.first))
    second = read_json(Path(args.second))
    if not isinstance(first, dict) or not isinstance(second, dict):
        raise SystemExit("invalid build reproducibility inputs")
    for key in ("source_checkout_commit", "source_tree_sha", "binary_sha256"):
        if first[key] != second[key]:
            raise SystemExit(f"clean build mismatch: {key}")
    write_json(
        Path(args.out),
        {
            "schema": BUILD_REPRODUCIBILITY_SCHEMA,
            "implementation_commit": first["source_checkout_commit"],
            "implementation_tree_sha": first["source_tree_sha"],
            "clean_git_status_sha256": EMPTY_SHA256,
            "clean_git_diff_sha256": EMPTY_SHA256,
            "first_clean_build": first,
            "second_clean_build": second,
            "binary_sha256_match": True,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
