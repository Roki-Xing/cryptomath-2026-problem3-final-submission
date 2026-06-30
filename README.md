# Route-Shell Guided Approximation for Challenge 3

This repository contains the final package for Challenge 3, "Approximation of Matrix-Chain Elements".  The main method is **Route-Shell Guided Sparse Dynamic Programming**: it models `M(r)[v,u]` as the linear correlation of `HS(r)` and evaluates selected coordinates by propagating masks through S-box correlation branches and deterministic linear layers.

Status: full exact-way2 dual-backend recomputation completed all 4760 unique
`(r,u)` columns; the compact summary artifact status is
`FULL_EXACT_WAY2_REVIEW`. Strategy-B Stage-A compact artifact status is
`STAGE_A_PASS`.

The displayed `138338` rows and `105843.622442471292742994` score remain the
frozen self-score results for the unchanged `submit.txt`. Full exact-way2
dual-backend recomputation has closed the way-2 mathematical and numerical
evidence chain. Evidence scope is summarized in `docs/EVIDENCE_SCOPE.md`.

当前仓库的 full exact-way2 双后端重算已完成全部 4760 个唯一 `(r,u)` 列，
其 compact summary artifact status 为 `FULL_EXACT_WAY2_REVIEW`；基于这组已完
成证据，仓库文档只声明方式二数学与数值证据链闭合。证据边界统一汇总于
`docs/EVIDENCE_SCOPE.md`。Strategy-B Stage-A compact artifact status 为
`STAGE_A_PASS`。

See `REPORT.md` for the full method, proof, complexity analysis, compliance boundary, experiment tables, and ablation discussion.  See `SUBMISSION_MANIFEST.md` for the final file manifest.

## Final result

```text
valid_count = 138338
total_score = 105843.622442471292742994
r=1 rows = 288
r=2 rows = 90236
r=3 rows = 47814
E06 merged rows = 384
E06 r=3 active-2 unique input masks = 6
certified no-truncation rows = 138338 / 138338
VE mismatch rows = 0
duplicate (u,v) rows = 0
zero u/v/VT/VE rows = 0
unique (r,u) = 4760
max generated transitions per (r,u) = 7578152
max ratio to 2^32 = 0.00176443
exact spotcheck count = 18
exact spotcheck mismatch_count = 0
E06 active-2 spotcheck query count = 4
full exact-way2 cpp_int columns = 4760
full exact-way2 int128_checked columns = 4760
full exact-way2 endpoints = 138338
full exact-way2 EXACT_EQUAL = 138338
Strategy-B Stage-A decision = STAGE_A_PASS
Strategy-B numerator mismatch count = 0
```

## Build and quick check

```bash
make -j
make test
python3 experiments/build_submit_from_sources.py --out /tmp/submit_rebuilt.txt
cmp submit.txt /tmp/submit_rebuilt.txt
./score --dedup uv --positive-only submit.txt
python3 experiments/check_submission.py --submit submit.txt
```

The expected score output is:

```text
valid_count = 138338
total_score = 105843.622442471292742994
```

## Main programs

- `estimator`: way-2 route-shell estimator. It uses S-box correlations, transpose-based linear-layer mask propagation, and sparse aggregation. It does not call the exact `2^32` plaintext oracle.
- `candidate_miner_approx`: pure way-2 low-active-mask candidate miner. It does not link or call the exact oracle.
- `enumerate_r1_positive`: one-round way-2 formula enumerator for all positive `r=1` rows.
- `experiments/build_submit_from_sources.py`: rebuilds the final `submit.txt` from way-2 certified source rows.
- `score`: checks `@(r,u,v,VT,VE)` records and computes the final score.
- `exact_oracle` / `exact_batch_mt`: way-1 validation-only spotcheck tools based on reference plaintext enumeration. They are not used to generate, rank, filter, populate, or backfill the submitted rows or the historical `VT` field.
- `search_candidates`: legacy research miner/verifier that emits candidate CSV only and never creates or modifies `submit.txt`. The final `submit.txt` is rebuilt from way-2 certified source rows by `experiments/build_submit_from_sources.py`.
- `experiments/build_submit_with_certified_r2.py`: historical helper that builds a high-score draft submit file from full `r=1` rows and certified `r=2` candidate CSVs by writing the certified way-2 route-shell value into both submission fields required by the contest format. It is not the current final submit generation path.
- `experiments/verify_top_candidates.py`: legacy validation helper for proxy-ranked CSV candidates. It is not part of the current final submit generation chain.

