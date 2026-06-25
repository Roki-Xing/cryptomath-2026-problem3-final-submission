#!/usr/bin/env python3
"""Verify the required Stage-A sanitizer and toolchain matrix."""

from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bench" / "way1" / "run_stage_toolchain.py"
AGGREGATE = ROOT / "bench" / "way1" / "STAGE_A_SUMMARY.json"
ARTIFACT_INDEX = ROOT / "bench" / "way1" / "ARTIFACT_INDEX.json"
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


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

    aggregate = json.loads(AGGREGATE.read_text(encoding="utf-8"))
    assert aggregate["decision"] == "STAGE_A_PASS"
    assert "source_head_commit" not in aggregate
    assert aggregate["stage_a_evidence_commit"] == "4b26302e5aa0c60b66bf2c11f29b50e3bc88fb8e"
    assert aggregate["stage_toolchain_evidence_commit"] == "04fb504250796c1d13261f4cedec1e06bca17a3a"
    assert aggregate["integration_head_commit"] == "5fbff142a72557060a45d490aaf4094dadaf8af1"
    assert aggregate["final_push_ci_run_id"] == 28032401682
    assert aggregate["final_pr_ci_run_id"] == 28032406708
    assert aggregate["non_goals"]["full_2_32_run_started"] is False
    assert aggregate["non_goals"]["stage_b_authorized"] is False
    assert aggregate["non_goals"]["strategy_b_decision"] == "NO_GO_PENDING_STAGE_B"
    assert aggregate["submission"] == {
        "sha256": module.DEFAULT_SUBMIT_SHA,
        "total_score": "105843.622442471292742994",
        "valid_count": 138338,
    }
    for stage in aggregate["stages"].values():
        summary_path = ROOT / "bench" / "way1" / stage["summary_path"]
        assert module.sha256_file(summary_path) == stage["summary_sha256"]
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary["status"] == stage["status"]
    assert aggregate["stages"]["toolchain"]["matrix_case_count"] == 69
    assert aggregate["stages"]["toolchain"]["semantic_mismatch_count"] == 0
    assert aggregate["stages"]["toolchain"]["sanitizer_diagnostic_count"] == 0

    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "--out-dir /tmp/stage_toolchain" in workflow
    assert "path: /tmp/stage_toolchain" in workflow

    artifact_index = json.loads(ARTIFACT_INDEX.read_text(encoding="utf-8"))
    assert artifact_index["schema"] == "way1-stage-a-artifact-index-v1"
    categories = {entry["category"] for entry in artifact_index["entries"]}
    assert categories == {
        "REQUIRED_SUMMARY",
        "REQUIRED_MANIFEST",
        "RAW_REPRODUCIBILITY_EVIDENCE",
        "CI_ONLY",
        "EXCLUDE_FROM_SUBMISSION_PACKAGE",
    }
    assert artifact_index["submit_sha256"] == module.DEFAULT_SUBMIT_SHA

    print("way-1 Stage-A toolchain matrix tests passed")


if __name__ == "__main__":
    main()
