# Paper Understanding 模块（M2.3）

---

## 1. 模块目标

基于证据生成学习卡片，LLM 输出必须绑定 evidence，无 evidence 必须进入 BLOCKED_UNDERSTANDING，不允许生成最终解释。

## 2. 非目标

- 不新增依赖
- 不改 frontend

## External Reference Boundary

ARIS provides useful paper-understanding reference patterns (Problem/Method/Results/Relevance, reviewer independence, verification_status), but does not replace ResearchSensei parser, evidence, cards, or auditor. ResearchSensei output must be paper_card / formula_cards / teaching_cards with evidence_ref binding, not ARIS-style markdown summaries. Card generation must use real LLM and evidence_ref; no evidence means BLOCKED_UNDERSTANDING.

## 3. 产品流程位置

M2.3 承接 M2.2 的证据链路，生成论文卡片：EvidencePack → LLM → paper_card / formula_cards / teaching_cards。

## 4. 可复用开源项目 / 外部服务调研

| 项目 | 用途 | GitHub / 官网 | 接入方式 | 是否默认依赖 | 风险 | 当前结论 |
|------|------|---------------|----------|--------------|------|----------|
| PaperQA | evidence-constrained answer | github.com/Future-House/paper-qa | REFERENCE_ONLY | 否 | — | 只借鉴 prompt 结构 |
| ARIS | reviewer independence | github.com/wanshuiyin/Auto-claude-code-research-in-sleep | REFERENCE_ONLY | 否 | — | 只借鉴 audit 思想 |

未完成调研不得进入代码开发。

## 5. 外部项目调研（详细）

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

## 6. 当前代码位置

- `src/researchsensei/paper_card.py` — `build_paper_card()` (rule-based baseline)
- `src/researchsensei/paper_card_v2.py` — v2 LLM builder (fail-closed)
- `src/researchsensei/formula_card.py` — `build_formula_card()` (rule-based baseline)
- `src/researchsensei/formula_card_v2.py` — v2 LLM builder (fail-closed)
- `src/researchsensei/teaching_card.py` — `build_teaching_card()` (rule-based baseline)
- `src/researchsensei/teaching_card_v2.py` — v2 LLM builder (fail-closed)
- `src/researchsensei/llm/validator.py` — LLM output validators
- `src/researchsensei/live_eval.py` — opt-in real LLM smoke / live eval helper
- `src/researchsensei/schemas/llm_output.py` — PaperCardLLMOutput, FormulaCardLLMOutput, TeachingCardLLMOutput
- `src/researchsensei/schemas/status.py` — UnderstandingStatus, DownstreamGates, EvidencePackSummary
- `src/researchsensei/ingestion/pipeline.py` — SinglePaperIngestionRunner (v2 path integration)

## 7. 输入输出

| 项 | 值 |
|----|-----|
| 输入 | paper_skeleton.json, evidence_pack, existing card baseline |
| 输出 | paper_card.json, formula_cards.json, teaching_cards.json, understanding_status.json |
| LLM prompt 只能使用 | paper title/metadata, paper_skeleton, evidence_pack, existing baseline card |
| 禁止 | 直接整篇论文全文塞入 prompt |

v2 prompt 额外约束：

- prompt 中必须列出 Allowed evidence_ref values。
- LLM 输出的 evidence_ref 必须从 Allowed evidence_ref values 中精确选择一个。
- 不允许把多个 evidence_ref 用逗号、空格或列表拼接。
- 如果证据不足，文本写 `INSUFFICIENT_EVIDENCE` 或不生成对应 card，不能编造 evidence_ref。

## 8. Artifact

- `paper_card.json`, `formula_cards.json`, `teaching_cards.json` 格式不变
- `understanding_status.json` 承载理解状态
- `quality_report.json` 承载审计结果
- 如果状态不是 SUCCESS，不得把 card 当最终用户结果

## 9. Schema / 数据结构

### EvidencePack（运行时对象，不持久化）

```python
class EvidencePackItem(SenseiModel):
    claim_id: str
    claim_type: str
    evidence_ref: str
    passage_id: str = ""
    quote_or_summary: str
    passage_text: str
    confidence: float
    retrieval_score: float = 0.0
    token_count: int = 0
    source_artifact: str = "evidence_index"
```

