# Exact dyadic route-shell implementation

## Scope

`estimator_exact` implements the frozen specification in
`docs/EXACT_DYADIC_SPEC.md`. It is independent of `BeamSearch`, priority
queues, top-K selection, tuple caps, beam caps, floating-point aggregation,
and candidate search. It does not modify or generate `submit.txt`.

The implementation supports frozen rounds `r=1,2,3` with two integer
backends:

- `boost::multiprecision::cpp_int`, the authoritative backend;
- checked signed `__int128`, a fast path whose result is converted to
  `cpp_int` and tested against the authoritative backend.

## Complete Cartesian product

`include/exact_cartesian.hpp` and `src/exact_cartesian.cpp` construct all
nonzero local branches directly from `SboxCorr::numerator(out,in)`. Each
branch stores

\[
q[b,a]=W[b,a]/4\in\{0,\pm1,\pm2,4\}.
\]

The mixed-radix iterator visits every element of

\[
\mathcal B(m^{(0)})\times\cdots\times\mathcal B(m^{(7)})
\]

exactly once. The emitted count must equal the product of the eight local
branch counts. A duplicate, missing, zero, or numerically inconsistent local
branch fails validation before propagation starts.

## Exact dynamic program

At round \(t\), the state map contains exact integers \(N_t[m]\) representing

\[
A_t[m]=N_t[m]/2^{16t}.
\]

Every emitted S-layer tuple applies

\[
N_{t+1}[P(b)]\mathrel{+}=N_t[m]\prod_j q[b_j,m_j],
\qquad
P(b)=\operatorname{mc\_inv\_transpose\_mask}
     (\operatorname{sr\_inv\_transpose\_mask}(b)).
\]

Only exact zeros are removed after aggregation. No nonzero state is pruned.
`cpp_int` multiplication and addition are exact. The `__int128` path checks
every multiplication and addition with compiler overflow intrinsics.

## Certification and failure closure

A successful result separately records:

- `exact_cartesian_complete`;
- `no_state_pruning`;
- `certified_no_truncation`;
- `certified_exact_dyadic`;
- `parseval_pass`.

The complete final column is checked with

\[
\sum_v N_r[v]^2=2^{32r}.
\]

Cancellation, a configured state or transition limit, incomplete Cartesian
enumeration, branch-table inconsistency, checked overflow, or Parseval failure
clears the partial state map and refuses exact certification.

When `--out` is supplied, `estimator_exact` serializes to a temporary file and
renames it only after the complete JSON artifact is written. A rejected or
interrupted run therefore leaves no certified output artifact.

## Build and examples

Boost headers are required for the authoritative backend.

```bash
make estimator_exact test_exact_cartesian test_exact_dyadic

./estimator_exact \
  --r 2 \
  --u 0x00002000 \
  --v 0x08880000 \
  --backend cpp_int \
  --out /tmp/exact-r2.json
```

The JSON endpoint artifact contains every field required by
`docs/EXACT_DYADIC_SPEC.md`, including source, input, and command SHA-256
provenance.

## Verification

`tests/test_exact_cartesian.cpp` verifies all 256 frozen Walsh entries, local
column Parseval, branch ordering, Cartesian cardinality, order independence,
and rejection of duplicate or missing branches.

`tests/test_exact_dyadic.cpp` verifies exact cancellation, all one-round
single-active inputs and endpoints, `cpp_int`/checked-`__int128` equality for
`r=1,2,3`, all 18 frozen way-1 spotchecks, divisibility into the way-1
normalization, full-column Parseval, and failure closure under an artificial
transition limit.
