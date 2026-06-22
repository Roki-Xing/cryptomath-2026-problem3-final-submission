# Official Specification Interpretation

This document separates confirmed evaluator behavior from repository compatibility
choices and unresolved provenance questions. It does not claim that compatibility
behavior is part of the official specification.

## Officially Confirmed

- The submitted tuple has five fields: `r`, `u`, `v`, `VT`, and `VE`.
- A nonzero correlation pair satisfies the tolerance check when
  `abs(VE - VT) <= 0.25 * abs(VT)`. The absolute value around `VT` is required
  for negative correlations.
- Hexadecimal mask fields such as `0x00000001` are accepted for `u` and `v`.

## Conservative Repository Interpretations

- Score deduplication and reporting are treated as distinct concerns. Reporting
  both `unique_uv` and `unique_ruv` does not select a deduplication policy.
- The parser also accepts decimal `u` and `v` fields. This is a compatibility
  behavior of `parse_mask`, not a claim that decimal masks are required by the
  official format. The frozen `submit.txt` remains unchanged.
- Algorithm interfaces accept any non-negative round count. Tests cover `r=0`
  and `r=4` with deliberately small resource bounds. Resource exhaustion or a
  caller-selected bound may stop a computation, but the interface must not
  reject a request solely because `r` is outside `1..3`.
- `score` computes both uniqueness statistics over records that are valid after
  parsing and active validity filters, but before the selected deduplication is
  applied:
  - `unique_uv` counts distinct `(u, v)` pairs and ignores `r`.
  - `unique_ruv` counts distinct `(r, u, v)` triples.
  - `--positive-only` is an active validity filter, so non-positive-score rows
    are excluded from both statistics when that option is present.
  - Malformed or otherwise invalid rows are excluded from both statistics.
- `--dedup none` remains the default. Explicit `--dedup uv` and
  `--dedup ruv` retain their existing best-score selection behavior and remain
  the only controls that change which valid rows contribute to `valid_count`
  and `total_score`.

## Not Yet Established by the Official Material

- The allowed provenance for `VT` has not been established here. In particular,
  this repository must not describe `VT` as coming from `exact_oracle` unless
  that exact computation was actually executed and recorded.
- Acceptance of a numerically matching `VT` does not by itself prove that its
  generation method is officially permitted.
- The repository therefore treats `VT` source authorization as unresolved and
  keeps way-1 execution evidence separate from way-2 estimates.
