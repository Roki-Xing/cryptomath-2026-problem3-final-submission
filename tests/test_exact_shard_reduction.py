#!/usr/bin/env python3
"""Exercise manifest-bound exact way-1 shard reduction and corruption rejection."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REDUCER = ROOT / "bench" / "way1" / "reduce_shards.py"
QUERY_SHA = "a" * 64
PROGRAM_SHA = "b" * 64
HEADER = ["r", "u", "v", "numerator", "denominator"]
QUERIES = [
    ("2", "0x00002000", "0x08880000"),
    ("2", "0x20000000", "0x00000888"),
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_part(
    path: Path,
    *,
    start: int,
    end: int,
    numerators: tuple[int, int],
    query_sha: str = QUERY_SHA,
    program_sha: str = PROGRAM_SHA,
    implementation: str = "grouped_uv",
    queries: list[tuple[str, str, str]] = QUERIES,
) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("# schema=way1-exact-shard-v2\n")
        handle.write(f"# implementation={implementation}\n")
        handle.write(f"# query_sha256={query_sha}\n")
        handle.write(f"# program_sha256={program_sha}\n")
        handle.write(f"# range_start={start}\n")
        handle.write(f"# range_end={end}\n")
        handle.write(f"# plaintext_count={end - start}\n")
        handle.write(f"# permutation_evaluations={end - start}\n")
        handle.write(f"# u_parity_evaluations={2 * (end - start)}\n")
        handle.write(f"# v_parity_evaluations={2 * (end - start)}\n")
        handle.write(f"# logical_query_updates={2 * (end - start)}\n")
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADER)
        for query, numerator in zip(queries, numerators, strict=True):
            writer.writerow([*query, numerator, end - start])

    manifest = path.with_suffix(".manifest.json")
    manifest.write_text(
        json.dumps(
            {
                "schema": "way1-shard-manifest-v1",
                "implementation": implementation,
                "query_path": "queries.csv",
                "query_sha256": query_sha,
                "program_path": "exact_batch_grouped_uv",
                "program_sha256": program_sha,
                "output_path": str(path),
                "output_sha256": sha256_file(path),
                "range_start": start,
                "range_end": end,
                "command": ["exact_batch_grouped_uv", "--start", str(start), "--end", str(end)],
                "exit_status": 0,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def run_reducer(out_path: Path, *manifests: Path) -> subprocess.CompletedProcess[str]:
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
            "--expected-query-sha256",
            QUERY_SHA,
            "--expected-program-sha256",
            PROGRAM_SHA,
            "--out",
            str(out_path),
            *map(str, manifests),
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


def rewrite_manifest(manifest: Path, **updates: object) -> Path:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data.update(updates)
    changed = manifest.with_name(manifest.stem + "-changed.json")
    changed.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return changed


def assert_rejected(completed: subprocess.CompletedProcess[str], text: str) -> None:
    assert completed.returncode != 0
    assert text in completed.stderr, completed.stderr


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        first_path = tmp_path / "first.csv"
        second_path = tmp_path / "second.csv"
        first = write_part(first_path, start=0, end=7, numerators=(3, -1))
        second = write_part(second_path, start=7, end=16, numerators=(5, 7))
        out_path = tmp_path / "reduced.csv"

        completed = run_reducer(out_path, second, first)
        assert completed.returncode == 0, completed.stderr
        rows = read_rows(out_path)
        assert [int(row["numerator"]) for row in rows] == [8, 6]
        assert [int(row["denominator"]) for row in rows] == [16, 16]
        output = out_path.read_text(encoding="utf-8")
        assert "# query_sha256=" + QUERY_SHA in output
        assert "# program_sha256=" + PROGRAM_SHA in output

        assert_rejected(run_reducer(out_path, first), "gap after final shard")
        assert_rejected(run_reducer(out_path, first, first, second), "overlap")

        overlap = write_part(
            tmp_path / "overlap.csv", start=6, end=16, numerators=(5, 7)
        )
        assert_rejected(run_reducer(out_path, first, overlap), "overlap")

        gap = write_part(tmp_path / "gap.csv", start=8, end=16, numerators=(5, 7))
        assert_rejected(run_reducer(out_path, first, gap), "gap")

        end_off_by_one = rewrite_manifest(second, range_end=15)
        assert_rejected(run_reducer(out_path, first, end_off_by_one), "range")

        query_drift = rewrite_manifest(second, query_sha256="c" * 64)
        assert_rejected(run_reducer(out_path, first, query_drift), "query_sha256")

        program_drift = rewrite_manifest(second, program_sha256="d" * 64)
        assert_rejected(run_reducer(out_path, first, program_drift), "program_sha256")

        denominator_path = tmp_path / "denominator.csv"
        denominator = write_part(
            denominator_path, start=7, end=16, numerators=(5, 7)
        )
        text = denominator_path.read_text(encoding="utf-8").replace(
            "0x08880000,5,9", "0x08880000,5,8"
        )
        denominator_path.write_text(text, encoding="utf-8")
        denominator = rewrite_manifest(
            denominator, output_sha256=sha256_file(denominator_path)
        )
        assert_rejected(run_reducer(out_path, first, denominator), "denominator")

        replacement = write_part(
            tmp_path / "replacement.csv",
            start=7,
            end=16,
            numerators=(5, 7),
            queries=[QUERIES[0], ("2", "0x20000000", "0x00000001")],
        )
        assert_rejected(run_reducer(out_path, first, replacement), "query rows/order")

        reversed_rows = write_part(
            tmp_path / "reversed.csv",
            start=7,
            end=16,
            numerators=(7, 5),
            queries=list(reversed(QUERIES)),
        )
        assert_rejected(run_reducer(out_path, first, reversed_rows), "query rows/order")

        mixed = write_part(
            tmp_path / "mixed.csv",
            start=7,
            end=16,
            numerators=(5, 7),
            implementation="grouped_u",
        )
        assert_rejected(run_reducer(out_path, first, mixed), "implementation")

        tampered_path = tmp_path / "tampered.csv"
        tampered = write_part(tampered_path, start=7, end=16, numerators=(5, 7))
        tampered_path.write_text(
            tampered_path.read_text(encoding="utf-8").replace(",5,9", ",6,9"),
            encoding="utf-8",
        )
        assert_rejected(run_reducer(out_path, first, tampered), "output_sha256")

    print("exact shard reduction tests passed")


if __name__ == "__main__":
    main()
