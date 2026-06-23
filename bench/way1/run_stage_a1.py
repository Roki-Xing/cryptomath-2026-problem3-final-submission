#!/usr/bin/env python3
"""Run the bounded Stage-A1 safe-domain matrix."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_stage_a0 import (  # noqa: E402
    DEFAULT_SUBMIT_SHA,
    GENERATOR,
    RUNNER,
    VARIANTS,
    assert_semantic_equivalence,
    environment_metadata,
    git_commit,
    iso_utc_now,
    output_paths,
    read_json,
    require_clean_tracked_worktree,
    run_checked,
    sha256_file,
    verify_result_schema,
    write_sha_manifest,
)


@dataclass(frozen=True)
class QuerySpec:
    rounds: int
    count: int
    domain_bits: int
    family: str
    profile: str
    skip_reason: str = ""

    @property
    def case_id(self) -> str:
        slug = {
            "uniform": "uniform",
            "frozen-subset": "frozen",
            "synthetic-frozen-shaped": "synthetic",
        }[self.family]
        return f"r{self.rounds}_q{self.count}_{slug}"


@dataclass(frozen=True)
class RunSpec:
    query: QuerySpec
    threads: int
    order: str

    @property
    def case_id(self) -> str:
        return f"{self.query.case_id}_{self.order}_t{self.threads}"


def build_query_specs() -> list[QuerySpec]:
    domain_bits = {8: 22, 64: 20, 512: 17, 4096: 14, 16384: 12}
    specs: list[QuerySpec] = []
    for rounds in (1, 2, 3):
        for count, bits in domain_bits.items():
            for family, profile in (
                ("uniform", "sha-order"),
                ("frozen-subset", "uv_core"),
                ("synthetic-frozen-shaped", "uv_core"),
            ):
                unavailable = (
                    family == "frozen-subset" and rounds == 1 and count > 288
                )
                specs.append(
                    QuerySpec(
                        rounds,
                        count,
                        bits,
                        family,
                        profile,
                        "SKIP_UNAVAILABLE" if unavailable else "",
                    )
                )
    return specs


def build_run_specs(query_specs: list[QuerySpec], threads: int) -> list[RunSpec]:
    if threads <= 1:
        raise ValueError("Stage A1 requires threads > 1")
    runs: list[RunSpec] = []
    for query in query_specs:
        if query.skip_reason:
            continue
        runs.append(RunSpec(query, threads, "canonical"))
        if query.count == 512:
            runs.append(RunSpec(query, threads, "shuffled"))
    return runs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, required=True)
    parser.add_argument("--seed", default="stage-a1-v1")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--max-rss-kib", type=int, default=2097152)
    parser.add_argument("--submit-sha256", default=DEFAULT_SUBMIT_SHA)
    parser.add_argument(
        "--out-dir", type=Path, default=ROOT / "bench" / "way1" / "stage_a1"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir = args.out_dir.resolve()
    if args.threads <= 1 or args.timeout_seconds <= 0 or args.max_rss_kib <= 0:
        raise SystemExit("error: invalid thread or resource limit")
    if args.out_dir.exists() and any(args.out_dir.iterdir()):
        raise SystemExit(f"error: output directory is not empty: {args.out_dir}")
    try:
        require_clean_tracked_worktree()
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc

    source = ROOT / "experiments" / "frozen" / "final_queries.csv"
    ru_source = ROOT / "experiments" / "frozen" / "final_ru.csv"
    submit = ROOT / "submit.txt"
    submit_before = sha256_file(submit)
    if submit_before != args.submit_sha256:
        raise SystemExit("error: submit SHA mismatch")

    started_at = iso_utc_now()
    started = time.perf_counter()
    environment = environment_metadata(
        argparse.Namespace(
            compiler_id="gcc",
            compiler_flags="-O3 -std=c++17 -Wall -Wextra -pedantic -pthread",
            cpu_affinity="unbound",
            threads=args.threads,
        )
    )
    query_dir = args.out_dir / "queries"
    result_dir = args.out_dir / "results"
    artifact_root = args.out_dir / "artifacts"
    for path in (query_dir, result_dir, artifact_root):
        path.mkdir(parents=True, exist_ok=True)

    specs = build_query_specs()
    runs = build_run_specs(specs, args.threads)
    query_paths: dict[str, Path] = {}
    query_records: list[dict[str, object]] = []
    skips: list[dict[str, object]] = []
    for spec in specs:
        if spec.skip_reason:
            skips.append({**asdict(spec), "case_id": spec.case_id})
            continue
        query_path = query_dir / f"{spec.case_id}.csv"
        metadata_path = query_dir / f"{spec.case_id}.json"
        run_checked(
            [
                "python3", "-X", "utf8", str(GENERATOR),
                "--source", str(source), "--ru-source", str(ru_source),
                "--family", spec.family, "--profile", spec.profile,
                "--r", str(spec.rounds), "--count", str(spec.count),
                "--seed", args.seed, "--out", str(query_path),
                "--metadata-out", str(metadata_path),
            ]
        )
        metadata = read_json(metadata_path)
        query_paths[spec.case_id] = query_path
        query_records.append(
            {
                **asdict(spec),
                "case_id": spec.case_id,
                "query_path": str(query_path.relative_to(args.out_dir)),
                "metadata_path": str(metadata_path.relative_to(args.out_dir)),
                "query_sha256": sha256_file(query_path),
                "semantic_query_sha256": metadata["semantic_query_sha256"],
                "unique_u": metadata["unique_u"],
                "unique_v": metadata["unique_v"],
            }
        )

    outputs: dict[str, list[Path]] = {case: [] for case in query_paths}
    run_records: list[dict[str, object]] = []
    for spec in runs:
        result_path = result_dir / f"{spec.case_id}.csv"
        log_path = result_dir / f"{spec.case_id}.runner.log"
        artifact_dir = artifact_root / spec.case_id
        command = [
            "python3", "-X", "utf8", str(RUNNER),
            "--queries", str(query_paths[spec.query.case_id]),
            "--query-family", spec.query.family,
            "--query-profile", spec.query.profile,
            "--seed", args.seed, "--order", spec.order,
            "--r", str(spec.query.rounds),
            "--domain-bits", str(spec.query.domain_bits),
            "--threads", str(spec.threads),
            "--variants", ",".join(VARIANTS), "--repeats", "1",
            "--timeout-seconds", str(args.timeout_seconds),
            "--max-rss-kib", str(args.max_rss_kib),
            "--compiler-id", str(environment["compiler_id"]),
            "--compiler-version", str(environment["compiler_version"]),
            f"--compiler-flags={environment['compiler_flags']}",
            "--cpu-model", str(environment["cpu_model"]),
            "--ram-bytes", str(environment["ram_bytes"]),
            "--numa", str(environment["numa"]),
            "--kernel", str(environment["kernel"]),
            "--cpu-affinity", str(environment["cpu_affinity"]),
            "--submit-sha256", args.submit_sha256,
            "--out", str(result_path), "--artifacts-dir", str(artifact_dir),
        ]
        completed = run_checked(command)
        log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
        rows = verify_result_schema(result_path, len(VARIANTS))
        case_outputs = output_paths(artifact_dir)
        outputs[spec.query.case_id].extend(case_outputs)
        run_records.append(
            {
                "case_id": spec.case_id,
                "query_case_id": spec.query.case_id,
                "order": spec.order,
                "result_path": str(result_path.relative_to(args.out_dir)),
                "result_sha256": sha256_file(result_path),
                "result_rows": len(rows),
            }
        )

    for paths in outputs.values():
        assert_semantic_equivalence(paths)
    submit_after = sha256_file(submit)
    if submit_after != submit_before:
        raise ValueError("submit SHA changed during Stage A1")

    summary = {
        "schema": "way1-stage-a1-summary-v1",
        "status": "STAGE_A1_PASS",
        "query_spec_count": len(specs),
        "available_query_artifacts": len(query_records),
        "skip_unavailable_count": len(skips),
        "run_case_count": len(run_records),
        "result_row_count": len(run_records) * len(VARIANTS),
        "semantic_mismatch_count": 0,
        "timeout_count": 0,
        "oom_count": 0,
        "nonzero_exit_count": 0,
        "submit_sha256_before": submit_before,
        "submit_sha256_after": submit_after,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    manifest = {
        "schema": "way1-stage-a1-manifest-v1",
        "status": "STAGE_A1_PASS",
        "started_at": started_at,
        "completed_at": iso_utc_now(),
        "repository_commit": git_commit(),
        "seed": args.seed,
        "environment": environment,
        "query_artifacts": query_records,
        "skips": skips,
        "runs": run_records,
        "summary": summary,
    }
    (args.out_dir / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.out_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_sha_manifest(args.out_dir)
    print("status=STAGE_A1_PASS")
    print(f"query_artifacts={len(query_records)}")
    print(f"skip_unavailable={len(skips)}")
    print(f"run_cases={len(run_records)}")
    print(f"submit_sha256={submit_after}")


if __name__ == "__main__":
    main()