### EvidencePackSummary（持久化在 UnderstandingStatus 中）

```python
class EvidencePackSummary(SenseiModel):
    included_claim_ids: list[str] = Field(default_factory=list)
    excluded_claim_ids: list[str] = Field(default_factory=list)
    total_tokens: int = 0
    claim_type_counts: dict[str, int] = Field(default_factory=dict)
    truncated_passage_ids: list[str] = Field(default_factory=list)
```

### UnderstandingStatus

```python
class DownstreamGates(SenseiModel):
    reading_display: bool = False
    phase12_patterns: bool = False       # legacy field name, 语义归属 M4
    phase12_drill: bool = False          # legacy field name, 语义归属 M4
    phase12_drill_degraded: bool = False # legacy field name, 语义归属 M4
    advisor_questions: bool = False

class UnderstandingStatus(SenseiModel):
    schema_version: str = "v2"
    paper_id: str
    status: str  # SUCCESS / DEGRADED_STRUCTURAL / BLOCKED_UNDERSTANDING / FAILED / BASELINE_ONLY
    blocking_reason: str = ""
    warnings: list[WarningItem] = Field(default_factory=list)
    allowed_for_user_display: bool
    allowed_for_phase12: bool  # legacy field, use allowed_downstream instead
    checked_artifacts: list[str] = Field(default_factory=list)
    component_status: dict[str, str] = Field(default_factory=dict)
    evidence_pack_summary: EvidencePackSummary | None = None
    allowed_downstream: DownstreamGates = Field(default_factory=DownstreamGates)
```

### 主状态定义

| 状态 | 含义 | allowed_for_user_display | downstream gating |
|------|------|--------------------------|-------------------|
| SUCCESS | LLM cards 生成成功，audit 通过 | True | 由 DownstreamGates 决定（全部 True） |
| DEGRADED_STRUCTURAL | 论文理解成功，但某些组件降级 | True | 由 DownstreamGates 决定 |
| BASELINE_ONLY | 无 LLM 或仅 rule-based baseline | False | 全部 False |
| BLOCKED_UNDERSTANDING | evidence / LLM / audit 导致理解不可信 | False | 全部 False |
| FAILED | 系统级异常（pipeline crash / 文件系统错误） | False | 全部 False |

### component_status

```
component_status:
  paper_card: SUCCESS / FAILED / BASELINE
  formula_cards: SUCCESS / SKIPPED / FAILED / BASELINE
  teaching_cards: SUCCESS / FAILED / BASELINE
  audit: SUCCESS / FAILED
```

### LLM 输出 schema

```python
class ClaimOutput(SenseiModel):
    text: str
    evidence_ref: str = ""

class PaperCardLLMOutput(SenseiModel):
    one_sentence_summary: str
    problem: ClaimOutput
    core_idea: ClaimOutput
    method_overview: ClaimOutput
    experiment_summary: ClaimOutput
    limitations: ClaimOutput

class FormulaCardLLMOutput(SenseiModel):
    purpose: str
    symbols: list[dict] = Field(default_factory=list)
    intuition: str = ""
    numeric_example: str = ""
    evidence_ref: str = ""

class TeachingCardLLMOutput(SenseiModel):
    human_explanation: str
    analogy_explanation: str = ""
    minimal_formula_explanation: str = ""
    numeric_example: str = ""
    paper_role_explanation: str = ""
    evidence_ref: str = ""
```

## 10. 核心类和方法签名

### Pipeline 集成 (fail-closed)

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

## 11. 错误/失败策略

