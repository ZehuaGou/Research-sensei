# Literature Search — 开发文档

方向搜索 / 选文模块。覆盖 query planner / acquisition adapters / candidate_pool / filtered_candidates / reading_plan。

---

## 1. 当前状态

Phase 11 已完成 direction pipeline v1：

```
query_plan.json → candidate_pool.json → filtered_candidates.json → reading_plan.json
```

**当前限制**：
- v1，不是完整 literature review system
- 中文 fallback 降级（无 LLM 时 direction_en 仍为中文）
- arXiv / OpenAlex 两个 adapter
- 无 cross-paper synthesis

---

## 2. 参考 / 复用项目

| 项目 | 决策 | 说明 |
|------|------|------|
| OpenAlex | DIRECT_ADAPTER（已有） | REST API，abstract_inverted_index 还原 |
| arXiv | DIRECT_ADAPTER（已有） | Atom API |
| Semantic Scholar | OPTIONAL_ADAPTER 候选 | 后续，citation counts, venue metadata, TLDR |
| Crossref | OPTIONAL_ADAPTER 候选 | 后续，DOI metadata |
| PaperQA | OPTIONAL_ADAPTER 候选 | 参考 passage retrieval / literature QA |
| ResearchPilot | REFERENCE_ONLY | 参考 structured findings / cross-paper patterns |
| STORM | REFERENCE_ONLY | 参考 outline / multi-perspective question asking |
| ARIS research-lit | REFERENCE_ONLY | 参考多源检索和 novelty-check workflow |

---

## 3. 当前模块

### Query Planner

- 文件：`src/researchsensei/query/planner.py`
- 类：`QueryPlanner`
- 方法：`async plan(user_query: str) -> QueryPlan`
- 输入：用户方向文本（中/英文）
- 输出：`QueryPlan`（direction_en, core_terms, search_intents, warnings）
- 错误：LLM 失败 → fallback 到规则提取
- 测试：`test_query_planner.py` (5 tests)

### arXiv Adapter

- 文件：`src/researchsensei/acquisition/arxiv_adapter.py`
- 类：`ArxivAdapter`
- 方法：`search(query: str, max_results: int = 20) -> list[CandidatePaper]`
- 输入：query string, max_results
- 输出：`CandidatePaper[]`
- 错误：抛异常，由 runner 捕获写入 warnings
- 测试：`test_acquisition_adapters.py`，MockTransport

### OpenAlex Adapter

- 文件：`src/researchsensei/acquisition/openalex_adapter.py`
- 类：`OpenAlexAdapter`
- 方法：`search(query: str, max_results: int = 20) -> list[CandidatePaper]`
- 输入：query string, max_results
- 输出：`CandidatePaper[]`
- 特殊：`abstract_inverted_index` 还原为文本
- 错误：抛异常，由 runner 捕获写入 warnings
- 测试：`test_acquisition_adapters.py`，MockTransport

### Selection Service

- 文件：`src/researchsensei/selection/service.py`
- 类：`SelectionService`
- 方法：
  - `build_candidate_pool(query, candidates, search_log, warnings) -> CandidatePool`
  - `deduplicate(candidates: list[CandidatePaper]) -> list[CandidatePaper]`
  - `build_reading_plan(query_plan, candidates) -> ReadingPlan`
- 去重：DOI（剥离 prefix + 小写）→ arXiv ID（剥离 arXiv: + vN）→ normalized_title
- 评分：relevance (0.36) + venue_prestige (0.22) + citation (0.14) + code (0.06) + method_rep (0.14) + recency (0.08)
- 测试：`test_selection_service.py` (16 tests)

### Direction Runner

- 文件：`src/researchsensei/direction/runner.py`
- 类：`DirectionRunner`
- 方法：`async run(user_query, direction_id) -> DirectionBundle`
- 编排：query → acquire → candidate_pool → dedup → filtered_candidates → reading_plan → write artifacts
- 错误：adapter 失败 → 写入 warnings/search_log，不 crash
- 测试：`test_direction_runner.py` (7 tests)

---

## 4. Artifact 详情

### query_plan.json

- 生成者：`QueryPlanner`
- 消费者：acquisition adapters
- 字段：user_query, language, direction_en, core_terms, search_intents, warnings
- Schema：`QueryPlan`

### candidate_pool.json

- 生成者：`SelectionService.build_candidate_pool()`
- 消费者：dedup
- 字段：query, retrieved_count, items, search_log, warnings
- Schema：`CandidatePool`

### filtered_candidates.json

- 生成者：`SelectionService.deduplicate()` + `build_candidate_pool()`
- 消费者：`build_reading_plan()`
- 字段：query, retrieved_count, deduplicated_count, items, warnings
- Schema：`CandidatePool`

### reading_plan.json

- 生成者：`SelectionService.build_reading_plan()`
- 消费者：用户 / source_resolver（A_READ papers）
- 字段：topic, items (ReadingPlanItem[]), warnings
- 每个 item：paper, priority, scoring_breakdown, selection_reason, risk_note
- Schema：`ReadingPlan`

---

## 5. 未来升级方向

| 方向 | 说明 |
|------|------|
| Query expansion | 中文 → 英文术语映射，同义词扩展 |
| Source-level failure warning | adapter 失败写入 candidate_pool.warnings |
| Low recall degraded | 搜索结果太少时降级并 warning |
| Semantic Scholar adapter | 新增 optional adapter |
| Crossref adapter | 新增 optional adapter |
| Structured findings | 从 reading_plan 提取跨论文结构 |
| Cross-paper synthesis | 参考 STORM，方向演化链 |
| Reading plan quality | selection_reason 更具体，评分可解释 |

---

## 6. 测试覆盖

| 测试文件 | 测试数 | 覆盖 |
|----------|--------|------|
| test_query_planner.py | 5 | LLM + fallback + 中文 + 英文 + comma-separated |
| test_acquisition_adapters.py | 7 | XML parse, JSON parse, empty, invalid, MockTransport |
| test_selection_service.py | 16 | scoring, venue, recency, max_a_read, empty, dedup (DOI/arXiv/title/merge/empty/order), A_READ ≤ 12 |
| test_direction_runner.py | 7 | full pipeline, no candidates, JSON valid, filtered_candidates, dedup across sources, reading_plan based on filtered, no paper_card |
| test_direction_schemas.py | 10 | round-trip: QueryPlan, CandidatePaper, ScoringBreakdown, ReadingPlanItem, ReadingPlan, CandidatePool, DirectionBundle, SearchIntent enum |
