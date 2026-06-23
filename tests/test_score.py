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

NEGATIVE_VT_ROWS = """\
@(1, 0x00000001, 0x00000010, -0.5, -0.625)
@(1, 0x00000002, 0x00000020, -0.5, -0.626)
@(1, 0x00000003, 0x00000030, -0.5, -0.375)
@(1, 0x00000004, 0x00000040, -0.5, -0.374)
"""

DECIMAL_MASK_ROWS = """\
@(1, 1, 16, 0.5, 0.5)
@(2, 1, 16, 0.5, 0.5)
"""

OFFICIAL_HEX_PARSING_ROW = """\
@(1, 0x000ee0f0, 0x08088880, 0.5, 0.5)
"""

DUPLICATE_RUV_ROWS = """\
@(2, 0x00000001, 0x00000010, 0.5, 0.5)
@(2, 0x00000001, 0x00000010, 0.5, 0.5)
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
        require(plain, "unique_uv=3")
        require(plain, "unique_ruv=4")

        explicit_none = run_score(score_bin, submit_path, "--dedup", "none")
        if explicit_none != plain:
            raise AssertionError("default dedup mode differs from --dedup none")

        positive = run_score(score_bin, submit_path, "--positive-only")
        require(positive, "line 6 r=1 u=0x00000005 v=0x00000050 VT=0.25 VE=0.25 valid=no kept=no score=0")
        require(positive, "valid_count=3")
        require(positive, "total_score=5")
        require(positive, "unique_uv=2")
        require(positive, "unique_ruv=3")

        dedup_uv = run_score(score_bin, submit_path, "--dedup", "uv", "--positive-only")
        require(dedup_uv, "line 7 r=1 u=0x00000006 v=0x00000060 VT=0.5 VE=0.5 valid=yes kept=no score=1")
        require(dedup_uv, "line 8 r=2 u=0x00000006 v=0x00000060 VT=0.5 VE=0.5 valid=yes kept=yes score=3")
        require(dedup_uv, "valid_count=2")
        require(dedup_uv, "total_score=4")
        require(dedup_uv, "unique_uv=2")
        require(dedup_uv, "unique_ruv=3")

        dedup_ruv = run_score(score_bin, submit_path, "--dedup", "ruv", "--positive-only")
        require(dedup_ruv, "line 7 r=1 u=0x00000006 v=0x00000060 VT=0.5 VE=0.5 valid=yes kept=yes score=1")
        require(dedup_ruv, "line 8 r=2 u=0x00000006 v=0x00000060 VT=0.5 VE=0.5 valid=yes kept=yes score=3")
        require(dedup_ruv, "valid_count=3")
        require(dedup_ruv, "total_score=5")
        require(dedup_ruv, "unique_uv=2")
        require(dedup_ruv, "unique_ruv=3")

        negative_path = Path(tmp) / "negative_vt_cases.txt"
        negative_path.write_text(NEGATIVE_VT_ROWS, encoding="utf-8")
        negative = run_score(score_bin, negative_path)
        require(negative, "line 1 r=1 u=0x00000001 v=0x00000010 VT=-0.5 VE=-0.625 valid=yes")
        require(negative, "line 2 r=1 u=0x00000002 v=0x00000020 VT=-0.5 VE=-0.626")
        require(negative, "line 3 r=1 u=0x00000003 v=0x00000030 VT=-0.5 VE=-0.375 valid=yes")
        require(negative, "line 4 r=1 u=0x00000004 v=0x00000040 VT=-0.5 VE=-0.374")
        negative_lines = negative.splitlines()
        if "valid=no" not in negative_lines[1] or "valid=no" not in negative_lines[3]:
            raise AssertionError(f"negative boundary rows were accepted\n{negative}")

        decimal_path = Path(tmp) / "decimal_mask_cases.txt"
        decimal_path.write_text(DECIMAL_MASK_ROWS, encoding="utf-8")
        decimal = run_score(score_bin, decimal_path)
        require(decimal, "line 1 r=1 u=0x00000001 v=0x00000010 VT=0.5 VE=0.5 valid=yes")
        require(decimal, "line 2 r=2 u=0x00000001 v=0x00000010 VT=0.5 VE=0.5 valid=yes")
        require(decimal, "unique_uv=1")
        require(decimal, "unique_ruv=2")

        official_hex_path = Path(tmp) / "official_hex_parsing_case.txt"
        official_hex_path.write_text(OFFICIAL_HEX_PARSING_ROW, encoding="utf-8")
        official_hex = run_score(score_bin, official_hex_path)
        require(
            official_hex,
            "line 1 r=1 u=0x000ee0f0 v=0x08088880 VT=0.5 VE=0.5 valid=yes",
        )

        duplicate_ruv_path = Path(tmp) / "duplicate_ruv_cases.txt"
        duplicate_ruv_path.write_text(DUPLICATE_RUV_ROWS, encoding="utf-8")
        duplicate_ruv = run_score(score_bin, duplicate_ruv_path)
        require(duplicate_ruv, "valid_count=2")
        require(duplicate_ruv, "unique_uv=1")
        require(duplicate_ruv, "unique_ruv=1")

    print("score rule tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
