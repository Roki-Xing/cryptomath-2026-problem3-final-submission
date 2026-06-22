# Reproducibility

This repository provides a reproducible **way-2** pipeline to generate `submit.txt` from algorithmic sources:
S-box correlation tables, linear-layer mask propagation, sparse DP, and certified candidate CSVs. The **way-1**
programs `exact_oracle` and `exact_batch_mt` are validation-only tools and are not used to generate submitted
`VE`, submitted `VT`, or the final `submit.txt` source chain.

The frozen query authority is `experiments/frozen/BASELINE.json`; the historical integration evidence remains
`experiments/manifests/E13_final_integration.md`.

## Requirements

- Linux / WSL2
- `make` and a C++17 compiler
- `python3`

## Quick Check

```bash
make clean
make -j
make test
python3 experiments/check_submission.py --submit submit.txt
```

`check_submission.py` performs score and summary-artifact checks by default. It does not run the full audit unless
`--run-full-audit` is explicitly provided.

## Freeze Final Query Baseline

Generate deterministic query-only artifacts directly from the unchanged `submit.txt`:

```bash
python3 -X utf8 experiments/freeze_baseline.py \
  --submit submit.txt \
  --out-dir experiments/frozen
(cd experiments/frozen && sha256sum -c SHA256SUMS.txt)
```

Expected output includes:

```text
submit_sha256=7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e
final_queries_rows=138338
final_ru_rows=4760
```

`final_queries.csv` contains only `r,u,v`. `final_ru.csv` contains only unique `r,u`. Both use normalized
eight-digit hexadecimal masks and deterministic numeric ordering. `BASELINE.json` records the frozen figures,
source hash, artifact counts/hashes, and canonical generation command; it intentionally records no git metadata.

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

提供方 PDF 与 TeX 的 SHA-256 已和原清单核对一致。PDF 已检查标题、17 页页数以及最终
`valid_count=138338` 和 `total_score=105843.622442471292742994`。当前 WSL 环境缺少 TeX
指定的物理中文字体，因此没有在本机重新导出 PDF；如需重导出，应在具备对应中文字体的
XeLaTeX 环境中连续编译两次并人工检查公式、表格和字体。