| 场景 | 行为 |
|------|------|
| LLM client 不存在 | BASELINE_ONLY，不得标记为 v2 understanding |
| LLM 调用失败 | BLOCKED_UNDERSTANDING，warning: "LLM_UNAVAILABLE" |
| LLM 输出 evidence_ref 不存在 | 丢弃，BLOCKED_UNDERSTANDING，warning: "INVALID_EVIDENCE_REF" |
| LLM 输出无 evidence_ref | 丢弃，BLOCKED_UNDERSTANDING，warning: "MISSING_EVIDENCE_REF" |
| LLM invalid JSON | BLOCKED_UNDERSTANDING，warning: "LLM_INVALID_JSON" |
| LLM timeout | BLOCKED_UNDERSTANDING，warning: "LLM_TIMEOUT" |
| evidence 不足 | INSUFFICIENT_EVIDENCE，不生成解释 |
| rule-based baseline | 只能作为 diagnostic，标记 BASELINE_ONLY |
| paper_card 成功 + teaching_cards 失败 | DEGRADED_STRUCTURAL |
| paper_card 成功 + formula_cards 失败（公式核心） | BLOCKED_UNDERSTANDING |
| paper_card 成功 + formula_cards SKIPPED（无公式） | 不阻断 |
| paper_card 失败 | BLOCKED |
| audit hard-fail (effect=BLOCK) | BLOCKED_UNDERSTANDING |
| audit warning only (effect=WARNING) | 不阻断，warning 写入 warnings |
| parser degraded | 不是 hard-fail，DEGRADED_STRUCTURAL（如果理解成功） |

BLOCKED_UNDERSTANDING 只能展示 status/blocking_reason/warnings/diagnostic metadata，不能包含论文解释、教学内容、核心思想推断或公式讲解。

## 12. M4 Downstream Gates

DownstreamGates 控制下游 M4 互动式学习的访问权限，不再用 `status != SUCCESS` 作为唯一判断。

> 注意：DownstreamGates 字段名 `phase12_patterns` / `phase12_drill` 等是 legacy 命名，语义归属 M4 互动式学习。

| 状态 | paper_card | teaching_cards | reading_display | phase12_patterns | phase12_drill | advisor_questions |
|------|-----------|----------------|-----------------|-----------------|---------------|-------------------|
| SUCCESS | SUCCESS | SUCCESS | True | True | True | True |
| DEGRADED | SUCCESS | SUCCESS | True | True | True | True |
| DEGRADED | SUCCESS | FAILED | True | True | True（降级） | False |
| BASELINE | — | — | False | False | False | False |
| BLOCKED | — | — | False | False | False | False |
| FAILED | — | — | False | False | False | False |

```python
if not understanding_status.allowed_downstream.phase12_patterns:
    raise GatingError("M4 patterns not allowed")

if not understanding_status.allowed_downstream.phase12_drill:
    if not understanding_status.allowed_downstream.phase12_drill_degraded:
        raise GatingError("M4 drill not allowed")

if not understanding_status.allowed_downstream.advisor_questions:
    raise GatingError("M4 advisor_questions not allowed")
```

## 13. 测试要求

### Baseline builder 测试

| 测试 | 断言 |
|------|------|
| test_baseline_paper_card | paper_card fields populated |
| test_baseline_formula_cards | formula_cards fields populated |
| test_baseline_teaching_cards | teaching_cards fields populated |

### v2 builder fail-closed 测试

| 测试 | 断言 |
|------|------|
| test_no_llm_client_produces_baseline_only | status == "BASELINE_ONLY" |
| test_mock_llm_client_produces_evidence_bound_card | card has evidence_refs, status is SUCCESS |
| test_llm_failure_blocks_understanding | BLOCKED_UNDERSTANDING, warning "LLM_UNAVAILABLE" |
| test_invalid_evidence_ref_blocks | BLOCKED_UNDERSTANDING, warning "INVALID_EVIDENCE_REF" |
| test_missing_evidence_ref_blocks | BLOCKED_UNDERSTANDING, warning "MISSING_EVIDENCE_REF" |
| test_baseline_only_not_allowed_for_downstream | allowed_for_user_display is False |

### LLM output validator 测试

| 测试 | 断言 |
|------|------|
| test_validate_paper_card_llm_output_valid | valid output passes |
| test_validate_paper_card_llm_output_missing_evidence_ref | missing evidence_ref → BLOCKED |
| test_validate_formula_cards_llm_output_valid | valid output passes |
| test_validate_teaching_cards_llm_output_valid | valid output passes |
| test_llm_invalid_json_blocks | invalid JSON → BLOCKED_UNDERSTANDING |

### Pipeline v2 路径测试

