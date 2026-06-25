# PR7 Stage-A 工具链验证 - Intent

## TaskIntentDraft

- Requested outcome: 完成 PR7 Stage-A sanitizer、编译器优化一致性和最终证据闸门
- Goal: 完成 PR7 Stage-A sanitizer、编译器优化一致性和最终证据闸门
- Success evidence:
- UBSan、ASan、TSan、GCC/Clang O0/O3 全部语义一致，submit SHA 不变，完整回归通过
- Stop condition: 完成全部证据后结束；依赖缺失则 needs-verification；禁止进入 Stage B
- Non-goals:
- Stage B、性能 GO 决策、submit 变更
- Scope: bench/way1 工具链验证、CI、证据汇总和 PR 文档
- Change kinds:
- verification
- Risk hints:
- TSan 运行环境兼容性和 CI 产物取回

## BaselineReadSetHint

- /mnt/c/Users/Xing/Desktop/PR 1：冻结基线与修复 provenance.md
- bench/way1/PROTOCOL.md
- bench/way1/SUMMARY.md

## ImpactStatementDraft

- Compatibility boundary: 不修改算法、不调用 exact dyadic backend、不运行完整 2^32 域
- Affected layers:
- benchmark verification
- Owners:
- bench/way1
- Invariants:
- submit.txt SHA256 保持 7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e
- Non-goals:
- Stage B、性能 GO 决策、submit 变更

These records are Method Pack drafts / hints, not authoritative runtime decisions.
