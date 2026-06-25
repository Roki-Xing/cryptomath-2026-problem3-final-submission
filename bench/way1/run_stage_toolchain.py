#!/usr/bin/env python3
"""Run the required Stage-A sanitizer and compiler consistency gates."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import shutil
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_protocol import parse_time_file, run_with_timeout  # noqa: E402
from run_stage_a0 import (  # noqa: E402
    DEFAULT_SUBMIT_SHA,
    cpu_model,
    git_commit,
    iso_utc_now,
    require_clean_tracked_worktree,
    sha256_file,
    write_sha_manifest,
)
from stage_a0_support import assert_semantic_equivalence  # noqa: E402


VARIANTS = ("current", "grouped_u", "grouped_uv")
APPS = {
    variant: ROOT / "apps" / f"exact_batch_{variant}.cpp"
    for variant in VARIANTS
}
SOURCES = (
    ROOT / "src" / "sbox_corr.cpp",
    ROOT / "src" / "linear_layer.cpp",
    ROOT / "src" / "beam_search.cpp",
    ROOT / "src" / "exact.cpp",
)
COMMON_FLAGS = (
    "-std=c++17",
    "-Wall",
    "-Wextra",
    "-pedantic",
    "-pthread",
)
SANITIZER_FLAGS = {
    "ubsan": (
        "-O1",
        "-g",
        "-fsanitize=undefined",
        "-fno-sanitize-recover=all",
        "-fno-omit-frame-pointer",
        *COMMON_FLAGS,
    ),
    "asan": (
        "-O1",
        "-g",
        "-fsanitize=address",
        "-fno-omit-frame-pointer",
        *COMMON_FLAGS,
    ),
    "tsan": (
        "-O1",
        "-g",
        "-fsanitize=thread",
        "-fno-omit-frame-pointer",
        *COMMON_FLAGS,
    ),
}
SANITIZER_ENV = {
    "ubsan": {"UBSAN_OPTIONS": "halt_on_error=1:print_stacktrace=1"},
    "asan": {"ASAN_OPTIONS": "detect_leaks=1:halt_on_error=1"},
    "tsan": {"TSAN_OPTIONS": "halt_on_error=1"},
}


@dataclass(frozen=True)
class ToolchainSpec:
    suite: str
    compiler: str
    optimization: str
    rounds: int
    count: int
    domain_bits: int
    variant: str
    threads: int
    family: str
    query_path: Path
    flags: tuple[str, ...]

    @property
    def case_id(self) -> str:
        compiler = self.compiler.replace("+", "p")
        return (
            f"{self.suite}_{compiler}_{self.optimization.lower()}_"
            f"r{self.rounds}_{self.variant}_t{self.threads}"
        )

    @property
    def build_id(self) -> str:
        compiler = self.compiler.replace("+", "p")
        return f"{self.suite}_{compiler}_{self.optimization.lower()}_{self.variant}"


def query_path(rounds: int) -> Path:
    return (
        ROOT
        / "bench"
        / "way1"
        / "stage_a0"
        / "queries"
        / f"r{rounds}_q64_frozen.csv"
    )


def build_matrix(multithread: int) -> list[ToolchainSpec]:
    if multithread <= 1:
        raise ValueError("multithread must be greater than one")
    specs: list[ToolchainSpec] = []
    sanitizer_matrix = (
        ("ubsan", 16, VARIANTS, (1, multithread)),
        ("asan", 14, VARIANTS, (1,)),
        ("tsan", 12, ("grouped_u", "grouped_uv"), (4,)),
    )
    for suite, domain_bits, variants, threads_values in sanitizer_matrix:
        for rounds in (1, 2, 3):
            for variant in variants:
                for threads in threads_values:
                    specs.append(
                        ToolchainSpec(
                            suite=suite,
                            compiler="g++",
                            optimization="O1",
                            rounds=rounds,
                            count=64,
                            domain_bits=domain_bits,
                            variant=variant,
                            threads=threads,
                            family="frozen-subset",
                            query_path=query_path(rounds),
                            flags=SANITIZER_FLAGS[suite],
                        )
                    )
    for compiler in ("g++", "clang++"):
        for optimization in ("O0", "O3"):
            flags = (f"-{optimization}", *COMMON_FLAGS)
            for rounds in (1, 2, 3):
                for variant in VARIANTS:
                    specs.append(
                        ToolchainSpec(
                            suite="optimization",
                            compiler=compiler,
                            optimization=optimization,
                            rounds=rounds,
                            count=64,
                            domain_bits=12,
                            variant=variant,
                            threads=1,
                            family="frozen-subset",
                            query_path=query_path(rounds),
                            flags=flags,
                        )
                    )
    return specs


def semantic_groups(
    specs: list[ToolchainSpec],
) -> dict[tuple[str, int], list[ToolchainSpec]]:
    groups: dict[tuple[str, int], list[ToolchainSpec]] = {}
    for spec in specs:
        groups.setdefault((spec.suite, spec.rounds), []).append(spec)
    return groups


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite",
        choices=("all", "ubsan", "asan", "tsan", "optimization"),
        default="all",
    )
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=float, default=300)
    parser.add_argument("--compile-timeout-seconds", type=float, default=600)
    parser.add_argument("--max-rss-kib", type=int, default=2097152)
    parser.add_argument("--submit-sha256", default=DEFAULT_SUBMIT_SHA)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "bench" / "way1" / "stage_toolchain",
    )
    return parser.parse_args()


def verify_submit(expected: str) -> None:
    actual = sha256_file(ROOT / "submit.txt")
    if actual != expected:
        raise ValueError(f"submit SHA mismatch: expected {expected}, got {actual}")


def verify_query(path: Path, rounds: int) -> None:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 64:
        raise ValueError(f"{path} has {len(rows)} queries, expected 64")
    if any(int(row["r"]) != rounds for row in rows):
        raise ValueError(f"{path} contains an unexpected round")


def compiler_version(compiler: str) -> str:
    return run_with_timeout([compiler, "--version"], 30)[1].splitlines()[0]


def compile_binary(
    spec: ToolchainSpec,
    destination: Path,
    log_path: Path,
    timeout_seconds: float,
) -> dict[str, object]:
    command = [
        spec.compiler,
        "-Iinclude",
        "-Iapps",
        *spec.flags,
        str(APPS[spec.variant]),
        *map(str, SOURCES),
        "-o",
        str(destination),
    ]
    returncode, stdout, stderr, wall = run_with_timeout(command, timeout_seconds)
    log_path.write_text(
        f"command={json.dumps(command, ensure_ascii=False)}\n"
        f"exit_status={returncode}\n"
        f"wall_seconds={wall:.6f}\n"
        f"stdout:\n{stdout}\nstderr:\n{stderr}",
        encoding="utf-8",
    )
    if returncode != 0:
        raise RuntimeError(f"compile failed for {spec.build_id}: {log_path}")
    return {
        "build_id": spec.build_id,
        "compiler": spec.compiler,
        "compiler_version": compiler_version(spec.compiler),
        "flags": list(spec.flags),
        "command": command,
        "program_sha256": sha256_file(destination),
        "compile_log": str(log_path),
        "compile_log_sha256": sha256_file(log_path),
        "wall_seconds": round(wall, 6),
    }


def run_case(
    spec: ToolchainSpec,
    binary: Path,
    output: Path,
    stderr_path: Path,
    timing_path: Path,
    args: argparse.Namespace,
) -> dict[str, object]:
    query_sha = sha256_file(spec.query_path)
    program_sha = sha256_file(binary)
    child = [
        str(binary),
        "--r",
        str(spec.rounds),
        "--queries",
        str(spec.query_path),
        "--query-sha256",
        query_sha,
        "--program-sha256",
        program_sha,
        "--start",
        "0",
        "--end",
        str(1 << spec.domain_bits),
        "--threads",
        str(spec.threads),
        "--out",
        str(output),
    ]
    command = [
        "/usr/bin/time",
        "-f",
        "%e,%U,%S,%M,%x",
        "-o",
        str(timing_path),
        *child,
    ]
    environment = os.environ.copy()
    environment.update(SANITIZER_ENV.get(spec.suite, {}))
    verify_submit(args.submit_sha256)
    returncode, stdout, stderr, process_wall = run_with_timeout(
        command, args.timeout_seconds, environment
    )
    stderr_path.write_text(
        f"stdout:\n{stdout}\nstderr:\n{stderr}", encoding="utf-8"
    )
    verify_submit(args.submit_sha256)
    if returncode != 0:
        raise RuntimeError(f"run failed for {spec.case_id}: {stderr_path}")
    timing = parse_time_file(timing_path)
    peak_rss = int(timing["peak_rss_kib"])
    if peak_rss > args.max_rss_kib:
        raise RuntimeError(f"{spec.case_id} exceeded RSS: {peak_rss} KiB")
    diagnostics = (
        "runtime error:",
        "ERROR: AddressSanitizer",
        "WARNING: ThreadSanitizer",
    )
    if any(marker in stderr for marker in diagnostics):
        raise RuntimeError(f"sanitizer diagnostic for {spec.case_id}")
    return {
        **asdict(spec),
        "query_path": str(spec.query_path.relative_to(ROOT)),
        "flags": list(spec.flags),
        "case_id": spec.case_id,
        "query_sha256": query_sha,
        "program_sha256": program_sha,
        "output_path": str(output),
        "output_sha256": sha256_file(output),
        "stderr_path": str(stderr_path),
        "stderr_sha256": sha256_file(stderr_path),
        "timing_path": str(timing_path),
        "timing_sha256": sha256_file(timing_path),
        "command": command,
        "process_wall_seconds": round(process_wall, 6),
        "wall_seconds": float(timing["wall_seconds"]),
        "peak_rss_kib": peak_rss,
        "exit_status": returncode,
    }


def main() -> None:
    args = parse_args()
    args.out_dir = args.out_dir.resolve()
    if (
        args.threads <= 1
        or args.timeout_seconds <= 0
        or args.compile_timeout_seconds <= 0
        or args.max_rss_kib <= 0
    ):
        raise SystemExit("error: invalid Stage-A toolchain resource setting")
    if args.out_dir.exists() and any(args.out_dir.iterdir()):
        raise SystemExit(f"error: output directory is not empty: {args.out_dir}")
    try:
        require_clean_tracked_worktree()
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc

    all_specs = build_matrix(args.threads)
    specs = [
        spec for spec in all_specs if args.suite == "all" or spec.suite == args.suite
    ]
    missing = sorted(
        {spec.compiler for spec in specs if shutil.which(spec.compiler) is None}
    )
    if missing:
        raise SystemExit(f"error: missing compilers: {', '.join(missing)}")
    for spec in specs:
        if not spec.query_path.is_file():
            raise SystemExit(f"error: missing query artifact: {spec.query_path}")
        verify_query(spec.query_path, spec.rounds)
    verify_submit(args.submit_sha256)

    started_at = iso_utc_now()
    started = time.perf_counter()
    compile_dir = args.out_dir / "compile"
    results_dir = args.out_dir / "results"
    compile_dir.mkdir(parents=True)
    results_dir.mkdir(parents=True)
    build_records: dict[str, dict[str, object]] = {}
    run_records: list[dict[str, object]] = []
    outputs_by_group: dict[tuple[str, int], list[Path]] = {
        key: [] for key in semantic_groups(specs)
    }

    with tempfile.TemporaryDirectory(prefix="way1-toolchain-") as temporary:
        binary_dir = Path(temporary)
        binaries: dict[str, Path] = {}
        for spec in specs:
            if spec.build_id not in binaries:
                binary = binary_dir / spec.build_id
                log_path = compile_dir / f"{spec.build_id}.log"
                build_records[spec.build_id] = compile_binary(
                    spec, binary, log_path, args.compile_timeout_seconds
                )
                binaries[spec.build_id] = binary
            output = results_dir / f"{spec.case_id}.csv"
            stderr_path = results_dir / f"{spec.case_id}.stderr.log"
            timing_path = results_dir / f"{spec.case_id}.time.csv"
            run_records.append(
                run_case(
                    spec,
                    binaries[spec.build_id],
                    output,
                    stderr_path,
                    timing_path,
                    args,
                )
            )
            outputs_by_group[(spec.suite, spec.rounds)].append(output)

        for outputs in outputs_by_group.values():
            assert_semantic_equivalence(outputs)

    verify_submit(args.submit_sha256)
    summary = {
        "schema": "way1-stage-toolchain-summary-v1",
        "status": "STAGE_TOOLCHAIN_PASS",
        "suite": args.suite,
        "matrix_case_count": len(specs),
        "semantic_group_count": len(outputs_by_group),
        "semantic_mismatch_count": 0,
        "timeout_count": 0,
        "oom_count": 0,
        "nonzero_exit_count": 0,
        "sanitizer_diagnostic_count": 0,
        "submit_sha256_before": args.submit_sha256,
        "submit_sha256_after": sha256_file(ROOT / "submit.txt"),
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    environment = {
        "cpu_model": cpu_model(),
        "logical_cpu_count": os.cpu_count(),
        "ram_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"),
        "kernel": platform.release(),
        "platform": platform.platform(),
    }
    manifest = {
        "schema": "way1-stage-toolchain-manifest-v1",
        "status": summary["status"],
        "started_at": started_at,
        "finished_at": iso_utc_now(),
        "program_commit": git_commit(),
        "environment": environment,
        "arguments": {
            **vars(args),
            "out_dir": str(args.out_dir),
        },
        "builds": list(build_records.values()),
        "runs": run_records,
        "summary": summary,
    }
    (args.out_dir / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.out_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    write_sha_manifest(args.out_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
