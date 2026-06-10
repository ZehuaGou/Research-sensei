# Full Pipeline 模块（M2.5）

---

## 1. 模块目标

定义单篇论文完整链路的输入输出、失败传递、状态约束。

## 2. 产品流程位置

M2.5 是 M2 的编排层：串联 M2.1-M2.4，管理 artifact 流转和状态门控。

## 3. 非目标

- 不实现新功能
- 不改现有代码

## External Projects / Adapter Candidates

| 项目 | 对应模块 | 具体能力 | 可复用文件/函数/CLI | 接入方式 | 是否默认依赖 | 风险 | 当前状态 |
|---|---|---|---|---|---|---|---|
| PaperQA / PaperQA2 | M2.5 / M4 | evidence-grounded QA、Docs/add/query、source citation、end-to-end grounded answer discipline | PaperQA docs/add/query APIs；必须调研 local corpus mode、citation schema、no-answer handling | STRATEGY_BORROW | 否 | 不能用 fake agent 作为验收；不能替代 ResearchSensei pipeline gates | DOC_DESIGNED |
| PaperQA pipeline adapter | M2.5 / M4 | 将 PaperQA-style grounded QA 作为可选证据问答路径 | 必须调研 PaperQA Python API、settings、citation refs、failure path | OPTIONAL_ADAPTER | 否 | 依赖 embeddings/vector store；必须通过 adapter，不得深耦合 | RESEARCH_REQUIRED |
| ARIS research-review | M2.5 / M4 | 导师式 review、claim matrix、状态门控参考、研究问题追问 | `skills/research-review/SKILL.md`; 必须调研 review tracing、claim matrix、failure reporting | STRATEGY_BORROW | 否 | 只能借鉴 gating/审查思想；不作为 runtime dependency | DOC_DESIGNED |
| ARIS research-refine-pipeline | M2.5 / M4 | problem anchor、weak point、remaining risks、must-run ablations | `skills/research-refine-pipeline/SKILL.md`; 必须调研 risk/ablation/claim 字段 | STRATEGY_BORROW | 否 | 不替代 DownstreamGates / UnderstandingStatus | DOC_DESIGNED |

## 4. 当前代码位置

- `src/researchsensei/ingestion/pipeline.py` — `SinglePaperIngestionRunner`
- `src/researchsensei/direction/runner.py` — `DirectionRunner`（M1 编排器）

## 5. 单篇论文链路

### Source-Aware Pipeline

Input from M1: `canonical_paper.md`, `source_resolution.json`, canonicalization status.

```
if canonical_paper.md exists and m2_ready == true:
    CanonicalPaperReader
    CanonicalPaperValidator
    CanonicalBlockBuilder
else:
    BLOCKED_UNDERSTANDING
```

Raw LaTeX / HTML / DeepXiv / PDF / OCR material normalization belongs to M1. M2.5 does not invoke MinerU / Marker / pix2tex directly; it consumes their canonical Markdown output.

### Status rules

- `canonicalization_status=success`: M2.1 may proceed if required front matter and body exist
- `canonicalization_status=degraded`: M2.1 may proceed with warnings; M2.3/M2.4 decide card gates
- `canonicalization_status=blocked` or `m2_ready=false`: BLOCKED_UNDERSTANDING
- `formula_explanation_allowed` depends on `formula_origin`, `formula_ocr_status`, core top-K selection, and audit

### Detailed chain

