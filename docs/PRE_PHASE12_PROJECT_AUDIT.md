# Pre-Phase12 Project Audit

审计日期: 2026-06-03
审计范围: Phase 0-11 全项目复查
结论: 项目健康，可进入 Phase 12

---

## A. Phase 0 / 项目基础

| 检查项 | 结果 |
|--------|------|
| README 与当前结构一致 | WARNING - README 可能描述过时的启动方式 |
| pyproject.toml 依赖合理 | PASS - 10 个 runtime 依赖，无多余 |
| .gitignore 完整 | PASS - 覆盖 .env/.venv/__pycache__/workspace/outputs 等 |
| .env.example 只有占位符 | PASS |
| 默认 pytest 排除 legacy/e2e | PASS - --ignore=legacy_tests --ignore=tests_e2e |
| GitHub 上传安全 | PASS - .env 未上传，旧历史已清除 |
| 无真实 key/大文件/缓存进仓库 | PASS |

## B. 架构边界

| 检查项 | 结果 |
|--------|------|
| 新功能只走 src/researchsensei/ | PASS - 0 个 backend/ import |
| 旧 backend/ 无 import | PASS |
| Vue 前端未误改 | PASS |
| legacy_tests/e2e 不进入默认 pytest | PASS |
| 无重复造轮子 | PASS |
| 模块边界清晰 | PASS |

## C. Phase 1-11 逐阶段检查

| Phase | 目标 | 状态 | 核心模块 | artifact | 测试数 | 问题 |
|-------|------|------|----------|----------|--------|------|
| 1 | 项目骨架/CLI | COMPLETE | __init__, __main__ | N/A | 4 | 无 |
| 2 | 配置/schema | COMPLETE | core/, schemas/ | N/A | 15 | 无 |
| 3 | workspace/job store | COMPLETE | workspace/, jobs/ | workspace 结构 | 8 | 无 |
| 4 | 文档解析 | COMPLETE | ingestion/ | parsed_document.json | 4 | 无 |
| 5 | source_resolver + API | COMPLETE | source_resolver, web/ | source_status.json | 27 | 无 |
| 6 | grounding + skeleton | COMPLETE | grounding, paper_skeleton | evidence_index, paper_skeleton | 8 | 无 |
| 7 | LLM infrastructure | COMPLETE | llm/ (6 files) | N/A | 70 | 无 |
| 8 | paper_card | COMPLETE | paper_card.py | paper_card.json | 18 | 无 |
| 9 | formula_cards | COMPLETE | formula_card.py | formula_cards.json | 17 | 无 |
| 10 | teaching_cards | COMPLETE | teaching_card.py | teaching_cards.json | 22 | 无 |
| 11 | direction/reading_plan | COMPLETE | query/, acquisition/, selection/, direction/ | 4 artifacts | 44 | 无 |

## D. Artifact 链路

### 单篇论文链路: 7/7 完整

| Artifact | 生成模块 | Schema | 测试 |
|----------|----------|--------|------|
| source_status.json | source_resolver | SourceStatus | YES |
| parsed_document.json | ingestion | DocumentIngestion | YES |
| evidence_index.json | grounding | EvidenceIndex | YES |
| paper_skeleton.json | paper_skeleton | PaperSkeleton | YES |
| paper_card.json | paper_card | PaperCard | YES |
| formula_cards.json | formula_card | FormulaCardBundle | YES |
| teaching_cards.json | teaching_card | TeachingCardBundle | YES |

### 方向链路: 4/4 完整

| Artifact | 生成模块 | Schema | 测试 |
|----------|----------|--------|------|
| query_plan.json | query/planner | QueryPlan | YES |
| candidate_pool.json | selection/service | CandidatePool | YES |
| filtered_candidates.json | selection/service | CandidatePool | YES |
| reading_plan.json | selection/service | ReadingPlan | YES |

无越界生成，无下游跳过上游。

## E. 测试体系

| 检查项 | 结果 |
|--------|------|
| 默认 pytest 真实联网 | NO |
| 默认 pytest 真实调 LLM | NO |
| 外部 API 用 MockTransport | YES |
| LLM 用 MockLLMClient | YES |
| P0 quality tests 生效 | YES - 23 tests |
| error path 覆盖 | 23/32 files |
| JSON round-trip 覆盖 | 8 files |
| quality smoke 覆盖 | YES - 8 tests |
| flaky 风险 | LOW |

## F. 内容质量

| 检查项 | 结果 |
|--------|------|
| paper_card 有质量门槛 | YES - P0 grounding + hallucination tests |
| formula_cards 避免假公式 | YES - P0 formula tests |
| teaching_cards 避免公式当人话 | YES - Phase 10 fix + P0 tests |
| reading_plan selection_reason | WARNING - 仍偏模板化，P1 待补 |
| 6 个 hard-fail 条件覆盖 | YES - HF-1 through HF-6 covered |
| P1 genericness tests | NOT YET - 可 Phase 12 后补 |

## G. Phase 12 准入判断

| 问题 | 回答 |
|------|------|
| Phase 12 应确认 = patterns + drill | YES - 以 PHASE_MAPPING.md 为权威 |
| 工程可靠性冲突 | RESOLVED - 推迟到后续 Phase |
| P0 quality tests 全部通过 | YES - 23/23 |
| 是否有阻塞 issue | NO |
| 可以进入 Phase 12 设计 | YES |
| 可以进入 Phase 12 代码开发 | YES - 需先确认 scope |

---

## H/M/L Issue 清单

### HIGH

无。

### MEDIUM

| # | 问题 | 状态 |
|---|------|------|
| M1 | 6 个根级 .py 文件组织不佳 | OPEN - 不阻塞 Phase 12 |
| M2 | 5 个 helper 函数在 3 个 card 文件中重复 | OPEN - 不阻塞 Phase 12 |
| M3 | aiosqlite 依赖声明但未使用 | OPEN - 不阻塞 Phase 12 |

### LOW

| # | 问题 | 状态 |
|---|------|------|
| L1 | selection/service.py 硬编码 current_year=2026 | OPEN |
| L2 | test_v05_docs_contracts 用相对路径 | OPEN |
| L3 | 无 conftest.py 共享 fixture | OPEN |
| L4 | .gitignore 缺 *.egg-info 等 | FIXED |
| L5 | 无自定义 pytest marker | OPEN |

---

## 测试结果

- P0 quality tests: 23 passed
- Full pytest: 269 passed
- 0 failures
