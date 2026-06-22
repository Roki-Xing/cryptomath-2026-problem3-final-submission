#!/usr/bin/env python3
"""Freeze deterministic query artifacts from the current submit file."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


EXPECTED_SUBMIT_SHA256 = "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e"
EXPECTED_QUERY_COUNT = 138338
EXPECTED_UNIQUE_RU = 4760
FROZEN_TOTAL_SCORE = "105843.622442471292742994"
FROZEN_MAX_GENERATED_TRANSITIONS_PER_RU = 7578152
FROZEN_CERTIFIED_ROWS = 138338
FROZEN_WAY2_MISMATCH = 0
FROZEN_EXACT_SPOTCHECK_COUNT = 18
FROZEN_EXACT_SPOTCHECK_MISMATCH = 0

SUBMIT_RE = re.compile(
    r"^@\(\s*(?P<r>\d+)\s*,\s*(?P<u>0x[0-9a-fA-F]+|\d+)\s*,\s*"
    r"(?P<v>0x[0-9a-fA-F]+|\d+)\s*,\s*[^,]+\s*,\s*[^)]+\s*\)$"
)


@dataclass(frozen=True, order=True)
class Query:
    r: int
    u: int
    v: int


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed CLI arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submit", default="submit.txt", help="Submission file used as the only query source.")
    parser.add_argument("--out-dir", default="experiments/frozen", help="Directory for frozen artifacts.")
    parser.add_argument("--expected-submit-sha256", default=EXPECTED_SUBMIT_SHA256)
    parser.add_argument("--expected-query-count", type=int, default=EXPECTED_QUERY_COUNT)
    parser.add_argument("--expected-unique-ru", type=int, default=EXPECTED_UNIQUE_RU)
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    """Compute a file SHA-256 digest.

    Args:
        path: File to hash.

    Returns:
        Lowercase hexadecimal SHA-256 digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_queries(path: Path) -> list[Query]:
    """Parse and deterministically order query coordinates from submit.txt.

    Args:
        path: Submission file.

    Returns:
        Queries sorted by numeric ``(r, u, v)``.
    """
    queries: list[Query] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = SUBMIT_RE.match(stripped)
        if not match:
            raise ValueError(f"bad submit line {line_number}: {stripped}")
        queries.append(
            Query(
                r=int(match.group("r")),
                u=int(match.group("u"), 0),
                v=int(match.group("v"), 0),
            )
        )
    return sorted(queries)


def write_csv(path: Path, header: list[str], rows: list[tuple[object, ...]]) -> None:
    """Write a deterministic UTF-8 CSV with LF line endings.

    Args:
        path: Output CSV path.
        header: Column names.
        rows: Data rows.
    """
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def write_json(path: Path, payload: object) -> None:
    """Write stable, human-readable JSON.

    Args:
        path: Output JSON path.
        payload: JSON-serializable value.
    """
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    """Generate and validate the frozen baseline artifacts.

    Returns:
        Exit code 0 after all expected counts and hashes match.
    """
    args = parse_args()
    submit_path = Path(args.submit)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    submit_sha256 = file_sha256(submit_path)
    if submit_sha256 != args.expected_submit_sha256:
        raise SystemExit(
            f"submit SHA-256 mismatch: expected {args.expected_submit_sha256}, got {submit_sha256}"
        )

    queries = load_queries(submit_path)
    unique_ru = sorted({(query.r, query.u) for query in queries})
    if len(queries) != args.expected_query_count:
        raise SystemExit(f"query count mismatch: expected {args.expected_query_count}, got {len(queries)}")
    if len(unique_ru) != args.expected_unique_ru:
        raise SystemExit(f"unique (r,u) mismatch: expected {args.expected_unique_ru}, got {len(unique_ru)}")

    queries_path = out_dir / "final_queries.csv"
    ru_path = out_dir / "final_ru.csv"
    baseline_path = out_dir / "BASELINE.json"
    checksums_path = out_dir / "SHA256SUMS.txt"

    write_csv(
        queries_path,
        ["r", "u", "v"],
        [(query.r, f"0x{query.u:08x}", f"0x{query.v:08x}") for query in queries],
    )
    write_csv(ru_path, ["r", "u"], [(r, f"0x{u:08x}") for r, u in unique_ru])

    baseline = {
        "schema_version": 1,
        "source": {
            "description": "Query coordinates parsed from the frozen submission file.",
            "path": str(submit_path),
            "sha256": submit_sha256,
        },
        "frozen_numbers": {
            "valid_count": args.expected_query_count,
            "total_score": FROZEN_TOTAL_SCORE,
            "unique_ru": args.expected_unique_ru,
            "max_generated_transitions_per_ru": FROZEN_MAX_GENERATED_TRANSITIONS_PER_RU,
            "certified_rows": FROZEN_CERTIFIED_ROWS,
            "way2_mismatch": FROZEN_WAY2_MISMATCH,
            "exact_spotcheck_count": FROZEN_EXACT_SPOTCHECK_COUNT,
            "exact_spotcheck_mismatch": FROZEN_EXACT_SPOTCHECK_MISMATCH,
        },
        "artifacts": {
            "final_queries.csv": {
                "columns": ["r", "u", "v"],
                "data_rows": len(queries),
                "sha256": file_sha256(queries_path),
            },
            "final_ru.csv": {
                "columns": ["r", "u"],
                "data_rows": len(unique_ru),
                "sha256": file_sha256(ru_path),
            },
        },
        "generation": {
            "command": (
                "python3 -X utf8 experiments/freeze_baseline.py "
                "--submit submit.txt --out-dir experiments/frozen"
            ),
            "ordering": "numeric ascending by (r,u,v); final_ru deduplicated then numeric ascending by (r,u)",
        },
    }
    write_json(baseline_path, baseline)

    checksum_paths = [baseline_path, queries_path, ru_path]
    checksum_lines = [f"{file_sha256(path)}  {path.name}" for path in sorted(checksum_paths)]
    checksums_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    print(f"submit_sha256={submit_sha256}")
    print(f"final_queries_rows={len(queries)}")
    print(f"final_ru_rows={len(unique_ru)}")
    print(f"frozen_dir={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