```
source resolved and normalized by M1
  → canonical_paper.md
    → CanonicalPaperReader / Validator
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
| CanonicalPaperReader.validate | canonical_paper.md | ParserResult | invalid canonical input → BLOCKED_UNDERSTANDING; degraded → DEGRADED_STRUCTURAL |
| build_passage_index | DocumentIngestion.blocks | PassageIndex → passage_index.json | NO_PASSAGES → BLOCKED |
| extract_claims | PassageIndex.passages | ClaimEvidence v2 → claim_evidence.json | NO_CLAIMS → BLOCKED |
| evidence_index wrapper | claim_evidence.json | evidence_index.json (v1) | — |
| build_paper_skeleton | DocumentIngestion + EvidenceIndex | PaperSkeleton | section MISSING warnings |
| build_evidence_pack | ClaimEvidence + PassageIndex | EvidencePack [runtime] | 空 → BLOCKED; 缺 METHOD → BLOCKED |
| LLM paper_card | EvidencePack + skeleton | paper_card.json | LLM 失败 → BLOCKED |
| LLM formula_cards | EvidencePack + skeleton + formula_origin policy | formula_cards.json | 核心 top-K 公式失败 → BLOCKED; 无公式 → SKIPPED; unknown origin → derivation blocked |
| LLM teaching_cards | EvidencePack + skeleton | teaching_cards.json | 失败 → DEGRADED_STRUCTURAL |
| QualityAuditor.audit | cards + evidence + passages | quality_report.json | finding BLOCK → BLOCKED |
| Runner → UnderstandingStatus | QualityReport + component_status | understanding_status.json | 映射 |

### 状态传递规则

| 上游状态 | 下游行为 |
|----------|----------|
| canonical_paper.md missing | BLOCKED_UNDERSTANDING |
| canonical front matter invalid | BLOCKED_UNDERSTANDING |
| m2_ready=false | BLOCKED_UNDERSTANDING |
| canonicalization_status=degraded | DEGRADED_STRUCTURAL（如果理解成功） |
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
| formula_origin=unknown | 详细公式推导 blocked |
| formula_origin=reconstructed | 只能推测解释，audit 必须可见 |
| formula_origin=ocr_latex | 必须带 OCR warning 和 confidence cap |
| teaching_cards 失败 + paper_card 成功 | DEGRADED_STRUCTURAL |
| audit finding effect=BLOCK | BLOCKED_UNDERSTANDING |
| audit finding effect=WARNING only | 不阻断，warning 写入 warnings |

### Artifact 数量按状态

| 状态 | artifact 数量 | 包含 |
|------|--------------|------|
| BASELINE_ONLY | 12 | source_status, canonical_paper.md, parsed_document, passage_index, claim_evidence, evidence_index, paper_skeleton, paper_card, formula_cards, teaching_cards, understanding_status, quality_report |
| SUCCESS | 12 | 同上（card 内容为 LLM 生成） |
| DEGRADED_STRUCTURAL | 11 | 同上但 teaching_cards 不写（或标记 BASELINE） |
| BLOCKED_UNDERSTANDING | 9 | source_status, canonical_paper.md when available, parsed_document, passage_index, claim_evidence, evidence_index, paper_skeleton, understanding_status, quality_report |
| FAILED | 0-3 | 取决于失败点，可能只有 source_status |

### 下游判断规则

- `allowed_for_phase12` 是 legacy 字段，新代码使用 `allowed_downstream`（DownstreamGates）
- M4 patterns 需要 `allowed_downstream.phase12_patterns == True`
- M4 drill 需要 `allowed_downstream.phase12_drill == True`（或 `phase12_drill_degraded == True`）
- M4 advisor 需要 `allowed_downstream.advisor_questions == True`
- M4 direction-level interaction 需要 `allowed_downstream.direction_framework_update_allowed == True`
- M4 cross-paper comparison 需要 `allowed_downstream.cross_paper_comparison_allowed == True`
- UI 只能展示 `allowed_for_user_display == True` 的结果
- 用户端走 `/cards` API，debug/admin 走 `/artifacts` / `/quality_report`
- BLOCKED 不展示 card 内容
- BASELINE_ONLY 只能作为 diagnostic artifact
- API/frontend gating 详见 M3 M3_FRONTEND_RENDER.md

### Direction-Support Gates

M2.5 DownstreamGates should include:

- `direction_framework_update_allowed: bool` — allows M1 direction framework to use this paper's direction-support fields
- `cross_paper_comparison_allowed: bool` — allows M4 cross-paper understanding to compare this paper with others

These gates require: SUCCESS or DEGRADED status, direction-support fields have evidence_ref, and audit did not BLOCK direction-related claims.

## 6. 研究方向链路（M1 连接点）

研究方向链路属于 M1，此处只写连接点：

```
M1 reading_plan.json
  → A_READ papers
    → M1.3 原始材料获取
      → M1 material normalization
        → canonical_paper.md
      → M2 单篇精读链路
