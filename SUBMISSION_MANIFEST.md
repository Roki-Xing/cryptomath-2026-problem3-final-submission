# Submission Manifest

Status: `FULL_EXACT_WAY2_CLOSED` with Strategy-B Stage-A `STAGE_A_PASS`.
Final package status: `FINAL_PACKAGE_RELEASE_CANDIDATE_READY`.
Manual PDF and figure-manuscript preflight have been completed and reflected in
the final package release-candidate state recorded by this manifest.
The `valid_count=138338` and `total_score=105843.622442471292742994` values are
the frozen self-score results for the unchanged `submit.txt`. Full exact-way2
dual-backend recomputation closed the way-2 mathematical and numerical
evidence chain. Complete way-1 `VT` provenance has not yet been closed.

## 包级交付物

- `提交说明.md`：提交入口、复现层次与工具边界。
- `PACKAGE_SOURCE_COMMIT.template`：源码树内的 package metadata 模板。
- `SHA256SUMS.txt`：除自身外全部包内文件的 SHA-256。
- `submit.txt`：最终 138338 条有效记录，自算分 105843.622442471292742994。
- `REPORT.md`：论文 Markdown 源及方法、证明、实验文本备份。
- `FINAL_CHECK.md`：最终得分、审计、复杂度与抽样摘要。
- `参赛论文/参赛论文_赛题三_稳稳接住.pdf`：由当前 TeX 在 XeLaTeX 环境中重导出的论文阅读版本；人工逐页检查已完成。
- `参赛论文/参赛论文_赛题三_稳稳接住.tex`：已同步当前证据状态的最终论文 TeX 源文件。
- `参赛论文/figures/`：TeX 源文件引用的三组 PDF/SVG 图。
- `第十一届0000002243图稿/`：独立图稿 Word 文件和三组 SVG/PDF；人工检查已完成。

## 可运行源码

- `include/`、`src/`：方式二动态规划、线性层、S 盒相关与 validation-only exact 支持。
- `apps/`：估计器、候选挖掘器、一轮枚举器、评分器与精确验证工具源码。
- `tests/`：核心 C++ 测试和评分器测试。
- `Makefile`：C++17 构建入口。

`exact_oracle`、`exact_batch_mt` 和 `reduce_exact_parts` 仅用于独立抽样验证。`search_candidates` 是 legacy utility，不属于最终生成链。

## 最终结果重建

- `experiments/build_submit_from_sources.py`：从一轮枚举和已保存的方式二认证来源 CSV 重建最终结果。
- `experiments/SOURCE_MANIFEST.csv`：构造脚本默认来源的逐文件参数、行数与 SHA-256。
- `experiments/r2_active*.csv`、`experiments/r3_active1_emit_all.csv`、`experiments/new_sweeps/r3_active2_lat/*.csv`：最终构造所需全部认证来源。

本包支持由已保存认证来源进行字节级重建，但不声称提供从零重新执行全部历史候选搜索的单命令流程。

## 证据链

- `experiments/frozen/BASELINE.json`：绑定仓库、源提交、`submit.txt` SHA-256/Git blob、冻结工具提交和固定生成时间。
- `experiments/frozen/final_queries.csv`、`final_ru.csv`：确定性冻结查询坐标与唯一 `(r,u)` 工作单元。
- `experiments/frozen/final_values_snapshot.csv`：分离历史 submitted-field snapshot、frozen way-2 `VE` 和尚未执行的 future way-1 字段。
- `experiments/frozen/SHA256SUMS.txt`：冻结 artifact 的独立哈希清单。
- `experiments/submit_audit.csv` 与 `experiments/audit/`：全量审计。
- `experiments/complexity/`：复杂度总表和按轮汇总。
- `experiments/spotcheck/`：18 条 validation-only 精确抽样，其中 E06 为 4 条。
- `experiments/traces/`：高分路线贡献追踪。
- `experiments/toy/`：缩小域 exact-vs-DP 对照。
- `experiments/manifests/E13_final_integration.md`：最终权威口径。
- `docs/CLAIMS_AND_EVIDENCE.md`：论文声明到 artifact 的映射。
- `docs/OFFICIAL_SPEC_INTERPRETATION.md`：官方明确、仓库保守解释与未决问题的唯一分类入口。
- `references/official/README.md`、`SOURCES.json`、`PAGE_MAP.json`：官方来源边界、已验证本地文件哈希、下载链接和页码映射。
- `artifacts/way2_exact/full/SUMMARY.json`、`COMPARE.json`、`FULL_RUN_AUTHORIZATION.json`、`PROVENANCE.json`、`MANIFEST.json`、`SHA256SUMS.txt`：full exact-way2 4760 列双后端重算的 compact evidence。
- `artifacts/way2_exact/full/RAW_EVIDENCE_INDEX.json`：full exact-way2 raw archive 的可移植索引；raw archives 不进入比赛提交包。
- `artifacts/strategy_b/stage_a/STAGE_A_SUMMARY.json`、`PROTOCOL.md`、`MANIFEST.json`、`SHA256SUMS.txt`：Strategy-B Stage-A 小域 way-1 batch 工具链证据；它不是 full way-1 `VT` provenance。
- `.github/workflows/ci.yml`：在 pull request 和 hardening/main push 上执行构建、测试、重建、评分与包检查。

