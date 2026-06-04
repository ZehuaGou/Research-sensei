# Literature Search 模块（M1）

---

## 1. 模块目标

搜索、筛选、排序论文，生成阅读计划。

M1 是用户研究方向探索的入口：用户输入研究问题 → M1 生成搜索计划 → 多源检索 → 去重评分 → 生成阅读计划 → M2 逐篇精读。

## 2. 非目标

- 不做单篇论文理解（M2 负责）
- 不做论文下载与解析（M2.0/M2.1 负责）
- 不做 cross-paper synthesis（后续）
- 不做真实联网测试
- 不调用 LLM 生成论文解释

## 3. 产品流程位置

M1 是用户研究的入口。M1 的终点是 reading_plan.json，不进入 M2 精读链路。

```
用户输入研究问题
  → M1.1 QueryPlanner.plan()
    → query_plan.json
      → M1.2 ArxivAdapter.search() + OpenAlexAdapter.search()
        → candidate_pool.json (raw)
          → M1.4 SelectionService.deduplicate() + build_reading_plan()
            → filtered_candidates.json
              → reading_plan.json
                → M2 单篇精读（由 reading_plan 中 A_READ 论文触发）
```

### 与上下游的关系

- **上游**: 用户直接输入研究问题
- **下游**: reading_plan.json 中 A_READ 论文 → source_resolver (M2.0) → 单篇精读 (M2.1-M2.5)
- **边界**: M1 不生成 paper_card / formula_cards / teaching_cards；M1 不解析 PDF；M1 不下载论文文件

## 4. 可复用开源项目 / 外部服务调研

| 项目 | 用途 | GitHub / 官网 | 接入方式 | 是否默认依赖 | 风险 | 当前结论 |
|------|------|---------------|----------|--------------|------|----------|
| arXiv Atom API | 论文搜索 | arxiv.org | DIRECT_ADAPTER | 是 | 无 | ✅ 已接入 ArxivAdapter |
| OpenAlex REST API | 论文搜索/元数据 | openalex.org | DIRECT_ADAPTER | 是 | 无 | ✅ 已接入 OpenAlexAdapter |
| Semantic Scholar | citation count / venue metadata | api.semanticscholar.org | OPTIONAL_ADAPTER | 否 | rate limit | 待接入，只借鉴 citation 数据 |
| Crossref | DOI metadata | api.crossref.org | OPTIONAL_ADAPTER | 否 | rate limit | 待接入，只借鉴 DOI 解析 |
| PaperQA | passage retrieval | github.com/Future-House/paper-qa | REFERENCE_ONLY | 否 | — | 只借鉴检索思路，不默认接入 |
| STORM | multi-perspective questioning | github.com/stanford-oval/storm | REFERENCE_ONLY | 否 | — | 只借鉴 M4 导师追问，不默认接入 |
| ARIS research-lit | 多源检索 + 去重 | github.com/wanshuiyin/Auto-claude-code-research-in-sleep | REFERENCE_ONLY | 否 | — | 只借鉴去重思路，不默认接入 |

未完成调研不得进入代码开发。

## 5. 外部项目调研（详细）

### arXiv Atom API

- **类型**: public API，已有 DIRECT_ADAPTER
- **能力**: 论文搜索，返回 Atom XML
- **当前已接入**: 是 — `ArxivAdapter`
- **限制**: 无 citation count，无 venue metadata

### OpenAlex REST API

- **类型**: public API，已有 DIRECT_ADAPTER
- **能力**: 论文搜索/元数据，abstract_inverted_index 还原，citation_count
- **当前已接入**: 是 — `OpenAlexAdapter`
- **限制**: 无 PDF 直链，需要通过 DOI 跳转

### Semantic Scholar

- **类型**: public API
- **能力**: citation count / venue metadata / TLDR
- **当前是否接入**: 否 — OPTIONAL_ADAPTER
- **未来接入**: 通过 adapter 接口，补充 citation 数据。接入前必须看 API rate limit、schema、许可。

### Crossref

- **类型**: public API
- **能力**: DOI metadata
- **当前是否接入**: 否 — OPTIONAL_ADAPTER
- **未来接入**: 通过 adapter 接口，补充 DOI 解析。接入前必须看 API rate limit、schema、许可。

