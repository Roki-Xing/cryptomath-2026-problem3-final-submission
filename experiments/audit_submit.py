#!/usr/bin/env python3
"""Generate an audit CSV for submit.txt rows.

Args:
    See --help for CLI options.

Returns:
    Exit code 0 when every row can be reproduced by estimator within tolerance.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SUBMIT_RE = re.compile(
    r"^@\(\s*(?P<r>\d+)\s*,\s*(?P<u>0x[0-9a-fA-F]+|\d+)\s*,\s*"
    r"(?P<v>0x[0-9a-fA-F]+|\d+)\s*,\s*(?P<vt>[^,]+)\s*,\s*(?P<ve>[^)]+)\s*\)$"
)


@dataclass(frozen=True)
class SubmitRow:
    r: int
    u: str
    v: str
    vt: float
    ve: float
    line: str


@dataclass(frozen=True)
class EstimatorAudit:
    estimator_ve: float
    proxy_score: float
    final_beam_size: int
    expanded_states: int
    generated_transitions: int
    certified_no_truncation: bool
    round_stats: str
    command: str


@dataclass(frozen=True)
class EstimatorBundle:
    values: dict[str, float]
    final_beam_size: int
    expanded_states: int
    generated_transitions: int
    certified_no_truncation: bool
    round_stats: str
    command: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit submit rows against the way-2 estimator.")
    parser.add_argument("--submit", default="submit.txt", help="Submit file to audit.")
    parser.add_argument("--out", default="experiments/submit_audit.csv", help="Audit CSV output path.")
    parser.add_argument("--estimator-bin", default="./estimator", help="Path to estimator executable.")
    parser.add_argument("--beam", type=int, default=10000, help="Estimator beam size.")
    parser.add_argument("--trans", type=int, default=10000, help="Estimator max transitions per state.")
    parser.add_argument("--branch", type=int, default=16, help="Estimator branch count per nibble.")
    parser.add_argument("--mode", choices=("aggregate", "routes"), default="aggregate", help="Estimator mode.")
    parser.add_argument("--tolerance", type=float, default=1e-18, help="VE reproduction tolerance.")
    return parser.parse_args()


def norm_mask(value: str) -> str:
    return f"0x{int(value, 0):08x}"


def score_value(r: int, ve: float) -> float:
    return 2.0 * r + math.log2(abs(ve)) if ve != 0.0 else float("-inf")


def valid_interval(vt: float, ve: float) -> bool:
    if vt == 0.0 or ve == 0.0 or not math.isfinite(vt) or not math.isfinite(ve):
        return False
    return abs(ve - vt) <= abs(vt) * 0.25 + 1e-30


def load_submit(path: Path) -> list[SubmitRow]:
    rows: list[SubmitRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = SUBMIT_RE.match(stripped)
        if not match:
            raise ValueError(f"bad submit line: {stripped}")
        rows.append(
            SubmitRow(
                r=int(match.group("r")),
                u=norm_mask(match.group("u")),
                v=norm_mask(match.group("v")),
                vt=float(match.group("vt")),
                ve=float(match.group("ve")),
                line=stripped,
            )
        )
    return rows


def parse_bool(value: str) -> bool:
    if value == "yes":
        return True
    if value == "no":
        return False
    raise ValueError(f"bad boolean: {value}")


def parse_estimator_output(output: str, command: list[str]) -> EstimatorAudit:
    fields: dict[str, str] = {}
    round_stats: list[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("round="):
            round_stats.append(stripped)
            continue
        if "=" in stripped:
            key, value = stripped.split("=", 1)
            fields[key.strip()] = value.strip()
    required = [
        "VE",
        "score*",
        "final_beam_size",
        "expanded_states",
        "generated_transitions",
        "certified_no_truncation",
    ]
    missing = [key for key in required if key not in fields]
    if missing:
        raise ValueError(f"estimator output missing fields {missing}: {output}")
    return EstimatorAudit(
        estimator_ve=float(fields["VE"]),
        proxy_score=float(fields["score*"]),
        final_beam_size=int(fields["final_beam_size"]),
        expanded_states=int(fields["expanded_states"]),
        generated_transitions=int(fields["generated_transitions"]),
        certified_no_truncation=parse_bool(fields["certified_no_truncation"]),
        round_stats=" | ".join(round_stats),
        command=" ".join(command),
    )


def parse_estimator_bundle(output: str, command: list[str]) -> EstimatorBundle:
    fields: dict[str, str] = {}
    round_stats: list[str] = []
    values: dict[str, float] = {}
    value_re = re.compile(r"^(0x[0-9a-fA-F]+)\s+VE=([^\s]+)\s+proxy_score=([^\s]+)$")
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        value_match = value_re.match(stripped)
        if value_match:
            values[norm_mask(value_match.group(1))] = float(value_match.group(2))
            continue
        if stripped.startswith("round="):
            round_stats.append(stripped)
            continue
        if "=" in stripped:
            key, value = stripped.split("=", 1)
            fields[key.strip()] = value.strip()
    required = [
        "final_beam_size",
        "expanded_states",
        "generated_transitions",
        "certified_no_truncation",
    ]
    missing = [key for key in required if key not in fields]
    if missing:
        raise ValueError(f"estimator output missing fields {missing}: {output}")
    return EstimatorBundle(
        values=values,
        final_beam_size=int(fields["final_beam_size"]),
        expanded_states=int(fields["expanded_states"]),
        generated_transitions=int(fields["generated_transitions"]),
        certified_no_truncation=parse_bool(fields["certified_no_truncation"]),
        round_stats=" | ".join(round_stats),
        command=" ".join(command),
    )


def run_estimator(row: SubmitRow, args: argparse.Namespace) -> EstimatorAudit:
    command = [
        args.estimator_bin,
        "--r",
        str(row.r),
        "--u",
        row.u,
        "--v",
        row.v,
        "--beam",
        str(args.beam),
        "--trans",
        str(args.trans),
        "--branch",
        str(args.branch),
        "--mode",
        args.mode,
    ]
    completed = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return parse_estimator_output(completed.stdout, command)


def run_estimator_bundle(row: SubmitRow, args: argparse.Namespace) -> EstimatorBundle:
    command = [
        args.estimator_bin,
        "--r",
        str(row.r),
        "--u",
        row.u,
        "--beam",
        str(args.beam),
        "--trans",
        str(args.trans),
        "--branch",
        str(args.branch),
        "--mode",
        args.mode,
        "--top",
        "1000000000",
    ]
    completed = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return parse_estimator_bundle(completed.stdout, command)


def main() -> int:
    args = parse_args()
    rows = load_submit(Path(args.submit))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    failures = 0
    bundle_cache: dict[tuple[int, str], EstimatorBundle] = {}
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "r",
                "u",
                "v",
                "VT",
                "VE",
                "valid",
                "score",
                "beam",
                "trans",
                "branch",
                "mode",
                "expanded_states",
                "generated_transitions",
                "final_beam_size",
                "certified_no_truncation",
                "estimator_ve",
                "ve_matches_submit",
                "ve_source",
                "vt_source",
                "estimator_command",
                "exact_command",
                "round_stats",
            ]
        )
        for row in rows:
            cache_key = (row.r, row.u)
            bundle = bundle_cache.get(cache_key)
            if bundle is None:
                bundle = run_estimator_bundle(row, args)
                bundle_cache[cache_key] = bundle
            estimator_ve = bundle.values.get(row.v, 0.0)
            matches = abs(estimator_ve - row.ve) <= args.tolerance
            if not matches:
                failures += 1
            writer.writerow(
                [
                    row.r,
                    row.u,
                    row.v,
                    f"{row.vt:.24g}",
                    f"{row.ve:.24g}",
                    int(valid_interval(row.vt, row.ve)),
                    f"{score_value(row.r, row.ve):.24g}",
                    args.beam,
                    args.trans,
                    args.branch,
                    args.mode,
                    bundle.expanded_states,
                    bundle.generated_transitions,
                    bundle.final_beam_size,
                    int(bundle.certified_no_truncation),
                    f"{estimator_ve:.24g}",
                    int(matches),
                    "estimator",
                    "exact_oracle",
                    bundle.command,
                    f"./exact_oracle --r {row.r} --u {row.u} --v {row.v}",
                    bundle.round_stats,
                ]
            )

    print(f"audit_rows={len(rows)}")
    print(f"ve_mismatch_count={failures}")
    print(f"audit_path={out_path}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
