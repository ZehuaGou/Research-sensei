# Full Pipeline 模块

---

## 1. 模块目标

定义单篇论文和研究方向两条完整链路的输入输出、失败传递、状态约束。

## 2. 非目标

- 不实现新功能
- 不改现有代码

## 3. 当前代码事实

- `SinglePaperIngestionRunner.run()` 编排单篇链路
- `DirectionRunner.run()` 编排方向链路
- 两条链路不交叉：direction 链路不生成 paper_card，单篇链路不生成 reading_plan
- 未来连接点：reading_plan 的 A_READ 论文 → source_resolver → 单篇精读

## 4. 单篇论文链路

```
source (PDF/MD/TXT)
  → ParserAdapter.parse()
    → ParserResult (DocumentIngestion + ParseMetadata)
      → parsed_document.json
        → build_passage_index()
          → passage_index.json (PassageIndex, v2)
            → extract_claims()
              → claim_evidence.json (ClaimEvidence v2)
                → evidence_index.json (v1 wrapper)
                  → build_paper_skeleton()
                    → paper_skeleton.json
                      → build_evidence_pack() [runtime]
                        → LLM paper_card → paper_card.json
                        → LLM formula_cards → formula_cards.json
                        → LLM teaching_cards → teaching_cards.json
                          → QualityAuditor.audit()
                            → quality_report.json
                              → Runner maps to UnderstandingStatus
                                → understanding_status.json
                                  → /cards API → frontend display
                                  → DownstreamGates
```

### 每步输入输出

| 步骤 | 输入 | 输出 | 失败行为 |
|------|------|------|----------|
| ParserAdapter.parse | source file | ParserResult | 系统异常 → FAILED; degraded → DEGRADED_STRUCTURAL |
| build_passage_index | DocumentIngestion.blocks | PassageIndex → passage_index.json | NO_PASSAGES → BLOCKED |
| extract_claims | PassageIndex.passages | ClaimEvidence v2 → claim_evidence.json | NO_CLAIMS → BLOCKED |
| evidence_index wrapper | claim_evidence.json | evidence_index.json (v1) | — |
| build_paper_skeleton | DocumentIngestion + EvidenceIndex | PaperSkeleton | section MISSING warnings |
| build_evidence_pack | ClaimEvidence + PassageIndex | EvidencePack [runtime] | 空 → BLOCKED; 缺 METHOD → BLOCKED |
| LLM paper_card | EvidencePack + skeleton | paper_card.json | LLM 失败 → BLOCKED |
| LLM formula_cards | EvidencePack + skeleton | formula_cards.json | 核心公式失败 → BLOCKED; 无公式 → SKIPPED |
| LLM teaching_cards | EvidencePack + skeleton | teaching_cards.json | 失败 → DEGRADED_STRUCTURAL |
| QualityAuditor.audit | cards + evidence + passages | quality_report.json | finding BLOCK → BLOCKED |
| Runner → UnderstandingStatus | QualityReport + component_status | understanding_status.json | 映射 |

### 状态传递规则

| 上游状态 | 下游行为 |
|----------|----------|
| parser 系统异常 | FAILED |
| parser degraded=True | DEGRADED_STRUCTURAL（如果理解成功） |
| no passages | BLOCKED_UNDERSTANDING |
| no claims | BLOCKED_UNDERSTANDING |
| missing method evidence | BLOCKED_UNDERSTANDING |
| evidence_pack 为空 | BLOCKED_UNDERSTANDING |
| evidence_pack 缺 METHOD | BLOCKED_UNDERSTANDING |
| 无 LLM client | BASELINE_ONLY |
| LLM invalid JSON / timeout | BLOCKED_UNDERSTANDING |
| LLM invalid evidence_ref | BLOCKED_UNDERSTANDING |
| LLM missing evidence_ref | BLOCKED_UNDERSTANDING |
| paper_card LLM 失败 | BLOCKED_UNDERSTANDING |
| formula_cards 核心公式失败 | BLOCKED_UNDERSTANDING |
| formula_cards 无公式 | SKIPPED，不阻断 |
| teaching_cards 失败 + paper_card 成功 | DEGRADED_STRUCTURAL |
| audit finding effect=BLOCK | BLOCKED_UNDERSTANDING |
| audit finding effect=WARNING only | 不阻断，warning 写入 warnings |

### 下游判断规则

- `allowed_for_phase12` 是 legacy 字段，新代码使用 `allowed_downstream`（DownstreamGates）
- Phase 12 patterns 需要 `allowed_downstream.phase12_patterns == True`
- Phase 12 drill 需要 `allowed_downstream.phase12_drill == True`（或 `phase12_drill_degraded == True`）
- advisor 需要 `allowed_downstream.advisor_questions == True`
- UI 只能展示 `allowed_for_user_display == True` 的结果
- 用户端走 `/cards` API，debug/admin 走 `/artifacts` / `/quality_report`
- BLOCKED 不展示 card 内容
- BASELINE_ONLY 只能作为 diagnostic artifact

## 5. 研究方向链路

```
user_query
  → QueryPlanner.plan()
    → query_plan.json (QueryPlan)
      → ArxivAdapter.search() + OpenAlexAdapter.search()
        → candidate_pool.json (CandidatePool)
          → SelectionService.deduplicate()
            → filtered_candidates.json (CandidatePool)
              → SelectionService.build_reading_plan()
                → reading_plan.json (ReadingPlan)
                  → A_READ papers → source_resolver → 单篇链路
```

### 每步输入输出

| 步骤 | 输入 | 输出 | 失败行为 |
|------|------|------|----------|
| QueryPlanner.plan | user_query | QueryPlan | LLM 失败 → fallback rules + warning |
| adapter.search | query string | CandidatePaper[] | 抛异常 → runner 捕获写 warning |
| build_candidate_pool | candidates | CandidatePool | — |
| deduplicate | candidates | deduplicated list | 三路去重 |
| build_reading_plan | candidates + QueryPlan | ReadingPlan | 无相关论文 → NO_RELEVANT_PAPERS |

### 状态传递规则

| 上游状态 | 下游行为 |
|----------|----------|
| 单 adapter 失败 | 其他 adapter 继续，warning 写入 candidate_pool |
| 所有 adapter 失败 | reading_plan 为空 + SEARCH_FAILED warning |
| 中文无 LLM | CHINESE_QUERY_NO_LLM_FALLBACK + EN_QUERY_UNAVAILABLE |

### 下游判断规则

- A_READ 论文进入单篇精读链路
- reading_plan 为空不阻止用户重试

## 6. 与上下游模块接口

- 上游：source_resolver（提供源文件）
- 下游：frontend（消费 artifact JSON）
- 下游：Phase 12 patterns/drill/advisor（通过 DownstreamGates 判断可用性；SUCCESS 通常全部可用，DEGRADED_STRUCTURAL 可能只允许部分下游能力）

## 7. 当前未解决问题

- understanding_status.json 未实现
- fail-closed 策略代码未完全落地
- 单篇链路和方向链路的连接点（A_READ → source_resolver）未实现自动化
- QualityReport 到 UnderstandingStatus 的映射规则
- Phase 12 gating 代码未实现
- formula_is_core 的具体判断算法
- DownstreamGates 的最终字段是否足够
- passage_index.json 和 claim_evidence.json 的生成顺序细节
