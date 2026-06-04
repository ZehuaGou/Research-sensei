# Full Pipeline 模块（M2.5）

---

## 1. 模块目标

定义单篇论文完整链路的输入输出、失败传递、状态约束。

## 2. 产品流程位置

M2.5 是 M2 的编排层：串联 M2.1-M2.4，管理 artifact 流转和状态门控。

## 3. 非目标

- 不实现新功能
- 不改现有代码

## 4. 当前代码位置

- `src/researchsensei/ingestion/pipeline.py` — `SinglePaperIngestionRunner`
- `src/researchsensei/direction/runner.py` — `DirectionRunner`（M1 编排器）

## 5. 单篇论文链路

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
                                  → DownstreamGates (M4)
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

### Artifact 数量按状态

| 状态 | artifact 数量 | 包含 |
|------|--------------|------|
| BASELINE_ONLY | 11 | source_status, parsed_document, passage_index, claim_evidence, evidence_index, paper_skeleton, paper_card, formula_cards, teaching_cards, understanding_status, quality_report |
| SUCCESS | 11 | 同上（card 内容为 LLM 生成） |
| DEGRADED_STRUCTURAL | 10 | 同上但 teaching_cards 不写（或标记 BASELINE） |
| BLOCKED_UNDERSTANDING | 8 | source_status, parsed_document, passage_index, claim_evidence, evidence_index, paper_skeleton, understanding_status, quality_report |
| FAILED | 0-3 | 取决于失败点，可能只有 source_status |

### 下游判断规则

- `allowed_for_phase12` 是 legacy 字段，新代码使用 `allowed_downstream`（DownstreamGates）
- M4 patterns 需要 `allowed_downstream.phase12_patterns == True`
- M4 drill 需要 `allowed_downstream.phase12_drill == True`（或 `phase12_drill_degraded == True`）
- M4 advisor 需要 `allowed_downstream.advisor_questions == True`
- UI 只能展示 `allowed_for_user_display == True` 的结果
- 用户端走 `/cards` API，debug/admin 走 `/artifacts` / `/quality_report`
- BLOCKED 不展示 card 内容
- BASELINE_ONLY 只能作为 diagnostic artifact
- API/frontend gating 详见 M3 M3_FRONTEND_RENDER.md

## 6. 研究方向链路（M1 连接点）

研究方向链路属于 M1，此处只写连接点：

```
M1 reading_plan.json
  → A_READ papers
    → M1.3 原始材料获取
      → M2 单篇精读链路
```

M1 链路由 `DirectionRunner` 编排，详见 M1_LITERATURE_SEARCH.md。

## 7. 与上下游模块接口

- 上游：M1.3 原始材料获取（提供源文件）
- 下游：M3 frontend（消费 artifact JSON）
- 下游：M4 interactive / drill / advisor（通过 DownstreamGates 判断可用性）

## 8. 测试要求

### BASELINE_ONLY 路径测试

| 测试 | 断言 |
|------|------|
| test_no_llm_client_baseline_only | status == "BASELINE_ONLY" |
| test_baseline_artifact_count | 11 artifacts written |
| test_baseline_no_user_display | allowed_for_user_display is False |

### SUCCESS 路径测试

| 测试 | 断言 |
|------|------|
| test_v2_success_status | status == "SUCCESS" |
| test_v2_success_artifact_count | 11 artifacts written |
| test_v2_success_cards_present | paper_card + formula_cards + teaching_cards written |
| test_v2_success_user_display | allowed_for_user_display is True |

### DEGRADED 路径测试

| 测试 | 断言 |
|------|------|
| test_degraded_teaching_failed | teaching_cards not written (or BASELINE) |
| test_degraded_artifact_count | 10 artifacts written |
| test_degraded_user_display | allowed_for_user_display is True (successful components only) |

### BLOCKED 路径测试

| 测试 | 断言 |
|------|------|
| test_blocked_no_card_artifacts | paper_card / formula_cards / teaching_cards NOT written |
| test_blocked_artifact_count | 8 artifacts written |
| test_blocked_no_user_display | allowed_for_user_display is False |
| test_blocked_has_blocking_reason | blocking_reason is non-empty |

### FAILED 路径测试

| 测试 | 断言 |
|------|------|
| test_parser_system_failure | job status FAILED |
| test_failed_artifact_count | 0-3 artifacts (depends on failure point) |

### Audit override 测试

| 测试 | 断言 |
|------|------|
| test_audit_block_overrides_success | v2 SUCCESS + audit BLOCK → BLOCKED |
| test_audit_block_overrides_degraded | DEGRADED + audit BLOCK → BLOCKED |
| test_audit_warning_does_not_block | WARNING only → not blocked |

### 全局规则

- 默认不真实调用 LLM
- 不联网
- 不新增依赖

## 9. 验收标准

- 单篇链路不同状态 artifact 数量正确
- 状态传递规则正确
- DownstreamGates 正确
- 默认测试不联网、不真实调用 LLM

## 10. 当前实现状态

- SinglePaperIngestionRunner 已实现
- ParserAdapter 已接入
- PassageIndex / ClaimEvidence / EvidencePack 已接入
- baseline path 已实现
- v2 path 已实现（SUCCESS / DEGRADED / BLOCKED）
- QualityAuditor 已接入
- understanding_status.json / quality_report.json 已写入
- DownstreamGates 已实现
- 测试已覆盖：15+ tests

## 11. 当前未解决问题

- formula_is_core 的具体判断算法
- DownstreamGates 的最终字段是否足够
- passage_index.json 和 claim_evidence.json 的生成顺序细节
