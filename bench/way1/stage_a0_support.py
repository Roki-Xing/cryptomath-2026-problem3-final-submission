"""Pure Stage-A0 matrix and semantic-result helpers."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class QuerySpec:
    rounds: int
    count: int
    family: str
    profile: str
    timeout_seconds: int
    skip_reason: str = ""

    @property
    def case_id(self) -> str:
        family_slug = {
            "uniform": "uniform",
            "frozen-subset": "frozen",
            "synthetic-frozen-shaped": "synthetic",
        }[self.family]
        return f"r{self.rounds}_q{self.count}_{family_slug}"


@dataclass(frozen=True)
class RunSpec:
    query: QuerySpec
    threads: int
    order: str

    @property
    def case_id(self) -> str:
        return f"{self.query.case_id}_{self.order}_t{self.threads}"


def build_query_specs() -> list[QuerySpec]:
    specs: list[QuerySpec] = []
    for rounds in (1, 2, 3):
        for count in (64, 512):
            timeout = 120 if count == 64 else 300
            for family, profile in (
                ("uniform", "sha-order"),
                ("frozen-subset", "uv_core"),
                ("synthetic-frozen-shaped", "uv_core"),
            ):
                skip = (
                    "SKIP_UNAVAILABLE"
                    if rounds == 1 and count == 512 and family == "frozen-subset"
                    else ""
                )
                specs.append(
                    QuerySpec(
                        rounds=rounds,
                        count=count,
                        family=family,
                        profile=profile,
                        timeout_seconds=timeout,
                        skip_reason=skip,
                    )
                )
    return specs


def build_run_specs(
    query_specs: list[QuerySpec], multithread: int
) -> list[RunSpec]:
    if multithread <= 1:
        raise ValueError("Stage A0 requires a multithread value greater than 1")
    return [
        RunSpec(query=query, threads=threads, order=order)
        for query in query_specs
        if not query.skip_reason
        for threads in (1, multithread)
        for order in ("canonical", "shuffled")
    ]


def semantic_result_map(path: Path) -> dict[tuple[int, int, int], tuple[int, int]]:
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    rows = csv.DictReader(lines)
    result: dict[tuple[int, int, int], tuple[int, int]] = {}
    for row in rows:
        key = (int(row["r"]), int(row["u"], 0), int(row["v"], 0))
        if key in result:
            raise ValueError(f"duplicate semantic result key in {path}: {key}")
        result[key] = (int(row["numerator"]), int(row["denominator"]))
    if not result:
        raise ValueError(f"no semantic result rows in {path}")
    return result


def assert_semantic_equivalence(paths: list[Path]) -> None:
    if not paths:
        raise ValueError("no result artifacts supplied for semantic comparison")
    reference = semantic_result_map(paths[0])
    for path in paths[1:]:
        if semantic_result_map(path) != reference:
            raise ValueError(f"semantic result mismatch: {paths[0]} != {path}")
