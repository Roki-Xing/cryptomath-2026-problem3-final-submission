#!/usr/bin/env python3
"""Verify deterministic queries, order/thread invariance, and runner provenance."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "bench" / "way1" / "generate_queries.py"
RUNNER = ROOT / "bench" / "way1" / "run_protocol.py"
SCHEMA = ROOT / "bench" / "way1" / "benchmark_schema.json"
SOURCE = ROOT / "experiments" / "frozen" / "final_queries.csv"
SUBMIT = ROOT / "submit.txt"
SUBMIT_SHA = "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e"


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


def semantic_results(path: Path) -> dict[tuple[str, str, str], tuple[str, str]]:
    return {
        (row["r"], row["u"], row["v"]): (row["numerator"], row["denominator"])
        for row in read_data_rows(path)
    }


def runner_command(
    queries: Path,
    out: Path,
    artifacts: Path,
    *,
    threads: int,
    order: str,
) -> list[str]:
    return [
        "python3",
        "-X",
        "utf8",
        str(RUNNER),
        "--queries",
        str(queries),
        "--query-family",
        "uniform",
        "--query-profile",
        "sha-order",
        "--seed",
        "pr7-test-order",
        "--order",
        order,
        "--r",
        "2",
        "--domain-bits",
        "10",
        "--threads",
        str(threads),
        "--variants",
        "current,grouped_u,grouped_uv",
        "--timeout-seconds",
        "30",
        "--max-rss-kib",
        "262144",
        "--compiler-id",
        "gcc",
        "--compiler-version",
        "test-version",
        "--compiler-flags=-O3 -std=c++17",
        "--cpu-model",
        "test-cpu",
        "--ram-bytes",
        "8589934592",
        "--numa",
        "1-node",
        "--kernel",
        "test-kernel",
        "--cpu-affinity",
        "unbound",
        "--submit-sha256",
        SUBMIT_SHA,
        "--out",
        str(out),
        "--artifacts-dir",
        str(artifacts),
    ]


def main() -> None:
    assert file_sha256(SUBMIT) == SUBMIT_SHA
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

        direct_outputs: dict[str, Path] = {}
        for implementation, executable in (
            ("current", ROOT / "exact_batch_current"),
            ("grouped_u", ROOT / "exact_batch_grouped_u"),
            ("grouped_uv", ROOT / "exact_batch_grouped_uv"),
        ):
            output = tmp_path / f"{implementation}.csv"
            program_sha = file_sha256(executable)
            completed = run(
                str(executable),
                "--r",
                "2",
                "--queries",
                str(queries_a),
                "--query-sha256",
                query_sha,
                "--program-sha256",
                program_sha,
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
            text = output.read_text(encoding="utf-8")
            assert f"# implementation={implementation}" in text
            assert f"# program_sha256={program_sha}" in text
            direct_outputs[implementation] = output

        reference = semantic_results(direct_outputs["current"])
        assert semantic_results(direct_outputs["grouped_u"]) == reference
        assert semantic_results(direct_outputs["grouped_uv"]) == reference

        canonical_results = tmp_path / "canonical-results.csv"
        shuffled_results = tmp_path / "shuffled-results.csv"
        canonical_artifacts = tmp_path / "canonical-artifacts"
        shuffled_artifacts = tmp_path / "shuffled-artifacts"
        canonical = run(
            *runner_command(
                queries_a,
                canonical_results,
                canonical_artifacts,
                threads=1,
                order="canonical",
            )
        )
        shuffled = run(
            *runner_command(
                queries_a,
                shuffled_results,
                shuffled_artifacts,
                threads=2,
                order="shuffled",
            )
        )
        assert canonical.returncode == 0, canonical.stderr
        assert shuffled.returncode == 0, shuffled.stderr

        canonical_rows = list(
            csv.DictReader(canonical_results.open(encoding="utf-8", newline=""))
        )
        shuffled_rows = list(
            csv.DictReader(shuffled_results.open(encoding="utf-8", newline=""))
        )
        assert len(canonical_rows) == 3
        assert len(shuffled_rows) == 3
        assert {row["threads"] for row in canonical_rows} == {"1"}
        assert {row["threads"] for row in shuffled_rows} == {"2"}
        assert {row["order"] for row in canonical_rows} == {"canonical"}
        assert {row["order"] for row in shuffled_rows} == {"shuffled"}
        assert {row["timing_metric_origin"] for row in canonical_rows} == {"MEASURED"}
        assert {row["counter_metric_origin"] for row in canonical_rows} == {
            "DETERMINISTIC_ALGORITHMIC_COUNT"
        }
        required_fields = set(
            json.loads(SCHEMA.read_text(encoding="utf-8"))["required_fields"]
        )
        assert required_fields == set(canonical_rows[0])
        assert all(
            value != ""
            for row in canonical_rows + shuffled_rows
            for value in row.values()
        )

        signatures: list[dict[tuple[str, str, str], tuple[str, str]]] = []
        for artifacts in (canonical_artifacts, shuffled_artifacts):
            manifests = sorted(artifacts.glob("*.manifest.json"))
            assert len(manifests) == 3
            for manifest_path in manifests:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                output_path = Path(manifest["output_path"])
                assert manifest["schema"] == "way1-shard-manifest-v1"
                assert manifest["exit_status"] == 0
                assert manifest["query_sha256"] == file_sha256(Path(manifest["query_path"]))
                assert manifest["program_sha256"] == file_sha256(
                    Path(manifest["program_path"])
                )
                assert manifest["output_sha256"] == file_sha256(output_path)
                signatures.append(semantic_results(output_path))
        assert all(signature == signatures[0] for signature in signatures[1:])
        assert file_sha256(SUBMIT) == SUBMIT_SHA

    print("way-1 benchmark protocol tests passed")


if __name__ == "__main__":
    main()
