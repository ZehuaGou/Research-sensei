# Literature Search 模块

---

## 1. 模块目标

搜索、筛选、排序论文，生成阅读计划。

## 2. 非目标

- 不做单篇论文理解
- 不做 cross-paper synthesis（后续）
- 不做真实联网测试

## 3. 外部项目调研

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

## 11. 当前未解决问题

- Semantic Scholar / Crossref adapter 未实现
- 中文 query fallback 降级策略（direction_en 仍为中文）
- cross-paper synthesis 未实现
