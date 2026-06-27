#!/usr/bin/env python3
"""Generate provenance, manifest, and SHA inventory for committed full artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    BUILD_REPRODUCIBILITY_SCHEMA,
    FULL_MANIFEST_SCHEMA,
    FULL_PROVENANCE_SCHEMA,
    read_json,
    sha256_file,
    write_json,
    write_text,
)


def categorize(path: Path) -> str:
    relative = str(path).replace("\\", "/")
    if relative in {
        "FULL_RUN_AUTHORIZATION.json",
        "FULL_SELECTION.csv",
        "FULL_SELECTION.json",
        "SELECTION_PROVENANCE.json",
        "PROTOCOL.md",
        "BUILD_REPRODUCIBILITY.json",
        "ENVIRONMENT.json",
        "RUNNER.json",
        "PIPELINE.json",
        "COMPARE.json",
        "COMPARISONS.csv",
        "MISMATCHES.csv",
        "WAY1_NUMERATOR_CHECK.csv",
        "SUMMARY.json",
        "SUMMARY.md",
        "RAW_EVIDENCE_INDEX.json",
        "RAW_EVIDENCE_MANIFEST.json",
        "PROVENANCE.json",
    }:
        return "REQUIRED_SUMMARY"
    if relative.startswith("representative_completed/"):
        return "REPRESENTATIVE_EVIDENCE"
    if relative in {"MANIFEST.json", "SHA256SUMS.txt"}:
        return "REQUIRED_MANIFEST"
    return "EXCLUDE_FROM_SUBMISSION_PACKAGE"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True)
    args = parser.parse_args()

    root = Path(args.artifact_root)
    summary = read_json(root / "SUMMARY.json")
    runner = read_json(root / "RUNNER.json")
    selection = read_json(root / "FULL_SELECTION.json")
    build_repro = read_json(root / "BUILD_REPRODUCIBILITY.json")
    auth = read_json(root / "FULL_RUN_AUTHORIZATION.json")
    if not all(isinstance(payload, dict) for payload in (summary, runner, selection, build_repro, auth)):
        raise SystemExit("invalid full attestation prerequisites")
    if build_repro.get("schema") != BUILD_REPRODUCIBILITY_SCHEMA:
        raise SystemExit("invalid build reproducibility schema")

    provenance = {
        "schema": FULL_PROVENANCE_SCHEMA,
        "source_checkout_commit": build_repro["implementation_commit"],
        "source_tree_sha": build_repro["implementation_tree_sha"],
        "source_tree_dirty": False,
        "git_status_porcelain_sha256": build_repro["clean_git_status_sha256"],
        "source_tree_diff_sha256": build_repro["clean_git_diff_sha256"],
        "binary_build_commit": build_repro["implementation_commit"],
        "binary_sha256": build_repro["first_clean_build"]["binary_sha256"],
        "compiler_path": build_repro["first_clean_build"]["compiler_path"],
        "compiler_version": build_repro["first_clean_build"]["compiler_version"],
        "build_command": build_repro["first_clean_build"]["build_command"],
        "selection_sha256": selection["selection_payload_sha256"],
        "authorization_sha256": sha256_file(root / "FULL_RUN_AUTHORIZATION.json"),
        "full_4760_run_started": True,
        "stage_b_authorized": False,
        "new_way1_run_started": False,
        "submit_txt_modified": False,
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
            "schema": FULL_MANIFEST_SCHEMA,
            "status": summary["status"],
            "files": manifest_files,
            "category_counts": category_counts,
        },
    )
    sha_lines = []
    for path in sorted(path for path in root.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt"):
        rel = "./" + str(path.relative_to(root)).replace("\\", "/")
        sha_lines.append(f"{sha256_file(path)}  {rel}")
    write_text(root / "SHA256SUMS.txt", "\n".join(sha_lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
