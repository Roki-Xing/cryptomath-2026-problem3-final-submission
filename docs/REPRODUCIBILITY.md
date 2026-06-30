# Reproducibility

This repository provides a reproducible **way-2** pipeline to generate `submit.txt`
from algorithmic sources. The current historical `VT` field is frozen as a
submitted-field snapshot; this repository does not claim that it was produced
by an actually executed way-1 run. Evidence scope is summarized in
`EVIDENCE_SCOPE.md`. See `VT_VE_COMPLIANCE.md`.

The frozen query authority is `experiments/frozen/BASELINE.json`; the historical integration evidence remains
`experiments/manifests/E13_final_integration.md`.

Current evidence state:

- full exact-way2 compact summary artifact status = `FULL_EXACT_WAY2_REVIEW`
- Strategy-B Stage-A compact artifact status = `STAGE_A_PASS`
- package-level boundary flags are listed in `EVIDENCE_SCOPE.md`

## Requirements

- Linux / WSL2
- `make` and a C++17 compiler
- `python3`
- `python3 -m pip install -r requirements-dev.txt`

The full exact-way2 archive path requires the Python package `zstandard`. The
repository declares it in `requirements-dev.txt`; if it is missing,
`experiments/exact_way2/archive_full_evidence.py` fails closed with an explicit
install message instead of silently skipping archive generation.

## Quick Check

```bash
make clean
make -j
make test
python3 experiments/check_submission.py --submit submit.txt
```

`check_submission.py` performs score and summary-artifact checks by default. It does not run the full audit unless
`--run-full-audit` is explicitly provided.

For the final package under `submission_final/source`, use the package-safe
checker instead of the repository checker:

```bash
cd submission_final/source
make clean && make -j2
python3 -X utf8 experiments/build_submit_from_sources.py --source-submit ../submit.txt --out /tmp/rebuilt_submission_final.txt
cmp ../submit.txt /tmp/rebuilt_submission_final.txt
./score --dedup uv --positive-only ../submit.txt
python3 -X utf8 experiments/check_submission_package.py --submit ../submit.txt
```

Within the final package, `experiments/SOURCE_MANIFEST.csv` records the saved
certified CSV inputs used by `build_submit_from_sources.py`. Its
`generation_command` column is a historical candidate-discovery label, not a
claim that the final package reruns repository-only discovery helpers.

## Freeze Final Query Baseline

Generate deterministic query-only artifacts directly from the unchanged `submit.txt`:

```bash
python3 -X utf8 experiments/freeze_baseline.py \
  --submit submit.txt \
  --submit-path-label submit.txt \
  --out-dir experiments/frozen \
  --repository Roki-Xing/cryptomath-2026-problem3-final-submission \
  --source-commit b4fd4061877660a4eefbd2ea88e8170a708e2da1 \
  --freeze-tool-commit 310916db55b8fde9de4bb882b30099ad1081e46a \
  --generated-at 2026-06-23T01:36:23Z
(cd experiments/frozen && sha256sum -c SHA256SUMS.txt)
```

Expected output includes:

```text
submit_sha256=7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e
final_queries_rows=138338
final_ru_rows=4760
final_values_snapshot_rows=138338
```

`final_queries.csv` contains only `r,u,v`. `final_ru.csv` contains only unique `r,u`. Both use normalized
eight-digit hexadecimal masks and deterministic numeric ordering.
`final_values_snapshot.csv` stores stable row IDs, the original submitted `VT`
field text, the original way-2 `VE` text, and empty future way-1 fields marked
`NOT_EXECUTED`. It preserves decimal strings without float parsing or
reformatting.

`BASELINE.json` records:

- repository and source submit path;
- source commit `b4fd4061877660a4eefbd2ea88e8170a708e2da1`;
- submit SHA-256 and Git blob SHA;
- freeze-tool commit `310916db55b8fde9de4bb882b30099ad1081e46a`;
- fixed generation time `2026-06-23T01:36:23Z`;
- artifact schemas, counts, hashes, and canonical generation command.

The timestamp and commits are explicit fixed inputs. Re-running the exact command
therefore reproduces byte-identical artifacts and hashes.

## Rebuild Submit

Rebuild the final submission from tracked way-2 sources and compare byte-for-byte:

```bash
python3 -X utf8 experiments/build_submit_from_sources.py --out /tmp/submit_rebuilt.txt
cmp submit.txt /tmp/submit_rebuilt.txt
```

Expected score after rebuild:

```text
valid_count=138338
total_score=105843.622442471292742994
```

## Score

```bash
./score --dedup uv --positive-only submit.txt
```

Expected round distribution:

| r | rows |
|---:|---:|
| 1 | 288 |
| 2 | 90236 |
| 3 | 47814 |

## Full Way-2 Audit

The full audit is reproducible but slower than the quick check:

```bash
python3 -X utf8 experiments/audit_submit.py \
  --submit submit.txt \
  --out experiments/submit_audit.csv \
  --beam 1000000 --trans 100000 --branch 16

python3 -X utf8 experiments/summarize_audit.py \
  --submit submit.txt \
  --audit experiments/submit_audit.csv \
  --out-json experiments/audit/submit_audit_summary.json \
  --out-md experiments/audit/submit_audit_summary.md
```

Expected final audit:

```text
audit_rows=138338
certified_no_truncation_rows=138338 / 138338
ve_mismatch_rows=0
duplicate_uv_rows=0
zero_u_rows=0
zero_v_rows=0
zero_vt_rows=0
zero_ve_rows=0
```

This is a way-2-only audit. Its provenance columns are:

```text
way2_executed
way2_value_source
submitted_vt_field_source
exact_executed
exact_command
exact_result_available
```

