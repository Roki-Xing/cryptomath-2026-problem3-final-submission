# PR7 pre-P0 benchmark snapshot

## Decision

`NO_GO_PENDING`

This file describes the original 27-row smoke artifact and is retained only as
historical evidence. `results.csv` predates the manifest-bound P0 provenance
changes and does not satisfy `way1-benchmark-results-v2`. It is not a Stage-A
result and cannot support a Strategy-B decision.

## Executed scope

- source: `experiments/frozen/final_queries.csv`;
- rounds: \(r=1,2,3\);
- query count: \(Q=8\) per round;
- plaintext interval: \([0,2^{16})\);
- threads: 2;
- repeats: 3 per implementation;
- implementations: `current`, `grouped_u`, `grouped_uv`;
- total result rows: 27;
- framework commit:
  `a8d2065f4621aac48943a70afff5496775055097`.

All runs exited with status 0. For each round, every implementation and repeat
produced identical integer numerators and denominators.

## Median wall time

| Round | current | grouped_u | grouped_uv |
| ---: | ---: | ---: | ---: |
| 1 | 0.003739985 s | 0.003695108 s | 0.005329281 s |
| 2 | 0.004914682 s | 0.005350033 s | 0.006912353 s |
| 3 | 0.006686928 s | 0.006600003 s | 0.009168022 s |

The \(Q=8\) samples each have eight unique input masks and eight unique output
masks. They therefore do not exercise the reuse pattern that grouped variants
target, and they are not suitable for choosing a winning implementation.

## Artifacts

- `results.csv`: raw benchmark metrics and provenance;
- `forecast.json`: explicitly provisional proportional projections;
- `benchmark_schema.json`: result-field contract;
- `PROTOCOL.md`: staged execution and safety gates;
- `SHA256SUMS.txt`: hashes for the files in this directory.

`forecast.json` must not be cited as a confirmed runtime estimate. Its decision
remains `NO_GO_PENDING`, and its extrapolation warning is part of the artifact.

## Current protocol authority

The current P0 contract and Stage-A gates are defined by `PROTOCOL.md` and
`benchmark_schema.json`. No full-domain run is authorized before the complete
Stage-A protocol reports `STAGE_A_PASS`.
