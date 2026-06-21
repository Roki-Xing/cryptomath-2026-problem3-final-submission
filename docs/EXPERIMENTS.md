# Experiments Included In The Formal Package

本文件只索引正式作品包中保留的结果与证据。开发期日志、临时 sweep、reproduced 目录和历史 pre-E06 baseline 未随正式包提交。

## Final Integration

- 最终权威 manifest：`experiments/manifests/E13_final_integration.md`
- 最终分数：`valid_count=138338`，`total_score=105843.622442471292742994`
- E06：384 条 r=3 active-2 记录，6 个唯一输入掩码。

## Rebuild Sources

- 构造脚本：`experiments/build_submit_from_sources.py`
- 机器可读来源清单：`experiments/SOURCE_MANIFEST.csv`
- 来源范围：r=2 active-1、active-2 batch/edge、active-3，r=3 active-1，以及三份 E06 r=3 active-2 CSV。
- 复现边界：使用包内已认证来源可字节级重建最终文件；不声称从零重跑全部历史搜索。

## Audit And Complexity

- 全量审计：`experiments/submit_audit.csv`、`experiments/audit/submit_audit_summary.*`
- 复杂度：`experiments/complexity/complexity_summary.*`、`complexity_by_round.*`
- 最终值：`unique_ru=4760`，`max_generated_transitions_per_ru=7578152`，比例 `0.00176443`。

## Independent Validation

- Exact spotcheck：`experiments/spotcheck/`，共 18 条，E06 4 条，mismatch 为 0。
- Manifest：`experiments/manifests/E02_exact_spotcheck.md`
- Exact 工具仅用于 validation-only 抽样，不参与最终生成链。

## Supporting Evidence

- Toy exact compare：`experiments/toy/`，manifest 为 `experiments/manifests/E04_toy_exact_compare.md`。
- 高分路线 trace：`experiments/traces/high_score_r2_00002000_08880000_trace.*`。
- 消融：`experiments/ablation_results.csv`、`experiments/ablation_summary.md`。
- LAT 辅助工具：`experiments/lat_spectrum.py`、`experiments/generate_lat_guided_masks.py`。
