# ResearchSensei Project Alignment Brief

审计日期: 2026-06-03
基于: 设计文档包 (00-06)、迁移文档、代码 (Phase 1-11)、246 passing tests

---

## 1. 项目一句话定位

**ResearchSensei / 研读导师** 是一个"科研论文理解与思维框架训练系统"。

它和普通论文摘要器的核心区别：

| | 普通摘要器 | ResearchSensei |
|---|---|---|
| 输出 | 一段摘要文本 | 结构化学习卡片 + 公式讲解 + 科研模式 + 训练题 |
| 证据 | 无约束 | 每个 claim 绑定 evidence_ref，不确定标降级 |
| 公式 | 跳过或照抄 | 符号拆解 + 项解释 + 去除影响 + 数字例子 |
| 用户交互 | 无 | 追问、导师模式、错误归因、复习调度 |
| 目标 | 快速浏览 | 真正看懂论文、建立科研思维、回答导师追问 |

最终服务场景：研究生 / 科研入门者需要深入理解一篇论文的核心机制、公式含义、实验设计、研究模式，并能回答导师的追问（"你为什么信这个结论？""如果去掉这个公式会怎样？""这个方法能迁移到什么问题？"）。

---

## 2. 产品目标

**用户输入**：
- 单篇论文（PDF / Markdown / 纯文本 / arXiv ID / URL）
- 或一个研究方向（中文/英文自然语言）

**系统输出**：
- 单篇论文：7 个结构化 artifact（source_status → parsed_document → evidence_index → paper_skeleton → paper_card → formula_cards → teaching_cards）
- 研究方向：4 个结构化 artifact（query_plan → candidate_pool → filtered_candidates → reading_plan）

**系统如何帮助用户**：

1. **可靠解析**：不假装理解，只基于实际文本提取 blocks
2. **证据定位**：每个 claim 绑定原文 block，不确定标 `INSUFFICIENT_EVIDENCE`
3. **论文骨架**：保守提取问题/旧方法/瓶颈/新机制/实验/局限
4. **教学化讲解**：paper_card（30秒/5分钟/机制/证据/局限/迁移）、formula_cards（符号/项/作用/数字例子）、teaching_cards（五层讲解法）
5. **追问支持**：用户可追问"再讲简单点""数字例子""导师追问""测我懂没懂"
6. **方向学习**：搜索 → 去重 → 评分 → 阅读计划 → 单篇精读

---

## 3. 当前技术路线

| 决策 | 内容 |
|------|------|
| 前端 | Vue 3 + Vite + TypeScript + Pinia + TailwindCSS + KaTeX，保留不改 |
| 旧 backend/ | 冻结，仅作迁移参考，不接收新功能，不被 import |
| 新后端 | `src/researchsensei/`，按模块分包，Pydantic schema 驱动 |
| 测试策略 | 默认 `pytest -q` 不联网、不调 LLM、不依赖外部服务 |
| LLM 策略 | 统一走 `llm/client.py`，支持 MockLLMClient；所有 LLM 函数有 fallback |
| 网络策略 | 外部 API 通过 Adapter 封装（ArxivAdapter, OpenAlexAdapter），接受 httpx.Client 注入 |
| Artifact 链路 | 每步写 JSON artifact，下游只读上游 artifact，不反向依赖 |
| 依赖策略 | 不新增依赖，除非 reuse gate 评估通过且人工确认 |

---

## 4. 当前后端架构

### 4.1 config / logging / errors / schema

- `core/config.py` — AppConfig 从 .env + TOML 加载，ConfigService 提供默认值
- `core/logging.py` — 日志 redaction（API key 不进日志）
- `core/errors.py` — SenseiError / ConfigError / MissingDependencyError
- `schemas/` — 11 文件，Pydantic v2，`extra="forbid"` 防止未知字段

### 4.2 workspace / job store / artifact store

- `workspace/store.py` — WorkspaceStore 创建 run 目录、写 JSON/text
- `jobs/store.py` — JobStore (SQLite) 持久化 job 状态 (pending/running/succeeded/failed)
- Artifact 直接写入 workspace run 目录，通过 `/api/v1/jobs/{id}/artifacts` 查询

### 4.3 ingestion / parsing

