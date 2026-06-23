#!/usr/bin/env python3
"""Verify the bounded Stage-A0 matrix and semantic cross-case comparison."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bench" / "way1" / "run_stage_a0.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_stage_a0", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_output(path: Path, rows: list[tuple[str, str, str, int, int]]) -> None:
    path.write_text(
        "# schema=way1-exact-shard-v2\n"
        "r,u,v,numerator,denominator\n"
        + "".join(
            f"{rounds},{u},{v},{numerator},{denominator}\n"
            for rounds, u, v, numerator, denominator in rows
        ),
        encoding="utf-8",
    )


def main() -> None:
    module = load_module()
    query_specs = module.build_query_specs()
    assert len(query_specs) == 18
    skipped = [spec for spec in query_specs if spec.skip_reason]
    assert len(skipped) == 1
    assert skipped[0].rounds == 1
    assert skipped[0].count == 512
    assert skipped[0].family == "frozen-subset"
    assert skipped[0].skip_reason == "SKIP_UNAVAILABLE"

    run_specs = module.build_run_specs(query_specs, multithread=8)
    assert len(run_specs) == 68
    assert {spec.threads for spec in run_specs} == {1, 8}
    assert {spec.order for spec in run_specs} == {"canonical", "shuffled"}
    assert all(not spec.query.skip_reason for spec in run_specs)

    grouped: dict[str, int] = {}
    for spec in run_specs:
        grouped[spec.query.case_id] = grouped.get(spec.query.case_id, 0) + 1
    assert set(grouped.values()) == {4}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        canonical = tmp_path / "canonical.csv"
        shuffled = tmp_path / "shuffled.csv"
        changed = tmp_path / "changed.csv"
        rows = [
            ("2", "0x00002000", "0x08880000", 16, 1024),
            ("2", "0x20000000", "0x00000888", -8, 1024),
        ]
        write_output(canonical, rows)
        write_output(shuffled, list(reversed(rows)))
        write_output(changed, [rows[0], (*rows[1][:3], -7, 1024)])
        assert module.semantic_result_map(canonical) == module.semantic_result_map(
            shuffled
        )
        try:
            module.assert_semantic_equivalence([canonical, changed])
        except ValueError as exc:
            assert "semantic result mismatch" in str(exc)
        else:
            raise AssertionError("changed numerator was not rejected")

    print("way-1 Stage-A0 orchestration tests passed")


if __name__ == "__main__":
    main()
