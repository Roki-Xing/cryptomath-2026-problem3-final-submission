#!/usr/bin/env python3
"""Verify the frozen 4-bit S-box Walsh table and dyadic branch facts."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TABLE_PATH = ROOT / "tests" / "data" / "walsh_table.csv"
SPEC_PATH = ROOT / "docs" / "EXACT_DYADIC_SPEC.md"
SBOX = [
    0xC,
    0x6,
    0x9,
    0x0,
    0x1,
    0xA,
    0x2,
    0xB,
    0x3,
    0x8,
    0x5,
    0xD,
    0x4,
    0xE,
    0x7,
    0xF,
]
EXPECTED_SPECTRUM = Counter({0: 123, -4: 52, 4: 44, 8: 19, -8: 17, 16: 1})
EXPECTED_BRANCH_COUNTS = [1, 10, 4, 10, 4, 10, 4, 10, 10, 10, 10, 10, 10, 10, 10, 10]
EXPECTED_ABS_COLUMN_SUMS = [16, 48, 32, 48, 32, 48, 32, 48, 48, 48, 48, 48, 48, 48, 48, 48]


def parity4(value: int) -> int:
    return (value & 0xF).bit_count() & 1


def compute_walsh_table() -> list[list[int]]:
    table: list[list[int]] = []
    for output_mask in range(16):
        row: list[int] = []
        for input_mask in range(16):
            numerator = 0
            for x in range(16):
                bit = parity4(input_mask & x) ^ parity4(output_mask & SBOX[x])
                numerator += -1 if bit else 1
            row.append(numerator)
        table.append(row)
    return table


def load_frozen_table() -> list[list[int]]:
    with TABLE_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["b\\a", *[format(value, "X") for value in range(16)]]
    assert len(rows) == 17
    table: list[list[int]] = []
    for output_mask, row in enumerate(rows[1:]):
        assert row[0] == format(output_mask, "X")
        assert len(row) == 17
        table.append([int(value) for value in row[1:]])
    return table


def main() -> None:
    frozen = load_frozen_table()
    computed = compute_walsh_table()
    assert frozen == computed

    spectrum = Counter(value for row in frozen for value in row)
    assert spectrum == EXPECTED_SPECTRUM
    assert all(value % 4 == 0 for row in frozen for value in row)

    branch_counts = [
        sum(frozen[output_mask][input_mask] != 0 for output_mask in range(16))
        for input_mask in range(16)
    ]
    assert branch_counts == EXPECTED_BRANCH_COUNTS

    abs_column_sums = [
        sum(abs(frozen[output_mask][input_mask]) for output_mask in range(16))
        for input_mask in range(16)
    ]
    assert abs_column_sums == EXPECTED_ABS_COLUMN_SUMS
    assert max(value // 16 for value in abs_column_sums) == 3

    q_values = {value // 4 for row in frozen for value in row}
    assert q_values == {-2, -1, 0, 1, 2, 4}
    assert 4**8 == 2**16

    spec = SPEC_PATH.read_text(encoding="utf-8")
    for required in (
        "exact Cartesian product",
        "must not use top-K",
        "must not use a priority queue",
        "certified_exact_dyadic",
        "cpp_int",
    ):
        assert required in spec

    print("Walsh spectrum and frozen table tests passed")


if __name__ == "__main__":
    main()
