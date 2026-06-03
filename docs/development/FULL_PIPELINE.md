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
    → parsed_document.json (DocumentIngestion)
      → build_evidence_index()
        → evidence_index.json (EvidenceIndex)
          → build_paper_skeleton()
            → paper_skeleton.json (PaperSkeleton)
              → [PassageIndex + ClaimEvidence] (Phase 11.7)
                → build_evidence_pack() (Phase 11.8)
                  → build_paper_card_with_llm() → paper_card.json
                  → build_formula_cards_with_llm() → formula_cards.json
                  → build_teaching_cards_with_llm() → teaching_cards.json
                    → audit → understanding_status.json
```

### 每步输入输出

| 步骤 | 输入 | 输出 | 失败行为 |
|------|------|------|----------|
| ParserAdapter.parse | source file | DocumentIngestion | degraded=True + warning |
| build_evidence_index | DocumentIngestion | EvidenceIndex | NO_BLOCKS_AVAILABLE warning |
| build_paper_skeleton | DocumentIngestion + EvidenceIndex | PaperSkeleton | section MISSING warnings |
| PassageIndex (11.7) | DocumentIngestion.blocks | PassageIndex | NO_PASSAGES warning |
| ClaimExtractor (11.7) | PassageIndex.passages | list[ClaimEvidence] | NO_CLAIMS warning |
| build_evidence_pack (11.8) | ClaimEvidence + PassageIndex | EvidencePack | 空 → BLOCKED_UNDERSTANDING |
| build_cards_with_llm (11.8) | EvidencePack + skeleton | cards | LLM 失败 → BLOCKED_UNDERSTANDING |
| audit (11.9) | cards + evidence_index | QualityReport | hard-fail → BLOCKED |
| understanding_status | audit result | UnderstandingStatus | — |

### 状态传递规则

| 上游状态 | 下游行为 |
|----------|----------|
| Parser degraded=True | DEGRADED_STRUCTURAL，不阻止理解但标记 |
| evidence_index 无 blocks | BLOCKED_UNDERSTANDING |
| evidence_pack 为空 | BLOCKED_UNDERSTANDING |
| LLM 失败 | BLOCKED_UNDERSTANDING |
| LLM 输出无效 evidence_ref | BLOCKED_UNDERSTANDING |
| audit hard-fail | BLOCKED_UNDERSTANDING |
| 无 LLM client | BASELINE_ONLY，不进 Phase 12 |

### 下游判断规则

- Phase 12 只能读取 `understanding_status.status == SUCCESS` 且 `allowed_for_phase12 == True`
- UI 只能展示 `allowed_for_user_display == True` 的结果
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
- 下游：Phase 12 patterns/drill（消费 SUCCESS 状态的 cards）

## 7. 当前未解决问题

- understanding_status.json 未实现
- fail-closed 策略代码未完全落地
- 单篇链路和方向链路的连接点（A_READ → source_resolver）未实现自动化
