#!/usr/bin/env python3
"""Compute the 4-bit S-box linear approximation table (LAT) spectrum.

This is a small helper for E06 (LAT-guided r=3 active-2 mining). It outputs every nonzero entry of the S-box
correlation table in a machine-readable CSV and prints per-input-mask summary stats.
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path


SBOX = [
    0xC,
    0x6,
    0x9,
    0x0,
    0x1,
    0xA,
    0x2,
    0xB,
    0x3,
    0x8,
    0x5,
    0xD,
    0x4,
    0xE,
    0x7,
    0xF,
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default="experiments/new_sweeps/r3_active2_lat/lat_spectrum.csv")
    return p.parse_args()


def parity4(x: int) -> int:
    return (x & 0xF).bit_count() & 1


def corr_num(out_mask: int, in_mask: int) -> int:
    s = 0
    for x in range(16):
        bit = parity4(in_mask & x) ^ parity4(out_mask & SBOX[x])
        s += -1 if bit else 1
    return s


@dataclass(frozen=True)
class Entry:
    in_mask: int
    out_mask: int
    num: int

    @property
    def value(self) -> float:
        return self.num / 16.0


def main() -> int:
    args = parse_args()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    entries: list[Entry] = []
    for in_mask in range(16):
        for out_mask in range(16):
            n = corr_num(out_mask, in_mask)
            if n == 0:
                continue
            entries.append(Entry(in_mask=in_mask, out_mask=out_mask, num=n))

    # Write full nonzero table.
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["in_mask", "out_mask", "numerator", "value", "abs_value", "log2_abs"])
        for e in sorted(entries, key=lambda t: (t.in_mask, -abs(t.num), t.out_mask)):
            abs_val = abs(e.value)
            log2_abs = math.log2(abs_val) if abs_val != 0 else float("-inf")
            w.writerow([f"0x{e.in_mask:x}", f"0x{e.out_mask:x}", e.num, f"{e.value:.8g}", f"{abs_val:.8g}", f"{log2_abs:.8g}"])

    # Print per-input summary.
    by_in: dict[int, list[Entry]] = {i: [] for i in range(16)}
    for e in entries:
        by_in[e.in_mask].append(e)

    print(f"out={out_path}")
    for in_mask in range(16):
        lst = by_in[in_mask]
        nz = len(lst)
        best = max((abs(e.num) for e in lst), default=0)
        best_outs = sorted([e.out_mask for e in lst if abs(e.num) == best])
        print(f"in=0x{in_mask:x} nonzero={nz} best_abs_num={best} best_out={','.join(f'0x{o:x}' for o in best_outs)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

