#!/usr/bin/env python3
"""Deterministically select the frozen exact-way2 pilot columns."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from common import (
    ROOT,
    SELECTION_SCHEMA,
    count_active_nibbles,
    current_source_commit,
    deterministic_hash,
    exact_band,
    load_final_queries,
    load_final_ru,
    percentile_rank,
    repo_relative,
    sha256_file,
    sha256_text,
    write_csv,
    write_json,
)


def load_complexity_rows() -> list[dict[str, object]]:
    source = ROOT / "experiments/submit_audit.csv"
    grouped: dict[tuple[int, str], dict[str, object]] = {}
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            key = (int(row["r"]), row["u"].lower())
            if key in grouped:
                continue
            grouped[key] = {
                "r": key[0],
                "u": key[1],
                "generated_transitions": int(row["generated_transitions"]),
                "expanded_states": int(row["expanded_states"]),
            }
    return [grouped[key] for key in sorted(grouped)]


def load_spotcheck_coordinate_rows() -> list[dict[str, object]]:
    source = ROOT / "experiments/spotcheck/exact_spotcheck.csv"
    rows: list[dict[str, object]] = []
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "r": int(row["r"]),
                    "u": row["u"].lower(),
                    "v": row["v"].lower(),
                }
            )
    rows.sort(key=lambda row: (int(row["r"]), str(row["u"]), str(row["v"])))
    return rows


def load_r2_spotcheck_u(rows: list[dict[str, object]]) -> set[str]:
    return {str(row["u"]) for row in rows if int(row["r"]) == 2}


def load_query_counts(final_queries: Path) -> dict[tuple[int, str], int]:
    counts: dict[tuple[int, str], int] = defaultdict(int)
    for row in load_final_queries(final_queries):
        counts[(row.r, row.u)] += 1
    return counts


def build_row(
    r: int,
    u: str,
    complexity: dict[tuple[int, str], dict[str, object]],
    query_counts: dict[tuple[int, str], int],
) -> dict[str, object]:
    stats = complexity[(r, u)]
    return {
        "r": r,
        "u": u,
        "active_count": count_active_nibbles(u),
        "generated_transitions": int(stats["generated_transitions"]),
        "expanded_states": int(stats["expanded_states"]),
        "query_count": query_counts[(r, u)],
        "deterministic_hash": deterministic_hash(r, u),
    }


def largest_remainder_allocate(groups: dict[str, list[dict[str, object]]], target: int) -> dict[str, int]:
    non_empty = {key: rows for key, rows in groups.items() if rows}
    if target < len(non_empty):
        raise SystemExit("not enough slots to assign at least one pilot to each non-empty stratum")
    base = {key: 1 for key in non_empty}
    remaining = target - len(non_empty)
    total = sum(len(rows) for rows in non_empty.values())
    if remaining == 0:
        return base
    shares = {}
    for key, rows in non_empty.items():
        ideal = remaining * (len(rows) / total)
        shares[key] = (int(ideal), ideal - int(ideal))
    allocation = {key: base[key] + shares[key][0] for key in non_empty}
    assigned = sum(allocation.values())
    leftovers = target - assigned
    ranked = sorted(non_empty, key=lambda key: (-shares[key][1], key))
    for key in ranked[:leftovers]:
        allocation[key] += 1
    return allocation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-ru", required=True)
    parser.add_argument("--final-queries", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    final_ru_path = Path(args.final_ru)
    final_queries_path = Path(args.final_queries)
    source_commit = current_source_commit()
    selector_command = (
        "python3 -X utf8 experiments/exact_way2/select_pilot.py "
        f"--final-ru {repo_relative(final_ru_path)} "
        f"--final-queries {repo_relative(final_queries_path)} "
        "--out <ARTIFACT_ROOT>"
    )

    complexity_rows = load_complexity_rows()
    complexity_input_path = out_dir / "COMPLEXITY_INPUT.csv"
    write_csv(
        complexity_input_path,
        ["r", "u", "generated_transitions", "expanded_states"],
        complexity_rows,
    )
    complexity = {(int(row["r"]), str(row["u"])): row for row in complexity_rows}

    spotcheck_rows = load_spotcheck_coordinate_rows()
    spotcheck_input_path = out_dir / "SPOTCHECK_COORDINATES.csv"
    write_csv(spotcheck_input_path, ["r", "u", "v"], spotcheck_rows)
    r2_spotcheck_u = load_r2_spotcheck_u(spotcheck_rows)

    final_ru = load_final_ru(final_ru_path)
    query_counts = load_query_counts(final_queries_path)
    selected: list[dict[str, object]] = []
    selected_keys: set[tuple[int, str]] = set()

    for r, u in final_ru:
        if r in (1, 3):
            row = build_row(r, u, complexity, query_counts)
            row["complexity_percentile"] = 100.0 if r == 1 else 0.0
            row["complexity_band"] = "[95,100]" if r == 1 else exact_band(0.0)
            row["selection_reason"] = "all_r1" if r == 1 else "all_r3"
            selected.append(row)
            selected_keys.add((r, u))

    r2_rows = [build_row(2, u, complexity, query_counts) for r, u in final_ru if r == 2]
    sorted_transitions = sorted(int(row["generated_transitions"]) for row in r2_rows)
    for row in r2_rows:
        row["complexity_percentile"] = round(
            percentile_rank(sorted_transitions, int(row["generated_transitions"])),
            6,
        )
        row["complexity_band"] = exact_band(float(row["complexity_percentile"]))

    r2_by_u = {str(row["u"]): row for row in r2_rows}
    required_u = set(r2_spotcheck_u)
    order_by_complexity = sorted(r2_rows, key=lambda row: (int(row["generated_transitions"]), str(row["u"])))
    required_u.add(str(order_by_complexity[0]["u"]))
    required_u.add(str(order_by_complexity[len(order_by_complexity) // 2]["u"]))
    required_u.add(
        str(order_by_complexity[min(len(order_by_complexity) - 1, int(len(order_by_complexity) * 0.95))]["u"])
    )
    required_u.add(str(order_by_complexity[-1]["u"]))

    for u in sorted(required_u):
        row = dict(r2_by_u[u])
        row["selection_reason"] = "required_anchor"
        selected.append(row)
        selected_keys.add((2, u))

    remaining = [row for row in r2_rows if (2, str(row["u"])) not in selected_keys]
    strata: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in remaining:
        key = f"a{row['active_count']}|{row['complexity_band']}"
        strata[key].append(row)
    for rows in strata.values():
        rows.sort(key=lambda row: (str(row["deterministic_hash"]), str(row["u"])))

    slots = 128 - len(required_u)
    allocation = largest_remainder_allocate(strata, slots)
    for key, count in allocation.items():
        for row in strata[key][:count]:
            chosen = dict(row)
            chosen["selection_reason"] = f"strata:{key}"
            selected.append(chosen)
            selected_keys.add((2, str(chosen["u"])))

    selected.sort(key=lambda row: (int(row["r"]), str(row["u"])))
    if len(selected) != 344:
        raise SystemExit(f"pilot selection must contain 344 columns, got {len(selected)}")

    fieldnames = [
        "r",
        "u",
        "selection_reason",
        "active_count",
        "complexity_percentile",
        "complexity_band",
        "generated_transitions",
        "expanded_states",
        "query_count",
        "deterministic_hash",
    ]
    write_csv(out_dir / "PILOT_SELECTION.csv", fieldnames, selected)
    selection_payload_sha256 = sha256_file(out_dir / "PILOT_SELECTION.csv")

    payload = {
        "schema": SELECTION_SCHEMA,
        "selected_columns": len(selected),
        "round_distribution": {
            "r1": sum(1 for row in selected if int(row["r"]) == 1),
            "r2": sum(1 for row in selected if int(row["r"]) == 2),
            "r3": sum(1 for row in selected if int(row["r"]) == 3),
        },
        "selector_source_commit": source_commit,
        "selector_command": selector_command,
        "final_ru_sha256": sha256_file(final_ru_path),
        "final_queries_sha256": sha256_file(final_queries_path),
        "complexity_input_sha256": sha256_file(complexity_input_path),
        "spotcheck_coordinates_sha256": sha256_file(spotcheck_input_path),
        "selection_payload_sha256": selection_payload_sha256,
        "selection": selected,
    }
    write_json(out_dir / "PILOT_SELECTION.json", payload)

    protocol_lines = [
        "# Exact Way-2 Pilot Protocol",
        "",
        f"- schema: `{SELECTION_SCHEMA}`",
        f"- selector source commit: `{source_commit}`",
        f"- selector command: `{selector_command}`",
        f"- final_ru input: `{repo_relative(final_ru_path)}`",
        f"- final_queries input: `{repo_relative(final_queries_path)}`",
        f"- complexity-only input: `{complexity_input_path.name}`",
        f"- spotcheck-coordinates input: `{spotcheck_input_path.name}`",
        f"- final_ru_sha256: `{sha256_file(final_ru_path)}`",
        f"- final_queries_sha256: `{sha256_file(final_queries_path)}`",
        f"- complexity_input_sha256: `{sha256_file(complexity_input_path)}`",
        f"- spotcheck_coordinates_sha256: `{sha256_file(spotcheck_input_path)}`",
        f"- selection_payload_sha256: `{selection_payload_sha256}`",
        "- forbidden during selection/compute: frozen VE values, score, submit VT/VE, way-1 outputs, candidate ranking",
        "- pilot size: `344` unique `(r,u)` columns",
        "- target distribution: `r1=120`, `r2=128`, `r3=96`",
    ]
    (out_dir / "PROTOCOL.md").write_text("\n".join(protocol_lines) + "\n", encoding="utf-8")
    protocol_sha = sha256_text("\n".join(protocol_lines) + "\n")

    write_json(
        out_dir / "SELECTOR_PROVENANCE.json",
        {
            "schema": SELECTION_SCHEMA,
            "selector_source_commit": source_commit,
            "selector_command": selector_command,
            "final_ru_sha256": sha256_file(final_ru_path),
            "final_queries_sha256": sha256_file(final_queries_path),
            "complexity_input_sha256": sha256_file(complexity_input_path),
            "spotcheck_coordinates_sha256": sha256_file(spotcheck_input_path),
            "selection_payload_sha256": selection_payload_sha256,
            "protocol_sha256": protocol_sha,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
