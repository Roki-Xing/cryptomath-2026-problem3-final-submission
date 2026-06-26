# Exact Way-2 Artifact Retention Plan

## Current pilot

The 344-column pilot may keep committed raw evidence in Git, but each file must
be classified as one of:

- `REQUIRED_SUMMARY`
- `REQUIRED_MANIFEST`
- `PILOT_RAW_EVIDENCE`
- `CI_ONLY`
- `EXCLUDE_FROM_SUBMISSION_PACKAGE`

The committed pilot evidence must remain reproducible from a clean committed
source checkout and must not be the only provenance source for CI attestation.

## Future full 4760-column run

The future full exact-way2 recompute must not commit tens of thousands of loose
raw files into Git. The intended retention boundary is:

- Git repository keeps:
  - protocol, provenance, selection, manifests, summaries, mismatch tables,
    SHA inventories, and a small representative sample of column bundles.
- Deterministic archives keep:
  - full raw column bundles packed as deterministic `tar.zst` volumes.
- Each archive volume must record:
  - archive SHA-256;
  - contained file count;
  - total bytes;
  - extracted manifest SHA-256;
  - source commit and source tree SHA.
- GitHub Release assets may mirror the deterministic archive volumes, but CI
  artifacts must not be the only long-term evidence carrier.
- The final competition delivery package only carries compact evidence, not the
  full raw exact-way2 archive.
