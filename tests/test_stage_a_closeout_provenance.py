#!/usr/bin/env python3
"""Validate Stage-A closeout provenance semantics."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = ROOT / "bench" / "way1" / "STAGE_A_SUMMARY.json"
MANIFEST_PATH = ROOT / "bench" / "way1" / "MANIFEST.json"
CI_EVIDENCE_PATH = ROOT / "bench" / "way1" / "CI_EVIDENCE.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def ensure_commit_present(commit: str) -> None:
    verify = subprocess.run(
        ["git", "rev-parse", "--verify", f"{commit}^{{commit}}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if verify.returncode == 0:
        return
    fetch = subprocess.run(
        ["git", "fetch", "--depth=256", "origin", commit],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert fetch.returncode == 0, f"unable to fetch commit {commit}: {fetch.stderr.strip()}"
    verify = subprocess.run(
        ["git", "rev-parse", "--verify", f"{commit}^{{commit}}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    assert verify.returncode == 0, f"commit still unavailable after fetch: {commit}"


def git_is_ancestor(ancestor: str, descendant: str) -> bool:
    ensure_commit_present(ancestor)
    ensure_commit_present(descendant)
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=ROOT,
        check=False,
    )
    return result.returncode == 0


def validate(summary: dict[str, object], manifest: dict[str, object], ci: dict[str, object]) -> None:
    for field in (
        "stage_a_evidence_commit",
        "stage_toolchain_source_head_commit",
        "stage_toolchain_execution_commit",
        "ci_attested_commit",
        "integration_head_commit",
    ):
        value = summary.get(field)
        assert isinstance(value, str) and HEX40.match(value), field

    assert summary["decision"] == "STAGE_A_PASS"
    assert summary["non_goals"]["stage_b_authorized"] is False
    assert summary["non_goals"]["full_2_32_run_started"] is False
    assert summary["non_goals"]["strategy_b_decision"] == "NO_GO_PENDING_STAGE_B"
    assert summary["stage_toolchain_execution_commit_kind"] == "ci_synthetic_merge"
    assert summary["integration_head_role"] == "pre_closeout_integration_evidence_head"

    assert summary["stage_a_evidence_commit"] != summary["stage_toolchain_execution_commit"]
    assert summary["stage_toolchain_source_head_commit"] != summary["stage_toolchain_execution_commit"]
    assert summary["ci_attested_commit"] == summary["integration_head_commit"]

    assert git_is_ancestor(summary["stage_a_evidence_commit"], summary["integration_head_commit"])
    assert git_is_ancestor(
        summary["stage_toolchain_source_head_commit"],
        summary["integration_head_commit"],
    )

    toolchain_artifact = summary["stage_toolchain_artifact"]
    assert toolchain_artifact["run_id"] == 28031330588
    assert toolchain_artifact["artifact_id"] == 7823007424
    assert (
        toolchain_artifact["artifact_digest"]
        == "sha256:47e62a52cc64cae5f2f26a3e9240a73dd33bea4f95b25f49a70c756d97b085c5"
    )
    assert toolchain_artifact["source_head_commit"] == summary["stage_toolchain_source_head_commit"]
    assert toolchain_artifact["execution_commit"] == summary["stage_toolchain_execution_commit"]

    assert summary["final_push_ci_run_id"] == 28032401682
    assert summary["final_pr_ci_run_id"] == 28032406708
    assert (
        summary["ci"]["final_push_artifact_digest"]
        == "sha256:2c38708b08b74cd68f8b64b9868c43215dae0daf353a391da0f81c30e2bc2817"
    )
    assert (
        summary["ci"]["final_pr_artifact_digest"]
        == "sha256:5cf4cd38a7d4d7baae1c2f885545415df56d70a6cfe353bf41498846126348b8"
    )

    assert manifest["stage_toolchain_source_head_commit"] == summary["stage_toolchain_source_head_commit"]
    assert manifest["stage_toolchain_execution_commit"] == summary["stage_toolchain_execution_commit"]
    assert manifest["ci_attested_commit"] == summary["ci_attested_commit"]
    assert manifest["integration_head_commit"] == summary["integration_head_commit"]
    assert manifest["integration_head_role"] == summary["integration_head_role"]

    assert ci["stage_toolchain_source_head_commit"] == summary["stage_toolchain_source_head_commit"]
    assert ci["stage_toolchain_execution_commit"] == summary["stage_toolchain_execution_commit"]
    assert ci["stage_toolchain_execution_commit_kind"] == "ci_synthetic_merge"
    assert ci["stage_toolchain_artifact"]["run_id"] == 28031330588
    assert ci["stage_toolchain_artifact"]["artifact_id"] == 7823007424
    assert (
        ci["stage_toolchain_artifact"]["artifact_digest"]
        == "sha256:47e62a52cc64cae5f2f26a3e9240a73dd33bea4f95b25f49a70c756d97b085c5"
    )
    assert ci["integration_push"]["run_id"] == 28032401682
    assert ci["integration_pull_request"]["run_id"] == 28032406708
    assert (
        ci["integration_push"]["artifact_digest"]
        == "sha256:2c38708b08b74cd68f8b64b9868c43215dae0daf353a391da0f81c30e2bc2817"
    )
    assert (
        ci["integration_pull_request"]["artifact_digest"]
        == "sha256:5cf4cd38a7d4d7baae1c2f885545415df56d70a6cfe353bf41498846126348b8"
    )


def main() -> None:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    ci = json.loads(CI_EVIDENCE_PATH.read_text(encoding="utf-8"))
    validate(summary, manifest, ci)

    bad_missing = dict(summary)
    del bad_missing["stage_toolchain_source_head_commit"]
    try:
        validate(bad_missing, manifest, ci)
    except Exception:
        pass
    else:
        raise AssertionError("missing source head commit should fail")

    bad_mixed = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    bad_mixed["stage_toolchain_source_head_commit"] = bad_mixed["stage_toolchain_execution_commit"]
    try:
        validate(bad_mixed, manifest, ci)
    except Exception:
        pass
    else:
        raise AssertionError("mixed source/execution semantics should fail")

    bad_digest = json.loads(CI_EVIDENCE_PATH.read_text(encoding="utf-8"))
    bad_digest["stage_toolchain_artifact"]["artifact_digest"] = "sha256:deadbeef"
    try:
        validate(summary, manifest, bad_digest)
    except Exception:
        pass
    else:
        raise AssertionError("wrong artifact digest should fail")

    print("stage-a closeout provenance tests passed")


if __name__ == "__main__":
    main()
