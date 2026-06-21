#!/usr/bin/env python3
"""Summarize per-(r,u) complexity certificates from a submit audit CSV.

This produces the P0/P1 evidence required by the guidance doc:
each unique (r,u) has bounded work and stays below the baseline 2^32 domain size.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path


TWO_POW_32 = 2**32


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", default="experiments/submit_audit.csv", help="Audit CSV path.")
    parser.add_argument(
        "--out-json",
        default="experiments/complexity/complexity_summary.json",
        help="Output JSON path.",
    )
    parser.add_argument(
        "--out-md",
        default="experiments/complexity/complexity_summary.md",
        help="Output Markdown path.",
    )
    return parser.parse_args()


def _percentile(sorted_values: list[int], q: float) -> int:
    """Nearest-rank percentile for non-empty sorted list."""
    if not sorted_values:
        raise ValueError("empty percentile input")
    if q <= 0:
        return sorted_values[0]
    if q >= 100:
        return sorted_values[-1]
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
    audit_path = Path(args.audit)
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)

    ru_stats: dict[tuple[int, int], tuple[int, int, int]] = {}
    ru_count_by_r: Counter[int] = Counter()

    with audit_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "r",
            "u",
            "generated_transitions",
            "expanded_states",
            "final_beam_size",
        }
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"audit CSV missing columns: {sorted(missing)}")

        for row in reader:
            ru_key = (int(row["r"]), int(row["u"], 0))
            if ru_key in ru_stats:
                continue
            stats = (
                int(row["generated_transitions"]),
                int(row["expanded_states"]),
                int(row["final_beam_size"]),
            )
            ru_stats[ru_key] = stats
            ru_count_by_r[ru_key[0]] += 1

    gen = sorted(s[0] for s in ru_stats.values())
    exp = sorted(s[1] for s in ru_stats.values())
    beam = sorted(s[2] for s in ru_stats.values())

    max_gen = gen[-1] if gen else 0
    max_exp = exp[-1] if exp else 0
    max_beam = beam[-1] if beam else 0

    summary = {
        "audit": str(audit_path),
        "unique_ru": len(ru_stats),
        "unique_ru_by_r": {str(k): v for k, v in sorted(ru_count_by_r.items())},
        "threshold_2_32": TWO_POW_32,
        "ru_generated_transitions_ge_2_32": sum(1 for v in gen if v >= TWO_POW_32),
        "ru_expanded_states_ge_2_32": sum(1 for v in exp if v >= TWO_POW_32),
        "max_generated_transitions_per_ru": max_gen,
        "max_expanded_states_per_ru": max_exp,
        "max_final_beam_size_per_ru": max_beam,
        "generated_transitions_ratio_to_2_32_max": (max_gen / TWO_POW_32) if TWO_POW_32 else None,
    }

    if gen:
        summary.update(
            {
                "generated_transitions_median_per_ru": _percentile(gen, 50),
                "generated_transitions_p95_per_ru": _percentile(gen, 95),
            }
        )
    if exp:
        summary.update(
            {
                "expanded_states_median_per_ru": _percentile(exp, 50),
                "expanded_states_p95_per_ru": _percentile(exp, 95),
            }
        )
    if beam:
        summary.update(
            {
                "final_beam_size_median_per_ru": _percentile(beam, 50),
                "final_beam_size_p95_per_ru": _percentile(beam, 95),
            }
        )

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
    )[:20]
    summary["worst_ru_by_generated_transitions_top20"] = worst_ru_by_generated_transitions

    write_json(out_json, summary)

    md = [
        "# Complexity Summary",
        "",
        f"- audit: `{audit_path}`",
        f"- unique_ru: {summary['unique_ru']}",
        f"- threshold_2_32: {summary['threshold_2_32']}",
        "",
        "## Gate Checks",
        "",
        f"- ru_generated_transitions_ge_2_32: {summary['ru_generated_transitions_ge_2_32']}",
        f"- ru_expanded_states_ge_2_32: {summary['ru_expanded_states_ge_2_32']}",
        "",
        "## Max (Unique `(r,u)`)",
        "",
        f"- max_generated_transitions_per_ru: {summary['max_generated_transitions_per_ru']}",
        f"- generated_transitions_ratio_to_2_32_max: {summary['generated_transitions_ratio_to_2_32_max']:.6g}",
        f"- max_expanded_states_per_ru: {summary['max_expanded_states_per_ru']}",
        f"- max_final_beam_size_per_ru: {summary['max_final_beam_size_per_ru']}",
    ]

    if "generated_transitions_median_per_ru" in summary:
        md.extend(
            [
                "",
                "## Distribution (Unique `(r,u)`)",
                "",
                f"- generated_transitions_median_per_ru: {summary['generated_transitions_median_per_ru']}",
                f"- generated_transitions_p95_per_ru: {summary['generated_transitions_p95_per_ru']}",
                f"- expanded_states_median_per_ru: {summary['expanded_states_median_per_ru']}",
                f"- expanded_states_p95_per_ru: {summary['expanded_states_p95_per_ru']}",
                f"- final_beam_size_median_per_ru: {summary['final_beam_size_median_per_ru']}",
                f"- final_beam_size_p95_per_ru: {summary['final_beam_size_p95_per_ru']}",
            ]
        )

    md.extend(
        [
            "",
            "## Worst `(r,u)` (by generated_transitions)",
            "",
            "```json",
            json.dumps(worst_ru_by_generated_transitions, indent=2, sort_keys=True),
            "```",
        ]
    )

    write_md(out_md, md)

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