| 测试 | 断言 |
|------|------|
| test_pipeline_accepts_optional_llm_client | no error, status is BASELINE_ONLY |
| test_pipeline_v2_success_artifacts | SUCCESS → paper_card + formula_cards + teaching_cards + understanding_status + quality_report written |
| test_pipeline_v2_degraded_artifacts | DEGRADED → teaching_cards not written |
| test_pipeline_v2_blocked_artifacts | BLOCKED → no card artifacts written |
| test_blocked_understanding_no_user_facing_content | no paper explanation text in blocked output |
| test_success_status_for_final_display | status == "SUCCESS", allowed_for_user_display is True |
| test_m2_real_llm_smoke | opt-in real LLM 生成可解析输出，并验证 evidence_ref 可追溯 |

### 全局规则

- 快速回归（`python -m pytest -q`）可使用 mock/fake，不作为模块验收依据
- 真实验收必须真实调用 LLM，使用真实 PDF 输入
- 不新增依赖
- M2 真实验收入口：`RUN_LLM_TESTS=1 RESEARCHSENSEI_LIVE_EVAL=1 python scripts/run_live_eval.py`

## 14. 验收标准

- LLM 输出必须绑定 evidence_ref
- 无效 evidence_ref → BLOCKED
- empty evidence_pack → BLOCKED
- baseline path 输出 BASELINE_ONLY
- v2 path fail-closed，不 fallback
- 真实验收必须使用真实 PDF 输入（不能只用 synthetic markdown）
- 真实验收必须真实调用 LLM，生成 paper/formula/teaching cards
- 真实验收必须通过 QualityAuditor 审计
- 真实验收必须生成 understanding_status.json
- evidence_ref 必须可追溯
- DEGRADED / BLOCKED 必须真实反映质量，不允许为通过测试放宽
- real LLM smoke 必须记录 model、prompt version、schema version、token、cost、latency、失败原因
- real LLM smoke 失败不能伪装成普通 mock 测试通过

## 15. 当前实现状态

- baseline builders 已实现（paper_card.py, formula_card.py, teaching_card.py）
- v2 LLM output schema 已实现（schemas/llm_output.py）
- v2 builders 已实现（paper_card_v2.py, formula_card_v2.py, teaching_card_v2.py）
- LLM output validator 已实现（llm/validator.py）
- pipeline v2 path 已接入（SUCCESS / DEGRADED / BLOCKED）
- EvidencePack 已实现
- UnderstandingStatus / DownstreamGates 已实现
- QualityAuditor 已接入
- understanding_status.json / quality_report.json 已写入
- 测试已覆盖：15+ tests
- Real LLM smoke 已实现 opt-in 入口：`tests_live/test_m2_real_llm_smoke.py` 与 `scripts/run_live_eval.py`
- v2 prompts 已加强 evidence_ref 精确选择约束，防止模型拼接多个 evidence_ref
- formula_is_core 判断未实现

## 16. ARIS Alignment

ARIS's structured paper output (Problem / Method / Results / Relevance / Source / Verification Status) overlaps with M2.3 paper understanding. ARIS also provides reference paper summary templates and "What They Did / Key Results / Limitations & Open Questions" structures.

| ARIS Capability | Reuse Mode | Application in M2.3 |
|---|---|---|
| Problem/Method/Results/Relevance structure | STRATEGY_BORROW | Enhance paper_card output schema |
| Reference Paper Summary template | STRATEGY_BORROW | Standardize paper_card fields |
| "What They Did" / "Key Results" | STRATEGY_BORROW | method_overview and experiment_summary fields |
| Limitations & Open Questions | STRATEGY_BORROW | limitations field with structured open questions |
| Verification status per claim | STRATEGY_BORROW | Track which claims are verified vs. inferred |
| Potential Improvement Directions | STRATEGY_BORROW | Future advisor/drill input |

**Boundary**: ARIS does not have formula_card or symbol explanation. ARIS does not have evidence_ref / PassageIndex / ClaimEvidence binding. These remain ResearchSensei-specific.

## 17. 当前未解决问题

- formula_is_core 的具体判断算法
- EvidencePackSummary 是否足够复现 LLM 输入
- component_status 的值是否还需要 DEGRADED
- 旧 rule-based baseline builders 与 v2 builders 的边界仍需确认（old `*_with_llm` 函数可能仍有 fallback，但 pipeline 不走它们）
- DownstreamGates 的最终字段是否足够
- 当前 real LLM smoke 只有一个 synthetic paper 样例，不能代表真实论文质量
- 当前成本估算依赖价格环境变量；未配置时报告 cost=0，但 token limit 仍生效
