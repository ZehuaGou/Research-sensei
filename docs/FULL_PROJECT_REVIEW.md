# Full Project Review: ResearchSensei Phase 1-11

审计日期: 2026-06-03
审计范围: Phase 1-11 全部代码、测试、文档、artifact 链路
审计方法: 静态代码分析 + pytest 运行 + 文档交叉验证

---

## 0. 审计时环境状态

| 项目 | 值 |
|------|-----|
| 分支 | master |
| 最近 commit | 26a897a fix phase 10 teaching card quality issues |
| 未提交变更 | 3 文件 modified + 11 文件 untracked (Phase 11 新增) |
| pytest 结果 | 213 passed, 18 failed |
| 失败原因 | 全部 18 个失败因 `python-multipart` 未安装 (FastAPI form data) |
| Phase 11 新增测试 | 29/29 passed (独立验证) |
| 源码总量 | 47 Python 文件, ~4650 行 |
| 测试总量 | 32 test files, 228 test functions |

---

## 1. 总体结论

**项目健康，可以进入 Phase 12。** 有 3 个 Phase 11 功能缺口需修复，1 个环境问题需处理，若干代码质量问题可后续优化。

核心评价:
- 架构边界干净: 0 个 `backend/` import，新代码全部在 `src/researchsensei/`
- 测试隔离合格: 默认 pytest 不联网、不调 LLM、不依赖外部服务
- Artifact 链路完整: Phase 1-10 的 7 个 artifact 全部可生成、可查询、有 schema
- Phase 11 链路基本完整，缺 `filtered_candidates.json` 和三路去重
- 文档基本准确，但 PROGRESS.md 对 Phase 11 的 "complete" 标记过早

---

## 2. Phase 1-11 完成度表

| Phase | 名称 | 状态 | 核心文件 | 测试数 | Mock | Artifact | 缺口 |
|-------|------|------|----------|--------|------|----------|------|
| 1 | 项目骨架/CLI/healthcheck | DONE | `__init__.py`, `__main__.py` | 4 | N/A | N/A | 无 |
| 2 | 配置/日志/错误/schema/StatusEnvelope | DONE | `core/`, `schemas/` | 15 | N/A | N/A | 无 |
| 3 | workspace/job store/artifact 写入 | DONE | `workspace/`, `jobs/` | 8 | N/A | workspace 结构 | 无 |
| 4 | 单篇文档解析 | DONE | `ingestion/lightweight.py` | 4 | N/A | parsed_document.json | 无 |
| 5 | source_resolver + parse API + job 查询 | DONE | `source_resolver.py`, `web/app.py` | 22 | MockTransport | source_status.json | 无 |
| 6 | grounding/evidence + paper_skeleton | DONE | `grounding.py`, `paper_skeleton.py` | 8 | N/A | evidence_index.json, paper_skeleton.json | 无 |
| 7 | LLM client/mock/prompt/cache/token | DONE | `llm/` (6 files) | 48 | MockLLMClient | N/A | 无 |
| 8 | paper_card.json | DONE | `paper_card.py`, `schemas/cards.py` | 18 | MockLLMClient | paper_card.json | 无 |
| 9 | formula_cards.json | DONE | `formula_card.py` | 17 | MockLLMClient | formula_cards.json | 无 |
| 10 | teaching_cards.json | DONE | `teaching_card.py` | 22 | MockLLMClient | teaching_cards.json | 无 |
| 11 | query/acquisition/selection/reading_plan | DONE | `query/`, `acquisition/`, `selection/`, `direction/` | 44 | MockTransport + MockLLM | query_plan.json, candidate_pool.json, filtered_candidates.json, reading_plan.json | 无 |

---

## 3. 高优先级问题

### H1: Phase 11 缺少三路去重逻辑

**严重度**: HIGH → **[已修复]**
**位置**: `src/researchsensei/selection/service.py`
**修复**: 新增 `deduplicate()` 方法，DOI → arXiv ID → normalized_title 三路去重，合并更完整元数据（abstract/citation_count/pdf_url 等）。8 个新增测试覆盖。

### H2: Phase 11 缺少 filtered_candidates.json 中间产物

**严重度**: HIGH → **[已修复]**
**位置**: `src/researchsensei/direction/runner.py`
**修复**: DirectionRunner 现在写出 4 个 artifact（query_plan/candidate_pool/filtered_candidates/reading_plan）。DirectionBundle 新增 `filtered_candidates` 字段。reading_plan 基于 filtered_candidates 构建。

