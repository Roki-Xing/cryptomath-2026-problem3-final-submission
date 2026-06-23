#!/usr/bin/env python3
"""Reduce exact way-1 shard artifacts with strict range and provenance checks."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


REQUIRED_METADATA = {
    "schema",
    "implementation",
    "query_sha256",
    "range_start",
    "range_end",
    "plaintext_count",
    "permutation_evaluations",
    "u_parity_evaluations",
    "v_parity_evaluations",
    "logical_query_updates",
}
EXPECTED_HEADER = ["r", "u", "v", "numerator", "denominator"]


@dataclass(frozen=True)
class Shard:
    path: Path
    metadata: dict[str, str]
    rows: tuple[tuple[str, str, str, int, int], ...]

    @property
    def start(self) -> int:
        return int(self.metadata["range_start"])

    @property
    def end(self) -> int:
        return int(self.metadata["range_end"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-start", type=int, required=True)
    parser.add_argument("--expected-end", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("parts", nargs="+", type=Path)
    return parser.parse_args()


def read_shard(path: Path) -> Shard:
    metadata: dict[str, str] = {}
    csv_lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith("# "):
            key, separator, value = raw_line[2:].partition("=")
            if not separator or not key:
                raise ValueError(f"bad metadata line in {path}: {raw_line}")
            if key in metadata:
                raise ValueError(f"duplicate metadata key {key} in {path}")
            metadata[key] = value
        elif raw_line:
            csv_lines.append(raw_line)

    missing = REQUIRED_METADATA - metadata.keys()
    if missing:
        raise ValueError(f"missing metadata in {path}: {sorted(missing)}")
    if metadata["schema"] != "way1-exact-shard-v1":
        raise ValueError(f"unsupported schema in {path}: {metadata['schema']}")

    reader = csv.reader(csv_lines)
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ValueError(f"missing CSV rows in {path}") from exc
    if header != EXPECTED_HEADER:
        raise ValueError(f"bad CSV header in {path}: {header}")

    rows: list[tuple[str, str, str, int, int]] = []
    seen: set[tuple[str, str, str]] = set()
    for fields in reader:
        if len(fields) != len(EXPECTED_HEADER):
            raise ValueError(f"bad row in {path}: {fields}")
        key = tuple(fields[:3])
        if key in seen:
            raise ValueError(f"duplicate query row in {path}: {key}")
        seen.add(key)
        rows.append((fields[0], fields[1], fields[2], int(fields[3]), int(fields[4])))

    start = int(metadata["range_start"])
    end = int(metadata["range_end"])
    if start >= end:
        raise ValueError(f"empty or reversed range in {path}")
    if int(metadata["plaintext_count"]) != end - start:
        raise ValueError(f"plaintext_count mismatch in {path}")
    if any(row[4] != end - start for row in rows):
        raise ValueError(f"row denominator mismatch in {path}")
    return Shard(path=path, metadata=metadata, rows=tuple(rows))


def validate_and_sort(
    shards: list[Shard], expected_start: int, expected_end: int
) -> list[Shard]:
    ordered = sorted(shards, key=lambda shard: (shard.start, shard.end, str(shard.path)))
    if ordered[0].start != expected_start:
        raise ValueError(
            f"gap before first shard: expected {expected_start}, got {ordered[0].start}"
        )

    cursor = expected_start
    for shard in ordered:
        if shard.start < cursor:
            raise ValueError(
                f"overlap at {shard.path}: range starts {shard.start}, covered through {cursor}"
            )
        if shard.start > cursor:
            raise ValueError(
                f"gap before {shard.path}: expected start {cursor}, got {shard.start}"
            )
        cursor = shard.end
    if cursor != expected_end:
        raise ValueError(f"gap after final shard: expected end {expected_end}, got {cursor}")

    first = ordered[0]
    expected_keys = tuple(row[:3] for row in first.rows)
    for shard in ordered[1:]:
        if shard.metadata["implementation"] != first.metadata["implementation"]:
            raise ValueError("implementation mismatch across shards")
        if shard.metadata["query_sha256"] != first.metadata["query_sha256"]:
            raise ValueError("query_sha256 mismatch across shards")
        if tuple(row[:3] for row in shard.rows) != expected_keys:
            raise ValueError(f"query rows/order mismatch in {shard.path}")
    return ordered


def write_reduced(path: Path, shards: list[Shard]) -> None:
    first = shards[0]
    totals = {
        key: sum(int(shard.metadata[key]) for shard in shards)
        for key in (
            "plaintext_count",
            "permutation_evaluations",
            "u_parity_evaluations",
            "v_parity_evaluations",
            "logical_query_updates",
        )
    }
    numerators = [0] * len(first.rows)
    denominators = [0] * len(first.rows)
    for shard in shards:
        for index, row in enumerate(shard.rows):
            numerators[index] += row[3]
            denominators[index] += row[4]

    expected_denominator = shards[-1].end - shards[0].start
    if any(value != expected_denominator for value in denominators):
        raise ValueError("reduced denominator does not equal covered domain")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("# schema=way1-exact-reduced-v1\n")
        handle.write(f"# implementation={first.metadata['implementation']}\n")
        handle.write(f"# query_sha256={first.metadata['query_sha256']}\n")
        handle.write(f"# range_start={shards[0].start}\n")
        handle.write(f"# range_end={shards[-1].end}\n")
        for key, value in totals.items():
            handle.write(f"# {key}={value}\n")
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(EXPECTED_HEADER)
        for row, numerator, denominator in zip(
            first.rows, numerators, denominators, strict=True
        ):
            writer.writerow([row[0], row[1], row[2], numerator, denominator])


def main() -> None:
    args = parse_args()
    if args.expected_start >= args.expected_end:
        raise SystemExit("error: expected range must be non-empty")
    try:
        shards = [read_shard(path) for path in args.parts]
        ordered = validate_and_sort(shards, args.expected_start, args.expected_end)
        write_reduced(args.out, ordered)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc
    print(f"reduced_shards={len(ordered)}")
    print(f"range_start={args.expected_start}")
    print(f"range_end={args.expected_end}")
    print(f"query_rows={len(ordered[0].rows)}")


if __name__ == "__main__":
    main()
