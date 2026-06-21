# Experiment Manifest

- Experiment ID: E13-final-integration-2026-06-07
- Branch: final/e06-spotcheck-doc-sync
- Package dir: password-final-submit-20260506_e38b20a
- Status: current final authority after E06 integration

## Purpose

Record the final E06-integrated submission state, so older baseline/audit/complexity manifests remain useful as
historical snapshots without being mistaken for the current final package.

No new large-scale search was run for this manifest. It records the already selected certified E06 rows, final
audit summaries, final complexity summaries, and the exact spotcheck extension.

## Final Score

- final valid_count: 138338
- final total_score: 105843.622442471292742994
- r=1 rows: 288
- r=2 rows: 90236
- r=3 rows: 47814

## E06 Merge

- E06 merged rows: 384
- E06 category: r=3 active-2 certified LAT-guided rows
- r=3 active-2 unique u: 6
- E06 source artifacts:
  - `experiments/new_sweeps/r3_active2_lat/r3_active2_lat_cert_u2020shift_u4040shift_top64_beam200k_trans100k.csv`
  - `experiments/new_sweeps/r3_active2_lat/r3_active2_lat_cert_u2020_u4040_top64_beam200k_trans100k.csv`
  - `experiments/new_sweeps/r3_active2_lat/r3_active2_lat_cert_u60600000_u006060_top64_beam200k_trans100k.csv`

## Final Audit Gate

- audit rows: 138338
- certified rows: 138338 / 138338
- ve_mismatch_rows: 0
- duplicate_uv_rows: 0
- zero_u_rows: 0
- zero_v_rows: 0
- zero_vt_rows: 0
- zero_ve_rows: 0

Primary artifacts:

- `experiments/submit_audit.csv`
- `experiments/audit/submit_audit_summary.json`
- `experiments/audit/submit_audit_summary.md`

## Final Complexity Gate

- unique_ru: 4760
- max_generated_transitions_per_ru: 7578152
- max_generated_transitions_ratio_to_2_32: 0.00176443
- ru_generated_transitions_ge_2_32: 0
- ru_expanded_states_ge_2_32: 0

Primary artifacts:

- `experiments/complexity/complexity_summary.json`
- `experiments/complexity/complexity_summary.md`

## Exact Spotcheck Status

E06 exact spotcheck has completed as a validation-only way-1 sample check.

- query count: 18
- E06 active-2 added query count: 4
- mismatch_count: 0
- max_abs_err: 0
- max_rel_err: 0

Primary artifacts:

- `experiments/spotcheck/exact_spotcheck_queries.csv`
- `experiments/spotcheck/exact_spotcheck.csv`
- `experiments/spotcheck/exact_spotcheck_summary.json`
- `experiments/spotcheck/exact_spotcheck_summary.md`

## Supersedes

For the current final package, this manifest supersedes the numeric final-state interpretation of:

- `experiments/manifests/E00_baseline_freeze.md` (historical pre-E06 baseline)
- `experiments/manifests/E01_audit_summary.md` (historical pre-E06 audit snapshot)
- `experiments/manifests/E09_complexity_summary.md` (historical pre-E06 complexity snapshot)

Those manifests are retained as experiment history only.
