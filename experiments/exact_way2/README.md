# Frozen exact-way2 recompute

This directory implements the PR C pilot for recomputing frozen `(r,u)` columns
with exact dyadic arithmetic.

Components:

- `select_pilot.py`: deterministic 344-column pilot selector.
- `run_frozen_exact.py`: controlled pilot runner with per-backend locks,
  clean-source provenance binding, directory-level atomic bundle publication,
  and strict resume verification.
- `compare_frozen_exact.py`: exact decimal comparison against the frozen
  snapshot after compute finishes, plus cross-backend and duplicate gates.
- `summarize_exact.py`: pilot gate summary, manifest, SHA inventory, and
  retention categorization.
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

No script in this directory modifies `submit.txt` or feeds way-1 outputs back
into candidate generation.
