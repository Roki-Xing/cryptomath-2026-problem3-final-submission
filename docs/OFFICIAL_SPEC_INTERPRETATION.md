# Official Specification Interpretation

This document is the canonical repository authority for classifying statements
as official, conservative repository behavior, or unresolved. It does not turn
repository behavior into an official rule.

## Source Boundary

The official challenge landing page identifies Challenge 3 as "矩阵连乘元素的逼近":
<https://www.cmathc.org.cn/mcm/st/434.html>.

Source index: `references/official/SOURCES.json`.

Source file: official analysis PDF not checked into this repository.

Redistribution status: not included because redistribution rights are not
established.

Page map recorded in `references/official/SOURCES.json`:

- page 12: `VT`/`VE` submitted fields and absolute error tolerance;
- page 14: approximate first, then verify;
- page 16/17: arbitrary-r discussion;
- page 18: strictly lower complexity and hexadecimal masks.

The detailed evaluator and complexity statements below follow the verified page
map in `references/official/SOURCES.json`. Because the original analysis PDF is
not packaged here, this limitation does not authorize stronger claims.

## OFFICIAL_EXPLICIT

- **`OFFICIAL_EXPLICIT-FIVE-FIELDS`**: The submitted tuple has five fields: `r`, `u`, `v`, `VT`, and `VE`.
- **`OFFICIAL_EXPLICIT-NEGATIVE-INTERVAL`**: A nonzero correlation pair satisfies the tolerance check when `abs(VE - VT) <= 0.25 * abs(VT)`. The absolute value around `VT` is required for negative correlations.
- **`OFFICIAL_EXPLICIT-HEX-MASKS`**: The official code reads hexadecimal mask fields. The repository regression uses `@(1, 0x000ee0f0, 0x08088880, 0.5, 0.5)` as a parsing-only example; it does not assert that `0.5` is the true correlation for that mask pair.
- **`OFFICIAL_EXPLICIT-COMPLEXITY`**: Way 2 must have complexity strictly lower than way 1.
- **`OFFICIAL_EXPLICIT-APPROXIMATE-THEN-VERIFY`**: The official analysis supports an approximate-first, verify-afterward workflow. The repository uses this only as a validation boundary; it does not authorize way-1 output to feed candidate generation.

## CONSERVATIVE_INTERPRETATION

- **`CONSERVATIVE_INTERPRETATION-DECIMAL-MASKS`**: `parse_mask` also accepts decimal `u` and `v` fields for compatibility. This is not a claim that decimal masks are required by the official format, and the frozen `submit.txt` remains unchanged.
- **`CONSERVATIVE_INTERPRETATION-UNIQUENESS-REPORTING`**: `score` reports both `unique_uv` and `unique_ruv` over parsed rows that remain valid after active filters and before selected deduplication. Reporting both statistics does not select an official deduplication key.
- **`CONSERVATIVE_INTERPRETATION-GENERIC-ROUNDS`**: Algorithm interfaces accept any non-negative round count. `r=0` is an internal identity-map test only and is not claimed as an official competition round count. Tests cover `r=4` with deliberately bounded work. Interface applicability for arbitrary `r` does not imply no-truncation, exact certification, acceptable accuracy, or lower measured cost for every `r`.
- **`CONSERVATIVE_INTERPRETATION-DEDUP-MODES`**: `--dedup none` remains the repository default. Explicit `--dedup uv` and `--dedup ruv` retain their existing best-score selection behavior; these are local controls, not an assertion of the official deduplication policy.

## UNRESOLVED

- **`UNRESOLVED-VT-PROVENANCE`**: The allowed provenance for `VT` has not been established. A numerically matching value does not prove that its generation method is officially permitted, and the repository must not describe `VT` as way-1 output unless that computation was actually executed and recorded.
- **`UNRESOLVED-DEDUP-KEY`**: The official material available in this repository does not establish whether duplicate handling is keyed by `(u,v)`, `(r,u,v)`, or another evaluator-specific rule.
- **`UNRESOLVED-COMPLEXITY-UNIT`**: The official material does not fully specify whether the required comparison unit is a single `(r,u,v)`, a fixed-`(r,u)` multi-output run, a whole submitted batch, an asymptotic operation count, or wall-clock resource usage. Repository transition counts are evidence for a stated local unit, not an official acceptance ruling.
- **`UNRESOLVED-SOURCE-PDF-REDISTRIBUTION`**: The official analysis PDF is not redistributed in this repository. `references/official/SOURCES.json` records the page map and limitation; adding the PDF requires a verified redistribution basis and SHA-256.
