# Frozen exact-way2 recompute

This directory implements the PR C pilot for recomputing frozen `(r,u)` columns
with exact dyadic arithmetic.

Components:

- `prepare_selector_inputs.py`: sanitize historical audit and spotcheck sources
  into complexity-only and coordinate-only selector inputs.
- `select_pilot.py`: deterministic 344-column pilot selector.
- `run_frozen_exact.py`: controlled compute runner with per-backend locks,
  clean-source provenance binding, directory-level atomic bundle publication,
  and strict resume verification.
- `run_pilot_pipeline.py`: outer orchestrator for selector, compute, compare,
  repeat subset, and summary timing.
- `compare_frozen_exact.py`: exact decimal comparison against the frozen
  snapshot after compute finishes, plus cross-backend and duplicate gates.
- `summarize_exact.py`: pilot gate summary only.
- `capture_build_reproducibility.py`: clean-worktree build capture for the
  exact recompute binary.
- `merge_build_reproducibility.py`: merge two clean build captures into
  `BUILD_REPRODUCIBILITY.json`.
- `attest_pilot_artifacts.py`: generate provenance, manifest, and SHA
  inventory after the evidence commit exists.
- `common.py`: shared hashing, parsing, and deterministic helpers.
- `ARTIFACT_RETENTION_PLAN.md`: committed-vs-release retention policy.

The compute phase only reads:

- `experiments/frozen/final_ru.csv`
- `experiments/frozen/final_queries.csv`

The compare phase may additionally read:

- `experiments/frozen/final_values_snapshot.csv`
- `experiments/spotcheck/exact_spotcheck.csv`

Published pilot artifacts use the bundle layout
`completed/r<r>_<u>_<backend>/column.json,endpoints.csv,DONE.json`.
Loose legacy `columns/*.json` or `endpoints/*.csv` outputs are rejected.

Selector preparation and selection must not read `VE`, `VT`, `score`,
way-1 numerators, or candidate rank/source fields. The compute phase only
reads `row_id,r,u,v` from the frozen query file.

No script in this directory modifies `submit.txt` or feeds way-1 outputs back
into candidate generation.
