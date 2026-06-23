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
