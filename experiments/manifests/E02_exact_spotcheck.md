# Experiment Manifest

- Experiment ID: E02-exact-spotcheck-2026-05-31
- Branch: main
- Date: 2026-05-31T18:13:09+08:00
- Commit before run: 809a81b9cac565a0a7b839ff94fd73ff67c83a87
- Package dir: password-final-submit-20260506_e38b20a
- Machine: WSL2 (Linux 6.6.87.2-microsoft-standard-WSL2)
- CPU: Intel(R) Core(TM) i7-14650HX (WSL vCPU: 8)
- RAM: 7.8 GiB (WSL reported)
- Compiler: g++ 13.3.0
- Python: 3.12.3

## Purpose

Independent way-1 exact verification on a small representative sample, to support the claim:
for certified submit rows, the way-2 no-truncation estimator value equals the true correlation.

## Command

```bash
mkdir -p experiments/spotcheck experiments/logs

python3 -X utf8 experiments/spotcheck/run_exact_spotcheck.py \
  --queries experiments/spotcheck/exact_spotcheck_queries.csv \
  --threads 8 \
  --out-csv experiments/spotcheck/exact_spotcheck.csv \
  --out-json experiments/spotcheck/exact_spotcheck_summary.json \
  --out-md experiments/spotcheck/exact_spotcheck_summary.md \
  --logs-dir experiments/logs \
  2>&1 | tee experiments/logs/E02_exact_spotcheck_runner.log
```

## Inputs

- queries: experiments/spotcheck/exact_spotcheck_queries.csv

## Outputs

- experiments/spotcheck/exact_spotcheck.csv
- experiments/spotcheck/exact_spotcheck_summary.json
- experiments/spotcheck/exact_spotcheck_summary.md
- experiments/logs/E02_exact_spotcheck_runner.log

## Result (Key Fields)

- count: 18
- mismatch_count: 0
- max_abs_err: 0
- max_rel_err: 0

The final query set includes four E06 r=3 active-2 certified samples, including positive and negative `VE`
examples for `u=0x00006060` and two additional active-2 input masks.

## Decision

- keep