### H3: 18 个测试因 python-multipart 缺失失败

**严重度**: HIGH → **[已修复]**
**位置**: `tests/test_api_documents_parse.py`, `tests/test_api_jobs_artifacts.py`, `tests/test_api_parse_sources.py`, `tests/test_package_healthcheck.py`
**修复**: `python-multipart>=0.0.20` 已安装到当前环境。该依赖已在 pyproject.toml 中声明，是 FastAPI multipart upload 的必要依赖。全部 18 个测试恢复通过。

---

## 4. 中优先级问题

### M1: SearchIntent 是 Pydantic model 而非 Enum

**严重度**: MEDIUM → **[已修复]**
**位置**: `src/researchsensei/schemas/enums.py`, `src/researchsensei/schemas/direction.py`
**修复**: `SearchIntent` 改为 `str, Enum`，值为 GENERAL/SURVEY/FOUNDATIONAL/SOTA/BENCHMARK/CODE。`QueryPlan.search_intents` 改为 `list[SearchIntent]`。QueryPlanner 使用 `_parse_intents()` 安全转换。3 个新增测试覆盖。

### M2: max_a_read 默认值 = 8，spec 允许最多 12

**严重度**: MEDIUM
**位置**: `src/researchsensei/selection/service.py:25`
**问题**: `SelectionService.__init__(self, max_a_read: int = 8)`。spec 说 "A_READ 默认不超过 12 篇"。当前 8 在 spec 范围内，但可能过早截断。
**影响**: 如果搜索质量高，用户可能错过有价值的论文。
**修复建议**: 考虑提高到 10-12，或让 DirectionRunner 可配置。

### M3: 6 个根级 Python 文件组织不佳

**严重度**: MEDIUM
**位置**: `src/researchsensei/` 根目录
**问题**: `paper_card.py`, `formula_card.py`, `teaching_card.py`, `paper_skeleton.py`, `grounding.py`, `source_resolver.py` 放在包根目录而非子模块。它们分别只被 `ingestion/pipeline.py` 或 `web/app.py` 导入。
**影响**: 包结构不清晰，新开发者难以理解模块边界。
**修复建议**: 后续可移入 `ingestion/` 或 `cards/` 子模块，但不阻塞 Phase 12。

### M4: 5 个 helper 函数在 3 个文件中重复

**严重度**: MEDIUM
**位置**: `paper_card.py`, `formula_card.py`, `teaching_card.py`
**问题**: `_format_evidence_for_prompt()`, `_collect_evidence_refs()`, `_overall_status()`, `_collect_warnings()`, `_bundle_confidence()` 在三个文件中各有一份，签名略有不同。
**影响**: 维护成本高，修改一处需改三处。
**修复建议**: 提取到 `cards/_utils.py` 共享模块。

### M5: aiosqlite 依赖声明但未使用

**严重度**: MEDIUM
**位置**: `pyproject.toml` 第 12 行
**问题**: 声明 `aiosqlite>=0.19` 但 `JobStore` 使用同步 `sqlite3`。
**影响**: 不必要的依赖。
**修复建议**: 移除 aiosqlite 或迁移到异步 sqlite。

---

## 5. 低优先级问题

### L1: selection/service.py 硬编码 current_year = 2026

**位置**: `src/researchsensei/selection/service.py:199`
**影响**: 2027 年后 recency_bonus 计算会偏差。低风险，因为 reading_plan 是一次性产物。
**修复**: `from datetime import date; current_year = date.today().year`

### L2: test_v05_docs_contracts.py 使用相对路径 Path("docs")

**位置**: `tests/test_v05_docs_contracts.py:16`
**影响**: 如果 CWD 不是项目根目录会失败。
**修复**: 改用 `Path(__file__).resolve().parents[1] / "docs"`。

### L3: 无 conftest.py，无共享 fixture

**位置**: 项目根目录和 tests/ 目录
**影响**: 每个测试文件独立创建测试数据，存在重复代码。
**修复**: 后续可添加 conftest.py 提供共享 fixture（如 sample_document, sample_paper_card）。

### L4: .gitignore 缺少 *.egg-info, build/, .mypy_cache/

