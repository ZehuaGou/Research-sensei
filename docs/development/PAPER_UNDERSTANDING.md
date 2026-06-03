# Paper Understanding 模块

---

## 1. 模块目标

基于证据生成学习卡片，LLM 输出必须绑定 evidence，无 evidence 必须进入 BLOCKED_UNDERSTANDING，不允许生成最终解释。

## 2. 非目标

- 默认测试不用真实 LLM
- 不新增依赖
- 不改 frontend

## 3. 外部项目调研

### PaperQA

- **机制**: evidence-constrained answer — 将 passages 注入 prompt，要求 LLM 在 passages 范围内回答并 cite
- **对本模块的用处**: evidence pack 注入 prompt 的方式可参考；citation-backed answer 的 prompt 结构可借鉴
- **当前是否直接接入**: 否 — PaperQA 是 QA 系统，不是教学系统
- **借鉴落地**: evidence pack 必须像 citation-backed answer 一样只包含可引用 passage；LLM 只能基于 EvidencePackItem 输出；输出必须携带 evidence_ref

### ARIS

- **机制**: reviewer independence（只传文件路径，不传摘要）；kill-argument（两线程对抗）；claim audit（零上下文验证）
- **对本模块的用处**: reviewer independence 原则可直接应用（审计者独立于生成者）；claim audit 的零上下文思路可借鉴
- **当前是否直接接入**: 否 — 只参考设计
- **借鉴落地**: card builder 只负责生成；audit 模块独立读取 card + evidence + source artifact；audit 不接收 card builder 的解释；audit 结果决定 understanding_status

### OpenScholar

- **机制**: citation-backed response + citation accuracy 评估
- **对本模块的用处**: citation accuracy 的评估标准可参考
- **当前是否直接接入**: 否

## 4. 当前代码位置

- `src/researchsensei/paper_card.py` — `build_paper_card()` (rule-based), `build_paper_card_with_llm()` (LLM-enhanced)
- `src/researchsensei/formula_card.py` — 同上
- `src/researchsensei/teaching_card.py` — 同上
- `src/researchsensei/ingestion/pipeline.py` — `SinglePaperIngestionRunner` 当前只用 rule-based

**当前现实**: 代码仍然是 fallback 模式（LLM 失败时 fallback 到 rule-based）。DEVELOPMENT.md 中的 fail-closed 策略是未来目标，当前代码还未完全实现。

## 5. 输入输出

| 项 | 值 |
|----|-----|
| 输入 | paper_skeleton.json, evidence_pack, existing card baseline |
| 输出 | paper_card.json, formula_cards.json, teaching_cards.json |
| LLM prompt 只能使用 | paper title/metadata, paper_skeleton, evidence_pack, existing baseline card |
| 禁止 | 直接整篇论文全文塞入 prompt |

## 6. Artifact

- `paper_card.json`, `formula_cards.json`, `teaching_cards.json` 格式不变
- 新增 `understanding_status.json` 承载理解状态（未来实现）
- 如果状态不是 SUCCESS，不得把 card 当最终用户结果

## 7. 核心类和方法签名

### EvidencePack

```python
class EvidencePackItem(SenseiModel):
    claim_id: str
    claim_type: str
    evidence_ref: str
    quote_or_summary: str
    passage_text: str
    confidence: float
```

### understanding_status.json

```python
class UnderstandingStatus(SenseiModel):
    paper_id: str
    status: str  # SUCCESS / DEGRADED_STRUCTURAL / BLOCKED_UNDERSTANDING / FAILED / BASELINE_ONLY
    blocking_reason: str = ""
    warnings: list[WarningItem] = []
    allowed_for_user_display: bool
    allowed_for_phase12: bool
    checked_artifacts: list[str] = []
```

| 状态 | allowed_for_user_display | allowed_for_phase12 |
|------|--------------------------|---------------------|
| SUCCESS | True | True |
| DEGRADED_STRUCTURAL | False | False |
| BLOCKED_UNDERSTANDING | False | False |
| FAILED | False | False |
| BASELINE_ONLY | False | False |

### Pipeline 集成 (fail-closed 目标)

```python
class SinglePaperIngestionRunner:
    def __init__(self, ..., llm_client: LLMClient | MockLLMClient | None = None):
        self.llm_client = llm_client

    def run(self, ...):
        ...
        if self.llm_client is None:
            return build_baseline_cards_with_status("BASELINE_ONLY")

        try:
            llm_cards = build_cards_with_llm(...)
        except Exception:
            return blocked_understanding("LLM_UNAVAILABLE")

        validated = validate_evidence_refs(llm_cards, evidence_index)
        if not validated.ok:
            return blocked_understanding(validated.reason)

        return llm_cards
```

## 8. 错误/失败策略

| 场景 | 行为 |
|------|------|
| LLM client 不存在 | BASELINE_ONLY，不得标记为 v2 understanding |
| LLM 调用失败 | BLOCKED_UNDERSTANDING，warning: "LLM_UNAVAILABLE" |
| LLM 输出 evidence_ref 不存在 | 丢弃，BLOCKED_UNDERSTANDING，warning: "INVALID_EVIDENCE_REF" |
| LLM 输出无 evidence_ref | 丢弃，BLOCKED_UNDERSTANDING，warning: "MISSING_EVIDENCE_REF" |
| evidence 不足 | INSUFFICIENT_EVIDENCE，不生成解释 |
| rule-based baseline | 只能作为 diagnostic，标记 BASELINE_ONLY |