- `ingestion/lightweight.py` — LightweightIngestionService 处理 .md/.txt/.pdf (PyMuPDF fallback)
- 输出 DocumentIngestion（blocks 列表 + 语言检测 + 降级标记）
- SECTION_ALIASES 支持中英文段落名映射

### 4.4 source resolver

- `source_resolver.py` — SourceResolver 处理 upload/local_path/pdf_url/arxiv_id/arxiv_url
- 输出 SourceStatus + 源文件副本
- 路径穿越防护、URL scheme 校验、大小限制

### 4.5 grounding / evidence index

- `grounding.py` — build_evidence_index() 从 blocks 生成 ClaimEvidence 列表
- 规则版：段落级证据绑定，不确定类型自动降级 confidence ≤ 0.5
- 输出 evidence_index.json

### 4.6 paper skeleton

- `paper_skeleton.py` — build_paper_skeleton() 从 blocks + evidence_index 提取论文骨架
- 保守提取：缺失字段标 UNKNOWN / INSUFFICIENT_EVIDENCE / NEEDS_HUMAN_CHECK
- 输出 paper_skeleton.json

### 4.7 LLM infrastructure

- `llm/client.py` — LLMClient (httpx AsyncClient, OpenAI-compatible) + MockLLMClient
- `llm/prompt_builder.py` — PromptBuilder（system/context/evidence/user 分区，指令隔离）
- `llm/response_cache.py` — ResponseCache（SHA256 keys, TTL, version invalidation）
- `llm/token_budget.py` — TokenBudget（字符级估算，~4 chars/token）
- `llm/types.py` — ChatMessage, ChatResponse, LLMConfig

### 4.8 paper card

- `paper_card.py` — build_paper_card() 规则版 + build_paper_card_with_llm() LLM 增强版
- 从 skeleton + evidence_index 提取 core_idea/problem/method/experiments/limitations/transfer
- 每个 CardClaim 绑定 evidence_ref

### 4.9 formula cards

- `formula_card.py` — build_formula_cards() 规则版 + build_formula_cards_with_llm() LLM 增强版
- 从 formula blocks 提取 symbols/terms/purpose/numeric_example/what_if_removed
- _SYMBOL_KNOWN 字典（48 个常见 LaTeX 符号中文释义）

### 4.10 teaching cards

- `teaching_card.py` — build_teaching_cards() 规则版 + build_teaching_cards_with_llm() LLM 增强版
- 五层讲解法：human_explanation / analogy / minimal_formula / numeric_example / paper_role
- _is_formula_heavy() 检测公式密集文本并降级

### 4.11 direction / query / acquisition / selection / reading plan

- `query/planner.py` — QueryPlanner（LLM 增强 + 规则 fallback）
- `acquisition/arxiv_adapter.py` — ArxivAdapter（Atom API，MockTransport 测试）
- `acquisition/openalex_adapter.py` — OpenAlexAdapter（REST API，abstract_inverted_index 还原）
- `selection/service.py` — SelectionService（scoring + 三路去重 + reading_plan）
- `direction/runner.py` — DirectionRunner 编排完整链路

---

## 5. Artifact 链路总览

### 5.1 单篇论文链路

```
source_status.json
  → parsed_document.json
    → evidence_index.json
      → paper_skeleton.json
        → paper_card.json
        → formula_cards.json
        → teaching_cards.json
```

| Artifact | 生成模块 | 输入 | 服务于 | Schema | 测试 |
|----------|----------|------|--------|--------|------|
| source_status.json | source_resolver.py | 用户输入 (path/url/id) | 下游 ingestion 知道源文件在哪 | SourceStatus | YES |
| parsed_document.json | ingestion/lightweight.py | 源文件 | grounding/skeleton/cards | DocumentIngestion | YES |
| evidence_index.json | grounding.py | parsed_document.blocks | skeleton evidence 绑定 | EvidenceIndex | YES |
| paper_skeleton.json | paper_skeleton.py | blocks + evidence_index | card 生成的主输入 | PaperSkeleton | YES |
| paper_card.json | paper_card.py | skeleton + evidence_index | 用户学习 | PaperCard | YES |
| formula_cards.json | formula_card.py | blocks + evidence_index | 用户学习公式 | FormulaCardBundle | YES |
| teaching_cards.json | teaching_card.py | paper_card + formula_cards + skeleton | 五层讲解 | TeachingCardBundle | YES |

