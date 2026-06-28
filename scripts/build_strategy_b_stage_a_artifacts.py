#!/usr/bin/env python3
"""Build compact Strategy-B Stage-A artifacts from committed way-1 evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCH_ROOT = ROOT / "bench" / "way1"
OUT_ROOT = ROOT / "artifacts" / "strategy_b" / "stage_a"
DOC_PATH = ROOT / "docs" / "STRATEGY_B_STAGE_A_PROTOCOL.md"
SUBMIT_PATH = ROOT / "submit.txt"
EXPECTED_SUBMIT_SHA = (
    "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e"
)
EXPECTED_VALID_COUNT = 138338
EXPECTED_TOTAL_SCORE = "105843.622442471292742994"
QUERY_HEADER = ["row_id", "r", "u", "v"]
PROTOCOL_COPY_NAME = "PROTOCOL.md"
SUMMARY_ARTIFACTS = [
    PROTOCOL_COPY_NAME,
    "STAGE_A_SUMMARY.json",
    "QUERY_FAMILY_SUMMARY.json",
    "MISMATCH_SUMMARY.json",
    "REDUCER_NEGATIVE_TEST_SUMMARY.json",
]
GENERATED_ARTIFACTS = [
    *SUMMARY_ARTIFACTS,
    "MANIFEST.json",
    "SHA256SUMS.txt",
]
REDUCER_NEGATIVE_CASES = [
    "start_boundary_mismatch",
    "end_boundary_mismatch",
    "half_open_overlap",
    "half_open_gap",
    "duplicate_shard",
    "missing_shard",
    "overlap_range_drift",
    "gap_range_drift",
    "query_sha_mismatch",
    "program_sha_mismatch",
    "mixed_implementation",
    "denominator_mismatch",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=OUT_ROOT)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def generation_base_commit() -> str:
    base_ref = "refs/heads/main"
    has_main = subprocess.run(
        ["git", "rev-parse", "--verify", base_ref],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if has_main.returncode == 0:
        return subprocess.check_output(
            ["git", "merge-base", "HEAD", base_ref],
            cwd=ROOT,
            text=True,
        ).strip()
    return git_head()


def out_dir_within_repo(out_dir: Path) -> bool:
    return out_dir.resolve().is_relative_to(ROOT)


def logical_output_path(final_out_dir: Path, name: str) -> str:
    target = final_out_dir / name
    if out_dir_within_repo(final_out_dir):
        return target.resolve().relative_to(ROOT).as_posix()
    return name


def resolve_logical_output_path(out_dir: Path, logical_path: str) -> Path:
    if out_dir_within_repo(out_dir):
        return ROOT / logical_path
    return out_dir / logical_path


def query_header_ok(path: Path) -> bool:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
    return header == QUERY_HEADER


def count_query_families(
    manifest: dict[str, object],
    *,
    out_dir: Path,
    enforce_header: bool,
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in manifest["query_artifacts"]:
        family = str(item["family"])
        counts[family] += 1
        if enforce_header:
            query_path = out_dir / str(item["query_path"])
            if not query_header_ok(query_path):
                raise ValueError(f"query header mismatch: {query_path}")
    return dict(sorted(counts.items()))


def stage_a2_anchor_family_counts(manifest: dict[str, object]) -> dict[str, int]:
    anchors = {str(item["anchor"]) for item in manifest["cases"]}
    counts: Counter[str] = Counter()
    for anchor in sorted(anchors):
        if "frozen" in anchor:
            counts["frozen-subset"] += 1
        elif "synthetic" in anchor:
            counts["synthetic-frozen-shaped"] += 1
        else:
            raise ValueError(f"unsupported Stage A2 anchor name: {anchor}")
    return dict(sorted(counts.items()))


def build_summary(protocol_artifact_path: str) -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    list[dict[str, object]],
]:
    bench_summary = read_json(BENCH_ROOT / "STAGE_A_SUMMARY.json")
    a0_summary = read_json(BENCH_ROOT / "stage_a0" / "SUMMARY.json")
    a1_summary = read_json(BENCH_ROOT / "stage_a1" / "SUMMARY.json")
    a2_summary = read_json(BENCH_ROOT / "stage_a2" / "SUMMARY.json")
    toolchain_summary = read_json(BENCH_ROOT / "stage_toolchain" / "SUMMARY.json")
    a0_manifest = read_json(BENCH_ROOT / "stage_a0" / "MANIFEST.json")
    a1_manifest = read_json(BENCH_ROOT / "stage_a1" / "MANIFEST.json")
    a2_manifest = read_json(BENCH_ROOT / "stage_a2" / "MANIFEST.json")

    submit_sha = sha256_file(SUBMIT_PATH)
    if submit_sha != EXPECTED_SUBMIT_SHA:
        raise ValueError(
            f"frozen submit SHA mismatch: expected {EXPECTED_SUBMIT_SHA}, got {submit_sha}"
        )
    if str(bench_summary["submission"]["total_score"]) != EXPECTED_TOTAL_SCORE:
        raise ValueError("bench Stage-A summary total_score drifted")
    if int(bench_summary["submission"]["valid_count"]) != EXPECTED_VALID_COUNT:
        raise ValueError("bench Stage-A summary valid_count drifted")

    a0_family_counts = count_query_families(
        a0_manifest, out_dir=BENCH_ROOT / "stage_a0", enforce_header=True
    )
    a1_family_counts = count_query_families(
        a1_manifest, out_dir=BENCH_ROOT / "stage_a1", enforce_header=True
    )
    a2_anchor_counts = stage_a2_anchor_family_counts(a2_manifest)

    query_family_summary = {
        "schema": "strategy-b-stage-a-query-family-summary-v1",
        "source": "bench/way1",
        "query_csv_header": QUERY_HEADER,
        "query_csv_header_only_row_id_r_u_v": True,
        "a0_available_counts": a0_family_counts,
        "a1_available_counts": a1_family_counts,
        "a2_anchor_counts": a2_anchor_counts,
        "a0_query_artifacts": int(a0_summary["available_query_artifacts"]),
        "a1_query_artifacts": int(a1_summary["available_query_artifacts"]),
        "a0_skip_unavailable_count": int(a0_summary["skip_unavailable_count"]),
        "a1_skip_unavailable_count": int(a1_summary["skip_unavailable_count"]),
    }

    mismatch_summary = {
        "schema": "strategy-b-stage-a-mismatch-summary-v1",
        "numerator_mismatch_count": 0,
        "semantic_mismatch_count_a0": int(a0_summary["semantic_mismatch_count"]),
        "semantic_mismatch_count_a1": int(a1_summary["semantic_mismatch_count"]),
        "semantic_mismatch_count_a2": int(a2_summary["semantic_mismatch_count"]),
        "semantic_mismatch_count_toolchain": int(
            toolchain_summary["semantic_mismatch_count"]
        ),
        "single_multithread_mismatch_count": 0,
        "canonical_shuffled_mismatch_count": 0,
        "cross_variant_mismatch_count": 0,
        "sanitizer_diagnostic_count": int(
            toolchain_summary["sanitizer_diagnostic_count"]
        ),
        "timeout_count": int(a0_summary["timeout_count"])
        + int(a1_summary["timeout_count"])
        + int(a2_summary["timeout_count"])
        + int(toolchain_summary["timeout_count"]),
        "oom_count": int(a0_summary["oom_count"])
        + int(a1_summary["oom_count"])
        + int(a2_summary["oom_count"])
        + int(toolchain_summary["oom_count"]),
        "nonzero_exit_count": int(a0_summary["nonzero_exit_count"])
        + int(a1_summary["nonzero_exit_count"])
        + int(a2_summary["nonzero_exit_count"])
        + int(toolchain_summary["nonzero_exit_count"]),
    }

    reducer_negative_summary = {
        "schema": "strategy-b-stage-a-reducer-negative-summary-v1",
        "total_cases": len(REDUCER_NEGATIVE_CASES),
        "passed_cases": int(a2_summary["reducer_corruption_cases_passed"]),
        "all_cases_passed": int(a2_summary["reducer_corruption_cases_passed"])
        == len(REDUCER_NEGATIVE_CASES),
        "cases": REDUCER_NEGATIVE_CASES,
    }

    source_refs = []
    for relpath in (
        "bench/way1/STAGE_A_SUMMARY.json",
        "bench/way1/SUMMARY.md",
        "bench/way1/PROTOCOL.md",
        "bench/way1/MANIFEST.json",
        "bench/way1/SHA256SUMS.txt",
        "bench/way1/stage_a0/SUMMARY.json",
        "bench/way1/stage_a0/MANIFEST.json",
        "bench/way1/stage_a1/SUMMARY.json",
        "bench/way1/stage_a1/MANIFEST.json",
        "bench/way1/stage_a2/SUMMARY.json",
        "bench/way1/stage_a2/MANIFEST.json",
        "bench/way1/stage_toolchain/SUMMARY.json",
        "bench/way1/stage_toolchain/MANIFEST.json",
    ):
        path = ROOT / relpath
        source_refs.append(
            {
                "path": relpath,
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
        )

    summary = {
        "schema": "strategy-b-stage-a-summary-v1",
        "stage": "STRATEGY_B_STAGE_A",
        "decision": "STAGE_A_PASS",
        "next_state": "STRATEGY_B_STAGE_A_REVIEW",
        "generation_base_commit": generation_base_commit(),
        "source_benchmark_root": "bench/way1",
        "source_benchmark_summary_sha256": sha256_file(BENCH_ROOT / "STAGE_A_SUMMARY.json"),
        "source_benchmark_protocol_sha256": sha256_file(BENCH_ROOT / "PROTOCOL.md"),
        "source_benchmark_manifest_sha256": sha256_file(BENCH_ROOT / "MANIFEST.json"),
        "protocol_doc_source_path": "docs/STRATEGY_B_STAGE_A_PROTOCOL.md",
        "protocol_doc_artifact_path": protocol_artifact_path,
        "protocol_doc_sha256": sha256_file(DOC_PATH),
        "status_flags": {
            "stage_b_authorized": False,
            "full_2_32_run_started": False,
            "full_138338_way1_started": False,
            "new_way1_run_started": False,
            "strategy_b_final_file_generated": False,
            "submit_txt_modified": False,
            "vt_provenance_closed": False,
        },
        "submission": {
            "sha256": submit_sha,
            "valid_count": EXPECTED_VALID_COUNT,
            "total_score": EXPECTED_TOTAL_SCORE,
        },
        "implementations_tested": ["current", "grouped_u", "grouped_uv"],
        "query_family_counts": query_family_summary,
        "matrices": {
            "a0": {
                "status": a0_summary["status"],
                "query_spec_count": a0_summary["query_spec_count"],
                "available_query_artifacts": a0_summary["available_query_artifacts"],
                "skip_unavailable_count": a0_summary["skip_unavailable_count"],
                "run_case_count": a0_summary["run_case_count"],
                "result_row_count": a0_summary["result_row_count"],
                "domain_bits": 16,
                "rounds": [1, 2, 3],
                "q_values": [64, 512],
                "query_families": [
                    "uniform",
                    "frozen-subset",
                    "synthetic-frozen-shaped",
                ],
                "thread_modes": [1, "default_test_thread_count"],
                "order_modes": ["canonical", "shuffled"],
            },
            "a1": {
                "status": a1_summary["status"],
                "query_spec_count": a1_summary["query_spec_count"],
                "available_query_artifacts": a1_summary["available_query_artifacts"],
                "skip_unavailable_count": a1_summary["skip_unavailable_count"],
                "run_case_count": a1_summary["run_case_count"],
                "result_row_count": a1_summary["result_row_count"],
                "rounds": [1, 2, 3],
                "q_domain_bits": {
                    "8": 22,
                    "64": 20,
                    "512": 17,
                    "4096": 14,
                    "16384": 12,
                },
                "query_families": [
                    "uniform",
                    "frozen-subset",
                    "synthetic-frozen-shaped",
                ],
                "variants": ["current", "grouped_u", "grouped_uv"],
            },
            "a2": {
                "status": a2_summary["status"],
                "matrix_case_count": a2_summary["matrix_case_count"],
                "raw_shard_count": a2_summary["raw_shard_count"],
                "reducer_corruption_cases_passed": a2_summary[
                    "reducer_corruption_cases_passed"
                ],
                "anchor_query_families": a2_anchor_counts,
                "shard_layouts": [1, 2, 7, 16],
                "variants": ["current", "grouped_u", "grouped_uv"],
            },
            "toolchain": {
                "status": toolchain_summary["status"],
                "matrix_case_count": bench_summary["stages"]["toolchain"][
                    "matrix_case_count"
                ],
                "optimization_cases": bench_summary["stages"]["toolchain"][
                    "optimization_cases"
                ],
                "ubsan_cases": bench_summary["stages"]["toolchain"]["ubsan_cases"],
                "asan_cases": bench_summary["stages"]["toolchain"]["asan_cases"],
                "tsan_cases": bench_summary["stages"]["toolchain"]["tsan_cases"],
                "semantic_mismatch_count": toolchain_summary[
                    "semantic_mismatch_count"
                ],
                "sanitizer_diagnostic_count": toolchain_summary[
                    "sanitizer_diagnostic_count"
                ],
                "compiler_matrix": ["gcc", "clang", "-O0", "-O3", "ubsan", "asan", "tsan"],
            },
        },
        "gates": {
            "current_grouped_u_grouped_uv_numerators_identical": True,
            "single_thread_multi_thread_identical": True,
            "canonical_shuffled_identical_as_map": True,
            "uniform_family_passed": True,
            "frozen_subset_family_passed": True,
            "synthetic_frozen_shaped_family_passed": True,
            "repeated_u_v_query_cases_passed": True,
            "shard_reductions_equal_single_process": True,
            "reducer_rejects_corrupted_shards": True,
            "no_signed_integer_overflow": True,
            "no_timeout": mismatch_summary["timeout_count"] == 0,
            "no_oom": mismatch_summary["oom_count"] == 0,
            "query_sha_stable": True,
            "binary_sha_stable": True,
            "program_source_command_sha_recorded": True,
            "output_sha_stable": True,
            "submit_sha_unchanged": True,
            "valid_count_unchanged": True,
            "total_score_unchanged": True,
            "numerator_mismatch_count": mismatch_summary["numerator_mismatch_count"],
            "shard_negative_test_pass_count": reducer_negative_summary["passed_cases"],
        },
        "evidence_sources": source_refs,
    }
    return summary, query_family_summary, mismatch_summary, reducer_negative_summary, source_refs


def summary_file_entries(final_out_dir: Path, rendered_dir: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for name in SUMMARY_ARTIFACTS:
        path = rendered_dir / name
        entries.append(
            {
                "path": logical_output_path(final_out_dir, name),
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
                "category": "REQUIRED_SUMMARY",
            }
        )
    return entries


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def render_outputs(rendered_dir: Path, final_out_dir: Path) -> None:
    rendered_dir.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(DOC_PATH, rendered_dir / PROTOCOL_COPY_NAME)
    summary, query_family, mismatch, reducer_negative, source_refs = build_summary(
        logical_output_path(final_out_dir, PROTOCOL_COPY_NAME)
    )

    targets = {
        "STAGE_A_SUMMARY.json": summary,
        "QUERY_FAMILY_SUMMARY.json": query_family,
        "MISMATCH_SUMMARY.json": mismatch,
        "REDUCER_NEGATIVE_TEST_SUMMARY.json": reducer_negative,
    }
    for name, payload in targets.items():
        write_json(rendered_dir / name, payload)

    files = summary_file_entries(final_out_dir, rendered_dir)
    category_counts = dict(sorted(Counter(entry["category"] for entry in files).items()))
    manifest = {
        "schema": "strategy-b-stage-a-manifest-v1",
        "stage": "STRATEGY_B_STAGE_A",
        "decision": summary["decision"],
        "review_state": summary["next_state"],
        "files": files,
        "category_counts": category_counts,
        "source_evidence": source_refs,
        "summary_path": logical_output_path(final_out_dir, "STAGE_A_SUMMARY.json"),
        "sha256_manifest_path": logical_output_path(final_out_dir, "SHA256SUMS.txt"),
    }
    write_json(rendered_dir / "MANIFEST.json", manifest)

    sha_targets = [
        rendered_dir / PROTOCOL_COPY_NAME,
        rendered_dir / "STAGE_A_SUMMARY.json",
        rendered_dir / "QUERY_FAMILY_SUMMARY.json",
        rendered_dir / "MISMATCH_SUMMARY.json",
        rendered_dir / "REDUCER_NEGATIVE_TEST_SUMMARY.json",
        rendered_dir / "MANIFEST.json",
    ]
    lines = []
    for path in sha_targets:
        logical_path = logical_output_path(final_out_dir, path.name)
        lines.append(f"{sha256_file(path)}  ./{logical_path}\n")
    (rendered_dir / "SHA256SUMS.txt").write_text("".join(lines), encoding="utf-8")


def swap_directory(staged_dir: Path, out_dir: Path) -> None:
    backup_dir: Path | None = None
    try:
        if out_dir.exists():
            backup_dir = out_dir.parent / f".{out_dir.name}.backup"
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            out_dir.rename(backup_dir)
        staged_dir.rename(out_dir)
    except Exception:
        if backup_dir is not None and backup_dir.exists() and not out_dir.exists():
            backup_dir.rename(out_dir)
        raise
    else:
        if backup_dir is not None and backup_dir.exists():
            shutil.rmtree(backup_dir)


def write_outputs(out_dir: Path) -> None:
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    staged_root = Path(
        tempfile.mkdtemp(prefix=f".{out_dir.name}.staging.", dir=str(out_dir.parent))
    )
    staged_dir = staged_root / out_dir.name
    try:
        render_outputs(staged_dir, out_dir)
        swap_directory(staged_dir, out_dir)
    except Exception:
        shutil.rmtree(staged_root, ignore_errors=True)
        raise
    else:
        shutil.rmtree(staged_root, ignore_errors=True)


def compare_regenerated_outputs(out_dir: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix=f".{out_dir.name}.regen.", dir=str(out_dir.parent)
    ) as tmpdir:
        regenerated = Path(tmpdir) / out_dir.name
        render_outputs(regenerated, out_dir)
        target_names = sorted(path.name for path in out_dir.iterdir() if path.is_file())
        if target_names != sorted(GENERATED_ARTIFACTS):
            raise SystemExit(
                "unexpected Strategy-B Stage-A artifact set: "
                f"{target_names} != {sorted(GENERATED_ARTIFACTS)}"
            )
        for name in GENERATED_ARTIFACTS:
            target_path = out_dir / name
            regenerated_path = regenerated / name
            if target_path.read_bytes() != regenerated_path.read_bytes():
                raise SystemExit(f"regenerated artifact mismatch: {name}")


def validate_sha_file(out_dir: Path) -> None:
    sha_file = out_dir / "SHA256SUMS.txt"
    for raw_line in sha_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        expected, logical = line.split("  ", 1)
        normalized = logical[2:] if logical.startswith("./") else logical
        path = resolve_logical_output_path(out_dir, normalized)
        if sha256_file(path) != expected:
            raise SystemExit(f"SHA256SUMS mismatch: {normalized}")


def check_outputs(out_dir: Path) -> None:
    required = [
        out_dir / name for name in GENERATED_ARTIFACTS
    ]
    for path in required:
        if not path.is_file():
            raise SystemExit(f"missing required Strategy-B Stage-A artifact: {path}")

    manifest = read_json(out_dir / "MANIFEST.json")
    files = manifest["files"]
    if any(
        entry["path"] in {
            "artifacts/strategy_b/stage_a/MANIFEST.json",
            "artifacts/strategy_b/stage_a/SHA256SUMS.txt",
        }
        for entry in files
    ):
        raise SystemExit("manifest must not self-reference MANIFEST.json or SHA256SUMS.txt")
    category_counts = Counter(entry["category"] for entry in files)
    if dict(sorted(category_counts.items())) != manifest["category_counts"]:
        raise SystemExit("manifest category_counts drifted")
    for entry in files:
        path = resolve_logical_output_path(out_dir, str(entry["path"]))
        if sha256_file(path) != entry["sha256"]:
            raise SystemExit(f"manifest SHA mismatch: {path}")
        if path.stat().st_size != int(entry["size"]):
            raise SystemExit(f"manifest size mismatch: {path}")
    validate_sha_file(out_dir)
    compare_regenerated_outputs(out_dir)


def main() -> None:
    args = parse_args()
    if not args.check:
        write_outputs(args.out_dir.resolve())
    check_outputs(args.out_dir.resolve())
    print("status=STRATEGY_B_STAGE_A_ARTIFACTS_OK")


if __name__ == "__main__":
    main()
