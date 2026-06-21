#!/usr/bin/env python3
"""Toy reduced-domain exact compare.

This is a correctness-focused experiment intended to validate the core way-2 math on a
small state size:

- exact (way-1): full enumeration over the toy domain 2^(4*n_nibbles)
- sparse DP (way-2): full, no-truncation correlation propagation via
  "S-box correlations + (L^T)^-1 mask propagation" (same principle as the main estimator)

For n_nibbles=2 we can check every (u,v) pair for the requested rounds.
For n_nibbles=4 we compare a sampled set of (u,v) pairs, but compute DP in blocks by
reusing a full DP vector per selected u.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SBOX: list[int] = [
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-nibbles", type=int, required=True, choices=[2, 4])
    parser.add_argument("--rounds", type=int, nargs="+", required=True)
    parser.add_argument("--sample-pairs", type=int, default=0, help="Only used for n-nibbles=4.")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--v-per-u", type=int, default=1000, help="Sampling block size for n-nibbles=4.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--tolerance", type=float, default=1e-15)
    return parser.parse_args()


def domain_size(n_nibbles: int) -> int:
    return 1 << (4 * n_nibbles)


def mask_space_size(n_nibbles: int) -> int:
    return 16**n_nibbles


def hex_mask(x: int, n_nibbles: int) -> str:
    return f"0x{x:0{n_nibbles}x}"


def get_nibble(x: int, pos: int, n_nibbles: int) -> int:
    shift = 4 * (n_nibbles - 1 - pos)
    return (x >> shift) & 0xF


def set_nibble(x: int, pos: int, n_nibbles: int, val: int) -> int:
    shift = 4 * (n_nibbles - 1 - pos)
    x &= ~(0xF << shift)
    x |= (val & 0xF) << shift
    return x


def unpack_nibbles(x: int, n_nibbles: int) -> list[int]:
    return [get_nibble(x, i, n_nibbles) for i in range(n_nibbles)]


def pack_nibbles(a: list[int], n_nibbles: int) -> int:
    x = 0
    for i, v in enumerate(a):
        x = set_nibble(x, i, n_nibbles, v)
    return x


def parity(x: int) -> int:
    return x.bit_count() & 1


def dot(a: int, b: int) -> int:
    return parity(a & b)


def sr_apply_state(x: int, n_nibbles: int) -> int:
    a = unpack_nibbles(x, n_nibbles)
    if n_nibbles == 2:
        return pack_nibbles([a[1], a[0]], n_nibbles)
    if n_nibbles == 4:
        # Small involutive permutation to exercise SR transpose/inverse logic.
        # Swaps the odd positions (1 <-> 3), keeps (0,2) fixed.
        return pack_nibbles([a[0], a[3], a[2], a[1]], n_nibbles)
    raise ValueError(f"unsupported n_nibbles: {n_nibbles}")


def mc_apply_state(x: int, n_nibbles: int) -> int:
    a = unpack_nibbles(x, n_nibbles)
    if n_nibbles == 2:
        # Invertible 2x2 mixing: [a0^a1, a0]
        return pack_nibbles([a[0] ^ a[1], a[0]], n_nibbles)
    if n_nibbles == 4:
        # Use the 4-nibble block from the full 8-nibble MC.
        return pack_nibbles(
            [
                a[0] ^ a[2] ^ a[3],
                a[0],
                a[1] ^ a[2],
                a[0] ^ a[2],
            ],
            n_nibbles,
        )
    raise ValueError(f"unsupported n_nibbles: {n_nibbles}")


def round_apply_state(x: int, n_nibbles: int) -> int:
    a = unpack_nibbles(x, n_nibbles)
    for i in range(n_nibbles):
        a[i] = SBOX[a[i]]
    return mc_apply_state(sr_apply_state(pack_nibbles(a, n_nibbles), n_nibbles), n_nibbles)


def permute(x: int, rounds: int, n_nibbles: int) -> int:
    y = x
    for _ in range(rounds):
        y = round_apply_state(y, n_nibbles)
    return y


def sr_transpose_mask(v: int, n_nibbles: int) -> int:
    # SR is a permutation matrix. For a permutation, transpose == inverse.
    # Our SR definitions are involutions, so transpose has the same mapping.
    return sr_apply_state(v, n_nibbles)


def sr_inv_transpose_mask(u: int, n_nibbles: int) -> int:
    # (SR^T)^-1 == SR for a permutation.
    return sr_apply_state(u, n_nibbles)


def mc_transpose_mask(v: int, n_nibbles: int) -> int:
    a = unpack_nibbles(v, n_nibbles)
    if n_nibbles == 2:
        # MC2 is symmetric at the bit-matrix level for this toy, so transpose==self.
        return pack_nibbles([a[0] ^ a[1], a[0]], n_nibbles)
    if n_nibbles == 4:
        return pack_nibbles(
            [
                a[0] ^ a[1] ^ a[3],
                a[2],
                a[0] ^ a[2] ^ a[3],
                a[0],
            ],
            n_nibbles,
        )
    raise ValueError(f"unsupported n_nibbles: {n_nibbles}")


def mc_inv_transpose_mask(u: int, n_nibbles: int) -> int:
    a = unpack_nibbles(u, n_nibbles)
    if n_nibbles == 2:
        # Inverse of MC2 (and thus (MC2^T)^-1): x0=y1, x1=y0^y1
        return pack_nibbles([a[1], a[0] ^ a[1]], n_nibbles)
    if n_nibbles == 4:
        # (MC^T)^-1 for the 4-nibble block, matching the full implementation structure.
        return pack_nibbles(
            [
                a[3],
                a[0] ^ a[1] ^ a[2],
                a[1],
                a[1] ^ a[2] ^ a[3],
            ],
            n_nibbles,
        )
    raise ValueError(f"unsupported n_nibbles: {n_nibbles}")


def round_linear_inv_transpose_after_sc(after_sc: int, n_nibbles: int) -> int:
    return mc_inv_transpose_mask(sr_inv_transpose_mask(after_sc, n_nibbles), n_nibbles)


def build_sbox_corr_num() -> list[list[int]]:
    corr: list[list[int]] = [[0 for _ in range(16)] for _ in range(16)]  # [out][in]
    for out_mask in range(16):
        for in_mask in range(16):
            s = 0
            for x in range(16):
                bit = parity(in_mask & x) ^ parity(out_mask & SBOX[x])
                s += -1 if bit else 1
            corr[out_mask][in_mask] = s
    return corr


def build_sbox_corr_matrix() -> list[list[float]]:
    num = build_sbox_corr_num()
    return [[n / 16.0 for n in row] for row in num]


def apply_axis(mat: list[list[float]], vec: list[float], n_nibbles: int, axis: int) -> list[float]:
    """Apply a 16x16 matrix along one base-16 digit axis of a length-16^n vector."""
    size = 16**n_nibbles
    if len(vec) != size:
        raise ValueError("vector length does not match n_nibbles")

    weight = 16 ** (n_nibbles - axis - 1)
    prefix_count = 16**axis
    stride = 16 * weight

    out = [0.0] * size
    for prefix in range(prefix_count):
        base = prefix * stride
        for suffix in range(weight):
            in_vals = [vec[base + d * weight + suffix] for d in range(16)]
            for out_d in range(16):
                row = mat[out_d]
                acc = 0.0
                for in_d, v in enumerate(in_vals):
                    if v != 0.0:
                        acc += row[in_d] * v
                out[base + out_d * weight + suffix] = acc
    return out


def apply_s_layer_vec(mat: list[list[float]], vec: list[float], n_nibbles: int) -> list[float]:
    cur = vec
    for axis in range(n_nibbles):
        cur = apply_axis(mat, cur, n_nibbles, axis)
    return cur


def build_inv_transpose_map(n_nibbles: int) -> list[int]:
    size = 16**n_nibbles
    out = [0] * size
    for w in range(size):
        out[w] = round_linear_inv_transpose_after_sc(w, n_nibbles)
    if len(set(out)) != size:
        raise RuntimeError("linear inv-transpose map is not a permutation")
    return out


def build_bitsets_from_values(values: Iterable[int], n_bits: int, n_items: int) -> list[int]:
    """Return bitset[j] where bit i is values[i]'s j-th bit."""
    bytes_len = (n_items + 7) // 8
    out: list[int] = []
    vals = list(values)
    if len(vals) != n_items:
        raise ValueError("values length mismatch")
    for bit in range(n_bits):
        buf = bytearray(bytes_len)
        for i, v in enumerate(vals):
            if (v >> bit) & 1:
                buf[i >> 3] |= 1 << (i & 7)
        out.append(int.from_bytes(buf, "little"))
    return out