**位置**: `.gitignore`
**影响**: 极低，这些目录通常在 .venv 中。
**修复**: 补充条目。

### L5: legacy_tests 中 2 个测试会调用真实 LLM

**位置**: `legacy_tests/test_v05_formula_context_interactive.py`, `legacy_tests/test_v05_ingestion_grounding_understanding.py`
**影响**: 已通过 `--ignore=legacy_tests` 排除，不影响默认测试。
**修复**: 无需处理，legacy_tests 已冻结。

### L6: 无自定义 pytest marker

**位置**: `pyproject.toml`
**影响**: 无法按类型（slow/network/llm）筛选测试。
**修复**: 后续可添加 `[tool.pytest.ini_options] markers`。

---

## 6. 架构边界检查

| 检查项 | 结果 |
|--------|------|
| 新功能只走 src/researchsensei/ | PASS - 0 个 backend/ import |
| 旧 backend/ 冻结 | PASS - 未被修改 |
| legacy_tests/ 不进入默认测试 | PASS - --ignore=legacy_tests |
| tests_e2e/ 不混入默认测试 | PASS - --ignore=tests_e2e |
| Vue 前端未被误改 | PASS - frontend/ 未修改 |
| 无重复造轮子 | PASS - Phase 7 LLM/cache/schema 全部复用 |

---

## 7. Artifact 链路检查

### 7.1 单篇论文链路 (Phase 4-10)

```
source_status.json → parsed_document.json → evidence_index.json
→ paper_skeleton.json → paper_card.json → formula_cards.json
→ teaching_cards.json
```

| Artifact | 生成模块 | Schema | 测试 | API 可查 |
|----------|----------|--------|------|----------|
| source_status.json | source_resolver.py | SourceStatus | YES | YES |
| parsed_document.json | ingestion/lightweight.py | DocumentIngestion | YES | YES |
| evidence_index.json | grounding.py | EvidenceIndex | YES | YES |
| paper_skeleton.json | paper_skeleton.py | PaperSkeleton | YES | YES |
| paper_card.json | paper_card.py | PaperCard | YES | YES |
| formula_cards.json | formula_card.py | FormulaCardBundle | YES | YES |
| teaching_cards.json | teaching_card.py | TeachingCardBundle | YES | YES |

**结论**: 单篇论文链路完整，7/7 artifact 全部可生成、有 schema、有测试、API 可查。

### 7.2 Direction 链路 (Phase 11)

```
用户输入 → query_plan.json → candidate_pool.json
→ filtered_candidates.json → reading_plan.json
```

| Artifact | 生成模块 | Schema | 测试 | API 可查 | 状态 |
|----------|----------|--------|------|----------|------|
| query_plan.json | query/planner.py | QueryPlan | YES | NO (只写文件) | DONE |
| candidate_pool.json | selection/service.py | CandidatePool | YES | NO | DONE |
| filtered_candidates.json | -- | -- | -- | -- | **MISSING** |
| reading_plan.json | selection/service.py | ReadingPlan | YES | NO | DONE |

**结论**: 缺少 filtered_candidates.json。Direction 链路未接入 web API（无 `/api/v1/directions/` endpoint）。

### 7.3 边界检查

| 检查项 | 结果 |
|--------|------|
| 搜索结果直接生成 paper_card | PASS - 不存在越界 |
| reading_plan 直接进入多论文精读 | PASS - 不存在越界 |
| 每个 artifact 有明确生成模块 | PASS (除 filtered_candidates.json) |
| 每个 artifact 有 schema | PASS (除 filtered_candidates.json) |
| artifact 可被 job/artifact API 读到 | PARTIAL - direction 链路 artifact 未接入 API |

---

## 8. 逐阶段验收检查

### Phase 1: 项目骨架
- **完成**: YES
- **核心文件**: `__init__.py`, `__main__.py`
- **测试**: `test_package_healthcheck.py` (4 tests)
- **Mock**: N/A
- **缺口**: CLI 只有 healthcheck 子命令，无业务 CLI

### Phase 2: 配置/日志/错误/schema
- **完成**: YES
- **核心文件**: `core/config.py`, `core/errors.py`, `core/logging.py`, `schemas/common.py`, `schemas/enums.py`
- **测试**: `test_core_config.py` (5), `test_core_errors_logging.py` (4), `test_schemas_core.py` (6)
- **Mock**: N/A
- **缺口**: 无