For the tracked audit, exact was not executed: `exact_executed=0`, `exact_command` is empty, and
`exact_result_available=0`. The separate way-1 spotcheck remains under `experiments/spotcheck/` and uses a
different CSV schema.

## Complexity Summary

```bash
python3 -X utf8 experiments/summarize_complexity.py \
  --audit experiments/submit_audit.csv \
  --out-json experiments/complexity/complexity_summary.json \
  --out-md experiments/complexity/complexity_summary.md
```

Expected final complexity:

```text
unique_ru=4760
max_generated_transitions_per_ru=7578152
max_generated_transitions_ratio_to_2_32=0.00176443
ru_generated_transitions_ge_2_32=0
ru_expanded_states_ge_2_32=0
```

The paper's by-round nonzero-transition table is supported by
`experiments/complexity/complexity_by_round.md` and
`experiments/complexity/complexity_by_round.json`, generated from `experiments/submit_audit.csv` by regrouping
unique `(r,u)` records by round `r`.

## Exact Spotcheck

Exact way-1 checks are representative spotchecks only. They do not participate in candidate generation, `VE`
generation, `VT` generation, or `submit.txt` rebuilding.

```bash
python3 -X utf8 experiments/spotcheck/run_exact_spotcheck.py \
  --queries experiments/spotcheck/exact_spotcheck_queries.csv \
  --threads 8 \
  --out-csv experiments/spotcheck/exact_spotcheck.csv \
  --out-json experiments/spotcheck/exact_spotcheck_summary.json \
  --out-md experiments/spotcheck/exact_spotcheck_summary.md \
  --logs-dir experiments/logs
```

Current final spotcheck status:

```text
count=18
e06_active2_query_count=4
mismatch_count=0
```

The E06 count is the number of rows in `experiments/spotcheck/exact_spotcheck_queries.csv` where
`category=r3_active2_e06`.

## Full Exact-Way2 Evidence

The full exact-way2 recomputation is a repository evidence artifact and does
not modify `submit.txt`.

```bash
sha256sum -c artifacts/way2_exact/full/SHA256SUMS.txt
python3 -X utf8 - <<'PY'
import json
s = json.load(open("artifacts/way2_exact/full/SUMMARY.json", encoding="utf-8"))
c = json.load(open("artifacts/way2_exact/full/COMPARE.json", encoding="utf-8"))
print(s["selected_columns"], s["cpp_int_completed_columns"], s["int128_completed_columns"])
print(s["certified_exact_dyadic_cpp_int"], s["certified_exact_dyadic_int128_checked"])
print(s["parseval_cpp_int"], s["parseval_int128_checked"])
print(c["frozen_comparison"])
PY
```

Expected:

```text
4760 4760 4760
4760 4760
4760 4760
{'EXACT_EQUAL': 138338, 'MISSING_ENDPOINT': 0, 'NOT_EQUAL': 0, 'PARSE_ERROR': 0}
```

This closes the way-2 mathematical and numerical evidence chain. It does not
close full way-1 `VT` provenance.

## Strategy-B Stage-A Evidence

Strategy-B Stage-A validates bounded way-1 batch tooling only. It does not run
the full `2^32` plaintext domain, does not run the full 138338-query way-1
workload, and does not generate a Strategy-B final file.

```bash
sha256sum -c artifacts/strategy_b/stage_a/SHA256SUMS.txt
python3 -X utf8 scripts/build_strategy_b_stage_a_artifacts.py --check
python3 -X utf8 - <<'PY'
import json
s = json.load(open("artifacts/strategy_b/stage_a/STAGE_A_SUMMARY.json", encoding="utf-8"))
print(s["stage"], s["decision"], s["next_state"])
print(s["matrices"]["a0"]["status"], s["matrices"]["a0"]["run_case_count"])
print(s["matrices"]["a1"]["status"], s["matrices"]["a1"]["run_case_count"])
print(s["matrices"]["a2"]["status"], s["matrices"]["a2"]["matrix_case_count"])
print(s["matrices"]["toolchain"]["status"], s["matrices"]["toolchain"]["matrix_case_count"])
print(s["gates"]["numerator_mismatch_count"], s["gates"]["shard_negative_test_pass_count"])
print(s["status_flags"])
PY
```

Expected status:

```text
STRATEGY_B_STAGE_A STAGE_A_PASS STRATEGY_B_STAGE_A_REVIEW
STAGE_A0_PASS 68
STAGE_A1_PASS 50
STAGE_A2_PASS 31
STAGE_TOOLCHAIN_PASS 69
0 12
```

## Toy Exact Compare

Reduced-domain toy comparisons validate the same DP algebra against exact enumeration on small domains:

```bash
python3 -X utf8 experiments/toy_exact_compare.py --n-nibbles 2 --rounds 1 2 3 \
  --out experiments/toy/toy_exact_compare_2n.csv

python3 -X utf8 experiments/toy_exact_compare.py --n-nibbles 4 --rounds 1 2 --sample-pairs 10000 \
  --out experiments/toy/toy_exact_compare_4n.csv
```

See `experiments/manifests/E04_toy_exact_compare.md`.

## Paper Files

最终论文文件位于：

- `参赛论文/参赛论文_赛题三_稳稳接住.pdf`
- `参赛论文/参赛论文_赛题三_稳稳接住.tex`
- `参赛论文/figures/`

当前 TeX 源文件已同步全部冻结端点的方式二精确复算结论与 Strategy-B
Stage-A 边界状态。PDF 已由当前 TeX 使用 `bash 参赛论文/build_paper.sh`
重导出。构建信息记录在 `参赛论文/PAPER_BUILD_INFO.json`，人工逐页检查
清单记录在 `参赛论文/PDF_PREFLIGHT.md`。
