# PR7 initial benchmark status

## Decision

`NO_GO_PENDING`

This is a framework and Stage-A smoke checkpoint, not the final PR7 Go/No-Go
decision. It does not satisfy the required Q/domain matrix, full-domain
cross-implementation comparisons, holdout prediction-error thresholds, or a
validated 95% prediction interval.

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

## Required next measurements

1. Complete the bounded Stage-A matrix for available frozen query counts and
   domain bits 16, 20, 24, and 28.
2. Add frozen-shaped cases with repeated \(u\) and repeated \(v\) before
   selecting a grouped implementation.
3. Run full-domain \(Q=8\) only after explicit resource approval, then progress
   to \(Q=64\) and \(Q=512\) conditionally.
4. Establish repeated-run variance, validated holdouts, resource budgets, and
   a real 95% prediction interval before changing the decision.
