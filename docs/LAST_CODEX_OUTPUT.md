# Last Codex Output

## 1. Commit

- commit hash: `af1541b`
- branch: main
- git status --short: clean

## 2. Task Summary

**目标**: 收敛 regression / smoke 的验收口径，删除 DEGRADED_PASS 说法。统一为：SUCCESS → PASS，DEGRADED_STRUCTURAL → DEGRADED，BLOCKED_UNDERSTANDING → BLOCKED，FAILED → FAIL。DEGRADED 和 BLOCKED 不算 PASS。

**实际完成**:
- 搜索全项目：无 PARTIAL_USABLE / usability_status / reader_ready / PASS_USABLE / SAFE_NOT_USABLE（干净）
- 删除 `DEGRADED_PASS` 共 24 处引用（代码 + 文档 + 测试）
- `evaluate_gating()`: BLOCKED_UNDERSTANDING 返回 "BLOCKED"（原 "DEGRADED"）；DEGRADED_STRUCTURAL 返回 "DEGRADED"；no-LLM BASELINE 返回 "DEGRADED"
- `run_main_chain_smoke.py` exit code: 仅 PASS 返回 0，DEGRADED/BLOCKED/FAIL 返回 2
- `run_main_chain_matrix.py`: 统计拆分 passed/degraded/blocked/failed
- `run_literature_acquisition_smoke.py`: 同口径 + exit code 仅 PASS 返回 0
- `docs/STATUS.md`: 所有 verdict 列的 DEGRADED_PASS → DEGRADED
- 前端 StatusBanner: 未改动——早已正确显示 "Degraded understanding" 而非 "通过"
- 不改变 QualityAuditor / FSA-5 / cards gating
- 未进入 M4

## 3. Code Changes

| 文件 | 改动 |
|------|------|
| `scripts/run_main_chain_smoke.py` | `evaluate_gating()`: BLOCKED_UNDERSTANDING 返回 "BLOCKED"（原 "DEGRADED"）。main() exit code 仅 PASS 返回 0。 |
| `scripts/run_main_chain_matrix.py` | `_build_summary()`: 统计 passed/degraded/blocked/failed 独立。`_classify_failure_root_cause()`: 添加 "BLOCKED" 分支。print_table: 展示 DEGRADED/BLOCKED/FAIL 拆分。 |
| `scripts/run_literature_acquisition_smoke.py` | `_verdict()`: 返回 "DEGRADED" 非 "DEGRADED_PASS"。main() exit code 仅 PASS 返回 0。 |
| `docs/STATUS.md` | 所有表格 verdict 列 DEGRADED_PASS → DEGRADED |
| `tests/test_main_chain_smoke.py` | 3 处断言更新，1 个测试重命名 |
| `tests/test_main_chain_matrix.py` | 3 处 fixture/断言更新 |
| `tests/test_literature_acquisition_fulltext.py` | 1 处断言更新 |

## 4. 新验收口径

| final_status | 新 verdict | 算 PASS? | reader_ready? |
|-------------|-----------|---------|--------------|
| SUCCESS | PASS | 是 | 是 |
| DEGRADED_STRUCTURAL | DEGRADED | 否 | 否 |
| BLOCKED_UNDERSTANDING | BLOCKED | 否 | 否 |
| FAILED | FAIL | 否 | 否 |
| BASELINE_ONLY (no LLM) | DEGRADED | 否 | 否 |

reader_ready 规则：`final_status == "SUCCESS"`。不写入 schema，不扩散到各模块。

## 5. Tests

- backend: **565 passed**, 15 skipped（0 fail）
- frontend: **42 passed**
- build: **success**

DEGRADED_PASS 遗留搜索：全项目 0 命中。

## 6. Current Strict Status

- **Broad REAL_E2E**: 否
- **Product-ready**: 否。DEGRADED 和 BLOCKED 不再计入 PASS。
- **M4 started**: 否
- **Current max shortfall**: (1) S2_API_KEY 缺失；(2) 2/12 矩阵条目为 DEGRADED（PDF-fallback 固有局限）；(3) 无新状态体系引入。

## 7. Next Suggested Step

无。验收口径已收敛，无需进一步复杂化。
