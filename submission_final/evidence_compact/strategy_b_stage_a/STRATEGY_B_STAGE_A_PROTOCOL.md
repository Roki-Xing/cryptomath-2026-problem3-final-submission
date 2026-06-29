# Strategy-B Stage-A Protocol

## Scope

This document defines the bounded Strategy-B Stage-A validation scope for the
exact way-1 batch toolchain. Stage A verifies only small-domain correctness,
query-family construction, shard reduction, compiler/sanitizer behavior, and
provenance binding. It does not authorize Stage B, a full \(2^{32}\)
plaintext-domain run, a full 138338-query way-1 run, or any Strategy-B final
file generation.

The compact Stage-A authority is:

- `artifacts/strategy_b/stage_a/STAGE_A_SUMMARY.json`
- `artifacts/strategy_b/stage_a/MANIFEST.json`
- `artifacts/strategy_b/stage_a/SHA256SUMS.txt`

The underlying bounded evidence remains under `bench/way1/`.

## Frozen boundaries

The query generators may read only:

- `experiments/frozen/final_queries.csv`
- `experiments/frozen/final_ru.csv`

Generated query CSV files contain only:

- `row_id`
- `r`
- `u`
- `v`

They must not contain or derive runtime behavior from:

- `VT`
- `VE`
- score
- candidate rank or source
- way-1 output

Stage A must preserve the frozen submission baseline:

```text
submit_sha256 = 7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e
valid_count = 138338
total_score = 105843.622442471292742994
```

## Implementations under test

Stage A compares three exact way-1 batch implementations:

- `current`
- `grouped_u`
- `grouped_uv`

The bounded result requirement is exact numerator/denominator identity for the
same `(r,u,v)` query map, independent of implementation, thread count, and
query order.

## Stage matrix

### A0 repeated-structure regression

- `r = 1,2,3`
- `Q = 64,512`
- `domain_bits = 16`
- query families:
  - `uniform`
  - `frozen-subset`
  - `synthetic-frozen-shaped`
- variants:
  - `current`
  - `grouped_u`
  - `grouped_uv`
- threads:
  - `1`
  - default multithread count
- orders:
  - canonical
  - seeded shuffled

### A1 safe-domain matrix

- `(Q, domain_bits) = (8,22), (64,20), (512,17), (4096,14), (16384,12)`
- `r = 1,2,3`
- bounded families from the committed Stage-A evidence:
  - `uniform`
  - `frozen-subset`
  - `synthetic-frozen-shaped`
- variants:
  - `current`
  - `grouped_u`
  - `grouped_uv`
- correctness comparison is mandatory

### A2 shard matrix

- shard layouts:
  - `1`
  - `2` equal shards
  - `7` unequal shards
  - `16` unequal shards
- anchor families:
  - frozen-subset
  - synthetic-frozen-shaped
- reducer must reject intentional corruption cases

## Required gates

Stage-A pass requires all of the following:

- current, grouped-u, and grouped-uv numerators are identical;
- single-thread and multithread results are identical;
- canonical and shuffled orders are identical as maps;
- uniform, frozen-subset, and synthetic-frozen-shaped families pass;
- repeated-`u` and repeated-`v` query structures pass;
- shard reduction equals the single-process semantic result;
- reducer rejects overlap, gap, duplicate, missing, boundary, hash, mixed
  implementation, and denominator drift cases;
- GCC and Clang builds pass;
- UBSan, ASan, and TSan bounded-domain checks pass;
- `-O0` and `-O3` produce identical numerators on the bounded matrix;
- no timeout, OOM, nonzero exit, or signed overflow is observed;
- query, binary, source, command, and output hashes are recorded;
- the frozen submit SHA, valid count, and total score remain unchanged.

## Non-goals

Stage A explicitly does not authorize or claim any of the following:

- `stage_b_authorized = false`
- `full_2_32_run_started = false`
- `full_138338_way1_started = false`
- `new_way1_run_started = false`
- `strategy_b_final_file_generated = false`
- `submit_txt_modified = false`
- `vt_provenance_closed = false`

The only allowed post-Stage-A state is:

```text
STRATEGY_B_STAGE_A_REVIEW
```
