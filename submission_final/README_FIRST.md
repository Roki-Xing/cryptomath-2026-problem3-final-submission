# Final Submission Package Release Candidate

Status: `FINAL_PACKAGE_PREFLIGHT_PENDING`.

This package contains the frozen final submission file, the paper, the
package-level rebuild source tree, and compact evidence.
The way-2 mathematical and numerical evidence chain is closed.
Way-1 evidence is included only as bounded tooling validation and
spotcheck validation; full way-1 `VT` provenance is not claimed.
See `docs/EVIDENCE_SCOPE.md`.
PDF preflight status: `FINAL_PACKAGE_PREFLIGHT_PENDING`.
Figure-manuscript preflight status: `FINAL_PACKAGE_PREFLIGHT_PASSED`.
See `docs/SUBMISSION_MANIFEST.md` for the recorded package state.

## Required Checks

```bash
sha256sum -c SHA256SUMS.txt
cd source
make clean && make -j2
python3 -X utf8 experiments/build_submit_from_sources.py --source-submit ../submit.txt --out /tmp/rebuilt_submission_final.txt
cmp ../submit.txt /tmp/rebuilt_submission_final.txt
./score --dedup uv --positive-only ../submit.txt
python3 -X utf8 experiments/check_submission_package.py --submit ../submit.txt
```

## Frozen Result

- `valid_count = 138338`
- `total_score = 105843.622442471292742994`
- `submit_sha256 = 7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e`
