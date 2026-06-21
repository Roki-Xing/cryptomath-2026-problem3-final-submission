#!/usr/bin/env python3
"""Generate a LAT-guided u-mask list for E06 (r=3 active-2 mining).

This script generates low-active 32-bit input masks u with exactly `--active` nonzero nibbles, where each active
nibble is chosen from a small LAT-motivated set (default {0x2,0x4,0x6}). The output is a plain-text list of masks
that can be consumed by `candidate_miner_approx --u-list`.
"""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--active", type=int, default=2, choices=[1, 2, 3, 4])
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--values", default="2,4,6", help="Comma-separated nibble values (hex digits without 0x).")
    p.add_argument("--out", default="experiments/new_sweeps/r3_active2_lat/r3_active2_lat_0500.txt")
    return p.parse_args()


def set_nibble(x: int, pos: int, val: int) -> int:
    shift = 28 - 4 * pos
    x &= ~(0xF << shift)
    x |= (val & 0xF) << shift
    return x


def main() -> int:
    args = parse_args()
    vals = [int(v.strip(), 16) for v in args.values.split(",") if v.strip()]
    if not vals:
        raise SystemExit("--values must be non-empty")
    if any(v <= 0 or v >= 16 for v in vals):
        raise SystemExit("--values must be nibble values in [1..15]")

    masks: list[int] = []
    positions = list(range(8))
    for pos_combo in itertools.combinations(positions, args.active):
        for val_combo in itertools.product(vals, repeat=args.active):
            u = 0
            for p, v in zip(pos_combo, val_combo):
                u = set_nibble(u, p, v)
            if u != 0:
                masks.append(u)

    masks = sorted(set(masks))
    out = masks[: args.limit]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# LAT-guided u list for candidate_miner_approx --u-list",
        f"# active={args.active} values={args.values} total_generated={len(masks)} limit={args.limit}",
        *[f"0x{u:08x}" for u in out],
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"out={out_path}")
    print(f"generated={len(masks)} written={len(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

