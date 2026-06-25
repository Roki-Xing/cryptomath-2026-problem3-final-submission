# Stage-A artifact retention plan

## Scope

This plan closes out Stage-A provenance without deleting or rewriting any raw
evidence. Stage B is not authorized here. The machine authority for CI
provenance is `CI_EVIDENCE.json`, and the aggregate decision authority is
`STAGE_A_SUMMARY.json`.

## Required summary

These files are the compact-package summary authority and must stay included:

- `STAGE_A_SUMMARY.json`
- `SUMMARY.md`
- `PROTOCOL.md`
- `benchmark_schema.json`
- `stage_a0/SUMMARY.json`
- `stage_a1/SUMMARY.json`
- `stage_a2/SUMMARY.json`
- `stage_toolchain/SUMMARY.json`

## Required manifest

These files are the machine-readable retention and integrity anchors:

- `MANIFEST.json`
- `CI_EVIDENCE.json`
- `ARTIFACT_INDEX.json`
- `ARTIFACT_RETENTION_PLAN.md`
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

Retain the committed raw evidence in place. Do not delete it and do not include
it in the compact package by default:

- `stage_a0/queries/`
- `stage_a0/results/`
- `stage_a0/artifacts/`
- `stage_a1/queries/`
- `stage_a1/results/`
- `stage_a1/artifacts/`
- `stage_a2/r*_*/`
- `stage_toolchain/compile/`
- `stage_toolchain/results/`

This bucket includes raw query CSVs, raw result CSVs, runner logs, timing
files, compile logs, sanitizer stderr logs, shard raw outputs, and sidecar
manifests. The builder must preserve these files in the repository unchanged.

## CI-only evidence

These references are authoritative CI evidence but are not copied into a compact
submission package:

- toolchain push run: `28031329201`
- toolchain pull-request run: `28031330588`
- final push run: `28032401682`
- final pull-request run: `28032406708`
- temporary CI output paths such as `/tmp/stage_toolchain`

## Exclude from submission package

These files stay in the repository but are outside the compact package boundary:

- `results.csv`
- `forecast.json`
- `__pycache__/`
- temporary files and compile products generated outside the retained manifests

`results.csv` and `forecast.json` remain historical smoke artifacts only. They
are not Stage-A evidence and must not be used for any Strategy-B decision.

## Compact package policy

The compact package is built by an explicit allowlist in
`scripts/build_stage_a_compact_package.py`. Required summaries and required
manifests are copied individually. Parent raw directories never override those
allowlisted files, so summary and manifest paths cannot be dropped by category
overlap.
