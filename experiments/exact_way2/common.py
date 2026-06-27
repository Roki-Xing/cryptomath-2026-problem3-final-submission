"""Shared helpers for exact way-2 frozen-column recomputation."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Sequence


DECIMAL_RE = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
ROOT = Path(__file__).resolve().parents[2]
PILOT_HASH_PREFIX = "EXACT-WAY2-PILOT-v1"
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
SELECTION_SCHEMA = "exact-way2-pilot-selection-v2"
BUNDLE_SCHEMA = "exact-way2-column-bundle-v2"
COMPARE_SCHEMA = "exact-way2-pilot-compare-v2"
SUMMARY_SCHEMA = "exact-way2-pilot-summary-v2"
PROVENANCE_SCHEMA = "exact-way2-pilot-provenance-v2"
MANIFEST_SCHEMA = "exact-way2-pilot-manifest-v2"
BUILD_REPRODUCIBILITY_SCHEMA = "exact-way2-build-reproducibility-v2"
FULL_SELECTION_SCHEMA = "exact-way2-full-selection-v1"
FULL_AUTHORIZATION_SCHEMA = "exact-way2-full-authorization-v1"
FULL_SUMMARY_SCHEMA = "exact-way2-full-summary-v1"
FULL_PROVENANCE_SCHEMA = "exact-way2-full-provenance-v1"
FULL_MANIFEST_SCHEMA = "exact-way2-full-manifest-v1"
FULL_EXPECTED_RU_COUNT = 4760
FULL_EXPECTED_ROUND_DISTRIBUTION = {1: 120, 2: 4544, 3: 96}
FULL_EXPECTED_ROUND_DISTRIBUTION_JSON = {
    "1": FULL_EXPECTED_ROUND_DISTRIBUTION[1],
    "2": FULL_EXPECTED_ROUND_DISTRIBUTION[2],
    "3": FULL_EXPECTED_ROUND_DISTRIBUTION[3],
}


@dataclass(frozen=True)
class QueryRow:
    row_id: str
    r: int
    u: str
    v: str


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bundle_output_sha(column_path: Path, endpoints_path: Path) -> str:
    return sha256_bytes(column_path.read_bytes() + b"\0" + endpoints_path.read_bytes())


def sha256_path_list(paths: Sequence[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        rel = str(path).replace("\\", "/").encode("utf-8")
        digest.update(rel)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def canonical_json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(payload))


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def hex32(value: int | str) -> str:
    if isinstance(value, str):
        value = int(value, 0)
    return f"0x{value & 0xffffffff:08x}"


def count_active_nibbles(mask_text: str) -> int:
    value = int(mask_text, 0)
    active = 0
    for _ in range(8):
        if value & 0xF:
            active += 1
        value >>= 4
    return active


def deterministic_hash(r: int, u: str) -> str:
    return sha256_text(f"{PILOT_HASH_PREFIX}|{r}|{u.lower()}")


def load_final_queries(path: Path) -> list[QueryRow]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for index, row in enumerate(reader, start=1):
            rows.append(
                QueryRow(
                    row_id=row.get("row_id", "") or f"FQ{index:06d}",
                    r=int(row["r"]),
                    u=row["u"].lower(),
                    v=row["v"].lower(),
                )
            )
    return rows


def load_final_ru(path: Path) -> list[tuple[int, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [(int(row["r"]), row["u"].lower()) for row in reader]


def load_full_selection_csv(path: Path) -> list[tuple[int, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows: list[tuple[int, str]] = []
        for row in reader:
            rows.append((int(row["r"]), row["u"].lower()))
    return rows


def validate_full_selection_csv(selection_path: Path, final_ru_path: Path) -> dict[str, object]:
    rows = load_full_selection_csv(selection_path)
    expected_rows = sorted(load_final_ru(final_ru_path))
    expected_unique = set(expected_rows)
    if len(expected_rows) != len(expected_unique):
        raise ValueError("final_ru.csv must contain unique (r,u) rows")
    if len(expected_rows) != FULL_EXPECTED_RU_COUNT:
        raise ValueError(
            f"final_ru.csv must contain exactly {FULL_EXPECTED_RU_COUNT} unique (r,u) rows; got {len(expected_rows)}"
        )
    if rows != sorted(rows):
        raise ValueError("FULL_SELECTION.csv must be deterministically sorted by (r,u)")
    if len(rows) != FULL_EXPECTED_RU_COUNT:
        raise ValueError(f"FULL_SELECTION.csv must contain exactly {FULL_EXPECTED_RU_COUNT} rows; got {len(rows)}")
    row_counter = Counter(rows)
    duplicates = sorted(key for key, count in row_counter.items() if count > 1)
    if duplicates:
        sample = ", ".join(f"(r={r},u={u})" for r, u in duplicates[:3])
        raise ValueError(f"FULL_SELECTION.csv contains duplicate (r,u) rows: {sample}")
    unique_rows = set(rows)
    missing = sorted(expected_unique - unique_rows)
    extra = sorted(unique_rows - expected_unique)
    if missing:
        sample = ", ".join(f"(r={r},u={u})" for r, u in missing[:3])
        raise ValueError(f"FULL_SELECTION.csv is missing final_ru rows: {sample}")
    if extra:
        sample = ", ".join(f"(r={r},u={u})" for r, u in extra[:3])
        raise ValueError(f"FULL_SELECTION.csv contains extra rows not in final_ru: {sample}")
    distribution_counter = Counter(r for r, _ in rows)
    distribution = {
        1: distribution_counter.get(1, 0),
        2: distribution_counter.get(2, 0),
        3: distribution_counter.get(3, 0),
    }
    if distribution != FULL_EXPECTED_ROUND_DISTRIBUTION:
        raise ValueError(
            "FULL_SELECTION.csv round distribution mismatch: "
            f"actual={distribution} expected={FULL_EXPECTED_ROUND_DISTRIBUTION}"
        )
    return {
        "row_count": len(rows),
        "unique_ru_count": len(unique_rows),
        "round_distribution": distribution,
        "round_distribution_json": {
            "1": distribution[1],
            "2": distribution[2],
            "3": distribution[3],
        },
        "selection_sha256": sha256_file(selection_path),
        "rows": rows,
    }


def validate_full_selection_json(
    selection_json_path: Path,
    *,
    expected_csv_sha256: str,
    expected_row_count: int,
    expected_unique_ru_count: int,
    expected_round_distribution_json: dict[str, int],
    expected_rows: Sequence[tuple[int, str]],
) -> dict[str, object]:
    payload = read_json(selection_json_path)
    if not isinstance(payload, dict):
        raise ValueError("FULL_SELECTION.json must be a JSON object")
    if payload.get("schema") != FULL_SELECTION_SCHEMA:
        raise ValueError(f"FULL_SELECTION.json schema mismatch: {payload.get('schema')!r}")
    if int(payload.get("selected_columns", -1)) != expected_row_count:
        raise ValueError(
            "FULL_SELECTION.json selected_columns mismatch: "
            f"actual={payload.get('selected_columns')!r} expected={expected_row_count}"
        )
    if int(payload.get("unique_ru_count", -1)) != expected_unique_ru_count:
        raise ValueError(
            "FULL_SELECTION.json unique_ru_count mismatch: "
            f"actual={payload.get('unique_ru_count')!r} expected={expected_unique_ru_count}"
        )
    if payload.get("selection_payload_sha256") != expected_csv_sha256:
        raise ValueError("FULL_SELECTION.json selection_payload_sha256 mismatch")
    if payload.get("round_distribution_by_r") != expected_round_distribution_json:
        raise ValueError(
            "FULL_SELECTION.json round_distribution_by_r mismatch: "
            f"actual={payload.get('round_distribution_by_r')!r} expected={expected_round_distribution_json!r}"
        )
    expected_round_distribution = {
        f"r{round_number}": count for round_number, count in expected_round_distribution_json.items()
    }
    if payload.get("round_distribution") != expected_round_distribution:
        raise ValueError(
            "FULL_SELECTION.json round_distribution mismatch: "
            f"actual={payload.get('round_distribution')!r} expected={expected_round_distribution!r}"
        )
    selection_rows = payload.get("selection")
    if not isinstance(selection_rows, list):
        raise ValueError("FULL_SELECTION.json selection must be a list")
    actual_rows = [(int(row["r"]), str(row["u"]).lower()) for row in selection_rows]
    if actual_rows != list(expected_rows):
        raise ValueError("FULL_SELECTION.json selection rows do not match FULL_SELECTION.csv")
    return payload


def parse_exact_decimal(text: str, *, max_digits: int = 10000, max_exponent: int = 10000) -> Fraction:
    if not DECIMAL_RE.fullmatch(text):
        raise ValueError("invalid finite decimal syntax")
    sign = -1 if text.startswith("-") else 1
    if text and text[0] in "+-":
        text = text[1:]
    mantissa = text
    exponent = 0
    if "e" in text or "E" in text:
        split = "e" if "e" in text else "E"
        mantissa, exponent_text = text.split(split, 1)
        exponent = int(exponent_text)
    if "." in mantissa:
        whole, frac = mantissa.split(".", 1)
    else:
        whole, frac = mantissa, ""
    digits = (whole + frac) or "0"
    if len(digits) > max_digits:
        raise ValueError("too many digits")
    if abs(exponent) > max_exponent:
        raise ValueError("exponent out of range")
    numerator = int(digits) if digits else 0
    scale = exponent - len(frac)
    if scale >= 0:
        numerator *= 10**scale
        denominator = 1
    else:
        denominator = 10 ** (-scale)
    return Fraction(sign * numerator, denominator)


def compare_dyadic_to_decimal(numerator: int, denominator_exp2: int, text: str) -> str:
    try:
        decimal_value = parse_exact_decimal(text)
    except ValueError:
        return "PARSE_ERROR"
    left = decimal_value.numerator * (1 << denominator_exp2)
    right = numerator * decimal_value.denominator
    return "EXACT_EQUAL" if left == right else "NOT_EQUAL"


def percentile_rank(sorted_values: list[int], value: int) -> float:
    if not sorted_values:
        return 0.0
    index = 0
    while index < len(sorted_values) and sorted_values[index] <= value:
        index += 1
    return (index / len(sorted_values)) * 100.0


def upper_median_index(length: int) -> int:
    if length <= 0:
        raise ValueError("length must be positive")
    return length // 2


def nearest_rank_index(length: int, percentile: float) -> int:
    if length <= 0:
        raise ValueError("length must be positive")
    if not 0.0 <= percentile <= 100.0:
        raise ValueError("percentile out of range")
    return max(0, math.ceil((percentile / 100.0) * length) - 1)


def exact_band(percentile: float) -> str:
    if percentile < 25:
        return "[0,25)"
    if percentile < 50:
        return "[25,50)"
    if percentile < 75:
        return "[50,75)"
    if percentile < 95:
        return "[75,95)"
    return "[95,100]"


def run_command(args: Sequence[str], *, cwd: Path = ROOT, allow_failure: bool = False) -> str:
    completed = subprocess.run(
        [*args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if not allow_failure and completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"command failed: {' '.join(args)}")
    return completed.stdout


def normalize_commit(value: str) -> str:
    normalized = value.strip().lower()
    if not COMMIT_RE.fullmatch(normalized):
        raise ValueError(f"invalid commit hash: {value!r}")
    return normalized


def current_source_commit(*, cwd: Path = ROOT) -> str:
    return normalize_commit(run_command(["git", "rev-parse", "HEAD"], cwd=cwd))


def current_source_tree_sha(*, cwd: Path = ROOT) -> str:
    return normalize_commit(run_command(["git", "rev-parse", "HEAD^{tree}"], cwd=cwd))


def git_status_porcelain(*, cwd: Path = ROOT) -> str:
    return run_command(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=cwd,
    )


def require_clean_worktree(*, cwd: Path = ROOT) -> tuple[str, str]:
    status = git_status_porcelain(cwd=cwd)
    if status:
        raise RuntimeError("pilot must run in a clean committed worktree")
    return EMPTY_SHA256, EMPTY_SHA256


def now_utc_microseconds() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def command_sha(argv: Sequence[str]) -> str:
    return sha256_bytes(b"\0".join(arg.encode("utf-8") for arg in argv))


def repo_relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")


def bundle_name(r: int, u: str, backend: str) -> str:
    return f"r{r}_{u.lower()}_{backend}"


def ensure_empty_dir(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise RuntimeError(f"artifact root must be empty without --resume: {path}")
    path.mkdir(parents=True, exist_ok=True)


def population_cv(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    if mean == 0.0:
        return 0.0
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance) / mean


def sibling_json_path(selection_path: Path) -> Path:
    return selection_path.with_suffix(".json")
