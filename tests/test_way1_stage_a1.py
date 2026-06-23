#!/usr/bin/env python3
"""Verify the bounded Stage-A1 query and run matrix."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bench" / "way1" / "run_stage_a1.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_stage_a1", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    module = load_module()
    query_specs = module.build_query_specs()
    assert len(query_specs) == 45
    skipped = [spec for spec in query_specs if spec.skip_reason]
    assert len(skipped) == 3
    assert {
        (spec.rounds, spec.count, spec.family, spec.skip_reason)
        for spec in skipped
    } == {
        (1, 512, "frozen-subset", "SKIP_UNAVAILABLE"),
        (1, 4096, "frozen-subset", "SKIP_UNAVAILABLE"),
        (1, 16384, "frozen-subset", "SKIP_UNAVAILABLE"),
    }

    expected_bits = {8: 22, 64: 20, 512: 17, 4096: 14, 16384: 12}
    assert all(spec.domain_bits == expected_bits[spec.count] for spec in query_specs)

    run_specs = module.build_run_specs(query_specs, threads=8)
    assert len(run_specs) == 50
    assert {spec.threads for spec in run_specs} == {8}
    assert sum(spec.order == "shuffled" for spec in run_specs) == 8
    assert all(
        spec.query.count == 512 for spec in run_specs if spec.order == "shuffled"
    )
    assert sum(spec.order == "canonical" for spec in run_specs) == 42

    print("way-1 Stage-A1 orchestration tests passed")


if __name__ == "__main__":
    main()
