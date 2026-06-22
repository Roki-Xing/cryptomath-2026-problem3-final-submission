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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    submit_text = """\
@(2, 16, 0x00000030, 0.5, 0.5)
@(1, 0x00000002, 0x00000020, -0.25, -0.25)
@(2, 0x00000010, 0x00000010, 0.125, 0.125)
"""

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        submit_path = tmp_path / "submit.txt"
        out_dir = tmp_path / "frozen"
        submit_path.write_text(submit_text, encoding="utf-8")
        submit_hash = sha256(submit_path)

        command = [
            sys.executable,
            str(SCRIPT),
            "--submit",
            str(submit_path),
            "--out-dir",
            str(out_dir),
            "--expected-submit-sha256",
            submit_hash,
            "--expected-query-count",
            "3",
            "--expected-unique-ru",
            "2",
        ]
        subprocess.run(command, cwd=ROOT, check=True)

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

        baseline = json.loads((out_dir / "BASELINE.json").read_text(encoding="utf-8"))
        assert baseline["source"]["path"] == str(submit_path)
        assert baseline["source"]["sha256"] == submit_hash
        assert baseline["artifacts"]["final_queries.csv"]["data_rows"] == 3
        assert baseline["artifacts"]["final_ru.csv"]["data_rows"] == 2
        assert baseline["artifacts"]["final_queries.csv"]["sha256"] == sha256(out_dir / "final_queries.csv")
        assert baseline["artifacts"]["final_ru.csv"]["sha256"] == sha256(out_dir / "final_ru.csv")
        assert baseline["generation"]["command"].startswith("python3 -X utf8 experiments/freeze_baseline.py")
        assert "git" not in baseline

        checksum_lines = (out_dir / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
        assert checksum_lines == [
            f"{sha256(out_dir / 'BASELINE.json')}  BASELINE.json",
            f"{sha256(out_dir / 'final_queries.csv')}  final_queries.csv",
            f"{sha256(out_dir / 'final_ru.csv')}  final_ru.csv",
        ]

        first_hashes = {path.name: sha256(path) for path in out_dir.iterdir()}
        subprocess.run(command, cwd=ROOT, check=True)
        second_hashes = {path.name: sha256(path) for path in out_dir.iterdir()}
        assert first_hashes == second_hashes

    print("freeze baseline tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
