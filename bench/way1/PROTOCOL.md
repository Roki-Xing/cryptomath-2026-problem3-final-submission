# Exact way-1 batch benchmark protocol

## Status and scope

PR7 remains Draft with decision `KEEP_DRAFT_NO_GO_PENDING`. This benchmark
evaluates exact way-1 batch implementations. It does not generate submitted
`VT` fields, call the exact-dyadic route-shell backend, or modify `submit.txt`.
No Stage-B or full-domain run is authorized before the complete Stage-A gate
passes.

`bench/way1/results.csv`, `forecast.json`, and the original 27-row summary are
pre-P0 historical smoke artifacts. They do not satisfy
`way1-benchmark-results-v2` and must not be presented as Stage-A results.

## Frozen inputs and query families

The generator may read only:

- `experiments/frozen/final_queries.csv`;
- `experiments/frozen/final_ru.csv`.

It may use only `r,u,v`, source row identity, and derived degree statistics.
It must not read `VT`, `VE`, score, way-1 outputs, or candidate provenance.

Generate a real frozen subset:

```bash
python3 -X utf8 bench/way1/generate_query_family.py \
  --source experiments/frozen/final_queries.csv \
  --ru-source experiments/frozen/final_ru.csv \
  --family frozen-subset \
  --profile uv_core \
  --r 2 --count 64 --seed stage-a0-v1 \
  --out /tmp/pr7-r2-q64-frozen.csv \
  --metadata-out /tmp/pr7-r2-q64-frozen.json
```

Supported families are:

- `uniform`: deterministic SHA-ordered frozen rows;
- `frozen-subset`: real frozen edges with `uv_core` or `u_stratified` stars;
- `synthetic-frozen-shaped`: explicitly synthetic masks with frozen-derived
  bipartite degree shape.

Requests larger than a round's frozen set fail closed. In particular,
`r=1,Q=512,frozen-subset` is `SKIP_UNAVAILABLE`, not an implicit synthetic
case. Every query metadata artifact records the raw and semantic query hashes,
source hash, generator commit, family/profile/seed, cardinalities, and degree
histograms.

## Implementations

- `current`: input and output parity per query.
- `grouped_u`: input parity once per unique \(u\).
- `grouped_uv`: input parity once per unique \(u\) and output parity once per
  unique \(v\).

All variants evaluate `permute(x,r)` once per plaintext and must produce the
same exact signed integer numerator and denominator for each query key.

## Runner provenance and guards

The runner requires query family/profile/seed/order, timeout, RSS budget,
compiler identity/version/flags, CPU affinity, and the frozen `submit.txt`
SHA. It checks the submit SHA before and after every child run, kills the
entire child process group on timeout, and rejects cross-variant semantic
result differences.

Each child output embeds the actual query and executable SHA-256. The runner
also writes a `way1-shard-manifest-v1` sidecar containing:

- actual query file SHA-256;
- actual executable SHA-256;
- actual raw output SHA-256;
- half-open range;
- complete command;
- exit status.

Example bounded run:

```bash
python3 -X utf8 bench/way1/run_protocol.py \
  --queries /tmp/pr7-r2-q64-frozen.csv \
  --query-family frozen-subset \
  --query-profile uv_core \
  --seed stage-a0-v1 \
  --order canonical \
  --r 2 --domain-bits 16 \
  --threads 1 \
  --variants current,grouped_u,grouped_uv \
  --repeats 1 \
  --timeout-seconds 120 \
  --max-rss-kib 1048576 \
  --compiler-id gcc \
  --compiler-version "$(g++ --version | head -n 1)" \
  --compiler-flags="-O3 -std=c++17 -Wall -Wextra -pedantic -pthread" \
  --cpu-model "$(lscpu | sed -n 's/^Model name:[[:space:]]*//p')" \
  --ram-bytes "$(awk '/MemTotal/ {print $2 * 1024}' /proc/meminfo)" \
  --numa "$(lscpu | sed -n 's/^NUMA node(s):[[:space:]]*//p')-node" \
  --kernel "$(uname -r)" \
  --cpu-affinity unbound \
  --submit-sha256 7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e \
  --out /tmp/pr7-r2-q64-results.csv \
  --artifacts-dir /tmp/pr7-r2-q64-artifacts
```

## Manifest-bound shard reduction

The reducer accepts sidecar manifests, recomputes each raw shard hash, and
cross-checks implementation, query hash, program hash, range, row order, and
denominator before summing:

```bash
python3 -X utf8 bench/way1/reduce_shards.py \
  --expected-start 0 \
  --expected-end 65536 \
  --expected-query-sha256 "$QUERY_SHA" \
  --expected-program-sha256 "$PROGRAM_SHA" \
  --out /tmp/reduced.csv \
  /tmp/shards/part-*.manifest.json
```

The corruption suite rejects missing, duplicate, overlapping, and gapped
shards; range drift; query/program hash drift; denominator drift; row
replacement/reordering; implementation mixing; and raw-output tampering.

## Stage A0 matrix

Stage A0 is bounded to:

| Parameter | Values |
| --- | --- |
| `r` | 1, 2, 3 |
| `Q` | 64, 512 |
| domain bits | 16 |
| families | uniform, frozen-subset, synthetic-frozen-shaped |
| variants | current, grouped_u, grouped_uv |
| threads | 1, `T` |
| order | canonical, seeded shuffled |
| repeats | 1 |

Per-variant limits are 120 seconds for `Q=64`, 300 seconds for `Q=512`, and
1 GiB peak RSS. The matrix stops immediately on numerator/denominator
disagreement, thread/order disagreement, sanitizer failure, submit/hash drift,
timeout, OOM, or nonzero exit.

Stage A1, Stage A2, sanitizer matrices, optimization/compiler comparisons, and
artifact aggregation remain required before `STAGE_A_PASS`. A0 passing alone
does not authorize Stage B.

Run the complete A0 matrix only from a clean tracked worktree with the three
benchmark executables already built:

```bash
python3 -X utf8 bench/way1/run_stage_a0.py --threads 8
```

The orchestrator fails closed on any missing matrix point or semantic
difference and writes `MANIFEST.json`, `SUMMARY.json`, query/results/artifact
directories, and `SHA256SUMS.txt` under `bench/way1/stage_a0/`.

## CI and immutable submission

CI builds and tests with GCC and Clang. `make test` exercises all three
variants, thread/order invariance, manifest-bound reduction corruption cases,
and deterministic query-family generation. It checks the frozen submit SHA
before and after the suite.

The immutable submission requirements are:

```text
submit_sha256 = 7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e
valid_count = 138338
total_score = 105843.622442471292742994
```

## Decision rule

PR7 may report only `STAGE_A_PASS` or `STAGE_A_FAIL` after the complete
Stage-A protocol. Until then its status remains `KEEP_DRAFT_NO_GO_PENDING`.
It must not report Strategy-B `GO` or start a full \(2^{32}\) run.