BLOCKED_UNDERSTANDING 只能展示 status/blocking_reason/warnings/diagnostic metadata，不能包含论文解释、教学内容、核心思想推断或公式讲解。

## 9. 测试断言

| 测试 | 断言 |
|------|------|
| test_pipeline_accepts_optional_llm_client | no error, status is BASELINE_ONLY |
| test_no_llm_client_produces_baseline_only | understanding_status.status == "BASELINE_ONLY" |
| test_mock_llm_client_produces_evidence_bound_card | card has evidence_refs, status is SUCCESS |
| test_llm_failure_blocks_understanding | BLOCKED_UNDERSTANDING, warning "LLM_UNAVAILABLE" |
| test_invalid_evidence_ref_blocks | BLOCKED_UNDERSTANDING, warning "INVALID_EVIDENCE_REF" |
| test_missing_evidence_ref_blocks | BLOCKED_UNDERSTANDING, warning "MISSING_EVIDENCE_REF" |
| test_baseline_only_not_allowed_for_phase12 | allowed_for_phase12 is False |
| test_blocked_understanding_no_user_facing_content | no paper explanation text |
| test_success_status_for_final_display | status == "SUCCESS", allowed_for_user_display is True |

## 10. Hard-Fail

| ID | 条件 |
|----|------|
| HF-1 | 核心 claim 无 evidence_ref 且未标 INSUFFICIENT_EVIDENCE |
| HF-2 | human_explanation 是公式文本 |
| HF-3 | formula symbol 解释与论文矛盾 |
| HF-4 | core_idea / problem 缺 evidence_ref |
| HF-5 | 输出无论文特有术语 |
| HF-6 | 输出与论文主题不符 |
| HF-7 | LLM failure produces final-looking cards |
| HF-8 | BASELINE_ONLY card used as v2/final understanding |
| HF-9 | BLOCKED_UNDERSTANDING still contains user-facing explanation text |
| HF-10 | warnings are strings instead of WarningItem |

## 11. EvidencePack 构建流程

**输入**: `ClaimEvidence` + `PassageIndex` + `paper_skeleton`

**算法**:
1. 过滤 `semantic_support == INSUFFICIENT_EVIDENCE` 的 claim
2. 按 claim_type 分组（PROBLEM / METHOD / RESULT / LIMITATION / FORMULA_CONTEXT）
3. 每个 claim 构建一个 `EvidencePackItem`
4. passage_text 从 PassageIndex 查找，截取前 500 chars
5. token_count = len(passage_text.split())
6. 按 token budget 截断（默认 4000 tokens）
7. 如果 evidence_pack 为空 → BLOCKED_UNDERSTANDING

**Schema**:
```python
class EvidencePackItem(SenseiModel):
    claim_id: str
    claim_type: str
    evidence_ref: str
    quote_or_summary: str
    passage_text: str
    confidence: float
    source_artifact: str = "evidence_index"
    token_count: int = 0

class EvidencePack(SenseiModel):
    paper_id: str
    items: list[EvidencePackItem]
    total_tokens: int = 0
    warnings: list[WarningItem] = []
```

## 12. LLM Prompt 结构

**system prompt**:
- 角色：论文研读导师
- 约束：只能基于 evidence pack 回答，不能编造
- 输出格式：JSON

**user prompt**:
- paper title / metadata（从 paper_skeleton）
- evidence pack（从 build_evidence_pack）
- 要求：生成指定字段的 JSON

**不允许**:
- 整篇论文全文塞入 prompt
- 超出 token budget

**输出 JSON schema**: 与 PaperCard / FormulaCard / TeachingCard schema 一致

**输出校验**:
- 每个 evidence_ref 必须存在于 evidence_index
- 无效 evidence_ref → 丢弃该字段
- 核心字段无有效 evidence_ref → BLOCKED_UNDERSTANDING

## 13. understanding_status.json

**Schema**: 放在 `src/researchsensei/schemas/understanding.py`

```python
class UnderstandingStatus(SenseiModel):
    paper_id: str
    status: str  # SUCCESS / DEGRADED_STRUCTURAL / BLOCKED_UNDERSTANDING / FAILED / BASELINE_ONLY
    blocking_reason: str = ""
    warnings: list[WarningItem] = []
    allowed_for_user_display: bool
    allowed_for_phase12: bool
    checked_artifacts: list[str] = []
```

**由 SinglePaperIngestionRunner 生成**，写入 `understanding_status.json`

**状态规则**:
| 状态 | allowed_for_user_display | allowed_for_phase12 |
|------|--------------------------|---------------------|
| SUCCESS | True | True |
| DEGRADED_STRUCTURAL | False | False |
| BLOCKED_UNDERSTANDING | False | False |
| FAILED | False | False |
| BASELINE_ONLY | False | False |

## 14. 当前未解决问题

- 当前代码仍有 baseline/fallback 模式，fail-closed 还未实现
- understanding_status.json schema 未定义
- LLM prompt 需要实际测试调优
- 输出校验规则需要实现
