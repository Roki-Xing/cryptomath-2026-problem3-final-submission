# Final Package Manifest

Status: `FINAL_PACKAGE_PREFLIGHT_PENDING`.

| field | value |
|---|---|
| repository | `Roki-Xing/cryptomath-2026-problem3-final-submission` |
| source_commit | `2185aa25c933a54fdbe3cd2bece068f3a21f4620` |
| source_tree_sha | `b9074140ffe518891c2c2ab5fbeca4ae05fa804d` |
| generated_at_utc | `2026-06-29T08:37:36Z` |
| submit_sha256 | `7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e` |
| valid_count | `138338` |
| total_score | `105843.622442471292742994` |
| package_dir | `submission_final/` |
| package_file_count | `274` |
| package_sha256s | `submission_final/SHA256SUMS.txt` |
| package_sha256s_sha256 | `4b949aa7d916de03d2de71592826e3cc0798b908ffdce3352b05f21e1894a96b` |
| archive | `submission_final.zip` |
| archive_bytes | `4924920` |
| archive_sha256 | `536c6df654c50b11455bff1e7f8469d1dd3c18fdfe54aaff191d4082143285d8` |
| archive_command | `python3 -X utf8 scripts/build_final_package.py --clean` |

## Inclusion Boundary

| category | package treatment |
|---|---|
| required submission artifacts | included: paper PDF/TeX, figure manuscript, `submit.txt`, score report, README |
| runnable submit rebuild source | included under `source/` with core C++/Python programs and final source CSVs |
| way-2 exact evidence | compact summaries/manifests included under `evidence_compact/way2_exact_full/` |
| Strategy-B Stage-A evidence | bounded toolchain summaries/manifests included under `evidence_compact/strategy_b_stage_a/` |
| repository-only raw evidence | excluded: full raw archives, CI artifacts, diagnostic logs |
| excluded artifacts | excluded: build outputs, `__pycache__`, temporary logs, fonts, superseded snapshots, legacy helpers |

## Source Boundary Notes

- Legacy and discovery-only helper programs are excluded from the final competition package and are not part of the final rebuild chain.
- The frozen final `submit.txt` is rebuilt from saved certified CSV sources, not by rerunning historical candidate discovery.
- The final package does not rerun Strategy-B, does not run new way-1 computation, and does not regenerate `submit.txt` from excluded helper utilities.

## Evidence State

```text
stage_b_authorized=false
full_2_32_run_started=false
full_138338_way1_started=false
new_way1_run_started=false
strategy_b_final_file_generated=false
submit_txt_modified=false
vt_provenance_closed=false
```

## Package Files

