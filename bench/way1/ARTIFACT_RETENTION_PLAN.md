# Stage-A artifact retention plan

## Scope

This plan classifies the committed way-1 Stage-A benchmark artifacts without
deleting or rewriting raw evidence. Stage-B is not authorized here.

## Required summary

Keep these files as the human and machine authority for the Stage-A closeout:

- `STAGE_A_SUMMARY.json`
- `SUMMARY.md`
- `PROTOCOL.md`
- `benchmark_schema.json`

## Required manifest

Keep these files as integrity and inventory anchors:

- `MANIFEST.json`
- `SHA256SUMS.txt`
- `stage_a0/MANIFEST.json`
- `stage_a0/SHA256SUMS.txt`
- `stage_a1/MANIFEST.json`
- `stage_a1/SHA256SUMS.txt`
- `stage_a2/MANIFEST.json`
- `stage_a2/SHA256SUMS.txt`
- `stage_toolchain/MANIFEST.json`
- `stage_toolchain/SHA256SUMS.txt`

## Raw reproducibility evidence

Retain these directories as raw evidence for reproducing the Stage-A decision:

- `stage_a0/`
- `stage_a1/`
- `stage_a2/`
- `stage_toolchain/`

These directories include query CSVs, sidecar manifests, raw exact-batch
outputs, reduced results, runner logs, compile logs, sanitizer logs, and timing
files.

## CI-only evidence

The final CI authority for the integration head is:

- final push run: `28032401682`
- final pull-request run: `28032406708`

The workflow uses temporary CI output paths such as `/tmp/stage_toolchain`.
Those temporary directories are CI-only and are not required in the submission
package.

## Exclude from submission package

The following files are committed historical or interpreter byproducts, but are
not part of the final submission package:

- `results.csv`
- `forecast.json`
- `__pycache__/`

`results.csv` and `forecast.json` are pre-P0 smoke artifacts. They are not
Stage-A evidence and must not be used as a Strategy-B decision.

## Submission policy

The submission package should include required summaries and required manifests.
Raw reproducibility evidence may stay in the repository, but should be excluded
from a compact final package unless a reviewer explicitly requests it.