### PaperQA

- **GitHub**: `Future-House/paper-qa`
- **能力**: literature QA / passage retrieval
- **对本模块的用处**: passage retrieval 的检索思路可参考
- **当前是否接入**: 否 — 不用于搜索源，只借鉴检索思路

### STORM

- **GitHub**: `stanford-oval/storm`
- **能力**: outline-guided synthesis / multi-perspective questioning
- **对本模块的用处**: multi-perspective questioning 可借鉴到 M4 advisor/drill
- **当前是否接入**: 否 — 只借鉴设计，不直接迁移

### ARIS research-lit

- **GitHub**: `wanshuiyin/Auto-claude-code-research-in-sleep`
- **能力**: 多源检索 + novelty-check workflow
- **对本模块的用处**: 多源聚合和去重思路可参考
- **当前是否接入**: 否 — 只借鉴多源检索和去重，不直接迁移

## 6. 当前代码位置

- `src/researchsensei/query/planner.py` — `QueryPlanner`
- `src/researchsensei/acquisition/arxiv_adapter.py` — `ArxivAdapter`
- `src/researchsensei/acquisition/openalex_adapter.py` — `OpenAlexAdapter`
- `src/researchsensei/selection/service.py` — `SelectionService`
- `src/researchsensei/direction/runner.py` — `DirectionRunner`
- `src/researchsensei/schemas/direction.py` — M1 schemas

## 7. 输入输出

### M1.1 用户问题与搜索规划

| 项 | 值 |
|----|-----|
| 输入 | `user_query: str`（用户研究问题） |
| 输出 | `query_plan.json`（QueryPlan） |
| 核心类 | `QueryPlanner.plan(user_query) -> QueryPlan` |
| 边界 | 不直接搜索论文。不直接生成阅读计划。 |

QueryPlanner 职责：将用户自然语言问题解析为结构化搜索计划（direction_name, core_terms, related_terms, exclude_terms, search_intents）。LLM 可用时用 LLM 解析，不可用时 fallback 到逗号分割启发式。

### M1.2 多源论文检索

| 项 | 值 |
|----|-----|
| 输入 | query string + max_results |
| 输出 | `candidate_pool.json`（CandidatePool，raw） |
| 核心类 | `ArxivAdapter.search()`, `OpenAlexAdapter.search()`, `SelectionService.build_candidate_pool()` |
| 边界 | 外部服务默认 mock。不允许单测真实联网。 |

每个 adapter 独立运行，互不影响。单 adapter 失败写入 warnings，不阻断其他 adapter。

### M1.3 论文原始材料获取

| 项 | 值 |
|----|-----|
| 输入 | CandidatePaper（含 arxiv_id, pdf_url, doi） |
| 输出 | 源文件（LaTeX source / PDF）或 metadata-only fallback |
| 核心类 | 方向：arXiv source fetch / PDF download / metadata fallback |
| 边界 | 下载不能污染解析模块。完整 source 解析由 M2.0 SourceResolver 负责。 |

M1.3 当前方向：
- 优先获取 arXiv LaTeX source（.tar.gz）
- 其次获取 PDF
- 再 fallback metadata-only（只保留 abstract + 元数据）
- 下载失败记录到 CandidatePaper 的 warnings
- source_status.json 表达获取状态

注意：完整 source 解析（LaTeX → DocumentIngestion, PDF → parsed_document）是 M2.0/M2.1 的职责。M1.3 只负责获取原始材料，不负责解析。

### M1.4 候选论文去重与评分

| 项 | 值 |
|----|-----|
| 输入 | `candidate_pool.json`（raw） |
| 输出 | `filtered_candidates.json`（CandidatePool，after dedup） |
| 核心类 | `SelectionService.deduplicate()`, `SelectionService.build_reading_plan()` |
| 边界 | 评分不能伪造。候选为空时返回空 reading_plan + warning。 |

去重规则：DOI（剥离 prefix + 小写）→ arXiv ID（剥离 arXiv: + vN）→ normalized_title

评分权重：relevance (0.36) + venue_prestige (0.22) + citation (0.14) + code (0.06) + method_rep (0.14) + recency (0.08)

### M1.5 阅读计划生成

