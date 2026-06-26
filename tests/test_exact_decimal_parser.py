import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "exact_way2"))

from common import compare_dyadic_to_decimal, parse_exact_decimal  # noqa: E402


VALID = [
    "0",
    "-0",
    "+1.2500",
    ".5",
    "-3.125e-1",
    "2E+3",
    "0001",
    "1.",
    "+0.000",
]

INVALID = [
    "",
    "NaN",
    "inf",
    "0x1p3",
    "1_000",
    "1.2.3",
    "1e10001",
    "--1",
    "1e-10001",
    "1e",
    "+",
]


def main() -> None:
    for text in VALID:
        parse_exact_decimal(text)
    for text in INVALID:
        try:
            parse_exact_decimal(text)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{text} should be rejected")

    assert compare_dyadic_to_decimal(1, 1, "0.5") == "EXACT_EQUAL"
    assert compare_dyadic_to_decimal(-1, 1, "-0.5") == "EXACT_EQUAL"
    assert compare_dyadic_to_decimal(1, 1, "0.25") == "NOT_EQUAL"
    assert compare_dyadic_to_decimal(1, 1, "NaN") == "PARSE_ERROR"
    print("exact decimal parser tests passed")


if __name__ == "__main__":
    main()
