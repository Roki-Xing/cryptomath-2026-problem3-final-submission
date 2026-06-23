#!/usr/bin/env python3
"""Verify exact-dyadic denominator, accumulator, and way-1 numerator bounds."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "docs" / "EXACT_DYADIC_SPEC.md"

ROUND_DENOMINATOR = 2**16
MAX_COLUMN_L1 = 3**8
ROUND_GROWTH_BOUND = ROUND_DENOMINATOR * MAX_COLUMN_L1
SIGNED_INT128_MAX = 2**127 - 1

EXPECTED_BOUNDS = {
    1: (65536, 17, 429981696, 29),
    2: (28179280429056, 45, 184884258895036416, 58),
    3: (12116574790945106558976, 74, 79496847203390844133441536, 87),
    4: (
        5209905378321422361129224503296,
        103,
        34182189187166852111368841966125056,
        115,
    ),
}


def way1_numerator(dyadic_numerator: int, rounds: int) -> int:
    denominator_exp2 = 16 * rounds
    if denominator_exp2 <= 32:
        return dyadic_numerator * 2 ** (32 - denominator_exp2)
    divisor = 2 ** (denominator_exp2 - 32)
    assert dyadic_numerator % divisor == 0
    return dyadic_numerator // divisor


def main() -> None:
    assert ROUND_GROWTH_BOUND == 429981696
    for rounds, expected in EXPECTED_BOUNDS.items():
        item_bound = ROUND_GROWTH_BOUND ** (rounds - 1) * ROUND_DENOMINATOR
        sum_bound = ROUND_GROWTH_BOUND**rounds
        assert (item_bound, item_bound.bit_length(), sum_bound, sum_bound.bit_length()) == expected
        assert item_bound <= SIGNED_INT128_MAX
        assert sum_bound <= SIGNED_INT128_MAX

    assert ROUND_GROWTH_BOUND**5 > SIGNED_INT128_MAX
    assert [16 * rounds for rounds in (1, 2, 3)] == [16, 32, 48]

    assert way1_numerator(3, 1) == 3 * 2**16
    assert way1_numerator(-7, 2) == -7
    assert way1_numerator(11 * 2**16, 3) == 11

    spec = SPEC_PATH.read_text(encoding="utf-8")
    for required in (
        "429981696",
        "34182189187166852111368841966125056",
        "r <= 4",
        "r = 5",
        "denominator_exp2 = 16 * r",
    ):
        assert required in spec

    print("exact dyadic bound tests passed")


if __name__ == "__main__":
    main()