### Phase 3: workspace/job store
- **完成**: YES
- **核心文件**: `workspace/store.py`, `jobs/store.py`
- **测试**: `test_workspace_store.py` (4), `test_job_store.py` (4)
- **Mock**: N/A
- **缺口**: 无

### Phase 4: 单篇文档解析
- **完成**: YES
- **核心文件**: `ingestion/lightweight.py`
- **测试**: `test_lightweight_ingestion.py` (4)
- **Mock**: N/A
- **缺口**: 无

### Phase 5: source_resolver + parse API
- **完成**: YES
- **核心文件**: `source_resolver.py`, `web/app.py`
- **测试**: `test_source_resolver.py` (10), `test_api_parse_sources.py` (8), `test_api_documents_parse.py` (5), `test_api_jobs_artifacts.py` (4)
- **Mock**: MockTransport (4 tests)
- **缺口**: test_api_documents_parse 和 test_api_jobs_artifacts 因 python-multipart 失败

### Phase 6: grounding + paper_skeleton
- **完成**: YES
- **核心文件**: `grounding.py`, `paper_skeleton.py`, `schemas/evidence.py`, `schemas/skeleton.py`
- **测试**: `test_phase6_evidence_schemas.py` (4), `test_phase6_grounding.py` (2), `test_phase6_paper_skeleton.py` (2)
- **Mock**: N/A
- **缺口**: 无

### Phase 7: LLM client/mock/prompt/cache
- **完成**: YES
- **核心文件**: `llm/client.py`, `llm/prompt_builder.py`, `llm/response_cache.py`, `llm/token_budget.py`, `llm/types.py`
- **测试**: `test_llm_client.py` (24), `test_prompt_builder.py` (13), `test_response_cache.py` (18), `test_token_budget.py` (8), `test_llm_config.py` (7)
- **Mock**: MockLLMClient
- **缺口**: 无

### Phase 8: paper_card.json
- **完成**: YES
- **核心文件**: `paper_card.py`, `schemas/cards.py`
- **测试**: `test_paper_card_schema.py` (7), `test_paper_card_builder.py` (11)
- **Mock**: MockLLMClient
- **缺口**: 无

### Phase 9: formula_cards.json
- **完成**: YES
- **核心文件**: `formula_card.py`
- **测试**: `test_formula_card_schema.py` (7), `test_formula_card_builder.py` (10)
- **Mock**: MockLLMClient
- **缺口**: 无

### Phase 10: teaching_cards.json
- **完成**: YES
- **核心文件**: `teaching_card.py`
- **测试**: `test_teaching_card_schema.py` (5), `test_teaching_card_builder.py` (17)
- **Mock**: MockLLMClient
- **缺口**: 无

### Phase 11: query/acquisition/selection/reading_plan
- **完成**: PARTIAL
- **核心文件**: `query/planner.py`, `acquisition/arxiv_adapter.py`, `acquisition/openalex_adapter.py`, `selection/service.py`, `direction/runner.py`, `schemas/direction.py`
- **测试**: `test_query_planner.py` (5), `test_acquisition_adapters.py` (7), `test_direction_runner.py` (3), `test_direction_schemas.py` (7), `test_selection_service.py` (7)
- **Mock**: MockTransport + MockLLMClient
- **缺口**:
  1. 三路去重未实现
  2. filtered_candidates.json 未生成
  3. max_a_read=8 (spec 允许 ≤12)
  4. SearchIntent 非 Enum

---

## 9. 测试体系检查

| 检查项 | 结果 |
|--------|------|
| 默认 pytest 会真实联网 | NO - 所有网络测试用 MockTransport |
| 默认 pytest 会真实调 LLM | NO - 所有 LLM 测试用 MockLLMClient |
| arXiv/OpenAlex 全部 MockTransport | YES - test_acquisition_adapters.py |
| 存在 flaky test | LOW RISK - test_v05_docs_contracts 用相对路径 |
| 只测 happy path | 部分 - 23/32 文件有 error path 测试 |
| 缺少 error path 测试 | 9 文件只有 happy path (见下表) |
| 缺少 artifact JSON 可读性测试 | 18 文件不验证 JSON 内容 |
| 缺少 schema validation 测试 | 24 文件不做 round-trip 验证 |
| 缺少 runner smoke test | test_direction_runner.py 有 pipeline smoke |
| 缺少 regression test | 无专门 regression 测试 |