| 项 | 值 |
|----|-----|
| 输入 | QueryPlan + filtered candidates |
| 输出 | `reading_plan.json`（ReadingPlan） |
| 核心类 | `SelectionService.build_reading_plan()`, `DirectionRunner.run()` |
| 边界 | 不直接生成 paper_card。不进入 M2 精读。 |

ReadingPlan 包含每篇论文的：
- priority: A_READ / B_SKIM / D_IGNORE
- role: SURVEY / METHOD / DATASET / TOOL / IRRELEVANT
- scoring_breakdown: 评分明细
- selection_reason: 推荐理由
- risk_note: 风险提示

DirectionRunner 是 M1 编排器：query plan → multi-source acquisition → dedup → reading plan。

## 8. Artifact

| Artifact | Schema | 说明 |
|----------|--------|------|
| `query_plan.json` | QueryPlan | 用户查询规划 |
| `candidate_pool.json` | CandidatePool | 原始候选论文池（含 search_log, warnings） |
| `filtered_candidates.json` | CandidatePool | 去重后的候选论文池 |
| `reading_plan.json` | ReadingPlan | 阅读计划（含 priority, role, scoring_breakdown） |

### Schema 列表

| Schema | 用途 |
|--------|------|
| QueryPlan | 用户查询规划（direction_name, core/related/exclude terms, search_intents） |
| CandidatePaper | 单篇候选论文（paper_id, title, authors, year, venue, source, doi, arxiv_id, abstract, citation_count） |
| CandidatePool | 候选论文池（query, items, counts, search_log, warnings） |
| ScoringBreakdown | 评分明细（relevance, venue, citation, code, method_rep, recency, penalty, weighted_total） |
| ReadingPlanItem | 阅读计划条目（CandidatePaper + role, priority, scoring_breakdown, selection_reason, risk_note） |
| ReadingPlan | 阅读计划（topic, items, timestamp, warnings） |
| DirectionBundle | 研究方向结果包（QueryPlan + CandidatePool raw/filtered + ReadingPlan + warnings） |

## 9. 核心类和方法签名

```python
class QueryPlanner:
    async def plan(self, user_query: str) -> QueryPlan: ...

class ArxivAdapter:
    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]: ...

class OpenAlexAdapter:
    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]: ...

class SelectionService:
    def build_candidate_pool(self, query, candidates, search_log=None, warnings=None) -> CandidatePool: ...
    def deduplicate(self, candidates: list[CandidatePaper]) -> list[CandidatePaper]: ...
    def build_reading_plan(self, query_plan, candidates) -> ReadingPlan: ...

class DirectionRunner:
    async def run(self, user_query: str, direction_id: str | None = None) -> DirectionBundle: ...
```

## 10. 状态流 / 错误策略

### 错误传播规则

| 场景 | 行为 |
|------|------|
| 单 adapter 失败 | 其他 adapter 继续，warning 写入 candidate_pool |
| 所有 adapter 失败 | reading_plan 为空 + `WarningItem(code="SEARCH_FAILED")` |
| LLM 不可用 | QueryPlanner fallback 到逗号分割启发式 + warning |
| 中文 query 无 LLM | `CHINESE_QUERY_NO_LLM_FALLBACK` + `EN_QUERY_UNAVAILABLE` |
| 候选为空 | reading_plan 为空，不阻断 |
| 去重后无剩余 | reading_plan 为空，不阻断 |

### 禁止

- adapter 失败不能静默吞掉
- 不能单测真实联网
- warnings 必须是 `WarningItem`，不能是 `str`
- `search_log` 必须记录每个 source 的结果

## 11. 测试要求

### M1.1 用户问题与搜索规划

| 测试 | 断言 |
|------|------|
| test_query_planner_normal_input | QueryPlan with correct direction_name, core_terms |
| test_query_planner_empty_input | fallback behavior, warning written |
| test_query_planner_chinese_query | Chinese text detected, direction_name_zh populated |
| test_query_planner_english_query | English terms correctly extracted |
| test_query_planner_overly_broad | broad query produces warning |
| test_query_plan_schema_round_trip | QueryPlan serialize → deserialize preserves all fields |
| test_query_planner_no_llm_fallback | comma-split heuristic works when LLM unavailable |

### M1.2 多源论文检索

