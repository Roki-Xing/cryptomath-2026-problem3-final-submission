#!/usr/bin/env python3
"""Run the frozen exact-way2 pilot with controlled bundle artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import os
import resource
import shutil
import subprocess
import time
from pathlib import Path

from common import (
    BUNDLE_SCHEMA,
    EMPTY_SHA256,
    ROOT,
    bundle_name,
    bundle_output_sha,
    command_sha,
    current_source_commit,
    current_source_tree_sha,
    ensure_empty_dir,
    now_utc_microseconds,
    read_json,
    repo_relative,
    require_clean_worktree,
    sha256_file,
    write_json,
)


def selection_rows(selection_path: Path) -> list[dict[str, str]]:
    with selection_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def selection_json_path(selection_path: Path, artifact_root: Path) -> Path:
    sibling = selection_path.with_name("PILOT_SELECTION.json")
    if sibling.exists():
        return sibling
    artifact_copy = artifact_root / "PILOT_SELECTION.json"
    if artifact_copy.exists():
        return artifact_copy
    raise FileNotFoundError(
        f"missing PILOT_SELECTION.json beside {selection_path} or under {artifact_root}"
    )


def logical_path(path: Path, *, logical_root: str | None, suffix: str | None = None) -> str:
    try:
        return repo_relative(path)
    except ValueError:
        if logical_root is None:
            raise RuntimeError("external artifact paths require --artifact-logical-root") from None
        base = logical_root.rstrip("/")
        if suffix:
            return f"{base}/{suffix.lstrip('/')}"
        return base


def check_partial_artifacts(root: Path) -> None:
    partials = sorted(root.rglob("*.tmp.*"))
    partials += sorted(root.rglob("*.partial.*"))
    partials += sorted(path for path in root.rglob("*") if ".staging" in path.parts and path != root / ".staging")
    if partials:
        sample = ", ".join(
            repo_relative(path) if path.is_relative_to(ROOT) else str(path) for path in partials[:8]
        )
        raise RuntimeError(f"partial or staging artifacts present: {sample}")


def verify_no_orphan_loose_outputs(root: Path) -> None:
    allowed_root_files = {
        "PILOT_SELECTION.csv",
        "PILOT_SELECTION.json",
        "PROTOCOL.md",
        "SELECTOR_PROVENANCE.json",
        "COMPLEXITY_INPUT.csv",
        "SPOTCHECK_COORDINATES.csv",
        "SELECTOR_INPUT_PREPARATION.json",
        "SELECTOR_INPUT_PROTOCOL.md",
        "BUILD_REPRODUCIBILITY.json",
        "ENVIRONMENT.json",
        "RUNNER.json",
        "PIPELINE.json",
        "COMPARE.json",
        "COMPARISONS.csv",
        "MISMATCHES.csv",
        "SUMMARY.json",
        "SUMMARY.md",
        "REPEAT_SUBSET.json",
        "REPEAT_SUBSET.md",
        "WAY1_NUMERATOR_CHECK.csv",
        "PROVENANCE.json",
        "MANIFEST.json",
        "SHA256SUMS.txt",
    }
    for subdir in ("columns", "endpoints"):
        if (root / subdir).exists():
            raise RuntimeError(f"legacy loose artifact directory is forbidden: {subdir}")
    for path in root.iterdir():
        if path.is_file() and path.name not in allowed_root_files:
            raise RuntimeError(f"unexpected loose artifact file is forbidden: {path.name}")


def lock_path(root: Path, r: int, u: str, backend: str) -> Path:
    return root / "locks" / f"{bundle_name(r, u, backend)}.lock"


def completed_bundle(root: Path, r: int, u: str, backend: str) -> Path:
    return root / "completed" / bundle_name(r, u, backend)


def verify_endpoint_csv(path: Path, *, r: int, u: str, expected_count: int) -> None:
    row_ids: set[str] = set()
    triples: set[tuple[int, str, str]] = set()
    count = 0
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            count += 1
            row_id = row["row_id"]
            triple = (int(row["r"]), row["u"].lower(), row["v"].lower())
            if row_id in row_ids:
                raise RuntimeError(f"duplicate row_id in endpoint bundle: {row_id}")
            if triple in triples:
                raise RuntimeError(f"duplicate (r,u,v) in endpoint bundle: {triple}")
            row_ids.add(row_id)
            triples.add(triple)
            if triple[0] != r or triple[1] != u:
                raise RuntimeError(f"unexpected endpoint key in bundle: {triple}")
    if count != expected_count:
        raise RuntimeError(f"endpoint count mismatch for r={r} u={u}: expected {expected_count}, got {count}")


def verify_done_bundle(bundle_dir: Path, *, expected: dict[str, object]) -> None:
    column_path = bundle_dir / "column.json"
    endpoints_path = bundle_dir / "endpoints.csv"
    done_path = bundle_dir / "DONE.json"
    if not column_path.exists() or not endpoints_path.exists() or not done_path.exists():
        raise RuntimeError(f"incomplete bundle during resume verification: {bundle_dir}")
    done = read_json(done_path)
    if not isinstance(done, dict):
        raise RuntimeError(f"invalid DONE payload: {done_path}")
    for key, expected_value in expected.items():
        if done.get(key) != expected_value:
            raise RuntimeError(f"resume metadata mismatch for {bundle_dir.name}: {key}")
    if done.get("schema") != BUNDLE_SCHEMA:
        raise RuntimeError(f"bundle schema mismatch for {bundle_dir.name}")
    actual_column_sha = sha256_file(column_path)
    actual_endpoints_sha = sha256_file(endpoints_path)
    actual_output_sha = bundle_output_sha(column_path, endpoints_path)
    if done.get("column_sha256") != actual_column_sha:
        raise RuntimeError(f"column SHA mismatch for {bundle_dir.name}")
    if done.get("endpoints_sha256") != actual_endpoints_sha:
        raise RuntimeError(f"endpoint SHA mismatch for {bundle_dir.name}")
    if done.get("output_sha256") != actual_output_sha:
        raise RuntimeError(f"bundle output SHA mismatch for {bundle_dir.name}")


def publish_bundle(
    *,
    artifact_root: Path,
    selection_row: dict[str, str],
    backend: str,
    binary: Path,
    queries: Path,
    bundle_expected: dict[str, object],
    max_wall_seconds: int,
    max_rss_bytes: int | None,
) -> dict[str, object]:
    r = int(selection_row["r"])
    u = selection_row["u"].lower()
    expected_count = int(selection_row["query_count"])
    bundle_dir = completed_bundle(artifact_root, r, u, backend)
    if bundle_dir.exists():
        verify_done_bundle(bundle_dir, expected=bundle_expected)
        done_payload = read_json(bundle_dir / "DONE.json")
        if not isinstance(done_payload, dict):
            raise RuntimeError(f"invalid DONE payload: {bundle_dir}")
        return done_payload

    staging_root = artifact_root / ".staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    staging_dir = staging_root / f"{bundle_name(r, u, backend)}.{os.getpid()}"
    if staging_dir.exists():
        raise RuntimeError(f"staging directory already exists: {staging_dir}")
    staging_dir.mkdir(parents=True)

    column_path = staging_dir / "column.json"
    endpoints_path = staging_dir / "endpoints.csv"
    done_path = staging_dir / "DONE.json"
    cmd = [
        str(binary),
        "--r",
        str(r),
        "--u",
        u,
        "--queries",
        str(queries),
        "--backend",
        backend,
        "--out-column",
        str(column_path),
        "--out-endpoints",
        str(endpoints_path),
    ]

    def preexec() -> None:
        if max_rss_bytes:
            resource.setrlimit(resource.RLIMIT_AS, (max_rss_bytes, max_rss_bytes))

    try:
        subprocess.run(
            cmd,
            check=True,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max_wall_seconds,
            preexec_fn=preexec if max_rss_bytes else None,
        )
        column_payload = json.loads(column_path.read_text(encoding="utf-8"))
        if not bool(column_payload["certified_exact_dyadic"]):
            raise RuntimeError(f"exact certificate false for {bundle_name(r, u, backend)}")
        if not bool(column_payload["parseval_pass"]):
            raise RuntimeError(f"parseval false for {bundle_name(r, u, backend)}")
        verify_endpoint_csv(endpoints_path, r=r, u=u, expected_count=expected_count)
        done_payload = {
            **bundle_expected,
            "schema": BUNDLE_SCHEMA,
            "column_sha256": sha256_file(column_path),
            "endpoints_sha256": sha256_file(endpoints_path),
            "output_sha256": bundle_output_sha(column_path, endpoints_path),
            "canonical_column_digest": column_payload["canonical_column_digest"],
            "completed_rounds": column_payload["completed_rounds"],
            "state_count": column_payload["state_count"],
            "sum_squares": column_payload["sum_squares"],
            "expected_sum_squares": column_payload["expected_sum_squares"],
            "certified_no_truncation": bool(column_payload["certified_no_truncation"]),
            "certified_exact_dyadic": bool(column_payload["certified_exact_dyadic"]),
            "parseval_pass": bool(column_payload["parseval_pass"]),
            "way1_numerator_convention": "K_r(u,v)",
        }
        write_json(done_path, done_payload)
        bundle_dir.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging_dir, bundle_dir)
        return done_payload
    except Exception:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", required=True)
    parser.add_argument("--backend", required=True, choices=["cpp_int", "int128_checked", "both"])
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--artifact-logical-root")
    parser.add_argument("--binary", default="recompute_frozen_exact")
    parser.add_argument("--binary-logical-path")
    parser.add_argument("--queries", default="experiments/frozen/final_queries.csv")
    parser.add_argument("--max-rss-bytes", type=int, default=0)
    args = parser.parse_args()

    if args.jobs != 1:
        raise SystemExit("current controlled pilot implementation requires --jobs 1")

    artifact_root = Path(args.artifact_root)
    selection_path = Path(args.selection)
    queries_path = ROOT / args.queries
    binary_path = Path(args.binary)
    if not binary_path.is_absolute():
        binary_path = ROOT / binary_path
    if not args.resume:
        ensure_empty_dir(artifact_root)
    else:
        artifact_root.mkdir(parents=True, exist_ok=True)

    require_clean_worktree(cwd=ROOT)
    source_commit = current_source_commit(cwd=ROOT)
    source_tree_sha = current_source_tree_sha(cwd=ROOT)
    verify_no_orphan_loose_outputs(artifact_root)
    check_partial_artifacts(artifact_root)
    binary = binary_path
    if not binary.exists():
        raise SystemExit("recompute_frozen_exact binary is missing; run make first")

    selection_payload = read_json(selection_json_path(selection_path, artifact_root))
    if not isinstance(selection_payload, dict):
        raise SystemExit("invalid selection JSON payload")
    selection_sha = sha256_file(selection_path)
    binary_sha = sha256_file(binary)
    input_sha = sha256_file(queries_path)
    artifact_root_logical = logical_path(artifact_root, logical_root=args.artifact_logical_root)
    binary_logical = logical_path(binary, logical_root=args.binary_logical_path or args.binary)
    selection_logical = logical_path(
        selection_path,
        logical_root=args.artifact_logical_root,
        suffix="PILOT_SELECTION.csv",
    )
    runner_command = (
        "python3 -X utf8 experiments/exact_way2/run_frozen_exact.py "
        f"--selection {selection_logical} "
        f"--backend {args.backend} "
        f"--jobs {args.jobs} "
        "--resume "
        f"--artifact-root {artifact_root_logical} "
        f"--binary {binary_logical} "
        f"--queries {repo_relative(queries_path)}"
    )
    runner_command_sha = command_sha(["python3", "-X", "utf8", runner_command])
    runner_start = time.perf_counter()
    runner_started_at = now_utc_microseconds()

    env_payload = {
        "artifact_root": artifact_root_logical,
        "selection_path": selection_logical,
        "queries_path": repo_relative(queries_path),
        "binary_path": binary_logical,
        "backend_mode": args.backend,
        "jobs": args.jobs,
        "source_checkout_commit": source_commit,
        "source_tree_sha": source_tree_sha,
        "source_tree_dirty": False,
        "git_status_porcelain_sha256": EMPTY_SHA256,
        "source_tree_diff_sha256": EMPTY_SHA256,
        "binary_build_commit": source_commit,
        "runner_commit": source_commit,
        "selector_commit": str(selection_payload["selector_source_commit"]),
        "artifact_generated_at_commit": source_commit,
        "binary_sha256": binary_sha,
        "final_ru_sha256": str(selection_payload["final_ru_sha256"]),
        "final_queries_sha256": str(selection_payload["final_queries_sha256"]),
        "selection_sha256": selection_sha,
        "command_sha256": runner_command_sha,
    }
    write_json(artifact_root / "ENVIRONMENT.json", env_payload)

    backends = ["cpp_int", "int128_checked"] if args.backend == "both" else [args.backend]
    rows = selection_rows(selection_path)
    (artifact_root / "locks").mkdir(exist_ok=True)

    completed_done_payloads: list[dict[str, object]] = []
    for row in rows:
        wall_limit = 120 if int(row["r"]) == 1 else 1200 if int(row["r"]) == 2 else 1800
        for backend in backends:
            lock = lock_path(artifact_root, int(row["r"]), row["u"], backend)
            if lock.exists():
                raise SystemExit(f"worker lock exists and must be audited explicitly: {repo_relative(lock)}")
            lock.write_text("locked\n", encoding="utf-8")
            try:
                bundle_expected = {
                    "r": int(row["r"]),
                    "u": row["u"].lower(),
                    "backend": backend,
                    "source_commit": source_commit,
                    "source_tree_sha": source_tree_sha,
                    "source_tree_dirty": False,
                    "binary_sha256": binary_sha,
                    "input_sha256": input_sha,
                    "selection_sha256": selection_sha,
                    "command_sha256": runner_command_sha,
                    "schema_version": BUNDLE_SCHEMA,
                }
                completed_done_payloads.append(
                    publish_bundle(
                        artifact_root=artifact_root,
                        selection_row=row,
                        backend=backend,
                        binary=binary,
                        queries=queries_path,
                        bundle_expected=bundle_expected,
                        max_wall_seconds=wall_limit,
                        max_rss_bytes=args.max_rss_bytes or None,
                    )
                )
            finally:
                if lock.exists():
                    lock.unlink()

    check_partial_artifacts(artifact_root)
    total_wall = time.perf_counter() - runner_start
    completed_dirs = sorted(path for path in (artifact_root / "completed").glob("*") if path.is_dir())
    peak_process_rss = 0
    cpp_wall_sum = 0.0
    int128_wall_sum = 0.0
    for bundle_dir in completed_dirs:
        column_payload = read_json(bundle_dir / "column.json")
        if isinstance(column_payload, dict):
            peak_process_rss = max(peak_process_rss, int(column_payload["peak_rss_bytes"]))
            if column_payload["backend"] == "cpp_int":
                cpp_wall_sum += float(column_payload["wall_seconds"])
            elif column_payload["backend"] == "int128_checked":
                int128_wall_sum += float(column_payload["wall_seconds"])

    write_json(
        artifact_root / "RUNNER.json",
        {
            **env_payload,
            "runner_command": runner_command,
            "runner_started_at_utc": runner_started_at,
            "runner_finished_at_utc": now_utc_microseconds(),
            "runner_elapsed_wall": total_wall,
            "cpp_int_column_wall_sum": cpp_wall_sum,
            "int128_column_wall_sum": int128_wall_sum,
            "peak_process_rss": peak_process_rss,
            "peak_total_concurrent_rss": peak_process_rss,
            "completed_bundle_count": len(completed_dirs),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
