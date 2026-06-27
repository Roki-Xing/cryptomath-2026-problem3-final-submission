#!/usr/bin/env python3
"""Run the full 4760-column exact-way2 recompute pipeline."""

from __future__ import annotations

import argparse
import os
import subprocess
import time
from pathlib import Path

from common import read_json, write_json


def run_cmd(args: list[str], *, cwd: Path) -> None:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(
        args,
        cwd=cwd,
        env=env,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--binary", default="recompute_frozen_exact")
    parser.add_argument("--queries", default="experiments/frozen/final_queries.csv")
    parser.add_argument("--snapshot", default="experiments/frozen/final_values_snapshot.csv")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--artifact-logical-root", default="artifacts/way2_exact/full")
    args = parser.parse_args()

    cwd = Path.cwd()
    root = Path(args.artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    total_started = time.perf_counter()

    verify_cmd = [
        "python3",
        "-X",
        "utf8",
        "experiments/exact_way2/verify_full_authorization.py",
        "--authorization",
        args.authorization,
        "--binary",
        args.binary,
        "--selection",
        args.selection,
        "--queries",
        args.queries,
        "--snapshot",
        args.snapshot,
        "--jobs",
        str(args.jobs),
    ]
    run_cmd(verify_cmd, cwd=cwd)

    orchestrator_started = time.perf_counter()
    run_cmd(
        [
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/run_frozen_exact.py",
            "--selection",
            args.selection,
            "--backend",
            "both",
            "--jobs",
            str(args.jobs),
            "--resume",
            "--artifact-root",
            str(root),
            "--artifact-logical-root",
            args.artifact_logical_root,
            "--binary",
            args.binary,
            "--binary-logical-path",
            Path(args.binary).name if Path(args.binary).is_absolute() else args.binary,
            "--queries",
            args.queries,
        ],
        cwd=cwd,
    )
    orchestrator_elapsed = time.perf_counter() - orchestrator_started

    compare_started = time.perf_counter()
    run_cmd(
        [
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/compare_frozen_exact.py",
            "--artifact-root",
            str(root),
            "--snapshot",
            args.snapshot,
            "--selection",
            args.selection,
        ],
        cwd=cwd,
    )
    compare_elapsed = time.perf_counter() - compare_started

    summarize_started = time.perf_counter()
    runner = read_json(root / "RUNNER.json")
    if not isinstance(runner, dict):
        raise SystemExit("invalid RUNNER.json")
    write_json(
        root / "PIPELINE.json",
        {
            "selector_elapsed_wall": 0.0,
            "orchestrator_elapsed_wall": orchestrator_elapsed,
            "comparison_elapsed_wall": compare_elapsed,
            "peak_process_rss": runner["peak_process_rss"],
            "peak_total_concurrent_rss": runner["peak_total_concurrent_rss"],
            "jobs": args.jobs,
            "total_full_elapsed_wall": 0.0,
        },
    )
    run_cmd(
        [
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/summarize_full_exact.py",
            "--artifact-root",
            str(root),
        ],
        cwd=cwd,
    )
    summarizer_elapsed = time.perf_counter() - summarize_started
    pipeline = read_json(root / "PIPELINE.json")
    if not isinstance(pipeline, dict):
        raise SystemExit("invalid PIPELINE.json")
    pipeline["summarizer_elapsed_wall"] = summarizer_elapsed
    pipeline["total_full_elapsed_wall"] = time.perf_counter() - total_started
    write_json(root / "PIPELINE.json", pipeline)
    run_cmd(
        [
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/summarize_full_exact.py",
            "--artifact-root",
            str(root),
        ],
        cwd=cwd,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
