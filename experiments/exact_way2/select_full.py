#!/usr/bin/env python3
"""Deterministically select all frozen exact-way2 columns for the full run."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    FULL_SELECTION_SCHEMA,
    ROOT,
    count_active_nibbles,
    current_source_commit,
    deterministic_hash,
    load_final_queries,
    load_final_ru,
    repo_relative,
    sha256_file,
    sha256_text,
    write_csv,
    write_json,
    write_text,
)


def load_query_counts(final_queries: Path) -> dict[tuple[int, str], int]:
    counts: dict[tuple[int, str], int] = {}
    for row in load_final_queries(final_queries):
        key = (row.r, row.u)
        counts[key] = counts.get(key, 0) + 1
    return counts


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
    query_counts = load_query_counts(final_queries_path)

    selection: list[dict[str, object]] = []
    distribution = {"r1": 0, "r2": 0, "r3": 0}
    for r, u in load_final_ru(final_ru_path):
        selection.append(
            {
                "r": r,
                "u": u,
                "selection_reason": "all_ru",
                "active_count": count_active_nibbles(u),
                "query_count": query_counts[(r, u)],
                "deterministic_hash": deterministic_hash(r, u),
            }
        )
        distribution[f"r{r}"] += 1
    selection.sort(key=lambda row: (int(row["r"]), str(row["u"])))

    fieldnames = ["r", "u", "selection_reason", "active_count", "query_count", "deterministic_hash"]
    selection_csv_path = out_dir / "FULL_SELECTION.csv"
    write_csv(selection_csv_path, fieldnames, selection)
    selection_sha = sha256_file(selection_csv_path)
    selector_command = (
        "python3 -X utf8 experiments/exact_way2/select_full.py "
        f"--final-ru {repo_relative(final_ru_path)} "
        f"--final-queries {repo_relative(final_queries_path)} "
        "--out <ARTIFACT_ROOT>"
    )
    payload = {
        "schema": FULL_SELECTION_SCHEMA,
        "selected_columns": len(selection),
        "round_distribution": distribution,
        "selector_source_commit": source_commit,
        "selector_command": selector_command,
        "final_ru_sha256": sha256_file(final_ru_path),
        "final_queries_sha256": sha256_file(final_queries_path),
        "selection_payload_sha256": selection_sha,
        "selection": selection,
    }
    write_json(out_dir / "FULL_SELECTION.json", payload)

    protocol_text = "\n".join(
        [
            "# Exact Way-2 Full Selection Protocol",
            "",
            f"- schema: `{FULL_SELECTION_SCHEMA}`",
            f"- selector source commit: `{source_commit}`",
            f"- selector command: `{selector_command}`",
            f"- final_ru input: `{repo_relative(final_ru_path)}`",
            f"- final_queries input: `{repo_relative(final_queries_path)}`",
            f"- final_ru_sha256: `{sha256_file(final_ru_path)}`",
            f"- final_queries_sha256: `{sha256_file(final_queries_path)}`",
            f"- selection_payload_sha256: `{selection_sha}`",
            "- selection scope: `all 4760 unique (r,u) columns from final_ru.csv`",
            "- compute phase inputs remain limited to `row_id,r,u,v` from the frozen query file",
        ]
    ) + "\n"
    write_text(out_dir / "PROTOCOL.md", protocol_text)
    write_json(
        out_dir / "SELECTION_PROVENANCE.json",
        {
            "schema": FULL_SELECTION_SCHEMA,
            "selector_source_commit": source_commit,
            "selector_command": selector_command,
            "final_ru_sha256": sha256_file(final_ru_path),
            "final_queries_sha256": sha256_file(final_queries_path),
            "selection_payload_sha256": selection_sha,
            "protocol_sha256": sha256_text(protocol_text),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
