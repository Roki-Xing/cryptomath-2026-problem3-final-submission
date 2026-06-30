# Final Package Reproducibility

This document applies only to the extracted `submission_final/` package.
It does not claim that repository-only discovery helpers or raw exact-way2
archives are present inside the package.
Evidence scope is summarized in `EVIDENCE_SCOPE.md`.

## Requirements

- Linux / WSL2
- `make` and a C++17 compiler
- `python3`
- `python3 -m pip install -r source/requirements-dev.txt` if additional Python helpers are needed

## Package-safe validation commands

```bash
sha256sum -c SHA256SUMS.txt
cd source
make clean && make -j2
python3 -X utf8 experiments/build_submit_from_sources.py --source-submit ../submit.txt --out /tmp/rebuilt_submission_final.txt
cmp ../submit.txt /tmp/rebuilt_submission_final.txt
./score --dedup uv --positive-only ../submit.txt
python3 -X utf8 experiments/check_submission_package.py --submit ../submit.txt
```

The package-safe checker validates only files that actually exist in the final
package. It does not require repository-only tests, CI workflows,
`freeze_baseline.py`, `audit_submit.py`, `candidate_miner_approx.cpp`, or
`search_candidates.cpp`.

## SOURCE_MANIFEST semantics

- `source/experiments/SOURCE_MANIFEST.csv` lists saved certified source CSV inputs used by the final package rebuild chain.
- `generation_command` records a historical discovery label for provenance; it is not a command that the final package promises to rerun.
- `source/experiments/build_submit_from_sources.py` is the runnable final-package generator.

## Evidence included vs excluded

- Included compact evidence: `evidence_compact/way2_exact_full/`, `evidence_compact/strategy_b_stage_a/`, `evidence_compact/final_check/`, and `evidence_compact/claims_and_evidence/`.
- Excluded repository-only evidence: full exact-way2 raw archives, CI artifacts, benchmark raw logs, temporary logs, build outputs, and fonts.
