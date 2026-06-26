#!/usr/bin/env python3
"""Generate provenance, manifest, and SHA inventory for committed pilot artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import MANIFEST_SCHEMA, PROVENANCE_SCHEMA, read_json, sha256_file, write_json, write_text


def categorize(path: Path) -> str:
    relative = str(path).replace("\\", "/")
    if relative in {
        "SUMMARY.json",
        "SUMMARY.md",
        "COMPARE.json",
        "COMPARISONS.csv",
        "MISMATCHES.csv",
        "PROVENANCE.json",
        "ENVIRONMENT.json",
        "RUNNER.json",
        "PIPELINE.json",
        "PILOT_SELECTION.csv",
        "PILOT_SELECTION.json",
        "PROTOCOL.md",
        "WAY1_NUMERATOR_CHECK.csv",
        "REPEAT_SUBSET.json",
        "REPEAT_SUBSET.md",
        "BUILD_REPRODUCIBILITY.json",
    }:
        return "REQUIRED_SUMMARY"
    if relative in {
        "MANIFEST.json",
        "SHA256SUMS.txt",
        "SELECTOR_PROVENANCE.json",
        "SELECTOR_INPUT_PREPARATION.json",
        "SELECTOR_INPUT_PROTOCOL.md",
        "COMPLEXITY_INPUT.csv",
        "SPOTCHECK_COORDINATES.csv",
    }:
        return "REQUIRED_MANIFEST"
    if relative.startswith("completed/"):
        return "PILOT_RAW_EVIDENCE"
    if relative.startswith("locks/") or relative.startswith(".staging/"):
        return "CI_ONLY"
    return "EXCLUDE_FROM_SUBMISSION_PACKAGE"


def logical_binary_path(path_text: str) -> str:
    path = Path(path_text)
    if path.is_absolute():
        return path.name
    return path_text.replace("\\", "/")


def logicalize_runner_command(command: str, observed_binary_path: str, binary_logical_path: str) -> str:
    if observed_binary_path and observed_binary_path in command:
        return command.replace(observed_binary_path, binary_logical_path)
    return command


def diagnostic_environment(raw_runner: dict[str, object]) -> dict[str, object]:
    existing = raw_runner.get("diagnostic_environment")
    if isinstance(existing, dict):
        return {
            "observed_artifact_root": str(existing.get("observed_artifact_root", "")),
            "observed_selection_path": str(existing.get("observed_selection_path", "")),
            "observed_queries_path": str(existing.get("observed_queries_path", "")),
            "observed_binary_path": str(existing.get("observed_binary_path", "")),
            "observed_runner_command": str(existing.get("observed_runner_command", "")),
        }
    return {
        "observed_artifact_root": raw_runner.get("artifact_root", ""),
        "observed_selection_path": raw_runner.get("selection_path", ""),
        "observed_queries_path": raw_runner.get("queries_path", ""),
        "observed_binary_path": raw_runner.get("binary_path", ""),
        "observed_runner_command": raw_runner.get("runner_command", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--artifact-committed-in-commit", required=True)
    args = parser.parse_args()

    root = Path(args.artifact_root)
    invocation_root = Path.cwd().resolve()
    summary = read_json(root / "SUMMARY.json")
    compare = read_json(root / "COMPARE.json")
    runner = read_json(root / "RUNNER.json")
    selection = read_json(root / "PILOT_SELECTION.json")
    build_repro = read_json(root / "BUILD_REPRODUCIBILITY.json")
    repeat_subset = read_json(root / "REPEAT_SUBSET.json")
    if not all(isinstance(payload, dict) for payload in (summary, compare, runner, selection, build_repro, repeat_subset)):
        raise SystemExit("invalid attestation prerequisites")

    binary_logical_path = logical_binary_path(str(runner["binary_path"]))
    runner_payload = {
        **runner,
        "artifact_root": "artifacts/way2_exact/pilot",
        "selection_path": "artifacts/way2_exact/pilot/PILOT_SELECTION.csv",
        "queries_path": "experiments/frozen/final_queries.csv",
        "binary_path": binary_logical_path,
        "runner_command": logicalize_runner_command(
            str(runner["runner_command"]),
            str(runner["binary_path"]),
            binary_logical_path,
        ),
        "diagnostic_environment": diagnostic_environment(runner),
    }
    write_json(root / "RUNNER.json", runner_payload)

    environment_payload = {
        "artifact_generated_at_commit": build_repro["implementation_commit"],
        "artifact_root": "artifacts/way2_exact/pilot",
        "backend_mode": runner_payload["backend_mode"],
        "binary_build_commit": build_repro["implementation_commit"],
        "binary_path": binary_logical_path,
        "binary_sha256": build_repro["first_clean_build"]["binary_sha256"],
        "command_sha256": runner_payload["command_sha256"],
        "final_queries_sha256": selection["final_queries_sha256"],
        "final_ru_sha256": selection["final_ru_sha256"],
        "git_status_porcelain_sha256": build_repro["clean_git_status_sha256"],
        "jobs": runner_payload["jobs"],
        "queries_path": "experiments/frozen/final_queries.csv",
        "runner_commit": runner_payload["runner_commit"],
        "selection_path": "artifacts/way2_exact/pilot/PILOT_SELECTION.csv",
        "selection_sha256": selection["selection_payload_sha256"],
        "selector_commit": runner_payload["selector_commit"],
        "source_checkout_commit": build_repro["implementation_commit"],
        "source_tree_diff_sha256": build_repro["clean_git_diff_sha256"],
        "source_tree_dirty": False,
        "source_tree_sha": build_repro["implementation_tree_sha"],
        "diagnostic_environment": diagnostic_environment(runner),
    }
    write_json(root / "ENVIRONMENT.json", environment_payload)

    provenance = {
        "schema": PROVENANCE_SCHEMA,
        "source_checkout_commit": build_repro["implementation_commit"],
        "source_tree_sha": build_repro["implementation_tree_sha"],
        "source_tree_dirty": False,
        "git_status_porcelain_sha256": build_repro["clean_git_status_sha256"],
        "source_tree_diff_sha256": build_repro["clean_git_diff_sha256"],
        "binary_build_commit": build_repro["implementation_commit"],
        "runner_commit": runner["runner_commit"],
        "selector_commit": runner_payload["selector_commit"],
        "artifact_generated_at_commit": build_repro["implementation_commit"],
        "artifact_committed_in_commit": args.artifact_committed_in_commit,
        "binary_sha256": build_repro["first_clean_build"]["binary_sha256"],
        "final_ru_sha256": selection["final_ru_sha256"],
        "final_queries_sha256": selection["final_queries_sha256"],
        "selection_sha256": selection["selection_payload_sha256"],
        "command_sha256": runner["command_sha256"],
        "compiler_path": build_repro["first_clean_build"]["compiler_path"],
        "compiler_version": build_repro["first_clean_build"]["compiler_version"],
        "build_command": build_repro["first_clean_build"]["build_command"],
        "compile_flags": build_repro["first_clean_build"]["environment"]["CXXFLAGS"],
        "artifact_root": "artifacts/way2_exact/pilot",
        "selection_path": "artifacts/way2_exact/pilot/PILOT_SELECTION.csv",
        "queries_path": "experiments/frozen/final_queries.csv",
        "binary_path": binary_logical_path,
        "jobs": runner_payload["jobs"],
        "selector_elapsed_wall": summary["selector_elapsed_wall"],
        "orchestrator_elapsed_wall": summary["orchestrator_elapsed_wall"],
        "comparison_elapsed_wall": summary["comparison_elapsed_wall"],
        "summarizer_elapsed_wall": summary["summarizer_elapsed_wall"],
        "total_pilot_elapsed_wall": summary["total_pilot_elapsed_wall"],
        "cpp_int_column_wall_sum": summary["cpp_int_column_wall_sum"],
        "int128_column_wall_sum": summary["int128_column_wall_sum"],
        "peak_process_rss": summary["peak_process_rss"],
        "peak_total_concurrent_rss": summary["peak_total_concurrent_rss"],
        "repeat_subset_path": "artifacts/way2_exact/pilot/REPEAT_SUBSET.json",
        "stage_b_authorized": False,
        "full_4760_run_started": False,
        "new_way1_run_started": False,
        "diagnostic_environment": diagnostic_environment(runner),
    }
    write_json(root / "PROVENANCE.json", provenance)

    files = sorted(path for path in root.rglob("*") if path.is_file())
    manifest_files = [
        {
            "path": str(path.relative_to(root)).replace("\\", "/"),
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
            "category": categorize(path.relative_to(root)),
        }
        for path in files
        if path.name not in {"MANIFEST.json", "SHA256SUMS.txt"}
    ]
    category_counts: dict[str, int] = {}
    for entry in manifest_files:
        category_counts[entry["category"]] = category_counts.get(entry["category"], 0) + 1
    write_json(
        root / "MANIFEST.json",
        {
            "schema": MANIFEST_SCHEMA,
            "status": summary["status"],
            "artifact_committed_in_commit": args.artifact_committed_in_commit,
            "files": manifest_files,
            "category_counts": category_counts,
        },
    )

    files_for_sha = sorted(
        path for path in root.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt"
    )
    sha_lines = []
    for path in files_for_sha:
        resolved = path.resolve()
        try:
            rel = resolved.relative_to(invocation_root)
        except ValueError:
            rel = path.relative_to(root)
        sha_lines.append(f"{sha256_file(path)}  ./{str(rel).replace('\\', '/')}")
    write_text(root / "SHA256SUMS.txt", "\n".join(sha_lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