| 测试 | 断言 |
|------|------|
| test_arxiv_adapter_mock | CandidatePaper with correct title, arxiv_id, year, authors |
| test_openalex_adapter_mock | CandidatePaper with correct title, abstract reconstructed |
| test_adapter_network_failure | exception caught, warning written to candidate_pool |
| test_adapter_empty_result | empty list returned, no crash |
| test_adapter_rate_limit | warning written, other adapter continues |
| test_candidate_pool_schema_round_trip | CandidatePool serialize → deserialize preserves all fields |
| test_both_adapters_fail | reading_plan empty, SEARCH_FAILED warning |

### M1.3 论文原始材料获取

| 测试 | 断言 |
|------|------|
| test_latex_source_priority | LaTeX source fetched before PDF |
| test_pdf_fallback | PDF fetched when LaTeX unavailable |
| test_metadata_only_fallback | metadata preserved when download fails |
| test_download_failure_recorded | failure recorded in warnings |
| test_source_status_schema_round_trip | source status serialize → deserialize preserves all fields |
| test_no_pollution_to_parser | M1.3 output does not contain parsed content |

### M1.4 候选论文去重与评分

| 测试 | 断言 |
|------|------|
| test_dedup_by_doi | same DOI → merged |
| test_dedup_by_arxiv_id | same arXiv ID → merged |
| test_dedup_by_title_similarity | similar title → merged |
| test_dedup_preserves_unique | different papers preserved |
| test_scoring_sort_order | higher weighted_total → higher priority |
| test_scoring_breakdown_fields | all 7 score fields present |
| test_empty_candidates | empty list → empty reading_plan, no crash |
| test_filtered_candidates_schema_round_trip | CandidatePool serialize → deserialize preserves all fields |

### M1.5 阅读计划生成

| 测试 | 断言 |
|------|------|
| test_reading_plan_generation | ReadingPlan with items, topic, timestamp |
| test_reading_order_stability | same input → same order |
| test_selection_reason_present | every ReadingPlanItem has non-empty selection_reason |
| test_a_read_limited_to_12 | count of A_READ items ≤ 12 |
| test_reading_plan_schema_round_trip | ReadingPlan serialize → deserialize preserves all fields |
| test_no_paper_card_generated | M1.5 output does not contain paper_card content |
| test_direction_bundle_schema_round_trip | DirectionBundle serialize → deserialize preserves all fields |

### 全局测试规则

- 默认 pytest 不联网、不真实调用 LLM
- HTTP 测试用 `httpx.MockTransport`
- adapter 失败必须写入 warnings，不能静默吞掉
- 去重必须有独立测试
- reading_plan 必须有 scoring_breakdown 测试

## 12. 验收标准

M1 完成后，应能做到：

1. 输入用户研究问题（中文或英文）
2. 生成 query_plan.json（含 core_terms, related_terms, search_intents）
3. 通过 mock adapter 获取 candidate_pool.json（含 search_log, warnings）
4. 去重并评分生成 filtered_candidates.json
5. 生成 reading_plan.json（含 priority, role, scoring_breakdown, selection_reason）
6. 每一步 artifact schema 可校验（round-trip 测试通过）
7. 所有外部服务测试默认 mock，不真实联网
8. 不调用 LLM 生成论文解释
9. 不进入 M2 精读链路
10. 单 adapter 失败不阻断整体流程
11. M1.1-M1.5 每个子模块都有测试覆盖
12. M1 一级模块有集成测试（query → candidate_pool → filtered → reading_plan）

## 13. 当前实现状态

- 代码已实现：QueryPlanner, ArxivAdapter, OpenAlexAdapter, SelectionService, DirectionRunner
- 测试已覆盖：298+ tests including acquisition/selection/direction
- Semantic Scholar / Crossref 未实现
- M1.3 论文原始材料获取未实现（arXiv source fetch / PDF download）
- cross-paper synthesis 未实现

## 14. 当前未解决问题

- Semantic Scholar / Crossref adapter 未实现
- M1.3 论文原始材料获取方案（arXiv source fetch / PDF download / metadata-only fallback）
- 中文 query fallback 降级策略（direction_en 仍为中文）
- cross-paper synthesis 未实现
- SourceResolver 与 M1.3 的职责边界（当前 SourceResolver 属于 M2.0）