正式 `PACKAGE_SOURCE_COMMIT.txt` 只在 release staging 目录中生成，不在源码树中预置，也不伪装为尚未存在的最终 release commit。

## 提交包边界

| category | included files | package treatment |
|---|---|---|
| required submission artifacts | `submit.txt`; `REPORT.md`; `参赛论文/参赛论文_赛题三_稳稳接住.pdf`; `参赛论文/参赛论文_赛题三_稳稳接住.tex`; `README.md`; `提交说明.md`; `FINAL_CHECK.md`; `SUBMISSION_MANIFEST.md` | 进入最终比赛提交包 |
| runnable submit rebuild program | `Makefile`; `include/`; `src/`; `apps/`; `experiments/build_submit_from_sources.py`; source CSVs listed by `experiments/SOURCE_MANIFEST.csv`; `score`; `experiments/check_submission.py` | 进入最终比赛提交包 |
| way-2 exact evidence | `artifacts/way2_exact/full/SUMMARY.json`; `COMPARE.json`; `FULL_RUN_AUTHORIZATION.json`; `PROVENANCE.json`; `MANIFEST.json`; `SHA256SUMS.txt`; `RAW_EVIDENCE_INDEX.json` | compact evidence may be included; raw archives are referenced, not embedded |
| Strategy-B Stage-A evidence | `artifacts/strategy_b/stage_a/STAGE_A_SUMMARY.json`; `PROTOCOL.md`; `MANIFEST.json`; `SHA256SUMS.txt`; `docs/STRATEGY_B_STAGE_A_PROTOCOL.md` | included as bounded way-1 tooling evidence only |
| repository-only raw evidence | full exact-way2 tar.zst release assets; large diagnostic logs; CI artifacts; benchmark raw logs | repository/release evidence only, not final competition package payload |
| excluded artifacts | temporary logs; `__pycache__`; build outputs; stale superseded artifacts; raw archives; CI-only artifacts; legacy helpers not required by rebuild | excluded from final competition package unless explicitly archived as not part of submission |

## Current evidence state

| state | result |
|---|---|
| `FULL_EXACT_WAY2_CLOSED` | full exact-way2 dual backend completed all 4760 unique `(r,u)` columns; 138338 frozen endpoints are `EXACT_EQUAL`; mismatch counters are 0 |
| `STRATEGY_B_STAGE_A` | bounded way-1 batch toolchain passed A0/A1/A2/toolchain gates; numerator mismatch count is 0; shard negative tests passed 12 |
| way-1 `VT` provenance | unresolved; no full `2^32` run and no full 138338-query way-1 run has been started |

```text
stage_b_authorized=false
full_2_32_run_started=false
full_138338_way1_started=false
new_way1_run_started=false
strategy_b_final_file_generated=false
submit_txt_modified=false
vt_provenance_closed=false
```

## Final gate

```bash
make clean && make -j
make test
python3 -X utf8 experiments/build_submit_from_sources.py --out /tmp/submit_rebuilt.txt
cmp submit.txt /tmp/submit_rebuilt.txt
./score --dedup uv --positive-only submit.txt
python3 experiments/check_submission.py --submit submit.txt
```

预期：

```text
valid_count=138338
total_score=105843.622442471292742994
```