- `PACKAGE_SOURCE_COMMIT.template`
- `PACKAGE_SOURCE_COMMIT.txt`
- `PACKAGE_SOURCE_TREE.txt`
- `README_FIRST.md`
- `docs/FINAL_CHECK.md`
- `docs/OFFICIAL_SPEC_INTERPRETATION.md`
- `docs/REPRODUCIBILITY.md`
- `docs/SUBMISSION_MANIFEST.md`
- `evidence_compact/claims_and_evidence/CLAIMS_AND_EVIDENCE.md`
- `evidence_compact/final_check/FINAL_CHECK.md`
- `evidence_compact/final_check/SUBMISSION_MANIFEST.md`
- `evidence_compact/final_check/experiments/audit/submit_audit_summary.json`
- `evidence_compact/final_check/experiments/audit/submit_audit_summary.md`
- `evidence_compact/final_check/experiments/complexity/complexity_summary.json`
- `evidence_compact/final_check/experiments/complexity/complexity_summary.md`
- `evidence_compact/final_check/experiments/manifests/E13_final_integration.md`
- `evidence_compact/final_check/experiments/spotcheck/exact_spotcheck_summary.json`
- `evidence_compact/final_check/experiments/spotcheck/exact_spotcheck_summary.md`
- `evidence_compact/strategy_b_stage_a/MANIFEST.json`
- `evidence_compact/strategy_b_stage_a/MISMATCH_SUMMARY.json`
- `evidence_compact/strategy_b_stage_a/PROTOCOL.md`
- `evidence_compact/strategy_b_stage_a/QUERY_FAMILY_SUMMARY.json`
- `evidence_compact/strategy_b_stage_a/REDUCER_NEGATIVE_TEST_SUMMARY.json`
- `evidence_compact/strategy_b_stage_a/SHA256SUMS.txt`
- `evidence_compact/strategy_b_stage_a/STAGE_A_SUMMARY.json`
- `evidence_compact/strategy_b_stage_a/STRATEGY_B_STAGE_A_PROTOCOL.md`
- `evidence_compact/way2_exact_full/COMPARE.json`
- `evidence_compact/way2_exact_full/FULL_RUN_AUTHORIZATION.json`
- `evidence_compact/way2_exact_full/MANIFEST.json`
- `evidence_compact/way2_exact_full/MISMATCHES.csv`
- `evidence_compact/way2_exact_full/PROVENANCE.json`
- `evidence_compact/way2_exact_full/RAW_EVIDENCE_INDEX.json`
- `evidence_compact/way2_exact_full/RAW_EVIDENCE_MANIFEST.json`
- `evidence_compact/way2_exact_full/SHA256SUMS.txt`
- `evidence_compact/way2_exact_full/SUMMARY.json`
- `evidence_compact/way2_exact_full/SUMMARY.md`
- `figure_manuscript/图0000002243.1.pdf`
- `figure_manuscript/图0000002243.1.svg`
- `figure_manuscript/图0000002243.2.pdf`
- `figure_manuscript/图0000002243.2.svg`
- `figure_manuscript/图0000002243.3.pdf`
- `figure_manuscript/图0000002243.3.svg`
- `figure_manuscript/第十一届0000002243图稿.docx`
- `paper/figures/fig1_certified_sparse_transition.pdf`
- `paper/figures/fig1_certified_sparse_transition.svg`
- `paper/figures/fig2_linear_hull_aggregation.pdf`
- `paper/figures/fig2_linear_hull_aggregation.svg`
- `paper/figures/figA1_generation_verification_boundary.pdf`
- `paper/figures/figA1_generation_verification_boundary.svg`
- `paper/参赛论文_赛题三_稳稳接住.pdf`
- `paper/参赛论文_赛题三_稳稳接住.tex`
- `score_report.txt`
- `source/Makefile`
- `source/apps/enumerate_r1_positive.cpp`
- `source/apps/estimator.cpp`
- `source/apps/estimator_exact.cpp`
- `source/apps/exact_batch_current.cpp`
- `source/apps/exact_batch_grouped_u.cpp`
- `source/apps/exact_batch_grouped_uv.cpp`
- `source/apps/exact_batch_mt.cpp`
- `source/apps/exact_batch_variant_app.hpp`
- `source/apps/exact_oracle.cpp`
- `source/apps/recompute_frozen_exact.cpp`
- `source/apps/reduce_exact_parts.cpp`
- `source/apps/score.cpp`
- `source/experiments/SOURCE_MANIFEST.csv`
- `source/experiments/build_submit_from_sources.py`
- `source/experiments/check_submission.py`
- `source/experiments/new_sweeps/r3_active2_lat/r3_active2_lat_cert_u2020_u4040_top64_beam200k_trans100k.csv`
- `source/experiments/new_sweeps/r3_active2_lat/r3_active2_lat_cert_u2020shift_u4040shift_top64_beam200k_trans100k.csv`
- `source/experiments/new_sweeps/r3_active2_lat/r3_active2_lat_cert_u60600000_u006060_top64_beam200k_trans100k.csv`
- `source/experiments/r2_active1_emit_all.csv`
- `source/experiments/r2_active2_batch_1000_0100.csv`
- `source/experiments/r2_active2_batch_1100_0100.csv`
- `source/experiments/r2_active2_batch_1200_0100.csv`
- `source/experiments/r2_active2_batch_1300_0100.csv`
- `source/experiments/r2_active2_batch_1400_0100.csv`
- `source/experiments/r2_active2_batch_1500_0100.csv`
- `source/experiments/r2_active2_batch_1600_0100.csv`
- `source/experiments/r2_active2_batch_1700_0100.csv`
- `source/experiments/r2_active2_batch_1800_0100.csv`
- `source/experiments/r2_active2_batch_1900_0100.csv`
- `source/experiments/r2_active2_batch_200_0100.csv`
- `source/experiments/r2_active2_batch_2100_0100.csv`
- `source/experiments/r2_active2_batch_2200_0100.csv`
- `source/experiments/r2_active2_batch_2300_0100.csv`
- `source/experiments/r2_active2_batch_2400_0100.csv`
- `source/experiments/r2_active2_batch_2500_0100.csv`
- `source/experiments/r2_active2_batch_2600_0100.csv`
- `source/experiments/r2_active2_batch_2700_0100.csv`
- `source/experiments/r2_active2_batch_2800_0100.csv`
- `source/experiments/r2_active2_batch_2900_0100.csv`
- `source/experiments/r2_active2_batch_3000_0100.csv`
- `source/experiments/r2_active2_batch_300_0100.csv`
- `source/experiments/r2_active2_batch_3100_0100.csv`
- `source/experiments/r2_active2_batch_3200_0100.csv`
- `source/experiments/r2_active2_batch_3300_0100.csv`
- `source/experiments/r2_active2_batch_3400_0100.csv`
- `source/experiments/r2_active2_batch_3500_0100.csv`
- `source/experiments/r2_active2_batch_3600_0100.csv`
- `source/experiments/r2_active2_batch_3700_0100.csv`
- `source/experiments/r2_active2_batch_3800_0100.csv`
- `source/experiments/r2_active2_batch_3900_0100.csv`
- `source/experiments/r2_active2_batch_4000_0100.csv`
- `source/experiments/r2_active2_batch_400_0100.csv`
- `source/experiments/r2_active2_batch_4100_0100.csv`
- `source/experiments/r2_active2_batch_4200_0100.csv`
- `source/experiments/r2_active2_batch_4300_0100.csv`
- `source/experiments/r2_active2_batch_4400_0100.csv`
- `source/experiments/r2_active2_batch_4500_0100.csv`
- `source/experiments/r2_active2_batch_4600_0100.csv`
- `source/experiments/r2_active2_batch_4700_0100.csv`
- `source/experiments/r2_active2_batch_4800_0100.csv`
- `source/experiments/r2_active2_batch_4900_0100.csv`
- `source/experiments/r2_active2_batch_5000_0100.csv`
- `source/experiments/r2_active2_batch_500_0100.csv`
- `source/experiments/r2_active2_batch_5100_0100.csv`
- `source/experiments/r2_active2_batch_5200_0100.csv`
- `source/experiments/r2_active2_batch_5300_0100.csv`
- `source/experiments/r2_active2_batch_5400_0100.csv`
- `source/experiments/r2_active2_batch_5500_0100.csv`
- `source/experiments/r2_active2_batch_5600_0100.csv`
- `source/experiments/r2_active2_batch_5700_0100.csv`
- `source/experiments/r2_active2_batch_5800_0100.csv`
- `source/experiments/r2_active2_batch_5900_0100.csv`
- `source/experiments/r2_active2_batch_6000_0100.csv`
- `source/experiments/r2_active2_batch_6100_0100.csv`
- `source/experiments/r2_active2_batch_6200_0100.csv`
- `source/experiments/r2_active2_batch_6300_0100.csv`
- `source/experiments/r2_active2_batch_700_0100.csv`
- `source/experiments/r2_active2_batch_800_0100.csv`
- `source/experiments/r2_active2_batch_900_0100.csv`
- `source/experiments/r2_active2_edge120.csv`
- `source/experiments/r2_active2_edge6400.csv`
- `source/experiments/r2_active3_a3_100020.csv`
- `source/experiments/r2_active3_a3_15020.csv`
- `source/experiments/r2_active3_a3_190020.csv`
- `source/experiments/r2_active3_a3_50020.csv`
- `source/experiments/r2_active3_near_100010_0020.csv`
- `source/experiments/r2_active3_near_100030_0020.csv`
- `source/experiments/r2_active3_near_100050_0020.csv`
- `source/experiments/r2_active3_near_100070_0020.csv`
- `source/experiments/r2_active3_near_100090_0020.csv`
- `source/experiments/r2_active3_near_100110_0020.csv`
- `source/experiments/r2_active3_near_100130_0020.csv`
- `source/experiments/r2_active3_near_100150_0020.csv`
- `source/experiments/r2_active3_near_100170_0020.csv`
- `source/experiments/r2_active3_near_100190_0020.csv`
- `source/experiments/r2_active3_near_100230_0020.csv`
- `source/experiments/r2_active3_near_100270_0020.csv`
- `source/experiments/r2_active3_near_100290_0020.csv`
- `source/experiments/r2_active3_near_14950_0020.csv`
- `source/experiments/r2_active3_near_14970_0020.csv`
- `source/experiments/r2_active3_near_15010_0020.csv`
- `source/experiments/r2_active3_near_15030_0020.csv`
- `source/experiments/r2_active3_near_15050_0020.csv`
- `source/experiments/r2_active3_near_15070_0020.csv`
- `source/experiments/r2_active3_near_15090_0020.csv`
- `source/experiments/r2_active3_near_189970_0020.csv`
- `source/experiments/r2_active3_near_189990_0020.csv`
- `source/experiments/r2_active3_near_190010_0020.csv`
- `source/experiments/r2_active3_near_190030_0020.csv`
- `source/experiments/r2_active3_near_190050_0020.csv`
- `source/experiments/r2_active3_near_190070_0020.csv`
- `source/experiments/r2_active3_near_190090_0020.csv`
- `source/experiments/r2_active3_near_190110_0020.csv`
- `source/experiments/r2_active3_near_190130_0020.csv`
- `source/experiments/r2_active3_near_190150_0020.csv`
- `source/experiments/r2_active3_near_190170_0020.csv`
- `source/experiments/r2_active3_near_190190_0020.csv`
- `source/experiments/r2_active3_near_190210_0020.csv`
- `source/experiments/r2_active3_near_190230_0020.csv`
- `source/experiments/r2_active3_near_190250_0020.csv`
- `source/experiments/r2_active3_near_190270_0020.csv`
- `source/experiments/r2_active3_near_190290_0020.csv`
- `source/experiments/r2_active3_near_190310_0020.csv`
- `source/experiments/r2_active3_near_190330_0020.csv`
- `source/experiments/r2_active3_near_49590_0020.csv`
- `source/experiments/r2_active3_near_49610_0020.csv`
- `source/experiments/r2_active3_near_49630_0020.csv`
- `source/experiments/r2_active3_near_49650_0020.csv`
- `source/experiments/r2_active3_near_49670_0020.csv`
- `source/experiments/r2_active3_near_49690_0020.csv`
- `source/experiments/r2_active3_near_49710_0020.csv`
- `source/experiments/r2_active3_near_49730_0020.csv`
- `source/experiments/r2_active3_near_49750_0020.csv`
- `source/experiments/r2_active3_near_49770_0020.csv`
- `source/experiments/r2_active3_near_49790_0020.csv`
- `source/experiments/r2_active3_near_49810_0020.csv`
- `source/experiments/r2_active3_near_49830_0020.csv`
- `source/experiments/r2_active3_near_49850_0020.csv`
- `source/experiments/r2_active3_near_49870_0020.csv`
- `source/experiments/r2_active3_near_49890_0020.csv`
- `source/experiments/r2_active3_near_49910_0020.csv`
- `source/experiments/r2_active3_near_49930_0020.csv`
- `source/experiments/r2_active3_near_49950_0020.csv`
- `source/experiments/r2_active3_near_49970_0020.csv`
- `source/experiments/r2_active3_near_49990_0020.csv`
- `source/experiments/r2_active3_near_50000_0020.csv`
- `source/experiments/r2_active3_near_50010_0020.csv`
- `source/experiments/r2_active3_near_50020_0020.csv`
- `source/experiments/r2_active3_near_50030_0020.csv`
- `source/experiments/r2_active3_near_50040_0020.csv`
- `source/experiments/r2_active3_near_50050_0020.csv`
- `source/experiments/r2_active3_near_50060_0020.csv`
- `source/experiments/r2_active3_near_50070_0020.csv`
- `source/experiments/r2_active3_near_50090_0020.csv`
- `source/experiments/r2_active3_near_50110_0020.csv`
- `source/experiments/r2_active3_near_50130_0020.csv`
- `source/experiments/r2_active3_near_50150_0020.csv`
- `source/experiments/r2_active3_near_50170_0020.csv`
- `source/experiments/r2_active3_near_50190_0020.csv`
- `source/experiments/r2_active3_near_50210_0020.csv`
- `source/experiments/r2_active3_near_50230_0020.csv`
- `source/experiments/r2_active3_near_50250_0020.csv`
- `source/experiments/r2_active3_near_50270_0020.csv`
- `source/experiments/r2_active3_near_50290_0020.csv`
- `source/experiments/r2_active3_near_50310_0020.csv`
- `source/experiments/r2_active3_near_50330_0020.csv`
- `source/experiments/r2_active3_near_50350_0020.csv`
- `source/experiments/r2_active3_near_50370_0020.csv`
- `source/experiments/r2_active3_near_50390_0020.csv`
- `source/experiments/r2_active3_near_50410_0020.csv`
- `source/experiments/r2_active3_near_50430_0020.csv`
- `source/experiments/r2_active3_near_50450_0020.csv`
- `source/experiments/r2_active3_near_50470_0020.csv`
- `source/experiments/r2_active3_near_50490_0020.csv`
- `source/experiments/r2_active3_near_50510_0020.csv`
- `source/experiments/r2_active3_near_50530_0020.csv`
- `source/experiments/r2_active3_near_50550_0020.csv`
- `source/experiments/r2_active3_near_50570_0020.csv`
- `source/experiments/r2_active3_near_50590_0020.csv`
- `source/experiments/r2_active3_near_50610_0020.csv`
- `source/experiments/r2_active3_near_50630_0020.csv`
- `source/experiments/r2_active3_near_50650_0020.csv`
- `source/experiments/r2_active3_near_50670_0020.csv`
- `source/experiments/r2_active3_near_50690_0020.csv`
- `source/experiments/r2_active3_near_50710_0020.csv`
- `source/experiments/r2_active3_near_50730_0020.csv`
- `source/experiments/r2_active3_near_50750_0020.csv`
- `source/experiments/r2_active3_near_50770_0020.csv`
- `source/experiments/r2_active3_near_50790_0020.csv`
- `source/experiments/r2_active3_near_50810_0020.csv`
- `source/experiments/r2_active3_near_99710_0020.csv`
- `source/experiments/r2_active3_near_99730_0020.csv`
- `source/experiments/r2_active3_near_99770_0020.csv`
- `source/experiments/r2_active3_near_99810_0020.csv`
- `source/experiments/r2_active3_near_99830_0020.csv`
- `source/experiments/r2_active3_near_99850_0020.csv`
- `source/experiments/r2_active3_near_99870_0020.csv`
- `source/experiments/r2_active3_near_99890_0020.csv`
- `source/experiments/r2_active3_near_99910_0020.csv`
- `source/experiments/r2_active3_near_99930_0020.csv`
- `source/experiments/r2_active3_near_99950_0020.csv`
- `source/experiments/r2_active3_near_99970_0020.csv`
- `source/experiments/r2_active3_near_99990_0020.csv`
- `source/experiments/r3_active1_emit_all.csv`
- `source/include/beam_search.hpp`
- `source/include/cli_utils.hpp`
- `source/include/exact.hpp`
- `source/include/exact_cartesian.hpp`
- `source/include/exact_dyadic.hpp`
- `source/include/linear_layer.hpp`
- `source/include/packing.hpp`
- `source/include/sbox_corr.hpp`
- `source/requirements-dev.txt`
- `source/src/beam_search.cpp`
- `source/src/exact.cpp`
- `source/src/exact_cartesian.cpp`
- `source/src/exact_dyadic.cpp`
- `source/src/linear_layer.cpp`
- `source/src/sbox_corr.cpp`
- `submit.txt`
- `SHA256SUMS.txt`
