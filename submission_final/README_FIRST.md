# Final Submission Package Release Candidate

Status: `FINAL_PACKAGE_PREFLIGHT_PENDING`.

This package preserves the frozen way-2 result file. It does not start Stage-B,
does not run a new way-1 computation, and does not claim full way-1 `VT`
provenance is closed.

## Required Checks

```bash
sha256sum -c SHA256SUMS.txt
cd source
make clean && make -j2
python3 -X utf8 experiments/build_submit_from_sources.py --source-submit ../submit.txt --out /tmp/rebuilt_submission_final.txt
cmp ../submit.txt /tmp/rebuilt_submission_final.txt
./score --dedup uv --positive-only ../submit.txt
```

## Frozen Result

- `valid_count = 138338`
- `total_score = 105843.622442471292742994`
- `submit_sha256 = 7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e`

## Evidence Boundaries

- Full exact-way2 evidence is included as compact summaries and manifests.
- Strategy-B Stage-A evidence is included only as bounded way-1 toolchain evidence.
- Full raw exact-way2 archives, CI artifacts, temporary logs, build outputs,
  and font files are intentionally excluded.

```text
stage_b_authorized=false
full_2_32_run_started=false
full_138338_way1_started=false
new_way1_run_started=false
strategy_b_final_file_generated=false
submit_txt_modified=false
vt_provenance_closed=false
```
