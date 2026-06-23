# PR7 Stage-A benchmark status

## Decision

`KEEP_DRAFT_NO_GO_PENDING`

Stage A0 and Stage A1 passed. A0 ran at commit
`1e4f62f5223445c0e27e53a065ebd2877429fd73`. This is not
`STAGE_A_PASS`: A2, sanitizer, compiler/optimization, and aggregate
artifact gates remain incomplete. Stage B and every full \(2^{32}\) run remain
prohibited.

## Stage A0 result

- query specifications: 18;
- generated query artifacts: 17;
- explicit unavailable case: `r=1,Q=512,frozen-subset`;
- run cases: 68;
- result rows: 204;
- variants: `current`, `grouped_u`, `grouped_uv`;
- threads: 1 and 8;
- orders: canonical and seeded shuffled;
- semantic mismatch count: 0;
- timeout/OOM/nonzero exit counts: 0;
- maximum observed wall time: 0.293089445 seconds;
- maximum observed peak RSS: 4096 KiB;
- elapsed orchestration time: 87.741985 seconds.

All query-key numerator/denominator maps matched across variants, thread
counts, and input orders. The three families were:

- seeded `UNIFORM_SYNTHETIC`, with `unique_u=unique_v=Q`;
- real `FROZEN_SUBSET`, preserving source row identity;
- explicit `SYNTHETIC_FROZEN_SHAPED`, preserving frozen-derived degree shape.

The submit SHA before and after A0 was:

```text
7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e
```

## A0 artifacts

- `stage_a0/MANIFEST.json`: environment, source hashes, query metadata, skips,
  run paths, result hashes, and summary;
- `stage_a0/SUMMARY.json`: machine-readable gate result;
- `stage_a0/queries/`: query CSV and degree-distribution metadata;
- `stage_a0/results/`: schema-v2 result CSV and runner logs;
- `stage_a0/artifacts/`: materialized order, raw outputs, time files, and
  sidecar manifests;
- `stage_a0/SHA256SUMS.txt`: independent hashes for every A0 artifact.

## Stage A1 result

- query specifications: 45;
- generated query artifacts: 42;
- explicit unavailable cases: 3;
- run cases: 50;
- result rows: 150;
- Q values: 8, 64, 512, 4096, 16384;
- domain bits: 22, 20, 17, 14, 12 respectively;
- canonical cases: 42;
- additional shuffled `Q=512` cases: 8;
- semantic mismatch count: 0;
- timeout/OOM/nonzero exit counts: 0;
- maximum observed wall time: 0.149288822 seconds;
- maximum observed peak RSS: 6656 KiB;
- elapsed orchestration time: 105.361217 seconds.

The A1 evidence is under `stage_a1/` with its own `MANIFEST.json`,
`SUMMARY.json`, queries, result/artifact directories, and `SHA256SUMS.txt`.

## Historical smoke

`results.csv` and `forecast.json` are the original 27-row pre-P0 smoke
snapshot. They do not satisfy `way1-benchmark-results-v2`, are not Stage-A
evidence, and must not be used as a runtime forecast or Strategy-B decision.

The current protocol authority is `PROTOCOL.md`; the result contract is
`benchmark_schema.json`.