### 缺少 error path 测试的文件

| 文件 | 建议补充的 error path |
|------|----------------------|
| test_v05_docs_contracts.py | 文档不存在时的处理 |
| test_workspace_store.py | 写入失败（磁盘满）处理 |
| test_token_budget.py | 空输入、超大输入 |
| test_package_healthcheck.py | CLI 参数错误 |
| test_phase6_grounding.py | 空文档输入 |
| test_phase6_paper_skeleton.py | 全 UNKNOWN skeleton |
| test_paper_card_schema.py | 无效 evidence_ref 格式 |
| test_formula_card_schema.py | 空 symbols 列表 |
| test_direction_schemas.py | 空 core_terms、无效 year |

### 缺少 schema round-trip 测试的文件

| 文件 | 建议补充 |
|------|----------|
| test_workspace_store.py | write_json → read → model_validate |
| test_job_store.py | create → get → JobRecord validate |
| test_source_resolver.py | SourceStatus round-trip |
| test_phase6_grounding.py | EvidenceIndex round-trip |
| test_phase6_paper_skeleton.py | PaperSkeleton round-trip |
| test_paper_card_builder.py | PaperCard full round-trip |
| test_formula_card_builder.py | FormulaCardBundle round-trip |
| test_teaching_card_builder.py | TeachingCardBundle round-trip |
| test_direction_runner.py | DirectionBundle full round-trip |
| test_selection_service.py | ReadingPlan round-trip |

---

## 10. Phase 10 内容质量回归检查

| 检查项 | 结果 |
|--------|------|
| human_explanation 是否可能输出公式文本 | PASS - `_is_formula_heavy()` 检测并降级 |
| formula-heavy 文本有 conservative fallback | PASS - 降级到保守描述 |
| confidence 合理降低 | PASS - formula-heavy 时 ≤ 0.3 |
| teaching_cards 面向论文理解 | PARTIAL - rule-based 的 paper_role_explanation 仍偏模板化 |
| 新增 7 个内容质量测试 | PASS - test_teaching_card_builder.py 中有 7 个专门测试 |

**结论**: Phase 10 修复已落地，核心问题（公式文本当人话）已解决。剩余的模板化问题是 rule-based 路径的固有限制，需 LLM 增强才能真正解决。

---

## 11. Phase 11 专项检查

| # | 检查项 | 状态 | 说明 |
|---|--------|------|------|
| 1 | SearchIntent 是 Enum | NO | Pydantic model with str field，非 Enum |
| 2 | QueryPlan schema 完整 | YES | 11 字段，含 warnings |
| 3 | CandidatePaper 完整 | YES | 14 字段，含 normalized_title/doi/arxiv_id |
| 4 | arXiv Adapter 用 Atom API | YES | XML 解析，extract_arxiv_ns |
| 5 | OpenAlex Adapter 用 REST API | YES | JSON 解析 |
| 6 | abstract_inverted_index 正确还原 | YES | `_openalex_abstract()` 有测试 |
| 7 | candidate_pool 聚合多来源 | YES | DirectionRunner._acquire() 遍历 sources |
| 8 | filtered_candidates.json 生成 | **NO** | 不存在 |
| 9 | 三路去重实际接入 | **NO** | _normalize_candidate 存在但未去重 |
| 10 | reading_plan 每篇有 scoring_breakdown/selection_reason/risk_note | YES | _score_item() 全部生成 |
| 11 | A_READ 默认不超过 12 | YES | max_a_read=8，≤ 12 |
| 12 | mock smoke test 跑完整 direction runner | YES | test_direction_runner_full_pipeline |

---

## 12. 文档一致性检查

| 文档 | 状态 | 问题 |
|------|------|------|
| docs/PROGRESS.md | **过早标记 complete** | 声称 Phase 11 完成，但三路去重和 filtered_candidates.json 未实现 |
| docs/PHASE_MAPPING.md | 基本一致 | Phase 11 标记 complete 需改为 partial |
| docs/OPEN_QUESTIONS.md | 需更新 | #8 (Phase 10 教学卡质量) 已修复但未关闭 |
| docs/PHASE_10_REVIEW.md | 已反映修复 | 修复标记 [已修复] 已添加 |
| docs/PHASE_1_7_REVIEW.md | 一致 | 无问题 |
| docs/REUSE_REPORT.md | 一致 | Phase 11 复用评估准确 |
| docs/ARCHITECTURE_DECISION.md | 一致 | 无问题 |
| docs/MIGRATION_PLAN.md | 一致 | 无问题 |
| docs/PHASE_11_REVIEW.md | **不存在** | 建议创建 |
| docs/FULL_PROJECT_REVIEW.md | 本文档 | -- |

