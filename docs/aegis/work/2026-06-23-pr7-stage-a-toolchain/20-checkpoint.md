# PR7 Stage-A 工具链验证 - Checkpoint

- Task ID: 2026-06-23-pr7-stage-a-toolchain
- Current todo: 实现工具链矩阵 runner 和测试
- Active slice: TDD: 先矩阵契约测试，后 runner/CI
- Blocked on: none
- Next step: 添加失败测试并验证 RED

## Checkpoint Update

- Current todo: 提交工具链基础设施并运行真实矩阵
- Active slice: 基础设施提交前验证
- Completed todos:
- 确认 A2 推送与 Draft PR 状态
- 按指导文档固化 69 点工具链矩阵
- 矩阵契约测试完成 RED/GREEN
- Evidence refs:
- tests/test_way1_stage_toolchain.py: 69 点矩阵测试通过
- bench/way1/run_stage_toolchain.py
- Blocked on: none
- Next step: 更新 SHA 清单、运行 make test、提交并推送

## DriftCheckDraft

- Scope status: 仅新增验证 runner、CI 和协议
- Compatibility status: 未改算法或 submit.txt
- Retirement status: 无旧路径替换；复用现有 A0 查询与 timeout helper
- New risk signals:
- 本机无 clang++，完整矩阵需 GitHub runner
- Advisory decision: needs-verification

## Checkpoint Update

- Current todo: 提交 Stage-A CI 证据与聚合结论
- Active slice: 证据固化与最终回归
- Completed todos:
- 工具链 runner 和 CI 基础设施已提交
- 本地 UBSan 18 点与 ASan 9 点通过
- GitHub 69 点工具链矩阵通过并下载核验
- Stage-A 14 项闸门聚合为 STAGE_A_PASS
- Evidence refs:
- GitHub PR run 28031330588: stage-a-toolchain/GCC/Clang 全绿
- bench/way1/stage_toolchain/SUMMARY.json: 69 cases, 0 mismatches
- bench/way1/STAGE_A_SUMMARY.json
- Blocked on: none
- Next step: 更新 SHA 清单、提交证据、跑最终 release gates

## DriftCheckDraft

- Scope status: 完成 Stage-A 有界验证与证据固化
- Compatibility status: submit 和算法未变，未调用 exact dyadic backend
- Retirement status: 历史 smoke 保留且明确标为 pre-P0；无新增兼容路径
- New risk signals:
- Stage B 仍未授权，性能 GO 仍待后续独立决策
- Advisory decision: continue

## Checkpoint Update

- Current todo: 提交并等待最终 CI
- Active slice: 提交 Stage-A 证据
- Completed todos:
- 干净构建与 make test 通过
- submit 重建逐字节一致
- final score 与 check_submission 通过
- 三层 SHA 清单通过
- Evidence refs:
- make test: exit 0
- cmp submit.txt /tmp/submit_rebuilt.txt: exit 0
- score: 138338 / 105843.622442471292742994
- check_submission.py: submission package checks passed
- Blocked on: none
- Next step: commit、push、等待最终 GitHub checks

## DriftCheckDraft

- Scope status: Stage-A 证据完整，本地 final gate 通过
- Compatibility status: submit SHA/score 不变，算法和 Stage B 未触碰
- Retirement status: pre-P0 smoke 仅历史保留并已降权
- New risk signals:
- 等待最终证据提交 HEAD 的 GitHub CI
- Advisory decision: needs-verification