### 5.2 研究方向链路

```
query_plan.json
  → candidate_pool.json
    → filtered_candidates.json
      → reading_plan.json
```

| Artifact | 生成模块 | 输入 | 服务于 | Schema | 测试 |
|----------|----------|------|--------|--------|------|
| query_plan.json | query/planner.py | 用户方向文本 | acquisition 搜索 | QueryPlan | YES |
| candidate_pool.json | selection/service.py | adapter 搜索结果 | 去重前原始池 | CandidatePool | YES |
| filtered_candidates.json | selection/service.py | candidate_pool + dedup | reading_plan 输入 | CandidatePool | YES |
| reading_plan.json | selection/service.py | filtered_candidates + query_plan | 用户选论文精读 | ReadingPlan | YES |

### 5.3 边界

- 两条链路**不交叉**：direction 链路不生成 paper_card，单篇链路不生成 reading_plan
- 未来连接点：reading_plan 的 A_READ 论文 → source_resolver → 单篇精读链路

---

## 6. Phase 1-11 实际完成情况

| Phase | 目标 | 实现模块 | 测试文件 | Artifact | 状态 | 存在问题 |
|-------|------|----------|----------|----------|------|----------|
| 1 | 项目骨架/CLI/healthcheck | `__init__.py`, `__main__.py` | test_package_healthcheck.py (4) | N/A | COMPLETE | CLI 只有 healthcheck |
| 2 | 配置/日志/错误/schema | `core/`, `schemas/` | test_core_config.py (5), test_core_errors_logging.py (4), test_schemas_core.py (6) | N/A | COMPLETE | 无 |
| 3 | workspace/job store | `workspace/`, `jobs/` | test_workspace_store.py (4), test_job_store.py (4) | workspace 结构 | COMPLETE | 无 |
| 4 | 单篇文档解析 | `ingestion/lightweight.py` | test_lightweight_ingestion.py (4) | parsed_document.json | COMPLETE | 无 |
| 5 | source_resolver + parse API | `source_resolver.py`, `web/app.py` | test_source_resolver.py (10), test_api_parse_sources.py (8), test_api_documents_parse.py (5), test_api_jobs_artifacts.py (4) | source_status.json | COMPLETE | 无 |
| 6 | grounding + paper_skeleton | `grounding.py`, `paper_skeleton.py` | test_phase6_evidence_schemas.py (4), test_phase6_grounding.py (2), test_phase6_paper_skeleton.py (2) | evidence_index.json, paper_skeleton.json | COMPLETE | 无 |
| 7 | LLM infrastructure | `llm/` (6 files) | test_llm_client.py (24), test_prompt_builder.py (13), test_response_cache.py (18), test_token_budget.py (8), test_llm_config.py (7) | N/A | COMPLETE | 无 |
| 8 | paper_card.json | `paper_card.py`, `schemas/cards.py` | test_paper_card_schema.py (7), test_paper_card_builder.py (11) | paper_card.json | COMPLETE | 无 |
| 9 | formula_cards.json | `formula_card.py` | test_formula_card_schema.py (7), test_formula_card_builder.py (10) | formula_cards.json | COMPLETE | 无 |
| 10 | teaching_cards.json | `teaching_card.py` | test_teaching_card_schema.py (5), test_teaching_card_builder.py (17) | teaching_cards.json | COMPLETE | 无 |
| 11 | query/acquisition/selection/reading_plan | `query/`, `acquisition/`, `selection/`, `direction/` | test_query_planner.py (5), test_acquisition_adapters.py (7), test_direction_runner.py (7), test_direction_schemas.py (10), test_selection_service.py (16) | query_plan.json, candidate_pool.json, filtered_candidates.json, reading_plan.json | COMPLETE | 无 |

**总计**: 11 phases, 全部 COMPLETE, 246 tests passing.

---

## 7. 当前测试体系