---

## 13. 代码质量检查

| 检查项 | 结果 |
|--------|------|
| 未使用文件/死代码 | 无 |
| 重复 schema | 无 |
| 重复 service | 5 个 helper 函数重复 (M4) |
| 过大函数 | teaching_card.py 558 行，最大文件但无单函数 > 60 行 |
| 异常吞掉不报 | 无 (source_resolver 已修复) |
| 不稳定路径/硬编码 | L2: test_v05_docs_contracts 用相对路径 |
| 测试依赖本地环境 | python-multipart 缺失导致 18 个 API 测试失败 |
| API key/缓存/大文件误提交 | 无 - .gitignore 正确排除 .env/workspace/outputs |

---

## 14. 建议新增 unit tests

### Phase 11 补充测试

| 测试 | 文件 | 说明 |
|------|------|------|
| 三路去重 - DOI 匹配 | test_selection_service.py | 两篇同 DOI 论文应合并 |
| 三路去重 - arXiv ID 匹配 | test_selection_service.py | 两篇同 arXiv ID 应合并 |
| 三路去重 - 标题相似 | test_selection_service.py | 标题 only 大小写/标点差异应合并 |
| 三路去重 - 不同论文不去重 | test_selection_service.py | 不同论文应保留 |
| filtered_candidates.json 生成 | test_direction_runner.py | pipeline 应写出该文件 |
| DirectionBundle 完整性 | test_direction_runner.py | bundle 应含 filtered_candidates |
| 多源去重集成 | test_direction_runner.py | arXiv + OpenAlex 重叠论文去重 |

### 通用补充测试

| 测试 | 文件 | 说明 |
|------|------|------|
| workspace write_json round-trip | test_workspace_store.py | 写入 → 读取 → model_validate |
| JobRecord round-trip | test_job_store.py | create → get → validate |
| ReadingPlan round-trip | test_selection_service.py | build → dump → validate |

---

## 15. 建议新增 smoke tests

| Smoke Test | 说明 |
|------------|------|
| direction runner 全链路 | 已有 test_direction_runner_full_pipeline |
| 单篇论文全链路 | 已有 test_single_paper_ingestion_runner |
| web API health check | 已有 test_package_healthcheck |
| direction + 单篇联合 | 建议: direction 产出 reading_plan → 选一篇 → 单篇精读 |

---

## 16. 进入 Phase 12 前必须修复的问题

| # | 问题 | 严重度 | 工作量 | 说明 |
|---|------|--------|--------|------|
| 1 | 安装 python-multipart | HIGH | 1 min | `pip install python-multipart`，解决 18 个测试失败 |
| 2 | 实现三路去重 | HIGH | ~30 行 | selection/service.py 添加 deduplicate() |
| 3 | 生成 filtered_candidates.json | HIGH | ~15 行 | direction/runner.py + DirectionBundle schema |
| 4 | 更新 PROGRESS.md | MEDIUM | doc | Phase 11 改为 "partial" |
| 5 | 更新 OPEN_QUESTIONS.md | LOW | doc | 关闭 #8 |

---

## 17. 是否可以把 Phase 11 标记为 complete

**不可以。** 三路去重和 filtered_candidates.json 是 spec 明确要求的功能点，当前未实现。修复工作量约 45 行代码 + 测试，建议在进入 Phase 12 前完成。

---

## 18. 是否可以进入 Phase 12

**修复 H1/H2/H3 后可以。** 无架构阻塞，无安全阻塞。Phase 11 的缺口是功能性的，修复成本低。

Phase 12 前 checklist:
- [ ] `pip install python-multipart`
- [ ] 实现三路去重
- [ ] 生成 filtered_candidates.json
- [ ] 更新 PROGRESS.md / PHASE_MAPPING.md
- [ ] 全量 pytest 通过 (目标: 0 failures)
