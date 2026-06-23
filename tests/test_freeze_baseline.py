#!/usr/bin/env python3
"""Test deterministic frozen-baseline generation."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/freeze_baseline.py"
REPOSITORY = "Roki-Xing/test-repository"
SOURCE_COMMIT = "a" * 40
FREEZE_TOOL_COMMIT = "b" * 40
GENERATED_AT = "2026-06-23T00:00:00Z"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_command(submit_path: Path, out_dir: Path, query_count: int, unique_ru: int) -> list[str]:
    return [
        sys.executable,
        str(SCRIPT),
        "--submit",
        str(submit_path),
        "--submit-path-label",
        "submit.txt",
        "--out-dir",
        str(out_dir),
        "--repository",
        REPOSITORY,
        "--source-commit",
        SOURCE_COMMIT,
        "--freeze-tool-commit",
        FREEZE_TOOL_COMMIT,
        "--generated-at",
        GENERATED_AT,
        "--expected-submit-sha256",
        sha256(submit_path),
        "--expected-query-count",
        str(query_count),
        "--expected-unique-ru",
        str(unique_ru),
    ]


def expect_failure(command: list[str]) -> None:
    completed = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert completed.returncode != 0


def main() -> int:
    submit_text = """\
@(2, 16, 0x00000030, 0.5000, 0.5000)
@(1, 0x00000002, 0x00000020, -0.25, -0.250)
@(2, 0x00000010, 0x00000010, 0.125, 0.1250)
"""

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        submit_path = tmp_path / "submit.txt"
        out_dir = tmp_path / "frozen"
        submit_path.write_text(submit_text, encoding="utf-8")
        submit_before = submit_path.read_bytes()
        submit_hash = sha256(submit_path)
        command = freeze_command(submit_path, out_dir, 3, 2)
        subprocess.run(command, cwd=ROOT, check=True)
        assert submit_path.read_bytes() == submit_before
        assert sha256(submit_path) == submit_hash

        with (out_dir / "final_queries.csv").open(encoding="utf-8", newline="") as handle:
            query_rows = list(csv.reader(handle))
        assert query_rows == [
            ["r", "u", "v"],
            ["1", "0x00000002", "0x00000020"],
            ["2", "0x00000010", "0x00000010"],
            ["2", "0x00000010", "0x00000030"],
        ]

        with (out_dir / "final_ru.csv").open(encoding="utf-8", newline="") as handle:
            ru_rows = list(csv.reader(handle))
        assert ru_rows == [
            ["r", "u"],
            ["1", "0x00000002"],
            ["2", "0x00000010"],
        ]

        with (out_dir / "final_values_snapshot.csv").open(encoding="utf-8", newline="") as handle:
            value_rows = list(csv.reader(handle))
        assert value_rows[0] == [
            "row_id",
            "r",
            "u",
            "v",
            "submitted_vt_field_snapshot",
            "frozen_way2_ve",
            "future_way1_vt",
            "future_way1_numerator",
            "future_way1_status",
        ]
        assert value_rows[1] == [
            "FQ000001",
            "1",
            "0x00000002",
            "0x00000020",
            "-0.25",
            "-0.250",
            "",
            "",
            "NOT_EXECUTED",
        ]
        assert value_rows[3][4:6] == ["0.5000", "0.5000"]

        baseline = json.loads((out_dir / "BASELINE.json").read_text(encoding="utf-8"))
        assert baseline["schema_version"] == 2
        assert baseline["source"]["repository"] == REPOSITORY
        assert baseline["source"]["submit_path"] == "submit.txt"
        assert baseline["source"]["submit_sha256"] == submit_hash
        assert baseline["source"]["submit_source_commit"] == SOURCE_COMMIT
        assert baseline["generation"]["freeze_tool_commit"] == FREEZE_TOOL_COMMIT
        assert baseline["generation"]["generated_at_utc"] == GENERATED_AT
        assert baseline["artifacts"]["final_queries.csv"]["data_rows"] == 3
        assert baseline["artifacts"]["final_ru.csv"]["data_rows"] == 2
        assert baseline["artifacts"]["final_values_snapshot.csv"]["data_rows"] == 3

        checksum_lines = (out_dir / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
        assert checksum_lines == [
            f"{sha256(out_dir / 'BASELINE.json')}  BASELINE.json",
            f"{sha256(out_dir / 'final_queries.csv')}  final_queries.csv",
            f"{sha256(out_dir / 'final_ru.csv')}  final_ru.csv",
            f"{sha256(out_dir / 'final_values_snapshot.csv')}  final_values_snapshot.csv",
        ]

        first_hashes = {path.name: sha256(path) for path in out_dir.iterdir()}
        subprocess.run(command, cwd=ROOT, check=True)
        second_hashes = {path.name: sha256(path) for path in out_dir.iterdir()}
        assert first_hashes == second_hashes

        conflict_submit = tmp_path / "conflict"
        conflict_submit.write_text(submit_text, encoding="utf-8")
        expect_failure(freeze_command(conflict_submit, conflict_submit, 3, 2))

        duplicate_ruv = tmp_path / "duplicate_ruv.txt"
        duplicate_ruv.write_text(
            "@(1, 1, 2, 0.5, 0.5)\n@(1, 1, 2, 0.5, 0.5)\n",
            encoding="utf-8",
        )
        expect_failure(freeze_command(duplicate_ruv, tmp_path / "duplicate_ruv_out", 2, 1))

        duplicate_uv = tmp_path / "duplicate_uv.txt"
        duplicate_uv.write_text(
            "@(1, 1, 2, 0.5, 0.5)\n@(2, 1, 2, 0.5, 0.5)\n",
            encoding="utf-8",
        )
        expect_failure(freeze_command(duplicate_uv, tmp_path / "duplicate_uv_out", 2, 2))

        zero_mask = tmp_path / "zero_mask.txt"
        zero_mask.write_text("@(1, 0, 2, 0.5, 0.5)\n", encoding="utf-8")
        expect_failure(freeze_command(zero_mask, tmp_path / "zero_mask_out", 1, 1))

    print("freeze baseline tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