```

M1 链路由 `DirectionRunner` 编排，详见 M1_LITERATURE_SEARCH.md。

## 7. 与上下游模块接口

- 上游：M1.3 原始材料获取 + material normalization（提供 `canonical_paper.md`）
- 下游：M3 frontend（消费 artifact JSON）
- 下游：M4 interactive / drill / advisor（通过 DownstreamGates 判断可用性）

## 8. 测试要求

### BASELINE_ONLY 路径测试

| 测试 | 断言 |
|------|------|
| test_no_llm_client_baseline_only | status == "BASELINE_ONLY" |
| test_baseline_artifact_count | 12 artifacts written |
| test_baseline_no_user_display | allowed_for_user_display is False |

### SUCCESS 路径测试

| 测试 | 断言 |
|------|------|
| test_v2_success_status | status == "SUCCESS" |
| test_v2_success_artifact_count | 12 artifacts written |
| test_v2_success_cards_present | paper_card + formula_cards + teaching_cards written |
| test_v2_success_user_display | allowed_for_user_display is True |

### DEGRADED 路径测试

| 测试 | 断言 |
|------|------|
| test_degraded_teaching_failed | teaching_cards not written (or BASELINE) |
| test_degraded_artifact_count | 11 artifacts written |
| test_degraded_user_display | allowed_for_user_display is True (successful components only) |

### BLOCKED 路径测试

| 测试 | 断言 |
|------|------|
| test_blocked_no_card_artifacts | paper_card / formula_cards / teaching_cards NOT written |
| test_blocked_artifact_count | 9 artifacts written |
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

### Canonical / formula pipeline 测试

| 测试 | 断言 |
|------|------|
| test_pipeline_requires_canonical_paper | missing canonical_paper.md → BLOCKED_UNDERSTANDING |
| test_pipeline_blocks_invalid_front_matter | invalid front matter → BLOCKED_UNDERSTANDING |
| test_pipeline_reads_formula_origin | formula_origin preserved into formula_cards/audit |
| test_pipeline_unknown_formula_blocks_derivation | unknown origin blocks detailed formula derivation |
| test_pipeline_ocr_formula_has_warning | ocr_latex keeps OCR warning |
| test_pipeline_top_k_formula_only | only core top-K formulas get deep cards |

### 全局规则

- M2.5 的结构性状态测试不能替代验收。M2.5 验收必须跑真实 source acquisition → `canonical_paper.md` → M2.1 canonical reader → evidence → real LLM → QualityAuditor → understanding_status 的端到端链路
- 不新增依赖

## 9. 验收标准

- 单篇链路不同状态 artifact 数量正确
- 状态传递规则正确
- DownstreamGates 正确
- 真实验收必须端到端：真实 source acquisition → `canonical_paper.md` → M2.1 reader → evidence → LLM → audit → understanding_status
- 真实验收通过 `RUN_LIVE_TESTS=1 RUN_LLM_TESTS=1 RESEARCHSENSEI_LIVE_EVAL=1 python scripts/run_live_eval.py`

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
- canonical_paper.md fallback pipeline: IMPLEMENTED (demoted to fallback after paper_4_unseen blind eval)
- canonical_paper.md canonical pipeline (MinerU2.5-Pro + optional Llama refiner): DOC_DESIGNED / NOT_IMPLEMENTED
- CanonicalPaperReader / formula_origin full chain: DOC_DESIGNED / NOT_IMPLEMENTED
- FormulaOCRAdapter: fallback only for unresolved crops, model not integrated

## 11. External Reference Implementation Notes

- **Reference source**: ARIS `tools/verify_papers.py` (verification_status), ARIS composed output discipline
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: verified / unverified / verify_pending / error status affects downstream gate; output must state why it cannot enter downstream
- **ResearchSensei-owned target**: `understanding_status.json`, `DownstreamGates`
- **Schema / artifact impact**: `source_verification_status`, `allowed_for_user_display`, `allowed_downstream`, `blocking_reason`, `warnings`
- **Boundary**: ResearchSensei gate controls M3/M4. ARIS composed output is only an output discipline reference.
- **Validation implication**: Unverified / low-evidence outputs cannot enter M4 advisor. DEGRADED / BLOCKED reasons must be visible.

## 12. 当前未解决问题

- formula_is_core 的具体判断算法
- DownstreamGates 的最终字段是否足够
- passage_index.json 和 claim_evidence.json 的生成顺序细节
