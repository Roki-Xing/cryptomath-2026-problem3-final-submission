#!/usr/bin/env python3
"""Run way-2 ablation experiments for candidate mining settings.

The script only invokes candidate_miner_approx. It does not call exact_oracle,
so every reported metric is based on the approximation/search side.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AblationConfig:
    name: str
    mode: str
    beam: int
    trans: int
    max_active: int
    max_u: int
    top_v: int


DEFAULT_CONFIGS = [
    AblationConfig("aggregate_beam100_trans100_active1", "aggregate", 100, 100, 1, 8, 4),
    AblationConfig("aggregate_beam1000_trans1000_active1", "aggregate", 1000, 1000, 1, 8, 4),
    AblationConfig("routes_beam1000_trans1000_active1", "routes", 1000, 1000, 1, 8, 4),
    AblationConfig("aggregate_beam1000_trans1000_active2", "aggregate", 1000, 1000, 2, 16, 4),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run small way-2 candidate mining ablations.")
    parser.add_argument("--miner-bin", default="./candidate_miner_approx", help="Path to candidate_miner_approx.")
    parser.add_argument("--r-start", type=int, default=2, help="First round count to test.")
    parser.add_argument("--r-end", type=int, default=2, help="Last round count to test.")
    parser.add_argument("--out-csv", default="experiments/ablation_results.csv", help="Machine-readable CSV output.")
    parser.add_argument("--out-md", default="experiments/ablation_summary.md", help="Markdown summary table output.")
    return parser.parse_args()


def read_candidates(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def summarize(config: AblationConfig, rows: list[dict[str, str]], command_template: list[str]) -> dict[str, str]:
    best = max(rows, key=lambda row: (float(row["proxy_score"]), abs(float(row["VE"])))) if rows else None
    certified = sum(1 for row in rows if row["certified_no_truncation"] == "1")
    generated = sum(int(row["generated_transitions"]) for row in rows)
    expanded = sum(int(row["expanded_states"]) for row in rows)
    return {
        "name": config.name,
        "mode": config.mode,
        "beam": str(config.beam),
        "trans": str(config.trans),
        "max_active": str(config.max_active),
        "max_u": str(config.max_u),
        "top_v": str(config.top_v),
        "rows": str(len(rows)),
        "certified_rows": str(certified),
        "expanded_states_total": str(expanded),
        "generated_transitions_total": str(generated),
        "best_r": best["r"] if best else "",
        "best_u": best["u"] if best else "",
        "best_v": best["v"] if best else "",
        "best_ve": best["VE"] if best else "",
        "best_proxy_score": best["proxy_score"] if best else "",
        "command": " ".join(command_template),
    }


def run_config(config: AblationConfig, args: argparse.Namespace, work_dir: Path) -> dict[str, str]:
    out_path = work_dir / f"{config.name}.csv"
    command_base = [
        args.miner_bin,
        "--r-start",
        str(args.r_start),
        "--r-end",
        str(args.r_end),
        "--max-active",
        str(config.max_active),
        "--max-u",
        str(config.max_u),
        "--top-v",
        str(config.top_v),
        "--beam",
        str(config.beam),
        "--trans",
        str(config.trans),
        "--branch",
        "16",
        "--mode",
        config.mode,
    ]
    command = [
        *command_base,
        "--out",
        str(out_path),
    ]
    command_template = [*command_base, "--out", f"<tmp>/{config.name}.csv"]
    subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return summarize(config, read_candidates(out_path), command_template)


def write_csv(path: Path, summaries: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(summaries[0].keys()) if summaries else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(summaries)


def write_markdown(path: Path, summaries: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Ablation Summary",
        "",
        "These runs use `candidate_miner_approx` only. They measure way-2 search behavior, not exact VT validation.",
        "",
        "| config | mode | beam | trans | max_active | rows | certified | generated_transitions | best `(r,u,v)` | best VE | proxy score |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for row in summaries:
        best = f"({row['best_r']},{row['best_u']},{row['best_v']})" if row["best_r"] else ""
        lines.append(
            "| {name} | {mode} | {beam} | {trans} | {max_active} | {rows} | {certified_rows} | "
            "{generated_transitions_total} | `{best}` | {best_ve} | {best_proxy_score} |".format(
                best=best,
                **row,
            )
        )
    lines.extend(
        [
            "",
            "Reproduce:",
            "",
            "```bash",
            "python3 experiments/run_ablation.py",
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        summaries = [run_config(config, args, work_dir) for config in DEFAULT_CONFIGS]
    write_csv(Path(args.out_csv), summaries)
    write_markdown(Path(args.out_md), summaries)
    print(f"ablation_configs={len(summaries)}")
    print(f"csv={args.out_csv}")
    print(f"markdown={args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
