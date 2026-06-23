#!/usr/bin/env python3
"""Exercise exact way-1 shard reduction success and fail-closed paths."""

from __future__ import annotations

import csv
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REDUCER = ROOT / "bench" / "way1" / "reduce_shards.py"
QUERY_SHA = "a" * 64
HEADER = ["r", "u", "v", "numerator", "denominator"]
QUERIES = [
    ("2", "0x00002000", "0x08880000"),
    ("2", "0x20000000", "0x00000888"),
]


def write_part(
    path: Path,
    *,
    start: int,
    end: int,
    numerators: tuple[int, int],
    query_sha: str = QUERY_SHA,
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("# schema=way1-exact-shard-v1\n")
        handle.write("# implementation=grouped_uv\n")
        handle.write(f"# query_sha256={query_sha}\n")
        handle.write(f"# range_start={start}\n")
        handle.write(f"# range_end={end}\n")
        handle.write(f"# plaintext_count={end - start}\n")
        handle.write(f"# permutation_evaluations={end - start}\n")
        handle.write(f"# u_parity_evaluations={2 * (end - start)}\n")
        handle.write(f"# v_parity_evaluations={2 * (end - start)}\n")
        handle.write(f"# logical_query_updates={2 * (end - start)}\n")
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADER)
        for query, numerator in zip(QUERIES, numerators, strict=True):
            writer.writerow([*query, numerator, end - start])


def run_reducer(out_path: Path, *parts: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python3",
            "-X",
            "utf8",
            str(REDUCER),
            "--expected-start",
            "0",
            "--expected-end",
            "16",
            "--out",
            str(out_path),
            *map(str, parts),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def read_rows(path: Path) -> list[dict[str, str]]:
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    return list(csv.DictReader(lines))


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        first = tmp_path / "first.csv"
        second = tmp_path / "second.csv"
        out_path = tmp_path / "reduced.csv"
        write_part(first, start=0, end=7, numerators=(3, -1))
        write_part(second, start=7, end=16, numerators=(5, 7))

        completed = run_reducer(out_path, second, first)
        assert completed.returncode == 0, completed.stderr
        rows = read_rows(out_path)
        assert [int(row["numerator"]) for row in rows] == [8, 6]
        assert [int(row["denominator"]) for row in rows] == [16, 16]
        output = out_path.read_text(encoding="utf-8")
        assert "# range_start=0" in output
        assert "# range_end=16" in output
        assert "# query_sha256=" + QUERY_SHA in output

        overlap = tmp_path / "overlap.csv"
        write_part(overlap, start=6, end=16, numerators=(5, 7))
        failed = run_reducer(out_path, first, overlap)
        assert failed.returncode != 0
        assert "overlap" in failed.stderr

        gap = tmp_path / "gap.csv"
        write_part(gap, start=8, end=16, numerators=(5, 7))
        failed = run_reducer(out_path, first, gap)
        assert failed.returncode != 0
        assert "gap" in failed.stderr

        mismatched_hash = tmp_path / "mismatched_hash.csv"
        write_part(
            mismatched_hash,
            start=7,
            end=16,
            numerators=(5, 7),
            query_sha="b" * 64,
        )
        failed = run_reducer(out_path, first, mismatched_hash)
        assert failed.returncode != 0
        assert "query_sha256" in failed.stderr

        failed = run_reducer(out_path, first, first, second)
        assert failed.returncode != 0
        assert "overlap" in failed.stderr

    print("exact shard reduction tests passed")


if __name__ == "__main__":
    main()