## Compliance boundary

The approximation path is intentionally separated from the exact oracle:

```text
estimator / candidate_miner_approx
  -> compute VE with S-box correlations, linear-layer mask propagation, and route-shell aggregation
  -> do not enumerate 2^32 plaintexts
  -> do not link, call, or read exact_oracle results while computing submitted VE values

exact_oracle / exact_batch_mt
  -> compute exact correlations by reference way-1 enumeration
  -> used only by the current repository's validation-only spotcheck path
  -> not invoked or read by the reproducible final submission builder

experiments/build_submit_from_sources.py / score
  -> load certified way-2 source rows
  -> preserve the historical final-submit construction that writes the certified route-shell value into both fields
  -> reject duplicate or non-positive-score rows
  -> emit the final submit.txt without reading exact_oracle output
```

For certified no-truncation sparse-DP rows, the way-2 route-shell dynamic program enumerates and sums all nonzero linear routes from `u` to `v`. By the correlation-matrix product expansion, this complete route-shell sum is `M(r)[v,u]`. The frozen submission contains equal numeric strings in its historical `VT` and `VE` fields, and the current builder reproduces those bytes without reading way-1 output. This mathematical equality does not establish that the historical `VT` field was generated by an actually executed way-1 run; that official provenance question remains `UNRESOLVED`. See `docs/VT_VE_COMPLIANCE.md`.

Full exact-way2 evidence is stored under `artifacts/way2_exact/full/`: both
`cpp_int` and `int128_checked` completed all 4760 unique `(r,u)` columns, and
all 138338 frozen endpoints compare as `EXACT_EQUAL`. Strategy-B Stage-A
evidence under `artifacts/strategy_b/stage_a/` validates bounded way-1 batch
tooling, shard reduction, compiler and sanitizer gates. See
`docs/EVIDENCE_SCOPE.md` for the precise boundary statement.

## No-truncation certificate

`estimator` reports a no-truncation certificate when all rounds satisfy:

1. no per-nibble S-box branch list is truncated;
2. no S-layer tuple enumeration is truncated;
3. no aggregated state is pruned by the round-state bound.

Under these conditions, the sparse dynamic program keeps every nonzero linear route contribution and the aggregate endpoint value equals the complete linear-hull sum. The proof is given in `REPORT.md`.

## Reproducibility documents

- `FINAL_CHECK.md`: final score, audit, complexity, and spotcheck gate.
- `docs/EXPERIMENTS.md`: experiment index including E06 final integration.
- `docs/REPRODUCIBILITY.md`: quick rebuild, full audit, complexity summary, exact spotcheck, and toy-check instructions.
- `docs/OFFICIAL_SPEC_INTERPRETATION.md`: canonical machine-readable classification of official, conservative, and unresolved statements.
- `docs/VT_VE_COMPLIANCE.md`: unresolved provenance status and the separated frozen-value schema.
- `artifacts/way2_exact/full/`: full exact-way2 dual-backend summary, compare, provenance, manifest, and raw archive index.
- `artifacts/strategy_b/stage_a/`: bounded Strategy-B Stage-A way-1 batch tooling evidence; not full way-1 `VT` provenance.
- `experiments/manifests/E13_final_integration.md`: final authority after E06; supersedes historical pre-E06 snapshots for final numbers.

Current boundary flags are listed in `docs/EVIDENCE_SCOPE.md`.

## Bit and nibble convention

The code follows the official sample: `0x x0 x1 x2 x3 x4 x5 x6 x7` means nibble `x0` is bits 31..28 and nibble `x7` is bits 3..0.  For a linear layer `y=Lx`, mask propagation in a route uses `v=(L^T)^-1 u`, because the correlation matrix is nonzero exactly when `L^T v=u`.

| Integer bits | Nibble |
| ------------ | ------ |
| 31..28 | `x0` |
| 27..24 | `x1` |
| 23..20 | `x2` |
| 19..16 | `x3` |
| 15..12 | `x4` |
| 11..8 | `x5` |
| 7..4 | `x6` |
| 3..0 | `x7` |
