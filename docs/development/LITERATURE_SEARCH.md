# Literature Search 模块（M1）

---

## 1. 模块目标

搜索、筛选、排序论文，生成阅读计划。

## 2. 非目标

- 不做单篇论文理解
- 不做 cross-paper synthesis（后续）
- 不做真实联网测试

## 3. 产品流程位置

M1 是用户研究的入口：用户输入研究方向 → M1 搜索论文 → 生成阅读计划 → M2 逐篇精读。

```
用户输入研究方向 → M1 搜索论文 → 生成阅读计划
                                    ↓
                            M2 单篇论文精读
```

## 4. 可复用开源项目 / 外部服务调研

| 项目 | 用途 | GitHub / 官网 | 接入方式 | 是否默认依赖 | 风险 | 当前结论 |
|------|------|---------------|----------|--------------|------|----------|
| arXiv Atom API | 论文搜索 | arxiv.org | DIRECT_ADAPTER | 是 | 无 | ✅ 已接入 ArxivAdapter |
| OpenAlex REST API | 论文搜索/元数据 | openalex.org | DIRECT_ADAPTER | 是 | 无 | ✅ 已接入 OpenAlexAdapter |
| Semantic Scholar | citation count / venue metadata | api.semanticscholar.org | OPTIONAL_ADAPTER | 否 | rate limit | 待接入 |
| Crossref | DOI metadata | api.crossref.org | OPTIONAL_ADAPTER | 否 | rate limit | 待接入 |
| PaperQA | passage retrieval | github.com/Future-House/paper-qa | REFERENCE_ONLY | 否 | — | 参考检索思路 |
| STORM | multi-perspective questioning | github.com/stanford-oval/storm | REFERENCE_ONLY | 否 | — | 参考 M4 导师追问 |
| ARIS research-lit | 多源检索 + 去重 | github.com/wanshuiyin/Auto-claude-code-research-in-sleep | REFERENCE_ONLY | 否 | — | 参考去重思路 |

未完成调研不得进入代码开发。

## 5. 外部项目调研（详细）

### arXiv Atom API

- **类型**: public API，已有 DIRECT_ADAPTER
- **能力**: 论文搜索，返回 Atom XML
- **当前已接入**: 是 — `ArxivAdapter`

### OpenAlex REST API

- **类型**: public API，已有 DIRECT_ADAPTER
- **能力**: 论文搜索/元数据，abstract_inverted_index 还原
- **当前已接入**: 是 — `OpenAlexAdapter`

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
- **当前是否接入**: 否 — 不用于搜索源，而是可能用于文献 QA / evidence retrieval

### ResearchPilot

- **能力**: research question → retrieval → structured findings → cross-paper patterns
- **GitHub repo**: 未验证；保持 REFERENCE_ONLY 直到 repo 实现确认
- **对本模块的用处**: structured findings 的设计可参考
- **当前是否接入**: 否

### STORM

- **GitHub**: `stanford-oval/storm`
- **能力**: outline-guided synthesis / multi-perspective questioning
- **对本模块的用处**: multi-perspective questioning 可借鉴到 advisor/drill
- **当前是否接入**: 否 — 可参考 outline/multi-perspective，但不是当前搜索 adapter

### ARIS research-lit

- **GitHub**: `wanshuiyin/Auto-claude-code-research-in-sleep`
- **能力**: 多源检索 + novelty-check workflow
- **对本模块的用处**: 多源聚合和去重思路可参考
- **当前是否接入**: 否 — 可参考多源检索和去重，但不直接迁移

## 4. 当前代码位置

- `src/researchsensei/query/planner.py` — `QueryPlanner`
- `src/researchsensei/acquisition/arxiv_adapter.py` — `ArxivAdapter`
- `src/researchsensei/acquisition/openalex_adapter.py` — `OpenAlexAdapter`
- `src/researchsensei/selection/service.py` — `SelectionService`
- `src/researchsensei/direction/runner.py` — `DirectionRunner`

