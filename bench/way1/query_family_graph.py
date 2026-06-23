"""Deterministic bipartite degree-sequence helpers for query generation."""

from __future__ import annotations

import bisect
import hashlib
import heapq


def keyed_digest(seed: str, *parts: object) -> bytes:
    payload = seed + "".join(f"\0{part}" for part in parts)
    return hashlib.sha256(payload.encode()).digest()


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
    right = sorted(right)
    if sum(left) != sum(right):
        return False
    right_prefix = [0]
    for degree in right:
        right_prefix.append(right_prefix[-1] + degree)
    left_prefix = 0
    for k, degree in enumerate(left, start=1):
        left_prefix += degree
        split = bisect.bisect_left(right, k)
        conjugate_prefix = right_prefix[split] + (len(right) - split) * k
        if left_prefix > conjugate_prefix:
            return False
    return True


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
    heap = [
        (-degree, keyed_digest(seed, "right", index), index)
        for index, degree in enumerate(right)
        if degree > 0
    ]
    heapq.heapify(heap)
    edges: list[tuple[int, int]] = []
    left_order = sorted(
        range(len(left)),
        key=lambda index: (-left[index], keyed_digest(seed, "left", index)),
    )
    for u_index in left_order:
        if len(heap) < left[u_index]:
            raise ValueError("Havel-Hakimi construction exhausted right vertices")
        selected: list[tuple[int, bytes, int]] = []
        for _ in range(left[u_index]):
            negative_degree, tie_break, v_index = heapq.heappop(heap)
            edges.append((u_index, v_index))
            selected.append((negative_degree + 1, tie_break, v_index))
        for entry in selected:
            if entry[0] < 0:
                heapq.heappush(heap, entry)
    if heap:
        raise ValueError("Havel-Hakimi construction left residual degree")
    return edges
