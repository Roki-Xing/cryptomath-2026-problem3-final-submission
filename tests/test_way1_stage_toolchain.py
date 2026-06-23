#!/usr/bin/env python3
"""Verify the required Stage-A sanitizer and toolchain matrix."""

from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bench" / "way1" / "run_stage_toolchain.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_stage_toolchain", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    module = load_module()
    specs = module.build_matrix(multithread=8)

    assert len(specs) == 69
    assert Counter(spec.suite for spec in specs) == {
        "ubsan": 18,
        "asan": 9,
        "tsan": 6,
        "optimization": 36,
    }
    assert {spec.rounds for spec in specs} == {1, 2, 3}
    assert {spec.count for spec in specs} == {64}
    assert all(spec.family == "frozen-subset" for spec in specs)
    assert all(spec.query_path.name == f"r{spec.rounds}_q64_frozen.csv" for spec in specs)

    ubsan = [spec for spec in specs if spec.suite == "ubsan"]
    assert {spec.domain_bits for spec in ubsan} == {16}
    assert {spec.threads for spec in ubsan} == {1, 8}
    assert {spec.variant for spec in ubsan} == {
        "current",
        "grouped_u",
        "grouped_uv",
    }
    assert {spec.compiler for spec in ubsan} == {"g++"}
    assert all("-fsanitize=undefined" in spec.flags for spec in ubsan)
    assert all("-fno-sanitize-recover=all" in spec.flags for spec in ubsan)

    asan = [spec for spec in specs if spec.suite == "asan"]
    assert {spec.domain_bits for spec in asan} == {14}
    assert {spec.threads for spec in asan} == {1}
    assert {spec.variant for spec in asan} == {
        "current",
        "grouped_u",
        "grouped_uv",
    }
    assert all("-fsanitize=address" in spec.flags for spec in asan)

    tsan = [spec for spec in specs if spec.suite == "tsan"]
    assert {spec.domain_bits for spec in tsan} == {12}
    assert {spec.threads for spec in tsan} == {4}
    assert {spec.variant for spec in tsan} == {"grouped_u", "grouped_uv"}
    assert all("-fsanitize=thread" in spec.flags for spec in tsan)

    optimization = [spec for spec in specs if spec.suite == "optimization"]
    assert {spec.domain_bits for spec in optimization} == {12}
    assert {spec.threads for spec in optimization} == {1}
    assert {spec.compiler for spec in optimization} == {"g++", "clang++"}
    assert {spec.optimization for spec in optimization} == {"O0", "O3"}
    assert all("-fsanitize=" not in spec.flags for spec in optimization)

    groups = module.semantic_groups(specs)
    assert len(groups) == 12
    assert all(len(group) >= 2 for group in groups.values())

    print("way-1 Stage-A toolchain matrix tests passed")


if __name__ == "__main__":
    main()
