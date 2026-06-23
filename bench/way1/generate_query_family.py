#!/usr/bin/env python3
"""Generate deterministic frozen and synthetic-frozen-shaped benchmark queries."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Query:
    row_id: int
    r: int
    u: int
    v: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--ru-source", type=Path, required=True)
    parser.add_argument(
        "--family",
        choices=("uniform", "frozen-subset", "synthetic-frozen-shaped"),
        required=True,
    )
    parser.add_argument("--profile", required=True)
    parser.add_argument("--r", type=int, required=True, choices=(1, 2, 3))
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--metadata-out", type=Path, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_sha256(query_path: Path, ru_path: Path) -> str:
    digest = hashlib.sha256()
    for label, path in (("final_queries", query_path), ("final_ru", ru_path)):
        digest.update(label.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def keyed_digest(seed: str, *parts: object) -> bytes:
    payload = seed + "".join(f"\0{part}" for part in parts)
    return hashlib.sha256(payload.encode()).digest()


def load_queries(path: Path, rounds: int) -> list[Query]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["r", "u", "v"]:
            raise ValueError(f"expected frozen r,u,v schema, got {reader.fieldnames}")
        rows = [
            Query(
                row_id=row_id,
                r=rounds,
                u=int(row["u"], 0),
                v=int(row["v"], 0),
            )
            for row_id, row in enumerate(reader, start=1)
            if int(row["r"]) == rounds
        ]
    if not rows:
        raise ValueError(f"no frozen rows for r={rounds}")
    return rows


def validate_ru_source(path: Path, rounds: int) -> None:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not {"r", "u"}.issubset(reader.fieldnames):
            raise ValueError("final_ru.csv must contain r,u columns")
        if not any(int(row["r"]) == rounds for row in reader):
            raise ValueError(f"final_ru.csv has no rows for r={rounds}")


def uniform_subset(rows: list[Query], count: int, seed: str) -> list[Query]:
    if count > len(rows):
        raise ValueError(f"requested {count} queries but only {len(rows)} are available")
    return sorted(
        rows,
        key=lambda query: (
            keyed_digest(seed, "uniform", query.row_id, query.r, query.u, query.v),
            query.row_id,
        ),
    )[:count]


def frozen_subset(rows: list[Query], count: int, seed: str, profile: str) -> list[Query]:
    if profile not in {"uv_core", "u_stratified"}:
        raise ValueError("frozen-subset profile must be uv_core or u_stratified")
    if count > len(rows):
        raise ValueError(
            f"requested {count} frozen queries but only {len(rows)} are available"
        )

    by_u: dict[int, list[Query]] = defaultdict(list)
    by_v: dict[int, list[Query]] = defaultdict(list)
    for query in rows:
        by_u[query.u].append(query)
        by_v[query.v].append(query)

    ranked_u = sorted(by_u, key=lambda mask: (len(by_u[mask]), mask))
    split1 = max(1, len(ranked_u) // 3)
    split2 = max(split1 + 1, 2 * len(ranked_u) // 3)
    buckets = {
        "LOW": ranked_u[:split1],
        "MID": ranked_u[split1:split2],
        "HIGH": ranked_u[split2:],
    }
    if not buckets["MID"]:
        buckets["MID"] = ranked_u
    if not buckets["HIGH"]:
        buckets["HIGH"] = ranked_u

    width = min(16, max(2, math.isqrt(count) // 2))
    quotas = {
        "HIGH": count // 2,
        "MID": count // 4,
        "LOW": count // 8 if profile == "uv_core" else count // 4,
    }
    if profile == "u_stratified":
        quotas["LOW"] = count - quotas["HIGH"] - quotas["MID"]

    selected: list[Query] = []
    selected_ids: set[int] = set()

    def add(query: Query) -> bool:
        if query.row_id in selected_ids or len(selected) >= count:
            return False
        selected.append(query)
        selected_ids.add(query.row_id)
        return True

    for bucket_name in ("HIGH", "MID", "LOW"):
        target = min(count, len(selected) + quotas[bucket_name])
        nodes = sorted(
            buckets[bucket_name],
            key=lambda mask: keyed_digest(seed, bucket_name, mask),
        )[:width]
        incident = {
            mask: sorted(
                by_u[mask],
                key=lambda query: keyed_digest(
                    seed, "u-edge", mask, query.row_id, query.v
                ),
            )
            for mask in nodes
        }
        max_degree = max((len(edges) for edges in incident.values()), default=0)
        for offset in range(max_degree):
            for mask in nodes:
                if len(selected) >= target:
                    break
                if offset < len(incident[mask]):
                    add(incident[mask][offset])
            if len(selected) >= target:
                break

    if profile == "uv_core" and len(selected) < count:
        ranked_v = sorted(
            by_v,
            key=lambda mask: (
                -len(by_v[mask]),
                keyed_digest(seed, "v-node", mask),
            ),
        )[:width]
        max_degree = max((len(by_v[mask]) for mask in ranked_v), default=0)
        for offset in range(max_degree):
            for mask in ranked_v:
                if len(selected) >= count:
                    break
                incident = sorted(
                    by_v[mask],
                    key=lambda query: keyed_digest(
                        seed, "v-edge", mask, query.row_id, query.u
                    ),
                )
                if offset < len(incident):
                    add(incident[offset])
            if len(selected) >= count:
                break

    remaining = sorted(
        rows,
        key=lambda query: keyed_digest(
            seed, "tail", query.row_id, query.r, query.u, query.v
        ),
    )
    for query in remaining:
        add(query)
        if len(selected) == count:
            break
    if len(selected) != count:
        raise ValueError("unable to fill frozen subset")
    return selected


def resampled_weights(source_degrees: list[int], count: int) -> list[int]:
    ordered = sorted(source_degrees)
    if count == 1:
        return [ordered[len(ordered) // 2]]
    return [
        ordered[round(index * (len(ordered) - 1) / (count - 1))]
        for index in range(count)
    ]


def scaled_degrees(weights: list[int], total: int, cap: int) -> list[int]:
    if len(weights) > total or total > len(weights) * cap:
        raise ValueError("degree target is outside graphical capacity")
    degrees = [1] * len(weights)
    remaining = total - len(weights)
    while remaining:
        candidates = [index for index, value in enumerate(degrees) if value < cap]
        if not candidates:
            raise ValueError("degree scaling exhausted capacity")
        weight_sum = sum(weights[index] for index in candidates)
        shares = {
            index: remaining * weights[index] / weight_sum for index in candidates
        }
        added = 0
        for index in candidates:
            increment = min(cap - degrees[index], int(shares[index]))
            degrees[index] += increment
            added += increment
        remaining -= added
        if remaining:
            ranked = sorted(
                candidates,
                key=lambda index: (
                    -(shares[index] - int(shares[index])),
                    -weights[index],
                    index,
                ),
            )
            for index in ranked:
                if remaining == 0:
                    break
                if degrees[index] < cap:
                    degrees[index] += 1
                    remaining -= 1
    return sorted(degrees, reverse=True)


def gale_ryser(left: list[int], right: list[int]) -> bool:
    left = sorted(left, reverse=True)
    right = sorted(right, reverse=True)
    if sum(left) != sum(right):
        return False
    return all(
        sum(left[:k]) <= sum(min(k, degree) for degree in right)
        for k in range(1, len(left) + 1)
    )


def repair_graphical(left: list[int], right: list[int]) -> tuple[list[int], list[int]]:
    original_left = sorted(left, reverse=True)
    original_right = sorted(right, reverse=True)
    left = sorted(left, reverse=True)
    right = sorted(right, reverse=True)
    for _ in range(10000):
        if gale_ryser(left, right):
            histogram_l1 = sum(
                abs(before - after)
                for before, after in zip(original_left, left, strict=True)
            ) + sum(
                abs(before - after)
                for before, after in zip(original_right, right, strict=True)
            )
            if histogram_l1 > 0.05 * (sum(left) + sum(right)):
                raise ValueError(
                    "Gale-Ryser repair exceeds the 5% degree-histogram L1 limit"
                )
            return left, right
        source = next((i for i, value in enumerate(left) if value > 1), None)
        target = next(
            (i for i in range(len(left) - 1, -1, -1) if left[i] < len(right)),
            None,
        )
        if source is None or target is None or source == target:
            source = next((i for i, value in enumerate(right) if value > 1), None)
            target = next(
                (i for i in range(len(right) - 1, -1, -1) if right[i] < len(left)),
                None,
            )
            if source is None or target is None or source == target:
                break
            right[source] -= 1
            right[target] += 1
            right.sort(reverse=True)
        else:
            left[source] -= 1
            left[target] += 1
            left.sort(reverse=True)
    raise ValueError("unable to repair degree sequences to Gale-Ryser feasibility")


def havel_hakimi(left: list[int], right: list[int], seed: str) -> list[tuple[int, int]]:
    remaining = list(right)
    edges: list[tuple[int, int]] = []
    left_order = sorted(
        range(len(left)),
        key=lambda index: (-left[index], keyed_digest(seed, "left", index)),
    )
    for u_index in left_order:
        candidates = sorted(
            (index for index, degree in enumerate(remaining) if degree > 0),
            key=lambda index: (
                -remaining[index],
                keyed_digest(seed, "right", u_index, index),
            ),
        )
        if len(candidates) < left[u_index]:
            raise ValueError("Havel-Hakimi construction exhausted right vertices")
        for v_index in candidates[: left[u_index]]:
            edges.append((u_index, v_index))
            remaining[v_index] -= 1
    if any(remaining):
        raise ValueError("Havel-Hakimi construction left residual degree")
    return edges


def synthetic_mask(seed: str, side: str, index: int, used: set[int]) -> int:
    counter = 0
    while True:
        digest = hashlib.sha256(f"{seed}\0{side}\0{index}\0{counter}".encode()).digest()
        value = 1 + int.from_bytes(digest[:4], "big") % ((1 << 32) - 1)
        if value not in used:
            used.add(value)
            return value
        counter += 1


def synthetic_queries(rows: list[Query], count: int, seed: str) -> list[Query]:
    u_degree = Counter(query.u for query in rows)
    v_degree = Counter(query.v for query in rows)
    edge_count = len(rows)
    unique_u = min(
        count,
        max(min(8, count), round(count * len(u_degree) / edge_count)),
    )
    unique_v = min(
        count,
        max(min(8, count), round(count * len(v_degree) / edge_count)),
    )
    left_target = scaled_degrees(
        resampled_weights(list(u_degree.values()), unique_u), count, unique_v
    )
    right_target = scaled_degrees(
        resampled_weights(list(v_degree.values()), unique_v), count, unique_u
    )
    left, right = repair_graphical(left_target, right_target)
    edges = havel_hakimi(left, right, seed)
    if len(edges) != count or len(set(edges)) != count:
        raise ValueError("synthetic graph does not contain exactly Q unique edges")

    used_u: set[int] = set()
    used_v: set[int] = set()
    u_masks = [synthetic_mask(seed, "u", index, used_u) for index in range(unique_u)]
    v_masks = [synthetic_mask(seed, "v", index, used_v) for index in range(unique_v)]
    queries = [
        Query(row_id=index, r=rows[0].r, u=u_masks[u], v=v_masks[v])
        for index, (u, v) in enumerate(edges, start=1)
    ]
    return sorted(
        queries,
        key=lambda query: keyed_digest(
            seed, "synthetic-order", query.row_id, query.u, query.v
        ),
    )


def degree_summary(rows: list[Query], side: str) -> tuple[dict[str, int], int, float, int]:
    degrees = Counter(getattr(query, side) for query in rows)
    values = sorted(degrees.values())
    histogram = Counter(values)
    p95 = values[max(0, math.ceil(0.95 * len(values)) - 1)]
    return (
        {str(key): histogram[key] for key in sorted(histogram)},
        max(values),
        statistics.median(values),
        p95,
    )


def semantic_sha256(rows: list[Query]) -> str:
    payload = "".join(
        f"{query.row_id},{query.r},0x{query.u:08x},0x{query.v:08x}\n"
        for query in sorted(rows, key=lambda row: (row.r, row.u, row.v, row.row_id))
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def generator_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def write_queries(path: Path, rows: list[Query]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["row_id", "r", "u", "v"])
        for query in rows:
            writer.writerow(
                [query.row_id, query.r, f"0x{query.u:08x}", f"0x{query.v:08x}"]
            )


def main() -> None:
    args = parse_args()
    try:
        if args.count <= 0:
            raise ValueError("--count must be positive")
        validate_ru_source(args.ru_source, args.r)
        source_rows = load_queries(args.source, args.r)
        family_seed = hashlib.sha256(
            (
                args.family.upper()
                + "-v1\0"
                + source_sha256(args.source, args.ru_source)
                + "\0"
                + args.seed
                + "\0"
                + str(args.r)
                + "\0"
                + str(args.count)
                + "\0"
                + args.profile
            ).encode()
        ).hexdigest()

        if args.family == "uniform":
            rows = uniform_subset(source_rows, args.count, family_seed)
            family_name = "UNIFORM_FROZEN"
            synthetic = False
        elif args.family == "frozen-subset":
            rows = frozen_subset(source_rows, args.count, family_seed, args.profile)
            family_name = "FROZEN_SUBSET"
            synthetic = False
        else:
            rows = synthetic_queries(source_rows, args.count, family_seed)
            family_name = "SYNTHETIC_FROZEN_SHAPED"
            synthetic = True

        if len({(query.r, query.u, query.v) for query in rows}) != len(rows):
            raise ValueError("query artifact contains duplicate edges")
        write_queries(args.out, rows)

        u_hist, u_max, u_median, u_p95 = degree_summary(rows, "u")
        v_hist, v_max, v_median, v_p95 = degree_summary(rows, "v")
        metadata = {
            "family": family_name,
            "profile": args.profile,
            "seed": args.seed,
            "source_sha256": source_sha256(args.source, args.ru_source),
            "generator_commit": generator_commit(),
            "Q": len(rows),
            "unique_u": len({query.u for query in rows}),
            "unique_v": len({query.v for query in rows}),
            "u_degree_histogram": u_hist,
            "v_degree_histogram": v_hist,
            "u_degree_max": u_max,
            "u_degree_median": u_median,
            "u_degree_p95": u_p95,
            "v_degree_max": v_max,
            "v_degree_median": v_median,
            "v_degree_p95": v_p95,
            "query_file_sha256": sha256_file(args.out),
            "semantic_query_sha256": semantic_sha256(rows),
            "synthetic": synthetic,
        }
        args.metadata_out.parent.mkdir(parents=True, exist_ok=True)
        args.metadata_out.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        if args.out.exists():
            args.out.unlink()
        if args.metadata_out.exists():
            args.metadata_out.unlink()
        raise SystemExit(f"error: {exc}") from exc

    print(f"query_rows={len(rows)}")
    print(f"query_sha256={metadata['query_file_sha256']}")
    print(f"semantic_query_sha256={metadata['semantic_query_sha256']}")
    print(f"metadata={args.metadata_out}")


if __name__ == "__main__":
    main()
