#!/usr/bin/env python3
"""Build an explicitly provisional full-run forecast from benchmark results."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


FULL_DOMAIN = 1 << 32
FROZEN_COUNTS = {1: 288, 2: 90236, 3: 47814}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * quantile)))
    return ordered[index]


def main() -> None:
    args = parse_args()
    with args.results.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit("error: results file is empty")

    grouped: dict[tuple[int, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(int(row["r"]), row["implementation"])].append(row)

    projections: list[dict[str, object]] = []
    for (rounds, implementation), samples in sorted(grouped.items()):
        rates = [
            float(sample["query_updates_per_second"])
            for sample in samples
            if float(sample["query_updates_per_second"]) > 0
        ]
        if not rates:
            continue
        target_updates = FULL_DOMAIN * FROZEN_COUNTS[rounds]
        center_rate = statistics.median(rates)
        conservative_rate = percentile(rates, 0.05)
        projections.append(
            {
                "r": rounds,
                "implementation": implementation,
                "sample_count": len(rates),
                "measured_q": sorted({int(sample["Q"]) for sample in samples}),
                "measured_plaintext_counts": sorted(
                    {int(sample["plaintext_count"]) for sample in samples}
                ),
                "center_wall_seconds": target_updates / center_rate,
                "conservative_upper_wall_seconds": target_updates
                / conservative_rate,
                "center_rate_query_updates_per_second": center_rate,
                "conservative_rate_query_updates_per_second": conservative_rate,
            }
        )

    payload = {
        "schema": "way1-full-run-projection-v1",
        "decision": "NO_GO_PENDING",
        "go_gate_passed": False,
        "reason": (
            "Stage A smoke data does not satisfy the required Q/domain matrix, "
            "full-domain cross-implementation checks, or holdout error gates."
        ),
        "prediction_basis": (
            "Direct proportional scaling of measured logical query-update throughput."
        ),
        "prediction_interval": (
            "The conservative bound uses the slowest measured throughput sample. "
            "It is not a validated 95% prediction interval until repeated Stage B/C "
            "runs and holdout checks are complete."
        ),
        "extrapolation_warning": (
            "These projections extrapolate beyond the measured domain and query count "
            "and must not be presented as confirmed completion times."
        ),
        "required_before_go": [
            "complete the prescribed r/Q/domain benchmark matrix",
            "verify full-domain Q=8 and Q=64 numerator equality",
            "obtain repeated-run variance and a validated 95% interval",
            "pass Q=512 and Q=16384 holdout error thresholds",
            "record available hours, RAM, disk, and planned shard efficiency",
        ],
        "projections": projections,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"decision={payload['decision']}")
    print(f"projection_rows={len(projections)}")


if __name__ == "__main__":
    main()
