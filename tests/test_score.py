#!/usr/bin/env python3
"""Exercise score CLI validity, filtering, and deduplication rules."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


SUBMIT_ROWS = """\
@(1, 0x00000001, 0x00000010, -0.5, -0.5)
@(1, 0x00000002, 0x00000020, 0.0, 0.0)
@(1, 0x00000003, 0x00000030, 0.5, 0.0)
@(1, 0x00000000, 0x00000040, 0.5, 0.5)
@(1, 0x00000004, 0x00000000, 0.5, 0.5)
@(1, 0x00000005, 0x00000050, 0.25, 0.25)
@(1, 0x00000006, 0x00000060, 0.5, 0.5)
@(2, 0x00000006, 0x00000060, 0.5, 0.5)
"""


def run_score(score_bin: str, submit_path: Path, *args: str) -> str:
    completed = subprocess.run(
        [score_bin, *args, str(submit_path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def require(text: str, needle: str) -> None:
    if needle not in text:
        raise AssertionError(f"missing expected output: {needle}\n{text}")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_score.py ./score", file=sys.stderr)
        return 2
    score_bin = sys.argv[1]

    with tempfile.TemporaryDirectory() as tmp:
        submit_path = Path(tmp) / "score_cases.txt"
        submit_path.write_text(SUBMIT_ROWS, encoding="utf-8")

        plain = run_score(score_bin, submit_path)
        require(plain, "line 1 r=1 u=0x00000001 v=0x00000010 VT=-0.5 VE=-0.5 valid=yes kept=yes score=1")
        require(plain, "line 2 r=1 u=0x00000002 v=0x00000020 VT=0 VE=0 valid=no kept=no score=0")
        require(plain, "line 3 r=1 u=0x00000003 v=0x00000030 VT=0.5 VE=0 valid=no kept=no score=0")
        require(plain, "line 4 r=1 u=0x00000000 v=0x00000040 VT=0.5 VE=0.5 valid=no kept=no score=0")
        require(plain, "line 5 r=1 u=0x00000004 v=0x00000000 VT=0.5 VE=0.5 valid=no kept=no score=0")
        require(plain, "line 6 r=1 u=0x00000005 v=0x00000050 VT=0.25 VE=0.25 valid=yes kept=yes score=0")
        require(plain, "valid_count=4")
        require(plain, "total_score=5")

        positive = run_score(score_bin, submit_path, "--positive-only")
        require(positive, "line 6 r=1 u=0x00000005 v=0x00000050 VT=0.25 VE=0.25 valid=no kept=no score=0")
        require(positive, "valid_count=3")
        require(positive, "total_score=5")

        dedup_uv = run_score(score_bin, submit_path, "--dedup", "uv", "--positive-only")
        require(dedup_uv, "line 7 r=1 u=0x00000006 v=0x00000060 VT=0.5 VE=0.5 valid=yes kept=no score=1")
        require(dedup_uv, "line 8 r=2 u=0x00000006 v=0x00000060 VT=0.5 VE=0.5 valid=yes kept=yes score=3")
        require(dedup_uv, "valid_count=2")
        require(dedup_uv, "total_score=4")

    print("score rule tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
