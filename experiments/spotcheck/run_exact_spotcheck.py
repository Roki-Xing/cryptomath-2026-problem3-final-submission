#!/usr/bin/env python3
"""Run way-1 exact spotcheck for a small set of submit rows.

This script:
- reads a CSV of (r,u,v) queries (typically from submit.txt)
- runs ./exact_batch_mt per-r on those queries (full 2^32 domain)
- compares exact VT to submit VE/VT (for certified rows VT==VE)
- writes a results CSV + JSON/MD summaries
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Query:
    r: int
    u: str
    v: str
    ve: float
    category: str
    reason: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", default="experiments/spotcheck/exact_spotcheck_queries.csv")
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--out-csv", default="experiments/spotcheck/exact_spotcheck.csv")
    parser.add_argument("--out-json", default="experiments/spotcheck/exact_spotcheck_summary.json")
    parser.add_argument("--out-md", default="experiments/spotcheck/exact_spotcheck_summary.md")
    parser.add_argument("--logs-dir", default="experiments/logs")
    parser.add_argument("--bin", default="./exact_batch_mt")
    parser.add_argument("--tolerance", type=float, default=1e-18)
    return parser.parse_args()


def norm_mask(value: str) -> str:
    return f"0x{int(value, 0):08x}"


def read_queries(path: Path) -> list[Query]:
    queries: list[Query] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"r", "u", "v", "VE", "category", "reason"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"queries CSV missing columns: {sorted(missing)}")
        for row in reader:
            queries.append(
                Query(
                    r=int(row["r"]),
                    u=norm_mask(row["u"]),
                    v=norm_mask(row["v"]),
                    ve=float(row["VE"]),
                    category=row["category"].strip(),
                    reason=row["reason"].strip(),
                )
            )
    return queries


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_exact_for_r(
    *,
    r: int,
    queries: list[Query],
    bin_path: str,
    threads: int,
    logs_dir: Path,
    workdir: Path,
    project_root: Path,
) -> dict[tuple[int, str, str], dict[str, str]]:
    """Return mapping (r,u,v) -> exact_batch_mt row dict."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    q_path = workdir / f"exact_spotcheck_r{r}_queries.csv"
    out_path = workdir / f"exact_spotcheck_r{r}_exact.csv"
    log_path = logs_dir / f"E02_exact_spotcheck_r{r}.log"

    q_path.parent.mkdir(parents=True, exist_ok=True)
    with q_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["u", "v"])
        for q in queries:
            writer.writerow([q.u, q.v])

    command = [
        bin_path,
        "--r",
        str(r),
        "--queries",
        str(q_path),
        "--threads",
        str(threads),
        "--out",
        str(out_path),
    ]
    completed = subprocess.run(
        command,
        cwd=str(project_root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )
    log_path.write_text(completed.stdout, encoding="utf-8")

    results: dict[tuple[int, str, str], dict[str, str]] = {}
    with out_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            key = (int(row["r"]), norm_mask(row["u"]), norm_mask(row["v"]))
            results[key] = row
    return results


def main() -> int:
    args = parse_args()
    queries_path = Path(args.queries)
    out_csv = Path(args.out_csv)
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    logs_dir = Path(args.logs_dir)

    queries = read_queries(queries_path)
    by_r: dict[int, list[Query]] = defaultdict(list)
    for q in queries:
        by_r[q.r].append(q)

    project_root = Path(__file__).resolve().parents[2]
    workdir = queries_path.parent
    exact_rows: dict[tuple[int, str, str], dict[str, str]] = {}
    for r, qlist in sorted(by_r.items()):
        exact_rows.update(
            run_exact_for_r(
                r=r,
                queries=qlist,
                bin_path=args.bin,
                threads=args.threads,
                logs_dir=logs_dir,
                workdir=workdir,
                project_root=project_root,
            )
        )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    mismatches: list[dict[str, object]] = []
    max_abs_err = 0.0
    max_rel_err = 0.0

    with out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "r",
                "u",
                "v",
                "submit_ve",
                "exact_vt",
                "abs_err",
                "rel_err",
                "match",
                "seconds",
                "status",
                "numerator",
                "denominator",
                "category",
                "reason",
            ]
        )

        for q in queries:
            key = (q.r, q.u, q.v)
            row = exact_rows.get(key)
            if row is None:
                raise SystemExit(f"missing exact result for query: {q}")
            exact_vt = float(row["VT"])
            abs_err = abs(exact_vt - q.ve)
            rel_err = abs_err / max(1e-300, abs(q.ve))
            match = abs_err <= args.tolerance
            max_abs_err = max(max_abs_err, abs_err)
            max_rel_err = max(max_rel_err, rel_err)
            if not match:
                mismatches.append(
                    {
                        "r": q.r,
                        "u": q.u,
                        "v": q.v,
                        "submit_ve": q.ve,
                        "exact_vt": exact_vt,
                        "abs_err": abs_err,
                        "rel_err": rel_err,
                        "seconds": row.get("seconds"),
                        "status": row.get("status"),
                        "category": q.category,
                        "reason": q.reason,
                    }
                )

            writer.writerow(
                [
                    q.r,
                    q.u,
                    q.v,
                    f"{q.ve:.24g}",
                    row["VT"],
                    f"{abs_err:.24g}",
                    f"{rel_err:.24g}",
                    int(match),
                    row.get("seconds", ""),
                    row.get("status", ""),
                    row.get("numerator", ""),
                    row.get("denominator", ""),
                    q.category,
                    q.reason,
                ]
            )

    summary = {
        "queries": str(queries_path),
        "count": len(queries),
        "by_r": {str(r): len(v) for r, v in sorted(by_r.items())},
        "tolerance": args.tolerance,
        "mismatch_count": len(mismatches),
        "max_abs_err": max_abs_err,
        "max_rel_err": max_rel_err,
        "mismatches": mismatches,
    }
    write_json(out_json, summary)

    md = [
        "# Exact Spotcheck Summary",
        "",
        f"- queries: `{queries_path}`",
        f"- count: {summary['count']}",
        f"- mismatch_count: {summary['mismatch_count']}",
        f"- tolerance: {summary['tolerance']}",
        f"- max_abs_err: {summary['max_abs_err']:.6g}",
        f"- max_rel_err: {summary['max_rel_err']:.6g}",
    ]
    if mismatches:
        md.extend(
            [
                "",
                "## Mismatches",
                "",
                "```json",
                json.dumps(mismatches, indent=2, sort_keys=True),
                "```",
            ]
        )
    write_md(out_md, md)

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
