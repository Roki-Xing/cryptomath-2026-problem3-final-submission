#!/usr/bin/env python3
"""Verify deterministic frozen-query sampling and benchmark shard artifacts."""

from __future__ import annotations

import csv
import hashlib
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "bench" / "way1" / "generate_queries.py"
REDUCER = ROOT / "bench" / "way1" / "reduce_shards.py"
RUNNER = ROOT / "bench" / "way1" / "run_protocol.py"
SOURCE = ROOT / "experiments" / "frozen" / "final_queries.csv"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_data_rows(path: Path) -> list[dict[str, str]]:
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    return list(csv.DictReader(lines))


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        queries_a = tmp_path / "queries_a.csv"
        queries_b = tmp_path / "queries_b.csv"
        generate = [
            "python3",
            "-X",
            "utf8",
            str(GENERATOR),
            "--source",
            str(SOURCE),
            "--r",
            "2",
            "--count",
            "8",
            "--seed",
            "pr7-test",
        ]
        first = run(*generate, "--out", str(queries_a))
        second = run(*generate, "--out", str(queries_b))
        assert first.returncode == 0, first.stderr
        assert second.returncode == 0, second.stderr
        assert queries_a.read_bytes() == queries_b.read_bytes()
        query_sha = file_sha256(queries_a)
        assert f"query_sha256={query_sha}" in first.stdout

        source_rows = {
            (row["r"], row["u"].lower(), row["v"].lower())
            for row in csv.DictReader(SOURCE.open(encoding="utf-8", newline=""))
        }
        sampled_rows = read_data_rows(queries_a)
        assert len(sampled_rows) == 8
        assert all(
            (row["r"], row["u"].lower(), row["v"].lower()) in source_rows
            for row in sampled_rows
        )

        oversized = run(
            *generate[:-4],
            "--count",
            "1000000",
            "--seed",
            "pr7-test",
            "--out",
            str(tmp_path / "oversized.csv"),
        )
        assert oversized.returncode != 0
        assert "available" in oversized.stderr

        outputs: dict[str, Path] = {}
        for implementation, executable in (
            ("current", ROOT / "exact_batch_current"),
            ("grouped_u", ROOT / "exact_batch_grouped_u"),
            ("grouped_uv", ROOT / "exact_batch_grouped_uv"),
        ):
            output = tmp_path / f"{implementation}.csv"
            completed = run(
                str(executable),
                "--r",
                "2",
                "--queries",
                str(queries_a),
                "--query-sha256",
                query_sha,
                "--start",
                "0",
                "--end",
                "1024",
                "--threads",
                "2",
                "--out",
                str(output),
            )
            assert completed.returncode == 0, completed.stderr
            assert f"implementation={implementation}" in output.read_text(encoding="utf-8")
            outputs[implementation] = output

        reference = [
            (row["r"], row["u"], row["v"], row["numerator"], row["denominator"])
            for row in read_data_rows(outputs["current"])
        ]
        for implementation in ("grouped_u", "grouped_uv"):
            compared = [
                (row["r"], row["u"], row["v"], row["numerator"], row["denominator"])
                for row in read_data_rows(outputs[implementation])
            ]
            assert compared == reference

        shard_a = tmp_path / "shard_a.csv"
        shard_b = tmp_path / "shard_b.csv"
        for start, end, output in ((0, 400, shard_a), (400, 1024, shard_b)):
            completed = run(
                str(ROOT / "exact_batch_grouped_uv"),
                "--r",
                "2",
                "--queries",
                str(queries_a),
                "--query-sha256",
                query_sha,
                "--start",
                str(start),
                "--end",
                str(end),
                "--threads",
                "2",
                "--out",
                str(output),
            )
            assert completed.returncode == 0, completed.stderr

        reduced = tmp_path / "reduced.csv"
        completed = run(
            "python3",
            "-X",
            "utf8",
            str(REDUCER),
            "--expected-start",
            "0",
            "--expected-end",
            "1024",
            "--out",
            str(reduced),
            str(shard_b),
            str(shard_a),
        )
        assert completed.returncode == 0, completed.stderr
        reduced_rows = read_data_rows(reduced)
        grouped_rows = read_data_rows(outputs["grouped_uv"])
        assert [
            (row["r"], row["u"], row["v"], row["numerator"], row["denominator"])
            for row in reduced_rows
        ] == [
            (row["r"], row["u"], row["v"], row["numerator"], row["denominator"])
            for row in grouped_rows
        ]

        benchmark_results = tmp_path / "benchmark_results.csv"
        completed = run(
            "python3",
            "-X",
            "utf8",
            str(RUNNER),
            "--queries",
            str(queries_a),
            "--r",
            "2",
            "--domain-bits",
            "10",
            "--threads",
            "2",
            "--variants",
            "grouped_uv",
            "--out",
            str(benchmark_results),
            "--artifacts-dir",
            str(tmp_path / "runner_artifacts"),
        )
        assert completed.returncode == 0, completed.stderr
        benchmark_rows = list(
            csv.DictReader(benchmark_results.open(encoding="utf-8", newline=""))
        )
        assert len(benchmark_rows) == 1
        assert float(benchmark_rows[0]["wall_seconds"]) > 0
        assert float(benchmark_rows[0]["query_updates_per_second"]) > 0

    print("way-1 benchmark protocol tests passed")


if __name__ == "__main__":
    main()