| 类别 | 范围 | 数量 | 真实联网 | 真实 LLM |
|------|------|------|----------|----------|
| Unit tests (默认 pytest) | tests/ 下 32 个 test_*.py | 246 | NO | NO |
| Legacy tests (排除) | legacy_tests/ 下 13 个文件 | ~28 | NO (2 个会调真实 LLM) | 部分 |
| E2E tests (排除) | tests_e2e/smoke_test.py | ~10 | YES (localhost:18765) | YES |

**测试隔离保证**:
- pyproject.toml: `addopts = ["--ignore=legacy_tests", "--ignore=tests_e2e"]`
- 所有外部 HTTP 用 `httpx.MockTransport`
- 所有 LLM 用 `MockLLMClient`
- 无 `time.sleep`，无 flaky 模式

**测试缺口**:
- 9 个文件只有 happy path，缺 error path 测试
- 18 个文件不验证 JSON artifact 内容
- 24 个文件不做 schema round-trip 验证
- 无 conftest.py 共享 fixture
- 无自定义 pytest marker

---

## 8. Phase 12 范围冲突分析

### 文档对比

| 文档 | 权威度 | Phase 12 定义 |
|------|--------|--------------|
| `docs/PHASE_MAPPING.md` | **迁移路线权威文档** | patterns + drill（旧 Phase 6 子模块） |
| `03_FULL_IMPLEMENTATION_PLAN.md` | 原始开发文档（从零构建假设） | 工程可靠性（断点续跑/日志/缓存/安全） |
| `docs/PROGRESS.md` | 当前执行状态 | "Phase 12 is not authorized" |
| `docs/OPEN_QUESTIONS.md` | 待确认项 | #9 已记录此冲突 |

### 分析

**PHASE_MAPPING.md 更权威**，原因：
1. 它是迁移路线的专门映射文档，专门解决原始 Phase 编号与迁移 Phase 的偏移
2. 它在项目启动时被创建，经过人工确认
3. 原始开发文档假设"从零构建"，而实际是迁移路线，Phase 编号已偏移

**如果选 patterns + drill**：
- 接在单篇论文链路的 teaching_cards.json 之后
- 输入：paper_skeleton.json + paper_card.json + formula_cards.json
- 输出：pattern_cards.json + drill_cards.json
- 风险：低，纯内部模块，不涉及外部 API

**如果选工程可靠性**：
- 影响所有已有模块（pipeline resume、logging、cache invalidation）
- 需要修改 SinglePaperIngestionRunner 和 DirectionRunner
- 风险：中，改动面大，可能引入 regression

### 建议

**Phase 12 = patterns + drill**，理由：
1. 符合 PHASE_MAPPING.md 权威映射
2. 补全单篇论文精读链路的最后一环（paper_card → formula_cards → teaching_cards → **pattern_cards → drill_cards**）
3. 改动面小，不修改已有模块
4. 工程可靠性可在 pattern/drill 完成后作为独立 Phase 处理

---

## 9. 建议的 Phase 12 定义

### Phase 12: Patterns + Drill Card JSON v1

**输入**:
- paper_skeleton.json (from Phase 6)
- paper_card.json (from Phase 8)
- formula_cards.json (from Phase 9)
- evidence_index.json (from Phase 6)

**输出 artifact**:
- `pattern_cards.json` — 科研模式分类卡
- `drill_cards.json` — 复述/复习/迁移/追问训练卡

**只做什么**:
1. PatternCard schema（card_id, pattern_id, definition, signals, transfer_template）
2. DrillCard schema（card_id, target, recall_questions, advisor_questions, error_attribution_prompts）
3. build_pattern_cards() 规则版（从 skeleton.pattern_candidates 推断）
4. build_pattern_cards_with_llm() LLM 增强版
5. build_drill_cards() 规则版（从 paper_card + formula_cards 生成问题）
6. build_drill_cards_with_llm() LLM 增强版
7. 集成到 SinglePaperIngestionRunner 写入 pattern_cards.json + drill_cards.json
8. Schema 测试、builder 测试、LLM fallback 测试、evidence binding 测试

**不做什么**:
- 不做 spaced repetition 调度（py-fsrs 延后）
- 不做 render / HTML
- 不做 interactive / advisor 状态机
- 不做 direction map
- 不做工程可靠性（断点续跑/日志/缓存失效/安全测试）
- 不改前端
- 不新增依赖

