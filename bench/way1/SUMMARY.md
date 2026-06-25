# PR7 Stage-A benchmark status

## Decision

`STAGE_A_PASS`

Stage A0, Stage A1, Stage A2, and the complete toolchain matrix passed. The
machine-readable authority is `STAGE_A_SUMMARY.json`. This is a bounded
correctness, provenance, and implementation-consistency result only. It does
not authorize Stage B, a full \(2^{32}\) run, or a Strategy-B `GO` decision.

The closeout provenance is split into distinct, non-interchangeable fields:

- `stage_a_evidence_commit`:
  `4b26302e5aa0c60b66bf2c11f29b50e3bc88fb8e`, the Stage-A aggregate evidence
  commit;
- `stage_toolchain_source_head_commit`:
  `abefde8643701d4f83c43cd8a527b70d5a268f3b`, the branch source head used by
  the Stage-A toolchain CI run;
- `stage_toolchain_execution_commit`:
  `04fb504250796c1d13261f4cedec1e06bca17a3a`, a CI synthetic merge commit
  recorded by the toolchain artifact and not a branch source head;
- `integration_head_commit`:
  `5fbff142a72557060a45d490aaf4094dadaf8af1`, the pre-closeout integration
  evidence head attested by the final integration CI runs; this field is not
  the current closeout branch head;
- `ci_attested_commit`:
  `5fbff142a72557060a45d490aaf4094dadaf8af1`, the commit attested by the final
  push and pull-request CI artifacts;
- `final_push_ci_run_id`: `28032401682`;
- `final_pr_ci_run_id`: `28032406708`.

The machine-readable CI contract is duplicated in `CI_EVIDENCE.json`.

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

## Stage A2 result

- anchor cases: `r1/Q64/frozen`, `r2/Q512/frozen`,
  `r3/Q512/synthetic`;
- matrix cases: 31;
- raw shards: 172;
- layouts: 1, 2, 7, and 16 shards;
- implementations: `current`, `grouped_u`, `grouped_uv`;
- reducer corruption cases passed: 12;
- semantic mismatch count: 0;
- timeout/OOM/nonzero exit counts: 0;
- elapsed orchestration time: 6.887331 seconds.

The A2 evidence is under `stage_a2/`; every raw shard is bound to actual query,
program, and output hashes by a sidecar manifest before reduction.

## Toolchain result

The Stage-A toolchain artifact was produced by GitHub Actions pull-request run
[`28031330588`](https://github.com/Roki-Xing/cryptomath-2026-problem3-final-submission/actions/runs/28031330588)
from branch source head
`abefde8643701d4f83c43cd8a527b70d5a268f3b`. The committed toolchain manifest
records CI execution commit
`04fb504250796c1d13261f4cedec1e06bca17a3a`, which is a CI synthetic merge
commit and must not be described as the branch source head.

The final integration evidence is attested by push run
[`28032401682`](https://github.com/Roki-Xing/cryptomath-2026-problem3-final-submission/actions/runs/28032401682)
and pull-request run
[`28032406708`](https://github.com/Roki-Xing/cryptomath-2026-problem3-final-submission/actions/runs/28032406708),
both for pre-closeout integration evidence head
`5fbff142a72557060a45d490aaf4094dadaf8af1`.

The committed CI artifact under `stage_toolchain/` contains:

- 69 matrix cases and 12 semantic comparison groups;
- 18 UBSan cases at `Q=64`, 16-bit domains, threads 1/8;
- 9 ASan cases at `Q=64`, 14-bit domains, one thread;
- 6 TSan cases at `Q=64`, 12-bit domains, four threads;
- 36 GCC/Clang `-O0/-O3` cases at `Q=64`, 12-bit domains;
- zero semantic mismatches, sanitizer diagnostics, timeouts, OOMs, or nonzero
  exits;
- unchanged submit SHA before and after the complete matrix.

The CI artifact has its own `MANIFEST.json`, `SUMMARY.json`, compile logs,
exact result files, timing files, sanitizer stderr logs, and
`SHA256SUMS.txt`. Local WSL execution independently passed UBSan and ASan; its
TSan runtime could not reserve the shadow mapping, so the committed Ubuntu CI
artifact is the TSan authority.

## Stage-A gate closure

All 14 protocol gates are satisfied:

- exact numerator/denominator maps match across all three variants;
- single-thread, multi-thread, canonical, and shuffled results match;
- uniform, frozen-subset, and synthetic-frozen-shaped families pass,
  including repeated-\(u\) and repeated-\(v\) cases;
- all shard layouts reduce to the same semantic result and all 12 corruption
  cases are rejected;
- UBSan, ASan, TSan, GCC/Clang, and `-O0/-O3` comparisons pass;
- query, program, raw-output, semantic-output, stage, and repository hashes
  are recorded and independently checked;
- no timeout, OOM, abnormal exit, schema omission, or submit SHA change was
  observed.

## Historical smoke

`results.csv` and `forecast.json` are the original 27-row pre-P0 smoke
snapshot. They do not satisfy `way1-benchmark-results-v2`, are not Stage-A
evidence, and must not be used as a runtime forecast or Strategy-B decision.

The current protocol authority is `PROTOCOL.md`; the result contract is
`benchmark_schema.json`.

## Artifact retention

`ARTIFACT_RETENTION_PLAN.md` and `ARTIFACT_INDEX.json` classify the Stage-A
files without deleting raw evidence:

- `REQUIRED_SUMMARY`: `STAGE_A_SUMMARY.json`, `SUMMARY.md`, `PROTOCOL.md`,
  `benchmark_schema.json`, and the four per-stage `SUMMARY.json` files;
- `REQUIRED_MANIFEST`: `MANIFEST.json`, `CI_EVIDENCE.json`,
  `ARTIFACT_INDEX.json`, `ARTIFACT_RETENTION_PLAN.md`, top-level
  `SHA256SUMS.txt`, and per-stage manifest/hash files;
- `RAW_REPRODUCIBILITY_EVIDENCE`: stage-specific query/result/artifact trees
  and toolchain compile/result trees only;
- `CI_ONLY`: CI temporary output locations and the fixed GitHub Actions runs;
- `EXCLUDE_FROM_SUBMISSION_PACKAGE`: historical smoke files, temporary files,
  and Python bytecode caches.

The compact package boundary is implemented by the explicit allowlist in
`scripts/build_stage_a_compact_package.py`. Raw directories remain in the
repository, but allowlisted summary and manifest files are never dropped by
parent-directory overlap. The retention classification does not authorize
Stage B and does not change the frozen submit SHA.
