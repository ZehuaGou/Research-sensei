# ResearchSensei Phase Mapping

## 权威声明

原始开发文档（`docs/researchsensei_full_dev_docs/`）仍作为**产品定义与总体架构依据**。

但实际执行以以下文件为准：

- `docs/PROGRESS.md` — 当前完成状态
- `docs/MIGRATION_PLAN.md` — 迁移步骤
- `docs/PHASE_MAPPING.md` — 本文档，Phase 编号映射
- `docs/REUSE_REPORT.md` — 复用评估记录

**后续 Agent 不得只按旧开发文档 Phase 编号执行。每个新 Phase 开始前仍必须执行 reuse gate。**

## Phase 编号映射

| 迁移 Phase | 名称 | 对应旧文档范围 | 状态 |
|---|---|---|---|
| Phase 1 | 项目骨架 | 旧 Phase 1 部分 | ✅ 完成 |
| Phase 2 | 配置与 Schema | 旧 Phase 2 部分 | ✅ 完成 |
| Phase 3 | Workspace / Job Store | 旧 Phase 3 部分 | ✅ 完成 |
| Phase 4 | 单篇文档轻量解析 | 旧 Phase 4 部分 | ✅ 完成 |
| Phase 5 | Source Resolver + Parse API | 旧 Phase 4-5 部分 | ✅ 完成 |
| Phase 6 | Grounding / Evidence + Paper Skeleton | 旧 Phase 5 部分 | ✅ 完成 |
| Phase 7 | LLM 基础设施 | 旧 Phase 3 LLM 层部分 | ✅ 完成 |
| Phase 8 | Evidence-Constrained Paper Card JSON v1 | 旧 Phase 6 teaching 部分 | ✅ 完成 |
| Phase 9 | Formula Card JSON v1 | 旧 Phase 6 formula 部分 | ✅ 完成 |
| Phase 10 | Teaching Card JSON v1 | 旧 Phase 6 teaching 部分 | ✅ 完成 |
| Phase 11 | Query / Acquisition / Selection / Reading Plan v1 | 旧 Phase 9 部分 | ✅ 完成 |
| Phase 12 | **待确认**（建议：patterns + drill） | 旧 Phase 6 patterns/drill 部分 | ❌ 未开始 |
| Phase 13 | **待确认**（建议：interactive + context） | 旧 Phase 8 部分 | ❌ 未开始 |
| Phase 14 | **待确认**（建议：render + direction） | 旧 Phase 7/10 部分 | ❌ 未开始 |
| Phase 15 | **待确认**（建议：evaluation / golden tests） | 旧 Phase 13 部分 | ❌ 未开始 |
| Phase 16 | **待确认**（建议：frontend API 对接） | 旧 Phase 7 前端部分 | ❌ 未开始 |

## 差异说明

旧开发文档的 Phase 编号基于"从零构建"假设。迁移路线因为复用已有代码和分阶段迁移，产生了编号偏移：

| 旧文档 Phase | 旧文档内容 | 迁移路线中的对应 |
|---|---|---|
| Phase 3 LLM 层 | LLM client / prompt / cache | 推迟到迁移 Phase 7+ |
| Phase 5 证据定位 | grounding + skeleton | 迁移 Phase 6 |
| Phase 6 卡片生成 | paper/formula/drill cards | 迁移 Phase 8+（需 LLM 基础设施） |
| Phase 7 HTML 渲染 | Jinja2 / HTMX 页面 | 迁移 Phase 9+ |

## Phase 7 确认范围：LLM 基础设施

已确认选择选项 A。Phase 7 包含：

- LLM client（OpenAI-compatible，httpx，mock mode）
- Provider config（已迁移的 ModelProviderConfig）
- Prompt builder（system/context/evidence/user 分区，指令隔离）
- Response cache（SHA256 keys，TTL，version invalidation）
- Token budget 估算（字符级，非 tiktoken）
- timeout / retry 基础（简单重试，非 tenacity）
- JSON 输出校验（pydantic model_validate_json）

Phase 7 不包含：teaching、card 生成、formula、advisor、render、前端变更。

复用评估详见 `docs/REUSE_REPORT.md` Phase 7 部分。

## Phase 8 确认范围：Evidence-Constrained Paper Card JSON v1

