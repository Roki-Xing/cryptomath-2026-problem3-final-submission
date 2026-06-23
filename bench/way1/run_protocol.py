#!/usr/bin/env python3
"""Run bounded exact way-1 benchmark variants and record reproducible metrics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FULL_DOMAIN = 1 << 32
DEFAULT_MAX_DOMAIN = 1 << 28
EXECUTABLES = {
    "current": ROOT / "exact_batch_current",
    "grouped_u": ROOT / "exact_batch_grouped_u",
    "grouped_uv": ROOT / "exact_batch_grouped_uv",
}
RESULT_FIELDS = [
    "run_id",
    "implementation",
    "r",
    "Q",
    "unique_u",
    "unique_v",
    "domain_start",
    "domain_end",
    "plaintext_count",
    "threads",
    "wall_seconds",
    "user_cpu_seconds",
    "system_cpu_seconds",
    "peak_rss_kib",
    "logical_query_updates",
    "query_updates_per_second",
    "plaintexts_per_second",
    "u_parity_evaluations",
    "v_parity_evaluations",
    "permutation_evaluations",
    "program_commit",
    "program_sha256",
    "input_sha256",
    "output_sha256",
    "exit_status",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--r", type=int, required=True, choices=(1, 2, 3))
    parser.add_argument("--domain-bits", type=int)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument(
        "--variants",
        default="current,grouped_u,grouped_uv",
        help="comma-separated subset of current,grouped_u,grouped_uv",
    )
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--artifacts-dir", type=Path, required=True)
    parser.add_argument("--allow-large-domain", action="store_true")
    parser.add_argument("--allow-full-domain", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_query_shape(path: Path, rounds: int) -> tuple[int, int, int]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not {"r", "u", "v"}.issubset(reader.fieldnames):
            raise ValueError("query file must contain r,u,v columns")
        rows = list(reader)
    if not rows:
        raise ValueError("query file contains no rows")
    if any(int(row["r"]) != rounds for row in rows):
        raise ValueError("query file contains a round different from --r")
    unique_u = {int(row["u"], 0) for row in rows}
    unique_v = {int(row["v"], 0) for row in rows}
    return len(rows), len(unique_u), len(unique_v)


def parse_metadata(path: Path) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("# "):
            continue
        key, separator, value = line[2:].partition("=")
        if separator:
            metadata[key] = value
    return metadata


def result_signature(path: Path) -> tuple[tuple[str, ...], ...]:
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    reader = csv.DictReader(lines)
    return tuple(
        (row["r"], row["u"], row["v"], row["numerator"], row["denominator"])
        for row in reader
    )


def parse_time_file(path: Path) -> dict[str, str]:
    fields = path.read_text(encoding="utf-8").strip().split(",")
    if len(fields) != 5:
        raise ValueError(f"unexpected /usr/bin/time output: {fields}")
    return {
        "wall_seconds": fields[0],
        "user_cpu_seconds": fields[1],
        "system_cpu_seconds": fields[2],
        "peak_rss_kib": fields[3],
        "exit_status": fields[4],
    }


def git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def main() -> None:
    args = parse_args()
    try:
        if args.threads <= 0 or args.repeats <= 0:
            raise ValueError("--threads and --repeats must be positive")
        if args.domain_bits is not None and args.end is not None:
            raise ValueError("--domain-bits and --end are mutually exclusive")
        if args.domain_bits is not None:
            if not 0 <= args.domain_bits <= 32:
                raise ValueError("--domain-bits must be in [0,32]")
            end = args.start + (1 << args.domain_bits)
        else:
            end = args.end
        if end is None or args.start < 0 or args.start >= end or end > FULL_DOMAIN:
            raise ValueError("invalid benchmark range")
        plaintext_count = end - args.start
        if plaintext_count == FULL_DOMAIN and not args.allow_full_domain:
            raise ValueError("full 2^32 domain requires --allow-full-domain")
        if plaintext_count > DEFAULT_MAX_DOMAIN and not args.allow_large_domain:
            raise ValueError("domain above 2^28 requires --allow-large-domain")

        variants = args.variants.split(",")
        if not variants or any(variant not in EXECUTABLES for variant in variants):
            raise ValueError(f"unsupported variants: {variants}")
        if len(set(variants)) != len(variants):
            raise ValueError("duplicate benchmark variant")

        query_count, unique_u, unique_v = read_query_shape(args.queries, args.r)
        input_sha = sha256_file(args.queries)
        commit = git_commit()
        args.artifacts_dir.mkdir(parents=True, exist_ok=True)
        args.out.parent.mkdir(parents=True, exist_ok=True)

        rows: list[dict[str, str | int]] = []
        reference_signature: tuple[tuple[str, ...], ...] | None = None
        for repeat in range(1, args.repeats + 1):
            for implementation in variants:
                executable = EXECUTABLES[implementation]
                if not executable.is_file():
                    raise ValueError(f"missing executable: {executable}")
                run_id = (
                    f"r{args.r}-q{query_count}-n{plaintext_count}-"
                    f"{implementation}-rep{repeat}"
                )
                output_path = args.artifacts_dir / f"{run_id}.csv"
                time_path = args.artifacts_dir / f"{run_id}.time.csv"
                command = [
                    "/usr/bin/time",
                    "-f",
                    "%e,%U,%S,%M,%x",
                    "-o",
                    str(time_path),
                    str(executable),
                    "--r",
                    str(args.r),
                    "--queries",
                    str(args.queries),
                    "--query-sha256",
                    input_sha,
                    "--start",
                    str(args.start),
                    "--end",
                    str(end),
                    "--threads",
                    str(args.threads),
                    "--out",
                    str(output_path),
                ]
                started = time.perf_counter()
                completed = subprocess.run(
                    command, cwd=ROOT, text=True, capture_output=True, check=False
                )
                measured_wall_seconds = time.perf_counter() - started
                if completed.returncode != 0:
                    raise RuntimeError(
                        f"{run_id} failed with {completed.returncode}: {completed.stderr}"
                    )
                timing = parse_time_file(time_path)
                metadata = parse_metadata(output_path)
                if metadata.get("implementation") != implementation:
                    raise ValueError(f"implementation metadata mismatch for {run_id}")
                if metadata.get("query_sha256") != input_sha:
                    raise ValueError(f"query hash metadata mismatch for {run_id}")

                signature = result_signature(output_path)
                if reference_signature is None:
                    reference_signature = signature
                elif signature != reference_signature:
                    raise ValueError(f"numerator mismatch for {run_id}")

                wall_seconds = measured_wall_seconds
                logical_updates = int(metadata["logical_query_updates"])
                rows.append(
                    {
                        "run_id": run_id,
                        "implementation": implementation,
                        "r": args.r,
                        "Q": query_count,
                        "unique_u": unique_u,
                        "unique_v": unique_v,
                        "domain_start": args.start,
                        "domain_end": end,
                        "plaintext_count": plaintext_count,
                        "threads": args.threads,
                        "wall_seconds": f"{wall_seconds:.9f}",
                        "user_cpu_seconds": timing["user_cpu_seconds"],
                        "system_cpu_seconds": timing["system_cpu_seconds"],
                        "peak_rss_kib": timing["peak_rss_kib"],
                        "logical_query_updates": logical_updates,
                        "query_updates_per_second": (
                            f"{logical_updates / wall_seconds:.9f}"
                            if wall_seconds > 0
                            else "inf"
                        ),
                        "plaintexts_per_second": (
                            f"{plaintext_count / wall_seconds:.9f}"
                            if wall_seconds > 0
                            else "inf"
                        ),
                        "u_parity_evaluations": metadata["u_parity_evaluations"],
                        "v_parity_evaluations": metadata["v_parity_evaluations"],
                        "permutation_evaluations": metadata[
                            "permutation_evaluations"
                        ],
                        "program_commit": commit,
                        "program_sha256": sha256_file(executable),
                        "input_sha256": input_sha,
                        "output_sha256": sha256_file(output_path),
                        "exit_status": timing["exit_status"],
                    }
                )

        with args.out.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"error: {exc}") from exc

    print(f"benchmark_rows={len(rows)}")
    print(f"numerator_cross_variant_match=1")
    print(f"results={args.out}")


if __name__ == "__main__":
    main()
