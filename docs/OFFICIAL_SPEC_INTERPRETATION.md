# Official Specification Interpretation

This document is the canonical repository authority for classifying statements
as official, conservative repository behavior, or unresolved. It does not turn
repository behavior into an official rule.

## Source Boundary

Structured source registry: `references/official/SOURCES.json`.

Structured page map: `references/official/PAGE_MAP.json`.

Official-site boundary used by this repository:

- `http://www.cmsecc.com/`: treated as the official challenge host because the
  public announcement page points to `www.cmsecc.com` as the official site.
- `http://www.cmsecc.com/xiazai/`: verified official download page.
- `https://www.cmathc.org.cn/mcm/st/434.html`: treated only as a
  `public_announcement_or_mirror`, not as the official landing page.

Official PDFs are not redistributed in this repository by default. Their local
verification metadata, including SHA-256, page counts, and retrieval time, is
recorded in `references/official/SOURCES.json`.

Verified page map used by the repository:

- page 12: way-1 computes `VT`; way-2 computes `VE`; absolute and relative
  error conditions; and the statement that way-2 complexity must be strictly
  lower than way-1.
- page 13: five-field submission format, score definition, and the required
  theory/data/program/self-score deliverables.
- page 14: approximate first and then verify; exact first and then design the
  approximation is also allowed.
- page 16: the method should apply to arbitrary `r`.
- page 17: traditional linear-analysis methods may be used, and the method
  still needs to apply to arbitrary rounds.
- page 18: way-2 complexity must be strictly lower than way-1, and submission
  masks are 32-bit hexadecimal values.

The page map constrains what the repository may claim. In particular, the
official allowance of "approximate first, then verify" does not establish that
an exact certified way-2 value can replace an actually executed way-1 `VT`.

Current repository status after full exact-way2 and Strategy-B Stage-A:

- `FULL_EXACT_WAY2_CLOSED`: closes the way-2 mathematical and numerical
  evidence chain for the frozen values.
- `STRATEGY_B_STAGE_A` / `STAGE_A_PASS`: validates bounded way-1 batch
  tooling, query families, shard reducer, compiler, and sanitizer gates.
- `UNRESOLVED-VT-PROVENANCE` remains unresolved: no full `2^32` way-1 run and
  no full 138338-query way-1 run has been started.

## OFFICIAL_EXPLICIT

- **`OFFICIAL_EXPLICIT-FIVE-FIELDS`**: The submitted tuple has five fields:
  `r`, `u`, `v`, `VT`, and `VE`.
- **`OFFICIAL_EXPLICIT-NEGATIVE-INTERVAL`**: A nonzero correlation pair
  satisfies the tolerance check when `abs(VE - VT) <= 0.25 * abs(VT)`. The
  absolute value around `VT` is required for negative correlations.
- **`OFFICIAL_EXPLICIT-HEX-MASKS`**: The official format uses 32-bit
  hexadecimal masks in the submission records.
- **`OFFICIAL_EXPLICIT-COMPLEXITY`**: Way 2 must have complexity strictly
  lower than way 1.
- **`OFFICIAL_EXPLICIT-APPROXIMATE-THEN-VERIFY`**: The official analysis
  allows an approximate-first, verify-afterward workflow, and also allows the
  reverse order of computing an exact value first and then designing the
  approximation.

## CONSERVATIVE_INTERPRETATION

- **`CONSERVATIVE_INTERPRETATION-DECIMAL-MASKS`**: `parse_mask` also accepts
  decimal `u` and `v` fields for compatibility. This is not a claim that
  decimal masks are required by the official format, and the frozen
  `submit.txt` remains unchanged.
- **`CONSERVATIVE_INTERPRETATION-UNIQUENESS-REPORTING`**: `score` reports both
  `unique_uv` and `unique_ruv` over parsed rows that remain valid after active
  filters and before selected deduplication. Reporting both statistics does not
  select an official deduplication key.
- **`CONSERVATIVE_INTERPRETATION-GENERIC-ROUNDS`**: Algorithm interfaces accept
  any non-negative round count. `r=0` is an internal identity-map test only
  and is not claimed as an official competition round count. Tests cover `r=4`
  with deliberately bounded work. Interface applicability for arbitrary `r`
  does not imply no-truncation, exact certification, acceptable accuracy, or
  lower measured cost for every `r`.
- **`CONSERVATIVE_INTERPRETATION-DEDUP-MODES`**: `--dedup none` remains the
  repository default. Explicit `--dedup uv` and `--dedup ruv` retain their
  existing best-score selection behavior; these are local controls, not an
  assertion of the official deduplication policy.

## UNRESOLVED

- **`UNRESOLVED-VT-PROVENANCE`**: The allowed provenance for `VT` has not been
  established. A numerically matching value does not prove that its generation
  method is officially permitted, and the repository must not describe `VT` as
  way-1 output unless that computation was actually executed and recorded.
- **`UNRESOLVED-DEDUP-KEY`**: The official material available in this
  repository does not establish whether duplicate handling is keyed by
  `(u,v)`, `(r,u,v)`, or another evaluator-specific rule.
- **`UNRESOLVED-COMPLEXITY-UNIT`**: The official material does not fully
  specify whether the required comparison unit is a single `(r,u,v)`, a
  fixed-`(r,u)` multi-output run, a whole submitted batch, an asymptotic
  operation count, or wall-clock resource usage. Repository transition counts
  are evidence for a stated local unit, not an official acceptance ruling.
- **`UNRESOLVED-SOURCE-PDF-REDISTRIBUTION`**: The official challenge and
  analysis PDFs are not redistributed in this repository. Their hashes,
  retrieval timestamps, and page counts are recorded in
  `references/official/SOURCES.json`.