已确认。Phase 8 包含：

- `PaperCard` schema（含 evidence_refs、warnings）
- `build_paper_card()` 规则版（从 skeleton + evidence_index 提取）
- LLM 增强版（可选，mock 测试）
- 集成到 parse flow 写入 `paper_card.json`
- 所有 claim 绑定 evidence_ref
- 不确定内容标注 degraded status

Phase 8 不包含：HTML 渲染、formula 深度讲解、teaching 五层引擎、drill、advisor、direction map、RAG、真实 LLM 默认测试。

复用评估详见 `docs/REUSE_REPORT.md` Phase 8 部分。

## 全模块覆盖对照

对照原开发文档核心模块，当前迁移路线覆盖情况：

| 模块 | 原文档 Phase | 迁移 Phase | 状态 |
|------|------------|-----------|------|
| `query`（方向理解） | 旧 9 | Phase 11 | ✅ 完成 |
| `acquisition`（论文搜索） | 旧 9 | Phase 11 | ✅ 完成 |
| `selection`（论文筛选/去重） | 旧 9 | Phase 11 | ✅ 完成 |
| `source_resolver`（来源获取） | 旧 4 | Phase 5 | ✅ 完成 |
| `ingestion`（文档解析） | 旧 4 | Phase 4 | ✅ 完成 |
| `grounding`（证据定位） | 旧 5 | Phase 6 | ✅ 完成 |
| `understanding`（论文骨架） | 旧 5 | Phase 6 | ✅ 完成 |
| `paper_card`（学习卡） | 旧 6 | Phase 8 | ✅ 完成 |
| `formula`（公式讲解） | 旧 6 | Phase 9 | ✅ 完成 |
| `teaching`（五层讲解） | 旧 6 | Phase 10 | ✅ 完成 |
| `patterns`（科研模式） | 旧 6 | Phase 12 | ❌ 未开始 |
| `drill`（复述/复习） | 旧 6 | Phase 12 | ❌ 未开始 |
| `interactive`（交互追问） | 旧 8 | Phase 13 | ❌ 未开始 |
| `context`（会话上下文） | 旧 8 | Phase 13 | ❌ 未开始 |
| `llm`（LLM 基础设施） | 旧 3 | Phase 7 | ✅ 完成 |
| `render`（HTML 渲染） | 旧 7 | Phase 14 | ❌ 未开始 |
| `direction`（方向脉络） | 旧 10 | Phase 14 | ❌ 未开始 |
| `frontend`（Vue 前端） | 旧 7 | Phase 16 | ⚠️ 保留现状 |
| `reuse/integrations` | 全局 | 每 Phase | ✅ 持续 |
| `testing/evaluation` | 旧 13 | Phase 15 | ⚠️ mock 完成，golden 未开始 |

**注意**：旧文档 Phase 6 包含 formula/teaching/patterns/drill 四个子模块，当前迁移路线将其拆分到 Phase 8-12。这是有意为之的分步策略，非遗漏。

## Phase 11 确认范围：Query / Acquisition / Selection / Reading Plan v1

已确认。Phase 11 包含：

- `SearchIntent` Enum（GENERAL/SURVEY/FOUNDATIONAL/SOTA/BENCHMARK/CODE）
- `QueryPlan` schema（含 core_terms、search_intents、warnings）
- `CandidatePaper` schema（含 normalized_title、doi、arxiv_id）
- `ArxivAdapter`（Atom API，MockTransport 测试）
- `OpenAlexAdapter`（REST API，abstract_inverted_index 还原，MockTransport 测试）
- `SelectionService`（scoring、dedup、reading_plan）
- 三路去重：DOI → arXiv ID → normalized_title，合并更完整元数据
- `DirectionRunner`（query → acquisition → candidate_pool → filtered_candidates → reading_plan）
- Artifact 链路：query_plan.json → candidate_pool.json → filtered_candidates.json → reading_plan.json
- `DirectionBundle` 包含 filtered_candidates 字段
- A_READ 默认不超过 12 篇
- 不生成 paper_card.json（direction 链路与单篇精读链路分离）

Phase 11 不包含：真实联网搜索、真实 LLM 调用、paper_card 生成、多论文批量精读、前端变更。
