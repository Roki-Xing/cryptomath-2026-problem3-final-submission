#!/usr/bin/env python3
"""Run the exact-way2 pilot pipeline from selector preparation through summary."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import time
from pathlib import Path

from common import bundle_output_sha, nearest_rank_index, population_cv, read_json, write_csv, write_json


def run_cmd(args: list[str], *, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def load_selection_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_repeat_subset_rows(selection_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    r1 = sorted(
        [row for row in selection_rows if int(row["r"]) == 1],
        key=lambda row: (row["deterministic_hash"], row["u"]),
    )[:4]
    r2_all = sorted(
        [row for row in selection_rows if int(row["r"]) == 2],
        key=lambda row: (int(row["generated_transitions"]), row["u"]),
    )
    r2 = [
        r2_all[0],
        r2_all[len(r2_all) // 2],
        r2_all[nearest_rank_index(len(r2_all), 95.0)],
        r2_all[-1],
    ]
    r3_all = [row for row in selection_rows if int(row["r"]) == 3]
    r3_max = max(r3_all, key=lambda row: (int(row["generated_transitions"]), row["u"]))
    r3_hash = sorted(r3_all, key=lambda row: (row["deterministic_hash"], row["u"]))
    chosen = {(int(r3_max["r"]), r3_max["u"])}
    r3 = [r3_max]
    for row in r3_hash:
        key = (int(row["r"]), row["u"])
        if key in chosen:
            continue
        r3.append(row)
        chosen.add(key)
        if len(r3) == 4:
            break
    subset = r1 + r2 + r3
    unique_keys = {(int(row["r"]), row["u"]) for row in subset}
    if len(subset) != 12 or len(unique_keys) != 12:
        raise SystemExit("repeat subset must contain 12 unique columns")
    return sorted(subset, key=lambda row: (int(row["r"]), row["u"]))


def combined_bundle_sha(root: Path) -> tuple[str, str]:
    bundle_lines = []
    endpoint_lines = []
    for bundle_dir in sorted((root / "completed").glob("*")):
        done = read_json(bundle_dir / "DONE.json")
        if not isinstance(done, dict):
            raise SystemExit(f"invalid repeat DONE bundle: {bundle_dir}")
        column_path = bundle_dir / "column.json"
        endpoints_path = bundle_dir / "endpoints.csv"
        bundle_lines.append(f"{bundle_dir.name}:{bundle_output_sha(column_path, endpoints_path)}")
        endpoint_lines.append(f"{bundle_dir.name}:{done['endpoints_sha256']}")
    return (
        __import__("hashlib").sha256("\n".join(bundle_lines).encode("utf-8")).hexdigest(),
        __import__("hashlib").sha256("\n".join(endpoint_lines).encode("utf-8")).hexdigest(),
    )


def run_repeat_subset(root: Path, selection_rows: list[dict[str, str]], binary: str, jobs: int) -> dict[str, object]:
    subset_rows = build_repeat_subset_rows(selection_rows)
    subset_csv = root / "repeat_subset_selection.csv"
    write_csv(subset_csv, list(subset_rows[0].keys()), subset_rows)
    shutil.copy2(root / "PILOT_SELECTION.json", root / "repeat_subset_selection.json")
    results: dict[str, object] = {
        "subset": [{"r": int(row["r"]), "u": row["u"]} for row in subset_rows],
        "cpp_int": {"runs": []},
        "int128_checked": {"runs": []},
    }
    for backend in ("cpp_int", "int128_checked"):
        previous_digest = None
        previous_endpoints = None
        for run_index in range(1, 4):
            repeat_root = root / f".repeat_tmp_{backend}_{run_index}"
            if repeat_root.exists():
                shutil.rmtree(repeat_root)
            repeat_root.mkdir(parents=True)
            shutil.copy2(subset_csv, repeat_root / "PILOT_SELECTION.csv")
            shutil.copy2(root / "PILOT_SELECTION.json", repeat_root / "PILOT_SELECTION.json")
            started = time.perf_counter()
            run_cmd(
                [
                    "python3",
                    "-X",
                    "utf8",
                    "experiments/exact_way2/run_frozen_exact.py",
                    "--selection",
                    str(repeat_root / "PILOT_SELECTION.csv"),
                    "--backend",
                    backend,
                    "--jobs",
                    str(jobs),
                    "--resume",
                    "--artifact-root",
                    str(repeat_root),
                    "--artifact-logical-root",
                    f"artifacts/way2_exact/pilot/repeat_tmp/{backend}_{run_index}",
                    "--binary",
                    binary,
                    "--binary-logical-path",
                    binary,
                ],
                cwd=Path.cwd(),
            )
            elapsed = time.perf_counter() - started
            bundle_sha, endpoint_sha = combined_bundle_sha(repeat_root)
            results[backend]["runs"].append(
                {
                    "run": run_index,
                    "wall_seconds": elapsed,
                    "bundle_output_sha256": bundle_sha,
                    "endpoint_payload_sha256": endpoint_sha,
                }
            )
            previous_digest = bundle_sha if previous_digest is None else previous_digest
            previous_endpoints = endpoint_sha if previous_endpoints is None else previous_endpoints
            if previous_digest != bundle_sha or previous_endpoints != endpoint_sha:
                results[backend]["digest_equal"] = False
                results[backend]["endpoint_equal"] = False
            shutil.rmtree(repeat_root)
        runs = [entry["wall_seconds"] for entry in results[backend]["runs"]]
        results[backend]["cv"] = population_cv(runs)
        results[backend].setdefault("digest_equal", True)
        results[backend].setdefault("endpoint_equal", True)
    lines = [
        "# Exact Way-2 Repeat Subset",
        "",
        f"- subset size: `{len(subset_rows)}`",
        f"- cpp_int CV: `{results['cpp_int']['cv']}`",
        f"- int128_checked CV: `{results['int128_checked']['cv']}`",
    ]
    write_json(root / "REPEAT_SUBSET.json", results)
    (root / "REPEAT_SUBSET.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-ru", default="experiments/frozen/final_ru.csv")
    parser.add_argument("--final-queries", default="experiments/frozen/final_queries.csv")
    parser.add_argument("--snapshot", default="experiments/frozen/final_values_snapshot.csv")
    parser.add_argument("--audit", default="experiments/submit_audit.csv")
    parser.add_argument("--spotcheck-queries", default="experiments/spotcheck/exact_spotcheck_queries.csv")
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--binary", default="recompute_frozen_exact")
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()

    cwd = Path.cwd()
    root = Path(args.artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    total_started = time.perf_counter()

    selector_started = time.perf_counter()
    run_cmd(
        [
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/prepare_selector_inputs.py",
            "--final-ru",
            args.final_ru,
            "--audit",
            args.audit,
            "--spotcheck-queries",
            args.spotcheck_queries,
            "--out",
            str(root),
        ],
        cwd=cwd,
    )
    run_cmd(
        [
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/select_pilot.py",
            "--final-ru",
            args.final_ru,
            "--final-queries",
            args.final_queries,
            "--complexity-input",
            str(root / "COMPLEXITY_INPUT.csv"),
            "--spotcheck-coordinates",
            str(root / "SPOTCHECK_COORDINATES.csv"),
            "--out",
            str(root),
        ],
        cwd=cwd,
    )
    selector_elapsed = time.perf_counter() - selector_started

    orchestrator_started = time.perf_counter()
    run_cmd(
        [
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/run_frozen_exact.py",
            "--selection",
            str(root / "PILOT_SELECTION.csv"),
            "--backend",
            "both",
            "--jobs",
            str(args.jobs),
            "--resume",
            "--artifact-root",
            str(root),
            "--artifact-logical-root",
            "artifacts/way2_exact/pilot",
            "--binary",
            args.binary,
            "--binary-logical-path",
            args.binary,
            "--queries",
            args.final_queries,
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
        ],
        cwd=cwd,
    )
    compare_elapsed = time.perf_counter() - compare_started

    selection_rows = load_selection_rows(root / "PILOT_SELECTION.csv")
    repeat_subset = run_repeat_subset(root, selection_rows, args.binary, args.jobs)

    summarize_started = time.perf_counter()
    runner = read_json(root / "RUNNER.json")
    if not isinstance(runner, dict):
        raise SystemExit("invalid RUNNER.json")
    write_json(
        root / "PIPELINE.json",
        {
            "selector_elapsed_wall": selector_elapsed,
            "orchestrator_elapsed_wall": orchestrator_elapsed,
            "comparison_elapsed_wall": compare_elapsed,
            "peak_process_rss": runner["peak_process_rss"],
            "peak_total_concurrent_rss": runner["peak_total_concurrent_rss"],
            "jobs": args.jobs,
            "repeat_subset": repeat_subset,
            "total_pilot_elapsed_wall": 0.0,
        },
    )
    run_cmd(
        [
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/summarize_exact.py",
            "--artifact-root",
            str(root),
        ],
        cwd=cwd,
    )
    summarizer_elapsed = time.perf_counter() - summarize_started
    total_elapsed = time.perf_counter() - total_started
    pipeline = read_json(root / "PIPELINE.json")
    if not isinstance(pipeline, dict):
        raise SystemExit("invalid PIPELINE.json")
    pipeline["summarizer_elapsed_wall"] = summarizer_elapsed
    pipeline["total_pilot_elapsed_wall"] = total_elapsed
    write_json(root / "PIPELINE.json", pipeline)
    run_cmd(
        [
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/summarize_exact.py",
            "--artifact-root",
            str(root),
        ],
        cwd=cwd,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
