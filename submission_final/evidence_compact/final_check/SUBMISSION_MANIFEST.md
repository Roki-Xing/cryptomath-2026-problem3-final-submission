# Submission Package Manifest

Status: `FINAL_PACKAGE_PREFLIGHT_PENDING`.
PDF preflight status: `FINAL_PACKAGE_PREFLIGHT_PENDING`.
Figure-manuscript preflight status: `FINAL_PACKAGE_PREFLIGHT_PASSED`.
Way-2 exact compact summary artifact status: `FULL_EXACT_WAY2_REVIEW`.
Strategy-B Stage-A compact artifact status: `STAGE_A_PASS`.
Evidence scope is summarized in `EVIDENCE_SCOPE.md`.

## Included package structure

- `README_FIRST.md`: package entry and frozen result summary.
- `PACKAGE_SOURCE_COMMIT.txt` / `PACKAGE_SOURCE_TREE.txt`: clean committed source provenance for this package build.
- `submit.txt`: unchanged frozen final submit file.
- `score_report.txt`: frozen self-score summary.
- `paper/`: final PDF, TeX, and figure assets used by the paper build.
- `figure_manuscript/`: Word figure manuscript plus figure source exports.
- `source/`: package-safe rebuild source tree and saved certified source CSV inputs.
- `docs/EVIDENCE_SCOPE.md`: single authority for the way-1 / way-2 boundary statement.
- `evidence_compact/`: compact way-2 exact evidence, Strategy-B Stage-A evidence, and final integration summaries.
- `SHA256SUMS.txt`: package-local SHA-256 manifest.

## Runnable package rebuild chain

```bash
cd source
make clean && make -j2
python3 -X utf8 experiments/build_submit_from_sources.py --source-submit ../submit.txt --out /tmp/rebuilt_submission_final.txt
cmp ../submit.txt /tmp/rebuilt_submission_final.txt
./score --dedup uv --positive-only ../submit.txt
python3 -X utf8 experiments/check_submission_package.py --submit ../submit.txt
```

Expected frozen result:

```text
valid_count=138338
total_score=105843.622442471292742994
submit_sha256=7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e
```

## SOURCE_MANIFEST boundary

- `source/experiments/SOURCE_MANIFEST.csv` records saved certified source CSV inputs used by the final rebuild chain.
- Its `generation_command` field is a historical discovery label, not a runnable final-package command.
- `candidate_miner_approx` is a repository-only historical discovery helper and is excluded from this package.
- `search_candidates` is a legacy helper and is excluded from this package.
- The final package rebuild path is `source/experiments/build_submit_from_sources.py` consuming the saved certified CSVs.

## Evidence boundaries

- The full exact-way2 rerun closes the way-2 mathematical and numerical evidence only.
- `evidence_compact/way2_exact_full/` contains compact summaries, compare outputs, provenance, and manifest files for the completed full exact-way2 rerun.
- `evidence_compact/strategy_b_stage_a/` contains bounded way-1 batch toolchain evidence only; it is not full way-1 `VT` provenance.
- Raw full exact-way2 archives, CI artifacts, benchmark logs, temporary logs, build outputs, `__pycache__`, fonts, and repository-only discovery helpers are excluded from this package.

```text
stage_b_authorized=false
full_2_32_run_started=false
full_138338_way1_started=false
new_way1_run_started=false
strategy_b_final_file_generated=false
submit_txt_modified=false
vt_provenance_closed=false
```