## 5. 输入输出

| 类 | 输入 | 输出 |
|----|------|------|
| QueryPlanner | user_query | QueryPlan |
| ArxivAdapter | query, max_results | CandidatePaper[] |
| OpenAlexAdapter | query, max_results | CandidatePaper[] |
| SelectionService | candidates | CandidatePool / ReadingPlan |
| DirectionRunner | user_query | DirectionBundle |

## 6. Artifact

- `query_plan.json` — QueryPlan
- `candidate_pool.json` — CandidatePool (raw, before dedup)
- `filtered_candidates.json` — CandidatePool (after dedup)
- `reading_plan.json` — ReadingPlan

## 7. 核心类和方法签名

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

### 去重规则

DOI（剥离 prefix + 小写）→ arXiv ID（剥离 arXiv: + vN）→ normalized_title

### 评分权重

relevance (0.36) + venue_prestige (0.22) + citation (0.14) + code (0.06) + method_rep (0.14) + recency (0.08)

## 8. 错误/失败策略

- arXiv 失败不影响 OpenAlex
- OpenAlex 失败不影响 arXiv
- 单 source 失败写入 `candidate_pool.warnings` (WarningItem)
- `search_log` 写 `source: failed (ExceptionType)`
- 所有 source 都失败，reading_plan 为空，写入 `WarningItem(code="SEARCH_FAILED")`
- BLOCKED_UNDERSTANDING 只用于单篇论文理解，不用于搜索
- 不能静默失败

## 9. 测试断言

| 测试 | 断言 |
|------|------|
| test_arxiv_xml_parse | CandidatePaper with correct title, arxiv_id, year, authors |
| test_openalex_abstract_inverted_index | abstract text reconstructed correctly |
| test_adapter_failure_to_runner_warnings | bundle.warnings contains "ACQUISITION_FAILED" |
| test_candidate_pool_contains_source_warning | candidate_pool.warnings contains failure warning |
| test_dedup_doi_arxiv_title | duplicates merged, unique preserved |
| test_reading_plan_has_scoring_breakdown | each item has scoring_breakdown, selection_reason, risk_note |
| test_a_read_limited_to_12 | count of A_READ items ≤ 12 |

## 10. Hard-Fail

- 真实联网在默认测试
- adapter 失败静默吞掉
- 去重不生效
- reading_plan 无 scoring_breakdown
- warnings 使用 str 而非 WarningItem

## 11. Schema / 数据结构

| Schema | 用途 |
|--------|------|
| QueryPlan | 用户查询规划 |
| CandidatePaper | 单篇候选论文 |
| CandidatePool | 候选论文池 |
| ReadingPlan | 阅读计划 |
| ScoringBreakdown | 评分明细 |
| DirectionBundle | 研究方向结果包 |

## 12. 测试要求

- 默认 pytest 不联网、不真实调用 LLM
- HTTP 测试用 `httpx.MockTransport`
- adapter 失败必须写入 warnings，不能静默吞掉
- 去重必须有独立测试
- reading_plan 必须有 scoring_breakdown 测试

## 13. 验收标准

- 用户输入查询后能生成 reading_plan
- arXiv 和 OpenAlex 双源检索
- 去重正确（DOI / arXiv ID / title）
- 评分有 breakdown
- A_READ 不超过 12 篇
- 单源失败不阻断整体

## 14. 当前实现状态

- 代码已实现：QueryPlanner, ArxivAdapter, OpenAlexAdapter, SelectionService, DirectionRunner
- 测试已覆盖：298+ tests including acquisition/selection/direction
- Semantic Scholar / Crossref 未实现
- cross-paper synthesis 未实现

## 15. 当前未解决问题

- Semantic Scholar / Crossref adapter 未实现
- 中文 query fallback 降级策略（direction_en 仍为中文）
- cross-paper synthesis 未实现