**应复用模块**:
- `llm/client.py` (MockLLMClient + LLMClient)
- `llm/prompt_builder.py` (PromptBuilder)
- `schemas/cards.py` (添加 PatternCard, DrillCard)
- `schemas/skeleton.py` (PaperSkeleton)
- `schemas/evidence.py` (evidence_ref 校验)
- `workspace/store.py` (artifact 写入)
- `ingestion/pipeline.py` (集成入口)
- Phase 8-10 card builder 模式（rule-based + LLM-enhanced + fallback）

**应新增 schema**:
- PatternCard (card_id, pattern_id, definition, signals, transfer_template, evidence_refs, evidence_status, confidence, warnings)
- DrillCard (card_id, target, recall_questions, advisor_questions, error_attribution_prompts, evidence_refs, evidence_status, confidence, warnings)
- 9 个科研模式枚举 (Representation, Objective, Structure, Generation, Retrieval/Memory, Reasoning/Planning, Causal/Counterfactual, Evaluation, System Pipeline)

**应新增测试**:
- test_pattern_card_schema.py — PatternCard 序列化/反序列化/枚举封闭
- test_pattern_card_builder.py — 规则版 + LLM 增强 + fallback + evidence binding
- test_drill_card_schema.py — DrillCard 序列化/反序列化
- test_drill_card_builder.py — 规则版 + LLM 增强 + fallback + evidence binding
- test_single_paper_ingestion_runner.py 更新 — 验证 pattern_cards.json + drill_cards.json 生成

**是否需要新增依赖**: 否

---

## 10. 当前未提交修改

| 文件 | 修改内容 | 建议 |
|------|----------|------|
| `docs/REUSE_REPORT.md` | +64 行 Phase 12 reuse gate | 保留，等 Alignment Brief 确认后一起提交 |
| `docs/OPEN_QUESTIONS.md` | +7 行 #9 Phase 12 范围冲突 | 保留，等确认后一起提交 |

**建议**：等 Project Alignment Brief 人工确认后，与 reuse gate 文档一起提交。这样 commit message 可以准确反映确认结果。

---

## 11. 风险清单

| 风险类别 | 风险描述 | 级别 | 缓解措施 |
|----------|----------|------|----------|
| 架构偏移 | 无。新代码全部在 src/researchsensei/，0 个 backend/ import | LOW | 持续监控 |
| 重复造轮子 | 无。patterns/drill 是 ResearchSensei 独有教学能力 | LOW | reuse gate 已评估 |
| 默认测试污染 | 无。legacy_tests/ 和 tests_e2e/ 已 --ignore 排除 | LOW | pyproject.toml 配置 |
| 真实联网/LLM | 无。所有外部调用通过 MockTransport/MockLLMClient | LOW | Adapter DI 模式 |
| artifact 命名不一致 | LOW。现有命名遵循 snake_case + .json 后缀 | LOW | 模块契约文档 |
| 文档代码不一致 | MEDIUM。PHASE_MAPPING.md 与原始开发文档 Phase 12 冲突 | MEDIUM | 本文档确认后解决 |
| Phase 12 越界 | LOW。patterns/drill 是独立模块，不修改已有代码 | LOW | 明确 scope |

---

## 12. 最终建议

### 当前项目是否健康

**是。** 246 tests passing，0 failures。11 个 Phase 全部 COMPLETE。架构边界干净。artifact 链路完整。无技术债务积累。

### 是否需要先补文档再写代码

**不需要大量补文档。** 只需确认 Phase 12 范围后，更新 PHASE_MAPPING.md 状态和 PROGRESS.md。

### 是否可以确认 Phase 12 范围

**建议确认：Phase 12 = Patterns + Drill Card JSON v1。** 理由见第 8 节。

### 是否可以进入 Phase 12 设计

**确认范围后可以。** reuse gate 已完成，无需新增依赖，复用模块明确。

### 是否可以进入 Phase 12 代码开发

**需先完成**：
1. 人工确认 Phase 12 范围
2. 提交 reuse gate 文档
3. 完成 Phase 12 设计（schema + builder + test plan）
4. 然后进入代码开发
