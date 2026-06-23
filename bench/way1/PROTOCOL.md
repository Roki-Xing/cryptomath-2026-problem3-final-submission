# Exact way-1 batch benchmark protocol

## Purpose

This benchmark determines whether full Strategy-B way-1 validation is feasible.
It does not generate submitted `VT` fields and does not modify `submit.txt`.

## Fixed constraints

- Query coordinates come only from
  `experiments/frozen/final_queries.csv`.
- Benchmark programs read `r,u,v`; they do not read frozen `VE`, score, or
  candidate-source fields.
- Signed integer numerator is authoritative. Decimal values are not benchmark
  outputs.
- No GPU or FWHT implementation is part of this PR.
- A full \(2^{32}\) run requires the explicit `--allow-full-domain` flag.
- Domains above \(2^{28}\) require the explicit `--allow-large-domain` flag.
- `submit.txt` is immutable.

The frozen `r=1` set contains only 288 rows. Therefore query counts above 288
cannot be represented by unique frozen `r=1` queries and must be reported as
unsupported rather than synthesized.

## Implementations

- `current`: computes input and output parity per query.
- `grouped_u`: computes input parity once per unique \(u\), while output parity
  remains per query.
- `grouped_uv`: computes input parity once per unique \(u\) and output parity
  once per unique \(v\).

All implementations evaluate `permute(x,r)` once per plaintext and produce the
same exact numerator for every query.

## Query generation

```bash
python3 -X utf8 bench/way1/generate_queries.py \
  --source experiments/frozen/final_queries.csv \
  --r 2 --count 64 --seed pr7-frozen-v1 \
  --out /tmp/pr7_r2_q64.csv
```

Selection is deterministic SHA-256 ordering over the fixed seed and source row
identity. Requests larger than the available frozen set fail closed.

## Stage A: bounded correctness and throughput

Start with \(2^{12}\), then use domain bits 16, 20, 24, and 28 only after the
smaller run passes. Run each round separately.

```bash
python3 -X utf8 bench/way1/run_protocol.py \
  --queries /tmp/pr7_r2_q64.csv \
  --r 2 --domain-bits 16 --threads 8 --repeats 3 \
  --out /tmp/pr7_r2_q64_n16_results.csv \
  --artifacts-dir /tmp/pr7_r2_q64_n16_artifacts
```

The runner rejects numerator disagreement across implementations or repeats.
It records wall time, CPU time, peak RSS, logical query updates, parity counts,
program/input/output hashes, and exit status.

## Sharding and reduction

Each shard covers a half-open interval and embeds its query SHA-256. Reduce
only shards from the same implementation and query file:

```bash
python3 -X utf8 bench/way1/reduce_shards.py \
  --expected-start 0 --expected-end 65536 \
  --out /tmp/reduced.csv \
  /tmp/shard_*.csv
```

The reducer rejects empty ranges, gaps, overlaps, duplicates, query hash
changes, implementation changes, row-order changes, and denominator mismatch.

## Stage B/C full-domain progression

Full-domain work is manual and gated:

1. start with \(Q=8\) for each \(r\);
2. compare all implementations and 2/4/8-shard grouped winners;
3. require repeated numerator equality and acceptable variance;
4. continue to \(Q=64\) and then \(Q=512\) only if resources permit;
5. do not automatically start full-domain \(Q\ge4096\).

No full-domain command is part of `make test` or CI.

## Forecast semantics

```bash
python3 -X utf8 bench/way1/build_forecast.py \
  --results bench/way1/results.csv \
  --out bench/way1/forecast.json
```

Until the prescribed matrix, full-domain comparisons, repeated-run variance,
and holdout thresholds are complete, the only valid decision is
`NO_GO_PENDING`. Initial proportional projections are planning signals, not
confirmed completion-time claims and not a validated 95% prediction interval.

## Final GO requirements

The final PR7 gate requires all Stage A-D correctness and forecasting
conditions from the hardening protocol, including full-domain cross-variant
numerator equality, shard recovery testing, validated holdout errors, a 95%
prediction interval, and explicit resource budgets. Only then may PR7 report
`GO`; otherwise it reports `NO_GO`.
