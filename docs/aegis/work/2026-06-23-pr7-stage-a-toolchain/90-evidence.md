# PR7 Stage-A 工具链验证 - Evidence

Evidence entries below are method-pack references; the committed benchmark
artifacts and CI run remain the verification authority.

## EvidenceBundleDraft

- Artifact key: toolchain-matrix-test
- Type: test
- Source: tests/test_way1_stage_toolchain.py
- Summary: 69 个必需运行点的矩阵契约测试通过
- Verifier: python3 -X utf8 tests/test_way1_stage_toolchain.py

## EvidenceBundleDraft

- Artifact key: github-toolchain-run
- Type: ci
- Source: https://github.com/Roki-Xing/cryptomath-2026-problem3-final-submission/actions/runs/28031330588
- Summary: 69 点 UBSan/ASan/TSan/GCC/Clang O0/O3 矩阵通过，0 mismatch，submit SHA 不变
- Verifier: gh run view 28031330588 --json status,conclusion,jobs

## EvidenceBundleDraft

- Artifact key: stage-a-aggregate
- Type: manifest
- Source: bench/way1/STAGE_A_SUMMARY.json
- Summary: A0/A1/A2/toolchain 14 项协议闸门聚合为 STAGE_A_PASS
- Verifier: python3 -X utf8 tests/test_way1_stage_toolchain.py

## EvidenceBundleDraft

- Artifact key: final-release-gates
- Type: test
- Source: local final gate output
- Summary: clean build、make test、submit rebuild/cmp、score、check_submission 和三层 SHA 均通过
- Verifier: CPLUS_INCLUDE_PATH=/tmp/boost-headers/usr/include make test && python3 -X utf8 experiments/build_submit_from_sources.py --out /tmp/submit_rebuilt.txt && cmp submit.txt /tmp/submit_rebuilt.txt && ./score --dedup uv --positive-only submit.txt && python3 -X utf8 experiments/check_submission.py --submit submit.txt
