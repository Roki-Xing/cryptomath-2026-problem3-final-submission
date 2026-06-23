#!/usr/bin/env python3
"""Select deterministic benchmark queries from the frozen query artifact only."""

from __future__ import annotations

import argparse
import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Query:
    row_id: int
    r: int
    u: str
    v: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--r", type=int, required=True, choices=(1, 2, 3))
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def load_queries(path: Path, rounds: int) -> list[Query]:
    queries: list[Query] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["r", "u", "v"]:
            raise ValueError(f"expected frozen r,u,v schema, got {reader.fieldnames}")
        for row_id, row in enumerate(reader, start=1):
            if int(row["r"]) != rounds:
                continue
            queries.append(
                Query(
                    row_id=row_id,
                    r=rounds,
                    u=f"0x{int(row['u'], 0):08x}",
                    v=f"0x{int(row['v'], 0):08x}",
                )
            )
    return queries


def selection_key(query: Query, seed: str) -> tuple[bytes, int]:
    payload = f"{seed}\0{query.row_id}\0{query.r}\0{query.u}\0{query.v}".encode()
    return hashlib.sha256(payload).digest(), query.row_id


def main() -> None:
    args = parse_args()
    try:
        if args.count <= 0:
            raise ValueError("--count must be positive")
        available = load_queries(args.source, args.r)
        if args.count > len(available):
            raise ValueError(
                f"requested {args.count} frozen queries for r={args.r}, "
                f"but only {len(available)} are available"
            )
        selected = sorted(available, key=lambda query: selection_key(query, args.seed))[
            : args.count
        ]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(["row_id", "r", "u", "v"])
            for query in selected:
                writer.writerow([query.row_id, query.r, query.u, query.v])
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc

    digest = hashlib.sha256(args.out.read_bytes()).hexdigest()
    print(f"query_rows={len(selected)}")
    print(f"query_sha256={digest}")
    print(f"source={args.source}")


if __name__ == "__main__":
    main()
