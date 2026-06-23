#!/usr/bin/env python3
"""Run the bounded Stage-A0 exact way-1 benchmark matrix."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from stage_a0_support import (  # noqa: E402
    QuerySpec,
    assert_semantic_equivalence,
    build_query_specs,
    build_run_specs,
    semantic_result_map,
)


GENERATOR = ROOT / "bench" / "way1" / "generate_query_family.py"
RUNNER = ROOT / "bench" / "way1" / "run_protocol.py"
SCHEMA = ROOT / "bench" / "way1" / "benchmark_schema.json"
DEFAULT_SUBMIT_SHA = (
    "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e"
)
VARIANTS = ("current", "grouped_u", "grouped_uv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT / "experiments" / "frozen" / "final_queries.csv",
    )
    parser.add_argument(
        "--ru-source",
        type=Path,
        default=ROOT / "experiments" / "frozen" / "final_ru.csv",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "bench" / "way1" / "stage_a0",
    )
    parser.add_argument("--threads", type=int, required=True)
    parser.add_argument("--seed", default="stage-a0-v1")
    parser.add_argument("--max-rss-kib", type=int, default=1048576)
    parser.add_argument("--submit-sha256", default=DEFAULT_SUBMIT_SHA)
    parser.add_argument("--compiler-id", default="gcc")
    parser.add_argument(
        "--compiler-flags",
        default="-O3 -std=c++17 -Wall -Wextra -pedantic -pthread",
    )
    parser.add_argument("--cpu-affinity", default="unbound")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def require_clean_tracked_worktree() -> None:
    for command in (
        ["git", "diff", "--quiet"],
        ["git", "diff", "--cached", "--quiet"],
    ):
        if subprocess.run(command, cwd=ROOT, check=False).returncode != 0:
            raise ValueError("Stage A0 requires a clean tracked worktree")


def compiler_version() -> str:
    return subprocess.check_output(
        ["g++", "--version"], cwd=ROOT, text=True
    ).splitlines()[0]


def cpu_model() -> str:
    for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("model name"):
            return line.partition(":")[2].strip()
    return platform.processor() or "unknown"


def environment_metadata(args: argparse.Namespace) -> dict[str, object]:
    node_paths = sorted(Path("/sys/devices/system/node").glob("node[0-9]*"))
    return {
        "cpu_model": cpu_model(),
        "logical_cpu_count": os.cpu_count(),
        "ram_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"),
        "numa": f"{len(node_paths) or 1}-node",
        "kernel": platform.release(),
        "compiler_id": args.compiler_id,
        "compiler_version": compiler_version(),
        "compiler_flags": args.compiler_flags,
        "cpu_affinity": args.cpu_affinity,
        "multithread": args.threads,
    }


def run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command, cwd=ROOT, text=True, capture_output=True, check=False
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
    return completed


def read_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def verify_result_schema(path: Path, expected_rows: int) -> list[dict[str, str]]:
    required = set(read_json(SCHEMA)["required_fields"])
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != expected_rows:
        raise ValueError(f"{path} has {len(rows)} rows, expected {expected_rows}")
    if not rows or set(rows[0]) != required:
        raise ValueError(f"{path} does not match benchmark_schema.json")
    if any(value == "" for row in rows for value in row.values()):
        raise ValueError(f"{path} contains an empty required field")
    if any(row["exit_status"] != "0" for row in rows):
        raise ValueError(f"{path} contains a nonzero exit status")
    return rows


def output_paths(artifacts_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for manifest_path in sorted(artifacts_dir.glob("*.manifest.json")):
        manifest = read_json(manifest_path)
        if manifest.get("exit_status") != 0:
            raise ValueError(f"nonzero manifest exit status: {manifest_path}")
        output = Path(str(manifest["output_path"]))
        if not output.is_file():
            raise ValueError(f"missing output referenced by {manifest_path}: {output}")
        if sha256_file(output) != manifest["output_sha256"]:
            raise ValueError(f"output SHA mismatch: {manifest_path}")
        paths.append(output)
    if len(paths) != len(VARIANTS):
        raise ValueError(
            f"{artifacts_dir} has {len(paths)} manifests, expected {len(VARIANTS)}"
        )
    return paths


def write_sha_manifest(root: Path) -> Path:
    manifest = root / "SHA256SUMS.txt"
    files = sorted(
        path for path in root.rglob("*") if path.is_file() and path != manifest
    )
    manifest.write_text(
        "".join(
            f"{sha256_file(path)}  ./{path.relative_to(root).as_posix()}\n"
            for path in files
        ),
        encoding="utf-8",
    )
    return manifest


def iso_utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main() -> None:
    args = parse_args()
    args.source = args.source.resolve()
    args.ru_source = args.ru_source.resolve()
    args.out_dir = args.out_dir.resolve()
    if args.threads <= 1:
        raise SystemExit("error: --threads must be greater than 1")
    if args.max_rss_kib <= 0:
        raise SystemExit("error: --max-rss-kib must be positive")
    if args.out_dir.exists() and any(args.out_dir.iterdir()):
        raise SystemExit(f"error: output directory is not empty: {args.out_dir}")
    expected_source = (ROOT / "experiments" / "frozen" / "final_queries.csv").resolve()
    expected_ru_source = (ROOT / "experiments" / "frozen" / "final_ru.csv").resolve()
    if args.source != expected_source or args.ru_source != expected_ru_source:
        raise SystemExit("error: Stage A0 accepts only the two frozen input artifacts")
    try:
        require_clean_tracked_worktree()
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
    for executable in (
        ROOT / "exact_batch_current",
        ROOT / "exact_batch_grouped_u",
        ROOT / "exact_batch_grouped_uv",
    ):
        if not executable.is_file():
            raise SystemExit(f"error: missing benchmark executable: {executable}")

    started_at = iso_utc_now()
    started_monotonic = time.perf_counter()
    submit_path = ROOT / "submit.txt"
    submit_before = sha256_file(submit_path)
    if submit_before != args.submit_sha256:
        raise SystemExit(
            f"error: submit SHA mismatch: expected {args.submit_sha256}, "
            f"got {submit_before}"
        )

    query_dir = args.out_dir / "queries"
    results_dir = args.out_dir / "results"
    artifacts_root = args.out_dir / "artifacts"
    query_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    artifacts_root.mkdir(parents=True, exist_ok=True)

    environment = environment_metadata(args)
    query_specs = build_query_specs()
    run_specs = build_run_specs(query_specs, args.threads)
    query_records: list[dict[str, object]] = []
    skip_records: list[dict[str, object]] = []
    query_paths: dict[str, Path] = {}

    for spec in query_specs:
        if spec.skip_reason:
            skip_records.append(
                {
                    **asdict(spec),
                    "case_id": spec.case_id,
                    "status": spec.skip_reason,
                }
            )
            continue
        query_path = query_dir / f"{spec.case_id}.csv"
        metadata_path = query_dir / f"{spec.case_id}.json"
        completed = run_checked(
            [
                "python3",
                "-X",
                "utf8",
                str(GENERATOR),
                "--source",
                str(args.source),
                "--ru-source",
                str(args.ru_source),
                "--family",
                spec.family,
                "--profile",
                spec.profile,
                "--r",
                str(spec.rounds),
                "--count",
                str(spec.count),
                "--seed",
                args.seed,
                "--out",
                str(query_path),
                "--metadata-out",
                str(metadata_path),
            ]
        )
        metadata = read_json(metadata_path)
        if metadata.get("Q") != spec.count:
            raise ValueError(f"query count mismatch: {metadata_path}")
        query_paths[spec.case_id] = query_path
        query_records.append(
            {
                **asdict(spec),
                "case_id": spec.case_id,
                "query_path": str(query_path.relative_to(args.out_dir)),
                "metadata_path": str(metadata_path.relative_to(args.out_dir)),
                "query_sha256": sha256_file(query_path),
                "metadata_sha256": sha256_file(metadata_path),
                "semantic_query_sha256": metadata["semantic_query_sha256"],
                "unique_u": metadata["unique_u"],
                "unique_v": metadata["unique_v"],
                "generator_stdout": completed.stdout.strip(),
            }
        )

    run_records: list[dict[str, object]] = []
    outputs_by_query: dict[str, list[Path]] = {
        case_id: [] for case_id in query_paths
    }
    for spec in run_specs:
        result_path = results_dir / f"{spec.case_id}.csv"
        log_path = results_dir / f"{spec.case_id}.runner.log"
        artifacts_dir = artifacts_root / spec.case_id
        command = [
            "python3",
            "-X",
            "utf8",
            str(RUNNER),
            "--queries",
            str(query_paths[spec.query.case_id]),
            "--query-family",
            spec.query.family,
            "--query-profile",
            spec.query.profile,
            "--seed",
            args.seed,
            "--order",
            spec.order,
            "--r",
            str(spec.query.rounds),
            "--domain-bits",
            "16",
            "--threads",
            str(spec.threads),
            "--variants",
            ",".join(VARIANTS),
            "--repeats",
            "1",
            "--timeout-seconds",
            str(spec.query.timeout_seconds),
            "--max-rss-kib",
            str(args.max_rss_kib),
            "--compiler-id",
            str(environment["compiler_id"]),
            "--compiler-version",
            str(environment["compiler_version"]),
            f"--compiler-flags={environment['compiler_flags']}",
            "--cpu-model",
            str(environment["cpu_model"]),
            "--ram-bytes",
            str(environment["ram_bytes"]),
            "--numa",
            str(environment["numa"]),
            "--kernel",
            str(environment["kernel"]),
            "--cpu-affinity",
            str(environment["cpu_affinity"]),
            "--submit-sha256",
            args.submit_sha256,
            "--out",
            str(result_path),
            "--artifacts-dir",
            str(artifacts_dir),
        ]
        completed = run_checked(command)
        log_path.write_text(
            completed.stdout + completed.stderr, encoding="utf-8"
        )
        rows = verify_result_schema(result_path, len(VARIANTS))
        outputs = output_paths(artifacts_dir)
        outputs_by_query[spec.query.case_id].extend(outputs)
        run_records.append(
            {
                "case_id": spec.case_id,
                "query_case_id": spec.query.case_id,
                "threads": spec.threads,
                "order": spec.order,
                "result_path": str(result_path.relative_to(args.out_dir)),
                "result_sha256": sha256_file(result_path),
                "log_path": str(log_path.relative_to(args.out_dir)),
                "log_sha256": sha256_file(log_path),
                "result_rows": len(rows),
                "semantic_query_sha256": rows[0]["semantic_query_sha256"],
                "manifest_count": len(outputs),
            }
        )

    for paths in outputs_by_query.values():
        assert_semantic_equivalence(paths)

    submit_after = sha256_file(submit_path)
    if submit_after != submit_before:
        raise ValueError(
            f"submit SHA changed during Stage A0: {submit_before} -> {submit_after}"
        )

    completed_at = iso_utc_now()
    elapsed_seconds = time.perf_counter() - started_monotonic
    summary = {
        "schema": "way1-stage-a0-summary-v1",
        "status": "STAGE_A0_PASS",
        "query_spec_count": len(query_specs),
        "available_query_artifacts": len(query_records),
        "skip_unavailable_count": len(skip_records),
        "run_case_count": len(run_records),
        "result_row_count": sum(int(record["result_rows"]) for record in run_records),
        "semantic_mismatch_count": 0,
        "timeout_count": 0,
        "oom_count": 0,
        "nonzero_exit_count": 0,
        "submit_sha256_before": submit_before,
        "submit_sha256_after": submit_after,
        "elapsed_seconds": round(elapsed_seconds, 6),
    }
    manifest = {
        "schema": "way1-stage-a0-manifest-v1",
        "status": "STAGE_A0_PASS",
        "started_at": started_at,
        "completed_at": completed_at,
        "repository_commit": git_commit(),
        "source_path": str(args.source.relative_to(ROOT)),
        "source_sha256": sha256_file(args.source),
        "ru_source_path": str(args.ru_source.relative_to(ROOT)),
        "ru_source_sha256": sha256_file(args.ru_source),
        "seed": args.seed,
        "domain_bits": 16,
        "variants": list(VARIANTS),
        "environment": environment,
        "query_artifacts": query_records,
        "skips": skip_records,
        "runs": run_records,
        "summary": summary,
    }
    (args.out_dir / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.out_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    sha_manifest = write_sha_manifest(args.out_dir)

    print("status=STAGE_A0_PASS")
    print(f"query_artifacts={len(query_records)}")
    print(f"skip_unavailable={len(skip_records)}")
    print(f"run_cases={len(run_records)}")
    print(f"result_rows={summary['result_row_count']}")
    print(f"submit_sha256={submit_after}")
    print(f"sha_manifest={sha_manifest}")


if __name__ == "__main__":
    main()
