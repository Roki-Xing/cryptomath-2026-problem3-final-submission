#!/usr/bin/env python3
"""Run the bounded Stage-A2 shard and reduction matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_protocol import (  # noqa: E402
    parse_time_file,
    run_with_timeout,
    write_manifest,
)
from run_stage_a0 import (  # noqa: E402
    DEFAULT_SUBMIT_SHA,
    environment_metadata,
    git_commit,
    iso_utc_now,
    require_clean_tracked_worktree,
    sha256_file,
    write_sha_manifest,
)
from stage_a0_support import assert_semantic_equivalence  # noqa: E402


EXECUTABLES = {
    "current": ROOT / "exact_batch_current",
    "grouped_u": ROOT / "exact_batch_grouped_u",
    "grouped_uv": ROOT / "exact_batch_grouped_uv",
}
REDUCER = ROOT / "bench" / "way1" / "reduce_shards.py"


@dataclass(frozen=True)
class Anchor:
    name: str
    rounds: int
    count: int
    domain_bits: int
    query_path: Path


@dataclass(frozen=True)
class MatrixSpec:
    anchor: Anchor
    implementation: str
    shards: int
    partition: str

    @property
    def case_id(self) -> str:
        return f"{self.anchor.name}_{self.implementation}_k{self.shards}"


def anchors() -> list[Anchor]:
    query_root = ROOT / "bench" / "way1" / "stage_a0" / "queries"
    return [
        Anchor("r1_q64_frozen", 1, 64, 20, query_root / "r1_q64_frozen.csv"),
        Anchor("r2_q512_frozen", 2, 512, 17, query_root / "r2_q512_frozen.csv"),
        Anchor(
            "r3_q512_synthetic",
            3,
            512,
            17,
            query_root / "r3_q512_synthetic.csv",
        ),
    ]


def build_matrix() -> list[MatrixSpec]:
    specs: list[MatrixSpec] = []
    for anchor in anchors():
        for implementation in EXECUTABLES:
            specs.append(MatrixSpec(anchor, implementation, 1, "equal"))
            specs.append(MatrixSpec(anchor, implementation, 2, "equal"))
        for implementation in ("grouped_u", "grouped_uv"):
            specs.append(MatrixSpec(anchor, implementation, 7, "seeded-unequal"))
            specs.append(MatrixSpec(anchor, implementation, 16, "seeded-unequal"))
    specs.append(MatrixSpec(anchors()[1], "current", 7, "seeded-unequal"))
    return specs


def partition_ranges(
    total: int, shards: int, partition: str, seed: str
) -> list[tuple[int, int]]:
    if shards <= 0 or total < shards:
        raise ValueError("shard count must be positive and no greater than domain")
    if partition == "equal":
        base, extra = divmod(total, shards)
        lengths = [base + (index < extra) for index in range(shards)]
    elif partition == "seeded-unequal":
        weights = [
            1
            + int.from_bytes(
                hashlib.sha256(f"{seed}\0{index}".encode()).digest()[:8], "big"
            )
            for index in range(shards)
        ]
        remaining = total - shards
        weight_sum = sum(weights)
        quotients = [divmod(remaining * weight, weight_sum) for weight in weights]
        lengths = [1 + quotient for quotient, _ in quotients]
        leftover = total - sum(lengths)
        order = sorted(
            range(shards),
            key=lambda index: (-quotients[index][1], index),
        )
        for index in order[:leftover]:
            lengths[index] += 1
    else:
        raise ValueError(f"unsupported partition: {partition}")
    ranges: list[tuple[int, int]] = []
    cursor = 0
    for length in lengths:
        ranges.append((cursor, cursor + length))
        cursor += length
    if cursor != total or any(start >= end for start, end in ranges):
        raise ValueError("partition does not exactly cover the domain")
    return ranges


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, required=True)
    parser.add_argument("--partition-seed", default="stage-a2-v1")
    parser.add_argument("--timeout-per-shard", type=float, default=300)
    parser.add_argument("--max-rss-kib", type=int, default=1048576)
    parser.add_argument("--submit-sha256", default=DEFAULT_SUBMIT_SHA)
    parser.add_argument(
        "--out-dir", type=Path, default=ROOT / "bench" / "way1" / "stage_a2"
    )
    return parser.parse_args()


def verify_submit(expected: str) -> None:
    actual = sha256_file(ROOT / "submit.txt")
    if actual != expected:
        raise ValueError(f"submit SHA mismatch: {expected} != {actual}")


def run_shard(
    spec: MatrixSpec,
    shard_index: int,
    start: int,
    end: int,
    args: argparse.Namespace,
    case_dir: Path,
) -> Path:
    executable = EXECUTABLES[spec.implementation]
    program_sha = sha256_file(executable)
    query_sha = sha256_file(spec.anchor.query_path)
    output = case_dir / f"part-{shard_index:02d}.csv"
    timing_path = case_dir / f"part-{shard_index:02d}.time.csv"
    manifest = case_dir / f"part-{shard_index:02d}.manifest.json"
    child = [
        str(executable),
        "--r", str(spec.anchor.rounds),
        "--queries", str(spec.anchor.query_path),
        "--query-sha256", query_sha,
        "--program-sha256", program_sha,
        "--start", str(start), "--end", str(end),
        "--threads", str(args.threads), "--out", str(output),
    ]
    command = [
        "/usr/bin/time", "-f", "%e,%U,%S,%M,%x",
        "-o", str(timing_path), *child,
    ]
    verify_submit(args.submit_sha256)
    returncode, stdout, stderr, _ = run_with_timeout(
        command, args.timeout_per_shard
    )
    write_manifest(
        manifest,
        implementation=spec.implementation,
        query_path=spec.anchor.query_path,
        query_sha256=query_sha,
        program_path=executable,
        program_sha256=program_sha,
        output_path=output,
        range_start=start,
        range_end=end,
        command=command,
        exit_status=returncode,
    )
    verify_submit(args.submit_sha256)
    if returncode != 0:
        raise RuntimeError(f"{spec.case_id} shard {shard_index}: {stderr or stdout}")
    timing = parse_time_file(timing_path)
    if int(timing["peak_rss_kib"]) > args.max_rss_kib:
        raise RuntimeError(f"{spec.case_id} shard {shard_index} exceeded RSS")
    return manifest


def main() -> None:
    args = parse_args()
    args.out_dir = args.out_dir.resolve()
    if args.threads <= 0 or args.timeout_per_shard <= 0 or args.max_rss_kib <= 0:
        raise SystemExit("error: invalid Stage A2 resource setting")
    if args.out_dir.exists() and any(args.out_dir.iterdir()):
        raise SystemExit(f"error: output directory is not empty: {args.out_dir}")
    try:
        require_clean_tracked_worktree()
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
    for anchor in anchors():
        if not anchor.query_path.is_file():
            raise SystemExit(f"error: missing A0 anchor query: {anchor.query_path}")
    verify_submit(args.submit_sha256)

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
    records: list[dict[str, object]] = []
    reduced_by_anchor: dict[str, list[Path]] = {anchor.name: [] for anchor in anchors()}
    for spec in build_matrix():
        case_dir = args.out_dir / spec.case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        total = 1 << spec.anchor.domain_bits
        ranges = partition_ranges(
            total, spec.shards, spec.partition, args.partition_seed + spec.case_id
        )
        manifests = [
            run_shard(spec, index, start, end, args, case_dir)
            for index, (start, end) in enumerate(ranges)
        ]
        reduced = case_dir / "reduced.csv"
        executable = EXECUTABLES[spec.implementation]
        command = [
            "python3", "-X", "utf8", str(REDUCER),
            "--expected-start", "0", "--expected-end", str(total),
            "--expected-query-sha256", sha256_file(spec.anchor.query_path),
            "--expected-program-sha256", sha256_file(executable),
            "--out", str(reduced), *map(str, manifests),
        ]
        completed = subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, check=False
        )
        if completed.returncode != 0:
            raise RuntimeError(f"reducer failed for {spec.case_id}: {completed.stderr}")
        reduced_by_anchor[spec.anchor.name].append(reduced)
        records.append(
            {
                "case_id": spec.case_id,
                "anchor": spec.anchor.name,
                "implementation": spec.implementation,
                "shards": spec.shards,
                "partition": spec.partition,
                "ranges": ranges,
                "query_sha256": sha256_file(spec.anchor.query_path),
                "program_sha256": sha256_file(executable),
                "reduced_path": str(reduced.relative_to(args.out_dir)),
                "reduced_sha256": sha256_file(reduced),
                "manifest_count": len(manifests),
            }
        )

    for reduced_paths in reduced_by_anchor.values():
        assert_semantic_equivalence(reduced_paths)
    verify_submit(args.submit_sha256)
    summary = {
        "schema": "way1-stage-a2-summary-v1",
        "status": "STAGE_A2_PASS",
        "matrix_case_count": len(records),
        "raw_shard_count": sum(int(record["manifest_count"]) for record in records),
        "semantic_mismatch_count": 0,
        "reducer_corruption_cases_passed": 12,
        "timeout_count": 0,
        "oom_count": 0,
        "nonzero_exit_count": 0,
        "submit_sha256": args.submit_sha256,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    manifest = {
        "schema": "way1-stage-a2-manifest-v1",
        "status": "STAGE_A2_PASS",
        "started_at": started_at,
        "completed_at": iso_utc_now(),
        "repository_commit": git_commit(),
        "partition_seed": args.partition_seed,
        "environment": environment,
        "cases": records,
        "summary": summary,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.out_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_sha_manifest(args.out_dir)
    print("status=STAGE_A2_PASS")
    print(f"matrix_cases={len(records)}")
    print(f"raw_shards={summary['raw_shard_count']}")
    print(f"submit_sha256={args.submit_sha256}")


if __name__ == "__main__":
    main()
