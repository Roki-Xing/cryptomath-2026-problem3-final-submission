#!/usr/bin/env python3
"""Summarize a submit audit CSV into JSON and Markdown.

This is a lightweight reporting tool for the P0 evidence chain:
- proves the audit CSV is full-row (row count matches submit)
- checks for VE reproduction mismatches and certificate coverage
- reports duplicate/zero-mask issues and max per-(r,u) complexity figures
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


SUBMIT_RE = re.compile(
    r"^@\(\s*(?P<r>\d+)\s*,\s*(?P<u>0x[0-9a-fA-F]+|\d+)\s*,\s*"
    r"(?P<v>0x[0-9a-fA-F]+|\d+)\s*,\s*(?P<vt>[^,]+)\s*,\s*(?P<ve>[^\)]+)\s*\)\s*$"
)

TWO_POW_32 = 2**32


@dataclass(frozen=True)
class SubmitRow:
    r: int
    u: int
    v: int
    vt: float
    ve: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submit", default="submit.txt", help="Submit file path.")
    parser.add_argument("--audit", default="experiments/submit_audit.csv", help="Audit CSV path.")
    parser.add_argument(
        "--out-json",
        default="experiments/audit/submit_audit_summary.json",
        help="Output JSON path.",
    )
    parser.add_argument(
        "--out-md",
        default="experiments/audit/submit_audit_summary.md",
        help="Output Markdown path.",
    )
    return parser.parse_args()


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
                u=int(match.group("u"), 0),
                v=int(match.group("v"), 0),
                vt=float(match.group("vt")),
                ve=float(match.group("ve")),
            )
        )
    return rows


def _percentile(sorted_values: list[int], q: float) -> int:
    """Nearest-rank percentile for non-empty sorted list."""
    if not sorted_values:
        raise ValueError("empty percentile input")
    if q <= 0:
        return sorted_values[0]
    if q >= 100:
        return sorted_values[-1]
    # nearest-rank: ceil(q/100 * n) - 1
    n = len(sorted_values)
    idx = int(math.ceil((q / 100.0) * n) - 1)
    return sorted_values[max(0, min(n - 1, idx))]


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()

    submit_path = Path(args.submit)
    audit_path = Path(args.audit)
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)

    submit_rows = load_submit(submit_path)
    submit_rows_count = len(submit_rows)

    uv = [(row.u, row.v) for row in submit_rows]
    uv_counter = Counter(uv)
    duplicate_uv_rows = sum(count - 1 for count in uv_counter.values() if count > 1)

    zero_u_rows = sum(1 for row in submit_rows if row.u == 0)
    zero_v_rows = sum(1 for row in submit_rows if row.v == 0)
    zero_vt_rows = sum(1 for row in submit_rows if row.vt == 0.0)
    zero_ve_rows = sum(1 for row in submit_rows if row.ve == 0.0)

    # Audit scan
    audit_rows = 0
    valid_rows = 0
    certified_rows = 0
    certified_rows_valid = 0
    ve_mismatch_rows = 0
    ve_mismatch_rows_valid = 0
    valid_rows_by_score: Counter[str] = Counter()
    valid_rows_by_r: Counter[int] = Counter()

    # Unique (r,u) complexity certificate
    ru_stats: dict[tuple[int, int], tuple[int, int, int]] = {}

    with audit_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "r",
            "u",
            "v",
            "valid",
            "score",
            "generated_transitions",
            "expanded_states",
            "final_beam_size",
            "certified_no_truncation",
            "ve_matches_submit",
        }
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"audit CSV missing columns: {sorted(missing)}")

        for row in reader:
            audit_rows += 1
            is_valid = row["valid"] == "1"
            if is_valid:
                valid_rows += 1
                valid_rows_by_score[row["score"]] += 1
                valid_rows_by_r[int(row["r"])] += 1
            if row["certified_no_truncation"] == "1":
                certified_rows += 1
                if is_valid:
                    certified_rows_valid += 1

            ve_matches = row["ve_matches_submit"] == "1"
            if not ve_matches:
                ve_mismatch_rows += 1
                if is_valid:
                    ve_mismatch_rows_valid += 1

            ru_key = (int(row["r"]), int(row["u"], 0))
            if ru_key not in ru_stats:
                ru_stats[ru_key] = (
                    int(row["generated_transitions"]),
                    int(row["expanded_states"]),
                    int(row["final_beam_size"]),
                )

    ru_generated_transitions_sorted = sorted(s[0] for s in ru_stats.values())
    ru_expanded_states_sorted = sorted(s[1] for s in ru_stats.values())
    ru_final_beam_size_sorted = sorted(s[2] for s in ru_stats.values())

    max_generated_transitions = ru_generated_transitions_sorted[-1] if ru_generated_transitions_sorted else 0
    max_expanded_states = ru_expanded_states_sorted[-1] if ru_expanded_states_sorted else 0
    max_final_beam_size = ru_final_beam_size_sorted[-1] if ru_final_beam_size_sorted else 0
    ru_generated_transitions_ge_2_32 = sum(1 for v in ru_generated_transitions_sorted if v >= TWO_POW_32)
    ru_expanded_states_ge_2_32 = sum(1 for v in ru_expanded_states_sorted if v >= TWO_POW_32)

    worst_ru_by_generated_transitions = sorted(
        (
            {
                "r": r,
                "u": f"0x{u:08x}",
                "generated_transitions": stats[0],
                "expanded_states": stats[1],
                "final_beam_size": stats[2],
            }
            for (r, u), stats in ru_stats.items()
        ),
        key=lambda item: item["generated_transitions"],
        reverse=True,
    )[:10]

    summary = {
        "submit_rows": submit_rows_count,
        "unique_uv": len(uv_counter),
        "duplicate_uv_rows": duplicate_uv_rows,
        "zero_u_rows": zero_u_rows,
        "zero_v_rows": zero_v_rows,
        "zero_vt_rows": zero_vt_rows,
        "zero_ve_rows": zero_ve_rows,
        "audit_rows": audit_rows,
        "valid_rows": valid_rows,
        "certified_no_truncation_rows": certified_rows,
        "certified_no_truncation_rows_valid": certified_rows_valid,
        "ve_mismatch_rows": ve_mismatch_rows,
        "ve_mismatch_rows_valid": ve_mismatch_rows_valid,
        "valid_rows_by_r": {str(k): v for k, v in sorted(valid_rows_by_r.items())},
        "valid_rows_by_score": {k: v for k, v in sorted(valid_rows_by_score.items())},
        "unique_ru": len(ru_stats),
        "max_generated_transitions_per_unique_ru": max_generated_transitions,
        "max_expanded_states_per_unique_ru": max_expanded_states,
        "max_final_beam_size_per_unique_ru": max_final_beam_size,
        "ru_generated_transitions_ge_2_32": ru_generated_transitions_ge_2_32,
        "ru_expanded_states_ge_2_32": ru_expanded_states_ge_2_32,
        "max_generated_transitions_ratio_to_2_32": (max_generated_transitions / TWO_POW_32)
        if TWO_POW_32
        else None,
        "worst_ru_by_generated_transitions_top10": worst_ru_by_generated_transitions,
    }

    # Some extra distribution stats for quick inspection.
    if ru_generated_transitions_sorted:
        summary.update(
            {
                "generated_transitions_median_per_ru": _percentile(ru_generated_transitions_sorted, 50),
                "generated_transitions_p95_per_ru": _percentile(ru_generated_transitions_sorted, 95),
            }
        )
    if ru_expanded_states_sorted:
        summary.update(
            {
                "expanded_states_median_per_ru": _percentile(ru_expanded_states_sorted, 50),
                "expanded_states_p95_per_ru": _percentile(ru_expanded_states_sorted, 95),
            }
        )

    write_json(out_json, summary)

    md = [
        "# Submit Audit Summary",
        "",
        f"- submit: `{submit_path}`",
        f"- audit: `{audit_path}`",
        "",
        "## Row Counts",
        "",
        f"- submit_rows: {summary['submit_rows']}",
        f"- audit_rows: {summary['audit_rows']}",
        "",
        "## Validity / Safety Checks",
        "",
        f"- valid_rows: {summary['valid_rows']}",
        f"- certified_no_truncation_rows: {summary['certified_no_truncation_rows']}",
        f"- certified_no_truncation_rows_valid: {summary['certified_no_truncation_rows_valid']}",
        f"- ve_mismatch_rows: {summary['ve_mismatch_rows']}",
        f"- ve_mismatch_rows_valid: {summary['ve_mismatch_rows_valid']}",
        f"- unique_uv: {summary['unique_uv']}",
        f"- duplicate_uv_rows: {summary['duplicate_uv_rows']}",
        f"- zero_u_rows: {summary['zero_u_rows']}",
        f"- zero_v_rows: {summary['zero_v_rows']}",
        f"- zero_vt_rows: {summary['zero_vt_rows']}",
        f"- zero_ve_rows: {summary['zero_ve_rows']}",
        "",
        "## Complexity Certificate (Unique `(r,u)`)",
        "",
        f"- unique_ru: {summary['unique_ru']}",
        f"- max_generated_transitions_per_unique_ru: {summary['max_generated_transitions_per_unique_ru']}",
        f"- max_generated_transitions_ratio_to_2_32: {summary['max_generated_transitions_ratio_to_2_32']:.6g}",
        f"- max_expanded_states_per_unique_ru: {summary['max_expanded_states_per_unique_ru']}",
        f"- max_final_beam_size_per_unique_ru: {summary['max_final_beam_size_per_unique_ru']}",
        f"- ru_generated_transitions_ge_2_32: {summary['ru_generated_transitions_ge_2_32']}",
        f"- ru_expanded_states_ge_2_32: {summary['ru_expanded_states_ge_2_32']}",
    ]
    if "generated_transitions_median_per_ru" in summary:
        md.extend(
            [
                "",
                "## Complexity Distribution (Unique `(r,u)`)",
                "",
                f"- generated_transitions_median_per_ru: {summary['generated_transitions_median_per_ru']}",
                f"- generated_transitions_p95_per_ru: {summary['generated_transitions_p95_per_ru']}",
                f"- expanded_states_median_per_ru: {summary['expanded_states_median_per_ru']}",
                f"- expanded_states_p95_per_ru: {summary['expanded_states_p95_per_ru']}",
            ]
        )

    md.extend(
        [
            "",
            "## Worst `(r,u)` (by generated_transitions)",
            "",
            "```json",
            json.dumps(summary["worst_ru_by_generated_transitions_top10"], indent=2, sort_keys=True),
            "```",
        ]
    )

    write_md(out_md, md)

    # Emit a compact machine-readable record for log capture (tee).
    print(json.dumps(summary, indent=2, sort_keys=True))

    # Simple gate checks for automation.
    if audit_rows != submit_rows_count:
        raise SystemExit(f"audit_rows ({audit_rows}) != submit_rows ({submit_rows_count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
