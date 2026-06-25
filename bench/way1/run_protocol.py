#!/usr/bin/env python3
"""Run bounded exact way-1 variants with manifest-bound provenance."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUBMIT = ROOT / "submit.txt"
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
    "query_family",
    "query_profile",
    "seed",
    "order",
    "semantic_query_sha256",
    "r",
    "Q",
    "unique_u",
    "unique_v",
    "domain_start",
    "domain_end",
    "plaintext_count",
    "threads",
    "wall_seconds",
    "process_wall_seconds",
    "user_cpu_seconds",
    "system_cpu_seconds",
    "peak_rss_kib",
    "timing_metric_origin",
    "logical_query_updates",
    "query_updates_per_second",
    "plaintexts_per_second",
    "u_parity_evaluations",
    "v_parity_evaluations",
    "permutation_evaluations",
    "counter_metric_origin",
    "program_commit",
    "program_sha256",
    "input_sha256",
    "output_sha256",
    "compiler_id",
    "compiler_version",
    "compiler_flags",
    "cpu_model",
    "ram_bytes",
    "numa",
    "kernel",
    "cpu_affinity",
    "timeout_seconds",
    "max_rss_kib",
    "submit_sha256",
    "exit_status",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--query-family", required=True)
    parser.add_argument("--query-profile", required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--order", choices=("canonical", "shuffled"), required=True)
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
    parser.add_argument("--timeout-seconds", type=float, required=True)
    parser.add_argument("--max-rss-kib", type=int, required=True)
    parser.add_argument("--compiler-id", required=True)
    parser.add_argument("--compiler-version", required=True)
    parser.add_argument("--compiler-flags", required=True)
    parser.add_argument("--cpu-model", required=True)
    parser.add_argument("--ram-bytes", type=int, required=True)
    parser.add_argument("--numa", required=True)
    parser.add_argument("--kernel", required=True)
    parser.add_argument("--cpu-affinity", default="")
    parser.add_argument("--submit-sha256", required=True)
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


def semantic_query_sha256(rows: list[dict[str, str]]) -> str:
    canonical = sorted(
        (
            int(row.get("row_id", "0")),
            int(row["r"]),
            int(row["u"], 0),
            int(row["v"], 0),
        )
        for row in rows
    )
    payload = "".join(
        f"{row_id},{rounds},0x{u:08x},0x{v:08x}\n"
        for row_id, rounds, u, v in canonical
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def load_query_rows(path: Path, rounds: int) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not {"r", "u", "v"}.issubset(reader.fieldnames):
            raise ValueError("query file must contain r,u,v columns")
        rows = list(reader)
    if not rows:
        raise ValueError("query file contains no rows")
    if any(int(row["r"]) != rounds for row in rows):
        raise ValueError("query file contains a round different from --r")
    return rows


def materialize_queries(
    source: Path,
    destination: Path,
    rounds: int,
    order: str,
    seed: str,
) -> tuple[int, int, int, str]:
    rows = load_query_rows(source, rounds)
    for index, row in enumerate(rows, start=1):
        row.setdefault("row_id", str(index))

    if order == "canonical":
        rows.sort(
            key=lambda row: (
                int(row["row_id"]),
                int(row["r"]),
                int(row["u"], 0),
                int(row["v"], 0),
            )
        )
    else:
        rows.sort(
            key=lambda row: hashlib.sha256(
                (
                    seed
                    + "\0"
                    + row["row_id"]
                    + "\0"
                    + row["r"]
                    + "\0"
                    + row["u"]
                    + "\0"
                    + row["v"]
                ).encode()
            ).digest()
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["row_id", "r", "u", "v"], lineterminator="\n"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "row_id": row["row_id"],
                    "r": row["r"],
                    "u": f"0x{int(row['u'], 0):08x}",
                    "v": f"0x{int(row['v'], 0):08x}",
                }
            )

    unique_u = {int(row["u"], 0) for row in rows}
    unique_v = {int(row["v"], 0) for row in rows}
    return len(rows), len(unique_u), len(unique_v), semantic_query_sha256(rows)


def parse_metadata(path: Path) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("# "):
            continue
        key, separator, value = line[2:].partition("=")
        if separator:
            metadata[key] = value
    return metadata


def result_signature(path: Path) -> dict[tuple[str, str, str], tuple[str, str]]:
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    reader = csv.DictReader(lines)
    signature: dict[tuple[str, str, str], tuple[str, str]] = {}
    for row in reader:
        key = (row["r"], row["u"], row["v"])
        if key in signature:
            raise ValueError(f"duplicate query key in {path}: {key}")
        signature[key] = (row["numerator"], row["denominator"])
    return signature


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


def verify_submit(expected: str) -> None:
    actual = sha256_file(SUBMIT)
    if actual != expected:
        raise ValueError(f"submit SHA mismatch: expected {expected}, got {actual}")


def run_with_timeout(
    command: list[str],
    timeout_seconds: float,
    environment: dict[str, str] | None = None,
) -> tuple[int, str, str, float]:
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        env=environment,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        return process.returncode, stdout, stderr, time.perf_counter() - started
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        return 124, stdout, stderr + "\nTIMEOUT", time.perf_counter() - started


def write_manifest(
    path: Path,
    *,
    implementation: str,
    query_path: Path,
    query_sha256: str,
    program_path: Path,
    program_sha256: str,
    output_path: Path,
    range_start: int,
    range_end: int,
    command: list[str],
    exit_status: int,
) -> None:
    output_sha = sha256_file(output_path) if output_path.is_file() else ""
    data = {
        "schema": "way1-shard-manifest-v1",
        "implementation": implementation,
        "query_path": str(query_path.resolve()),
        "query_sha256": query_sha256,
        "program_path": str(program_path.resolve()),
        "program_sha256": program_sha256,
        "output_path": str(output_path.resolve()),
        "output_sha256": output_sha,
        "range_start": range_start,
        "range_end": range_end,
        "command": command,
        "exit_status": exit_status,
    }
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    args = parse_args()
    try:
        if args.threads <= 0 or args.repeats <= 0:
            raise ValueError("--threads and --repeats must be positive")
        if args.timeout_seconds <= 0 or args.max_rss_kib <= 0:
            raise ValueError("timeout and RSS limits must be positive")
        if not all(
            (
                args.query_family,
                args.query_profile,
                args.seed,
                args.compiler_id,
                args.compiler_version,
                args.compiler_flags,
                args.cpu_model,
                args.numa,
                args.kernel,
            )
        ):
            raise ValueError("query and compiler provenance fields must be non-empty")
        if args.ram_bytes <= 0:
            raise ValueError("--ram-bytes must be positive")
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

        verify_submit(args.submit_sha256)
        args.artifacts_dir.mkdir(parents=True, exist_ok=True)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        materialized_queries = args.artifacts_dir / f"queries-{args.order}.csv"
        query_count, unique_u, unique_v, semantic_sha = materialize_queries(
            args.queries, materialized_queries, args.r, args.order, args.seed
        )
        input_sha = sha256_file(materialized_queries)
        commit = git_commit()

        rows: list[dict[str, str | int]] = []
        reference_signature: dict[tuple[str, str, str], tuple[str, str]] | None = None
        for repeat in range(1, args.repeats + 1):
            for implementation in variants:
                verify_submit(args.submit_sha256)
                executable = EXECUTABLES[implementation]
                if not executable.is_file():
                    raise ValueError(f"missing executable: {executable}")
                program_sha = sha256_file(executable)
                run_id = (
                    f"r{args.r}-q{query_count}-n{plaintext_count}-t{args.threads}-"
                    f"{args.order}-{implementation}-rep{repeat}"
                )
                output_path = args.artifacts_dir / f"{run_id}.csv"
                time_path = args.artifacts_dir / f"{run_id}.time.csv"
                manifest_path = args.artifacts_dir / f"{run_id}.manifest.json"
                child_command = [
                    str(executable),
                    "--r",
                    str(args.r),
                    "--queries",
                    str(materialized_queries.resolve()),
                    "--query-sha256",
                    input_sha,
                    "--program-sha256",
                    program_sha,
                    "--start",
                    str(args.start),
                    "--end",
                    str(end),
                    "--threads",
                    str(args.threads),
                    "--out",
                    str(output_path.resolve()),
                ]
                if args.cpu_affinity and args.cpu_affinity != "unbound":
                    child_command = ["taskset", "-c", args.cpu_affinity, *child_command]
                command = [
                    "/usr/bin/time",
                    "-f",
                    "%e,%U,%S,%M,%x",
                    "-o",
                    str(time_path.resolve()),
                    *child_command,
                ]
                returncode, stdout, stderr, measured_wall_seconds = run_with_timeout(
                    command, args.timeout_seconds
                )
                write_manifest(
                    manifest_path,
                    implementation=implementation,
                    query_path=materialized_queries,
                    query_sha256=input_sha,
                    program_path=executable,
                    program_sha256=program_sha,
                    output_path=output_path,
                    range_start=args.start,
                    range_end=end,
                    command=command,
                    exit_status=returncode,
                )
                verify_submit(args.submit_sha256)
                if returncode != 0:
                    raise RuntimeError(
                        f"{run_id} failed with {returncode}: {stderr or stdout}"
                    )

                timing = parse_time_file(time_path)
                if int(timing["peak_rss_kib"]) > args.max_rss_kib:
                    raise RuntimeError(
                        f"{run_id} peak RSS {timing['peak_rss_kib']} exceeds "
                        f"{args.max_rss_kib} KiB"
                    )
                metadata = parse_metadata(output_path)
                if metadata.get("implementation") != implementation:
                    raise ValueError(f"implementation metadata mismatch for {run_id}")
                if metadata.get("query_sha256") != input_sha:
                    raise ValueError(f"query hash metadata mismatch for {run_id}")
                if metadata.get("program_sha256") != program_sha:
                    raise ValueError(f"program hash metadata mismatch for {run_id}")

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
                        "query_family": args.query_family,
                        "query_profile": args.query_profile,
                        "seed": args.seed,
                        "order": args.order,
                        "semantic_query_sha256": semantic_sha,
                        "r": args.r,
                        "Q": query_count,
                        "unique_u": unique_u,
                        "unique_v": unique_v,
                        "domain_start": args.start,
                        "domain_end": end,
                        "plaintext_count": plaintext_count,
                        "threads": args.threads,
                        "wall_seconds": f"{wall_seconds:.9f}",
                        "process_wall_seconds": timing["wall_seconds"],
                        "user_cpu_seconds": timing["user_cpu_seconds"],
                        "system_cpu_seconds": timing["system_cpu_seconds"],
                        "peak_rss_kib": timing["peak_rss_kib"],
                        "timing_metric_origin": "MEASURED",
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
                        "counter_metric_origin": "DETERMINISTIC_ALGORITHMIC_COUNT",
                        "program_commit": commit,
                        "program_sha256": program_sha,
                        "input_sha256": input_sha,
                        "output_sha256": sha256_file(output_path),
                        "compiler_id": args.compiler_id,
                        "compiler_version": args.compiler_version,
                        "compiler_flags": args.compiler_flags,
                        "cpu_model": args.cpu_model,
                        "ram_bytes": args.ram_bytes,
                        "numa": args.numa,
                        "kernel": args.kernel,
                        "cpu_affinity": args.cpu_affinity or "unbound",
                        "timeout_seconds": args.timeout_seconds,
                        "max_rss_kib": args.max_rss_kib,
                        "submit_sha256": args.submit_sha256,
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
    print("numerator_cross_variant_match=1")
    print(f"results={args.out}")


if __name__ == "__main__":
    main()