def parity_bitset(mask: int, bitsets_by_bit: list[int]) -> int:
    bs = 0
    m = mask
    while m:
        lsb = m & -m
        bit = lsb.bit_length() - 1
        bs ^= bitsets_by_bit[bit]
        m ^= lsb
    return bs


@dataclass(frozen=True)
class PairBlock:
    u: int
    vs: list[int]


def sample_blocks(*, size: int, sample_pairs: int, v_per_u: int, seed: int) -> list[PairBlock]:
    rng = random.Random(seed)
    if sample_pairs <= 0:
        raise ValueError("sample_pairs must be positive for sampling mode")
    blocks: list[PairBlock] = []

    remaining = sample_pairs
    u_count = max(1, (sample_pairs + v_per_u - 1) // v_per_u)
    us: list[int] = []
    seen_u: set[int] = set()
    while len(us) < u_count:
        u = rng.randrange(size)
        if u in seen_u:
            continue
        seen_u.add(u)
        us.append(u)

    for u in us:
        take = min(v_per_u, remaining)
        remaining -= take
        vs = [rng.randrange(size) for _ in range(take)]
        blocks.append(PairBlock(u=u, vs=vs))
        if remaining <= 0:
            break
    return blocks


def main() -> int:
    args = parse_args()
    n = args.n_nibbles
    rounds_list = sorted(set(args.rounds))
    max_round = max(rounds_list)
    size = mask_space_size(n)
    dom = domain_size(n)
    n_bits = 4 * n

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[toy] n_nibbles={n} mask_space={size} domain={dom} rounds={rounds_list}")

    # Precompute DP components.
    s_mat = build_sbox_corr_matrix()
    inv_map = build_inv_transpose_map(n)

    # Exact (way-1) bitset basis for x.
    x_vals = list(range(dom))
    x_bitsets = build_bitsets_from_values(x_vals, n_bits, dom)
    cache_x: dict[int, int] = {}

    # Prepare pair blocks.
    blocks: list[PairBlock]
    if n == 2:
        blocks = [PairBlock(u=u, vs=list(range(size))) for u in range(size)]
        print(f"[toy] n=2 full compare: {size}*{size} pairs per round")
    else:
        if args.sample_pairs <= 0:
            raise SystemExit("--sample-pairs must be > 0 for n-nibbles=4")
        blocks = sample_blocks(size=size, sample_pairs=args.sample_pairs, v_per_u=args.v_per_u, seed=args.seed)
        total_pairs = sum(len(b.vs) for b in blocks)
        print(f"[toy] n=4 sampled compare: blocks={len(blocks)} pairs={total_pairs} (v_per_u={args.v_per_u})")

    # Main loop per rounds: build y bitsets for exact, then run DP blocks once per u.
    rows_total = 0
    mismatches = 0
    sign_failures = 0
    transpose_like = 0
    max_abs_err = 0.0

    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "n_nibbles",
                "rounds",
                "u",
                "v",
                "exact",
                "dp",
                "abs_err",
                "rel_err",
                "match",
                "sign_flip_suspect",
                "transpose_like_suspect",
            ]
        )

        for rounds in rounds_list:
            print(f"[toy] building exact bitsets for rounds={rounds} ...")
            y_vals = [permute(x, rounds, n) for x in range(dom)]
            y_bitsets = build_bitsets_from_values(y_vals, n_bits, dom)
            cache_y: dict[int, int] = {}

            for block in blocks:
                # Precompute parity bitset for this u.
                if block.u not in cache_x:
                    cache_x[block.u] = parity_bitset(block.u, x_bitsets)
                par_u = cache_x[block.u]

                # DP: compute full f vector once per u, up to the requested rounds.
                f = [0.0] * size
                f[block.u] = 1.0
                for r in range(1, rounds + 1):
                    g = apply_s_layer_vec(s_mat, f, n)
                    f2 = [0.0] * size
                    for w, val in enumerate(g):
                        f2[inv_map[w]] = val
                    f = f2

                for v in block.vs:
                    if v not in cache_y:
                        cache_y[v] = parity_bitset(v, y_bitsets)
                    par_v = cache_y[v]
                    diff = (par_u ^ par_v).bit_count()
                    exact = (dom - 2 * diff) / dom

                    dp = f[v]
                    abs_err = abs(dp - exact)
                    rel_err = abs_err / max(1e-300, abs(exact))
                    match = abs_err <= args.tolerance

                    rows_total += 1
                    if not match:
                        mismatches += 1
                        if abs(dp + exact) <= args.tolerance:
                            sign_failures += 1

                        # Very rough "transpose-like" heuristic: does dp match exact(v,u)?
                        # (This can only meaningfully trigger in the full n=2 sweep; for n=4
                        # it is still computed but may be rare.)
                        if v not in cache_x:
                            cache_x[v] = parity_bitset(v, x_bitsets)
                        par_u_swapped = cache_x[v]
                        if block.u not in cache_y:
                            cache_y[block.u] = parity_bitset(block.u, y_bitsets)
                        par_v_swapped = cache_y[block.u]
                        diff_swapped = (par_u_swapped ^ par_v_swapped).bit_count()
                        exact_swapped = (dom - 2 * diff_swapped) / dom
                        if abs(dp - exact_swapped) <= args.tolerance:
                            transpose_like += 1

                    max_abs_err = max(max_abs_err, abs_err)
                    writer.writerow(
                        [
                            n,
                            rounds,
                            hex_mask(block.u, n),
                            hex_mask(v, n),
                            f"{exact:.20g}",
                            f"{dp:.20g}",
                            f"{abs_err:.6e}",
                            f"{rel_err:.6e}",
                            "1" if match else "0",
                            "1" if (not match and abs(dp + exact) <= args.tolerance) else "0",
                            "1" if (not match and abs(dp - exact_swapped) <= args.tolerance) else "0",
                        ]
                    )

    print("[toy] done")
    print(f"[toy] rows_total={rows_total}")
    print(f"[toy] mismatches={mismatches}")
    print(f"[toy] max_abs_error={max_abs_err:.6e}")
    print(f"[toy] sign_flip_suspects={sign_failures}")
    print(f"[toy] transpose_like_suspects={transpose_like}")

    if mismatches != 0:
        raise SystemExit("toy exact compare failed: mismatches detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

