# VT/VE Compliance Notes

This document clarifies the intended compliance boundary for Challenge 3, and why the two numeric fields `VT` and `VE` have the same value on certified no-truncation rows **without** using way-1 plaintext enumeration outputs to generate the submission.

## Definitions

- **Way 1 (exact)**: enumerate the full `2^32` plaintext domain to compute the correlation value directly
  (`exact_oracle`, `exact_batch_mt`).
- **Way 2 (structured)**: compute the same matrix coordinate by structured correlation propagation using:
  - S-box correlation table (per-nibble Walsh values),
  - deterministic linear-layer mask propagation via transpose/inverse-transpose,
  - aggregation of all nonzero route contributions (a complete linear-hull sum when no truncation happens).

In this repository, `estimator` / `candidate_miner_approx` implement way 2. See `README.md` and `REPORT.md`.

## Submission Generation Boundary (Red Lines)

Not allowed (and not done here):

- using `exact_oracle` / `exact_batch_mt` outputs to generate submitted `VE` or submitted `VT`,
- using exact outputs to filter/rank candidates that become submitted rows,
- copying exact values into candidate CSV sources and then building the submission from them.

Allowed (and done here):

- using way-2 mining (`candidate_miner_approx`) and way-2 estimation (`estimator`) to generate candidate `VE`,
- promoting only **no-truncation-certified** rows into the final submission,
- using way-1 exact programs only for **independent spot checks** on a small subset.

## Why Certified Rows Have the Same Numeric Value in `VT` and `VE`

`VT` 与 `VE` 数值相同，是 certified way-2 complete route-shell summation 的结果，不是复制 way-1 输出。

For a round function composed of an S-box layer and an invertible linear layer, the matrix coordinate `M(r)[v,u]`
can be interpreted as the correlation of the `r`-round permutation between input mask `u` and output mask `v`.

In certified mode (no branch/tuple truncation and no beam pruning), the way-2 DP:

1. enumerates **all** nonzero S-box correlation branches (Kronecker product structure),
2. propagates masks deterministically through the linear layer using the correct transpose relation,
3. aggregates signed route contributions into a complete linear-hull sum for each endpoint.

Therefore, on a certified row, the way-2 output equals the exact matrix coordinate `M(r)[v,u]`. In that case,
the same numeric value is written to the two fields required by the submission format because the value is produced by the way-2 structured route-shell computation, not by plaintext enumeration.

## Evidence In This Repo

- **Frozen final-query baseline**:
  - Generator: `experiments/freeze_baseline.py`
  - Query coordinates: `experiments/frozen/final_queries.csv`
  - Unique way-2 work units: `experiments/frozen/final_ru.csv`
  - Metadata and hashes: `experiments/frozen/BASELINE.json`, `experiments/frozen/SHA256SUMS.txt`
  - These files are derived from the frozen `submit.txt`; they do not run candidate search, estimator, or exact code.

- **E01 full audit (way-2)**:
  - Audit CSV: `experiments/submit_audit.csv`
  - Summary: `experiments/audit/submit_audit_summary.md`
  - Manifest: `experiments/manifests/E01_audit_summary.md`
  - Historical manifest plus current summary record `certified_no_truncation` and reconstruction stats per submit
    row. Current final audit rows are 138338 and `ve_mismatch_rows=0`.
  - Its provenance schema records `way2_executed=1`, `way2_value_source=estimator`,
    `submitted_vt_field_source=submit.txt`, `exact_executed=0`, an empty `exact_command`, and
    `exact_result_available=0`. It does not claim that submitted `VT` came from `exact_oracle`.

- **E13 final integration**:
  - Manifest: `experiments/manifests/E13_final_integration.md`
  - Current final authority after E06: 138338 rows, 138338 / 138338 certified rows, 0 mismatch rows, and
    `unique_ru=4760`.

- **E02 exact spotcheck (way-1 validation only)**:
  - Results: `experiments/spotcheck/exact_spotcheck.csv`
  - Summary: `experiments/spotcheck/exact_spotcheck_summary.md`
  - Logs: `experiments/logs/E02_exact_spotcheck_r*.log`
  - Manifest: `experiments/manifests/E02_exact_spotcheck.md`
  - This output has a separate schema and is not merged into the way-2 audit CSV.

- **E04 toy reduced-domain exact compare (correctness sanity)**:
  - Script: `experiments/toy_exact_compare.py`
  - Outputs: `experiments/toy/toy_exact_compare_2n.csv`, `experiments/toy/toy_exact_compare_4n.csv`
  - Manifest: `experiments/manifests/E04_toy_exact_compare.md`
  - Confirms toy way-2 DP equals toy exact enumeration on reduced domains.

- **E09 complexity summary**:
  - `experiments/complexity/complexity_summary.md`
  - Manifest: `experiments/manifests/E09_complexity_summary.md`
  - Summarizes complexity per unique `(r,u)` from the audit file, for an apples-to-apples comparison against
    way-1 per-`(r,u,v)` full enumeration.

## How To Re-Verify Locally

```bash
make -j
python3 -X utf8 experiments/freeze_baseline.py
./score --dedup uv --positive-only submit.txt
python3 -X utf8 experiments/audit_submit.py --submit submit.txt --out experiments/submit_audit.csv \
  --beam 1000000 --trans 100000 --branch 16
python3 -X utf8 experiments/spotcheck/run_exact_spotcheck.py --threads 16
```

The full audit command above executes way 2 only. The exact spotcheck command is separate and writes only under
`experiments/spotcheck/`.
