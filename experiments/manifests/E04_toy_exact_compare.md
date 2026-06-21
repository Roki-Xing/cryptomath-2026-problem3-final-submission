# Experiment Manifest

- Experiment ID: E04-toy-exact-compare-20260531
- Branch: main
- Commit before run: c5e3b248f6f49138f8b0a310f1b459931581a40b
- Date: 2026-05-31T18:55:06+08:00
- Machine: local (WSL)
- Commands:
  - `python3 experiments/toy_exact_compare.py --n-nibbles 2 --rounds 1 2 3 --out experiments/toy/toy_exact_compare_2n.csv`
  - `python3 experiments/toy_exact_compare.py --n-nibbles 4 --rounds 1 2 --sample-pairs 10000 --out experiments/toy/toy_exact_compare_4n.csv`
- Output files:
  - `experiments/toy/toy_exact_compare_2n.csv`
  - `experiments/toy/toy_exact_compare_4n.csv`
  - `experiments/logs/E04_toy_2n.log`
  - `experiments/logs/E04_toy_4n.log`

## Summary

- 2n:
  - rows_total=196608
  - mismatches=0
  - max_abs_error=0
- 4n:
  - rows_total=20000
  - mismatches=0
  - max_abs_error=0

- Decision: keep

## Notes

- The toy cipher reuses the same 4-bit S-box but uses reduced-size SR/MC variants (2-nibble / 4-nibble) to exercise the same "S-box correlation + linear mask propagation via (L^T)^-1" logic.
- The DP path is full (no truncation): all S-box correlation branches are included in the toy DP.

