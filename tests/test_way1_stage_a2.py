#!/usr/bin/env python3
"""Verify deterministic Stage-A2 partitions and matrix coverage."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bench" / "way1" / "run_stage_a2.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_stage_a2", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    module = load_module()
    assert module.partition_ranges(100, 1, "equal", "seed") == [(0, 100)]
    assert module.partition_ranges(100, 2, "equal", "seed") == [(0, 50), (50, 100)]
    unequal = module.partition_ranges(100, 7, "seeded-unequal", "seed")
    assert unequal == module.partition_ranges(100, 7, "seeded-unequal", "seed")
    assert len(unequal) == 7
    assert unequal[0][0] == 0 and unequal[-1][1] == 100
    assert all(start < end for start, end in unequal)
    assert all(left[1] == right[0] for left, right in zip(unequal, unequal[1:]))
    assert len({end - start for start, end in unequal}) > 1

    specs = module.build_matrix()
    assert len(specs) == 31
    assert sum(spec.shards == 1 for spec in specs) == 9
    assert sum(spec.shards == 2 for spec in specs) == 9
    assert sum(spec.shards == 7 for spec in specs) == 7
    assert sum(spec.shards == 16 for spec in specs) == 6
    assert sum(
        spec.implementation == "current" and spec.shards == 7 for spec in specs
    ) == 1
    assert not any(
        spec.implementation == "current" and spec.shards == 16 for spec in specs
    )

    print("way-1 Stage-A2 orchestration tests passed")


if __name__ == "__main__":
    main()
