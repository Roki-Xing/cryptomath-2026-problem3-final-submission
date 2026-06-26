#!/usr/bin/env python3
"""Prepare sanitized selector inputs for the exact-way2 pilot."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from common import (
    ROOT,
    SELECTION_SCHEMA,
    current_source_commit,
    load_final_ru,
    repo_relative,
    sha256_file,
    write_csv,
    write_json,
    write_text,
)


def load_complexity_rows(audit_path: Path, allowed_keys: set[tuple[int, str]]) -> list[dict[str, object]]:
    per_key: dict[tuple[int, str], dict[str, object]] = {}
    transitions_seen: dict[tuple[int, str], set[int]] = defaultdict(set)
    expanded_seen: dict[tuple[int, str], set[int]] = defaultdict(set)
    with audit_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            key = (int(row["r"]), row["u"].lower())
            if key not in allowed_keys:
                continue
            transitions = int(row["generated_transitions"])
            expanded = int(row["expanded_states"])
            transitions_seen[key].add(transitions)
            expanded_seen[key].add(expanded)
            if key not in per_key:
                per_key[key] = {
                    "r": key[0],
                    "u": key[1],
                    "generated_transitions": transitions,
                    "expanded_states": expanded,
                }
    missing = sorted(allowed_keys - set(per_key))
    if missing:
        sample = ", ".join(f"(r={r},u={u})" for r, u in missing[:8])
        raise SystemExit(f"missing complexity rows for final_ru keys: {sample}")
    inconsistent = []
    for key in sorted(allowed_keys):
        if len(transitions_seen[key]) != 1 or len(expanded_seen[key]) != 1:
            inconsistent.append(key)
    if inconsistent:
        sample = ", ".join(f"(r={r},u={u})" for r, u in inconsistent[:8])
        raise SystemExit(
            "historical complexity rows are inconsistent for the same (r,u): "
            f"{sample}"
        )
    return [per_key[key] for key in sorted(per_key)]


def load_spotcheck_rows(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[tuple[int, str, str]] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            triple = (int(row["r"]), row["u"].lower(), row["v"].lower())
            if triple in seen:
                continue
            seen.add(triple)
            rows.append({"r": triple[0], "u": triple[1], "v": triple[2]})
    rows.sort(key=lambda row: (int(row["r"]), str(row["u"]), str(row["v"])))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-ru", required=True)
    parser.add_argument("--audit", default="experiments/submit_audit.csv")
    parser.add_argument("--spotcheck-queries", default="experiments/spotcheck/exact_spotcheck_queries.csv")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    final_ru_path = Path(args.final_ru)
    audit_path = ROOT / args.audit
    spotcheck_queries_path = ROOT / args.spotcheck_queries
    final_ru = load_final_ru(final_ru_path)
    allowed_keys = set(final_ru)

    complexity_rows = load_complexity_rows(audit_path, allowed_keys)
    complexity_path = out_dir / "COMPLEXITY_INPUT.csv"
    write_csv(
        complexity_path,
        ["r", "u", "generated_transitions", "expanded_states"],
        complexity_rows,
    )

    spotcheck_rows = load_spotcheck_rows(spotcheck_queries_path)
    spotcheck_path = out_dir / "SPOTCHECK_COORDINATES.csv"
    write_csv(spotcheck_path, ["r", "u", "v"], spotcheck_rows)

    command = (
        "python3 -X utf8 experiments/exact_way2/prepare_selector_inputs.py "
        f"--final-ru {repo_relative(final_ru_path)} "
        f"--audit {repo_relative(audit_path)} "
        f"--spotcheck-queries {repo_relative(spotcheck_queries_path)} "
        "--out <ARTIFACT_ROOT>"
    )
    protocol = "\n".join(
        [
            "# Exact Way-2 Selector Input Preparation",
            "",
            f"- schema: `{SELECTION_SCHEMA}`",
            f"- source commit: `{current_source_commit()}`",
            f"- command: `{command}`",
            f"- final_ru input: `{repo_relative(final_ru_path)}`",
            f"- audit source: `{repo_relative(audit_path)}`",
            f"- spotcheck query source: `{repo_relative(spotcheck_queries_path)}`",
            "- allowed fields in complexity input: `r,u,generated_transitions,expanded_states`",
            "- allowed fields in spotcheck coordinates: `r,u,v`",
            "- forbidden during selector preparation: `VE,VT,score,way-1 numerator,candidate rank/source`",
        ]
    ) + "\n"
    write_text(out_dir / "SELECTOR_INPUT_PROTOCOL.md", protocol)
    write_json(
        out_dir / "SELECTOR_INPUT_PREPARATION.json",
        {
            "schema": SELECTION_SCHEMA,
            "source_commit": current_source_commit(),
            "command": command,
            "final_ru_sha256": sha256_file(final_ru_path),
            "audit_sha256": sha256_file(audit_path),
            "spotcheck_queries_sha256": sha256_file(spotcheck_queries_path),
            "complexity_input_sha256": sha256_file(complexity_path),
            "spotcheck_coordinates_sha256": sha256_file(spotcheck_path),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
