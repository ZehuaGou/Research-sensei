# 互动式学习与长期记忆模块（M4）

---

## 1. 模块目标

在 M2 单篇论文理解完成后，提供互动式学习能力：让用户通过选中内容、追问、训练、长期记忆，真正掌握论文，而非只看一遍卡片。

M4 是正式一级模块。当前状态：文档设计中，代码未实现，当前不进入代码开发。

---

## 2. 非目标

- 不重复 M2 的论文解析和卡片生成
- 不替代 M1 的论文搜索
- 不实现自动写论文
- 不在当前阶段实现代码

---

## 3. 产品流程位置

```
M1 找论文 → M2 读懂论文 → M3 展示结果 → M4 互动学习与长期记忆
```

M4 在 M3 之后：用户已经看到论文卡片，开始互动学习。

M4 依赖 M2 的 artifacts：
- paper_card.json, formula_cards.json, teaching_cards.json
- passage_index.json, claim_evidence.json, evidence_index.json
- understanding_status.json

M4 的下游 gates 由 M2 的 DownstreamGates 控制（legacy field names）：
- `allowed_downstream.phase12_patterns` → M4 patterns
- `allowed_downstream.phase12_drill` → M4 drill
- `allowed_downstream.advisor_questions` → M4 advisor

---

## 4. 可复用开源项目 / 外部服务调研

| 项目 | 用途 | GitHub / 官网 | 接入方式 | 是否默认依赖 | 风险 | 当前结论 |
|------|------|---------------|----------|--------------|------|----------|
| LangChain Memory | 长期记忆框架 | github.com/langchain-ai/langchain | REFERENCE_ONLY | 否 | 过重 | 只借鉴 memory 模块设计 |
| MemGPT / Letta | 会话记忆管理 | github.com/cpacker/MemGPT | REFERENCE_ONLY | 否 | 过重 | 只借鉴 session memory 设计 |
| STORM | 多视角追问 | github.com/stanford-oval/storm | REFERENCE_ONLY | 否 | — | 只借鉴 multi-perspective questioning |
| ARIS research-review | 对抗式评估 | github.com/wanshuiyin/Auto-claude-code-research-in-sleep | REFERENCE_ONLY | 否 | — | 参考 advisor 评估思路 |

未完成调研不得进入代码开发。

## 5. 当前代码位置

### 已存在（M3 前端占位）

- `frontend/src/components/` — AskPanel / TextSelectionToolbar 组件占位
- M3 中 patterns / drill tabs 显示"未开放"，后续归 M4

### 未实现

- M4 API endpoints, M4 schemas, M4 memory persistence
- M4 retrieval logic, M4 advisor question generation
- M4 frontend integration, M4 tests

---

## 6. M4.1 选中内容解释

### 目标

用户在论文原文、卡片、公式、段落中选中一段内容，系统解释它在当前论文中的含义和作用。

### 输入

| 字段 | 说明 |
|------|------|
| job_id | 任务 ID |
| paper_id | 论文 ID |
| selected_text | 用户选中的文本 |
| selection_range | 选中范围（可选） |
| passage_id / evidence_ref | 关联的 passage 或 evidence |
| block_ids | 关联的 block（可选） |
| current_tab / current_view | 当前所在 tab（可选） |
| user_question | 用户追问（可选） |

### 输出

```python
class SelectionExplanation(SenseiModel):
    answer: str
    cited_evidence_refs: list[str] = Field(default_factory=list)
    cited_passage_ids: list[str] = Field(default_factory=list)
    relation_to_current_section: str = ""
    relation_to_paper_claim: str = ""
    confidence: float = 0.0
    used_memory_ids: list[str] = Field(default_factory=list)
    warnings: list[WarningItem] = Field(default_factory=list)
```

### 边界

- 不允许脱离 evidence_ref 泛泛解释
- 没有 evidence_ref 时必须降级
- 不生成新的 paper_card
- 不直接修改长期记忆，除非用户确认保存或策略允许

### 测试要求

| 测试 | 断言 |
|------|------|
| test_selection_valid_evidence_ref | grounded explanation with cited_evidence_refs |
| test_selection_missing_evidence_ref | degraded / rejected + warning |
| test_selection_not_in_paper | rejected / warning |
| test_selection_has_citations | cited_evidence_refs 非空 |
| test_selection_real_llm_grounded_explanation | 真实 LLM 返回 grounded explanation with cited_evidence_refs |
| test_selection_failure_path | LLM failure → degraded |

---

## 7. M4.2 符号与公式解释

### 目标

解释公式整体、单个符号、符号来源、公式直觉、数值例子、公式在论文中的作用。

### 输入

| 字段 | 说明 |
|------|------|
| job_id | 任务 ID |
| paper_id | 论文 ID |
| formula_id | 公式 ID |
| formula_latex | 公式 LaTeX |
| selected_symbol | 选中的符号（可选） |
| evidence_ref / passage_id | 关联的 evidence |
| surrounding_text | 公式上下文 |
| related_formula_card | 关联的 formula_card（可选） |

### 输出

```python
class FormulaSymbolExplanation(SenseiModel):
    formula_id: str
    symbol: str
    meaning: str
    source_sentence: str = ""
    intuition: str = ""
    numeric_example: str = ""
    role_in_method: str = ""
    evidence_ref: str = ""
    confidence: float = 0.0
    warnings: list[WarningItem] = Field(default_factory=list)
```

### 边界

- 不编造符号含义
- 公式上下文不足时必须标记 NEEDS_HUMAN_CHECK
- 符号解释优先使用 formula_cards / passage_index / claim_evidence
- 不重新解析 PDF

### 测试要求

| 测试 | 断言 |
|------|------|
| test_formula_valid_symbol | symbol explanation with meaning |
| test_formula_unknown_symbol | NEEDS_HUMAN_CHECK |
| test_formula_missing_context | degraded response |
| test_formula_has_evidence_ref | evidence_ref 非空 |
| test_formula_no_fabrication | 不伪造论文实验结果 |

---

## 8. M4.3 上下文追问

### 目标

用户围绕当前论文继续追问，系统结合当前段落、全文理解、证据链、已读论文记忆回答。

### 输入

| 字段 | 说明 |
|------|------|
| job_id | 任务 ID |
| paper_id | 论文 ID |
| user_question | 用户问题 |
| current_focus | 当前关注点（可选） |
| selected_text | 选中文本（可选） |
| session_id | 会话 ID |
| context_scope | selection / passage / paper / memory / all |

### 输出

```python
class InteractiveAnswer(SenseiModel):
    answer: str
    evidence_refs: list[str] = Field(default_factory=list)
    memory_refs: list[str] = Field(default_factory=list)
    uncertainty: str = ""
    follow_up_suggestions: list[str] = Field(default_factory=list)
    used_context: dict[str, bool] = Field(default_factory=dict)
    warnings: list[WarningItem] = Field(default_factory=list)
```

### 检索顺序（固定策略）

1. 先查 SessionContext
2. 再查 UserQuestionMemory（重复问题命中 → 不调用 LLM）
3. 再查 PaperMemory / PassageMemory / FormulaMemory
4. 再查当前 paper artifacts（paper_card / formula_cards / teaching_cards）
5. 再查 passage_index / claim_evidence / evidence_pack
6. 最后才调用 LLM
7. LLM 输出必须带证据引用
8. 无证据时降级，不编造

### 测试要求

| 测试 | 断言 |
|------|------|
| test_question_from_memory | 不调用 LLM |
| test_question_from_evidence | 真实 LLM 基于 evidence 回答 |
| test_question_missing_evidence | degraded answer |
| test_question_has_refs | evidence_refs 或 memory_refs 非空 |
| test_repeated_question_memory | 命中 memory |
| test_no_duplicate_llm_call | 同一问题不调用 LLM 两次 |

---

## 9. M4.4 导师式追问与研究训练

### 目标

模拟博士生导师 / 论文导师的思维方式，对用户进行组会、开题、答辩式追问，训练用户真正理解论文。

### 追问重点

- 论文核心假设
- 方法为什么有效
- 公式机制
- 实验设计是否合理
- 消融实验是否支撑结论
- 和已有工作的区别
- 创新点是否站得住
- 方法失败场景
- 可扩展方向
- 研究价值
- 用户是否能用自己的话讲清论文

### advisor_mode

| 模式 | 说明 |
|------|------|
| group_meeting | 组会式追问，偏方法细节 |
| defense | 答辩式追问，偏全局理解 |
| qualifying_exam | 资格考试式追问，偏基础概念 |
| paper_review | 论文审稿式追问，偏创新性和局限性 |

### 输入

| 字段 | 说明 |
|------|------|
| paper_id | 论文 ID |
| paper_card | 论文卡片 |
| formula_cards | 公式卡片 |
| teaching_cards | 教学卡片 |
| claim_evidence | 证据链 |
| user_answer | 用户回答（可选） |
| previous_questions | 之前的问题列表 |
| advisor_mode | group_meeting / defense / qualifying_exam / paper_review |

### 输出

```python
class AdvisorQuestion(SenseiModel):
    question: str
    target_concept: str = ""
    difficulty: str = "medium"  # easy / medium / hard
    expected_answer_points: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    question_type: str = ""  # assumption / method / experiment / limitation / innovation
    follow_up_policy: str = ""  # deeper / redirect / praise_then_deeper

class AdvisorEvaluation(SenseiModel):
    score: float = 0.0
    missing_points: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    next_question: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    feedback: str = ""
```

### 边界

- 不生成泛泛学习题
- 问题必须基于当前论文
- 追问必须能回到 evidence_ref
- 不用导师口吻吓人，但要有研究训练强度
- 用户回答不确定时要追问，而不是直接给满分

### 测试要求

| 测试 | 断言 |
|------|------|
| test_advisor_question_has_refs | evidence_refs 非空 |
| test_advisor_targets_concept | question_type 覆盖 assumption/method/experiment/limitation |
| test_advisor_weak_follow_up | weak answer → follow-up question |
| test_advisor_strong_deeper | strong answer → deeper question |
| test_advisor_mode_style | advisor_mode 影响 question style |
| test_advisor_no_generic | 基于当前论文 |
| test_advisor_real_llm_question_generation | 真实 LLM 生成 paper-specific 问题 |

---

## 10. M4.5 论文知识库与长期记忆

### 目标

存储用户已读论文、已解释内容、用户回答、导师追问结果，供后续检索和复用。

### 输入

- paper_card, formula_cards, teaching_cards
- user interactions（选中解释、追问、回答）
- advisor evaluations, session events

### Schema

```python
class PaperMemory(SenseiModel):
    memory_id: str = ""
    paper_id: str
    core_claims: list[str] = Field(default_factory=list)
    key_formulas: list[str] = Field(default_factory=list)
    user_understanding_level: str = "unknown"
    source_artifact: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    schema_version: str = "v1"

class PassageMemory(SenseiModel):
    memory_id: str = ""
    passage_id: str
    paper_id: str
    key_concepts: list[str] = Field(default_factory=list)
    user_explanation: str = ""
    understanding_score: float = 0.0
    source_artifact: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    schema_version: str = "v1"

class FormulaMemory(SenseiModel):
    memory_id: str = ""
    formula_id: str
    paper_id: str
    symbol_explanations: dict[str, str] = Field(default_factory=dict)
    user_explanation: str = ""
    source_artifact: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    schema_version: str = "v1"

class SymbolMemory(SenseiModel):
    memory_id: str = ""
    symbol: str
    paper_id: str
    meaning: str = ""
    user_explanation: str = ""
    source_artifact: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    schema_version: str = "v1"

class SessionContext(SenseiModel):
    session_id: str
    paper_id: str
    current_focus: str = ""
    question_history: list[dict] = Field(default_factory=list)
    token_budget_used: int = 0
    created_at: str = ""
    updated_at: str = ""
    schema_version: str = "v1"

class UserQuestionMemory(SenseiModel):
    memory_id: str = ""
    question_id: str
    paper_id: str
    question: str = ""
    answer: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)
    source_artifact: str = ""
    created_at: str = ""
    updated_at: str = ""
    schema_version: str = "v1"
```

### Artifact / 持久化内容

当前未实现。候选 artifact / DB 表：

| 内容 | 候选格式 |
|------|----------|
| paper_memory | paper_memory.json / DB table |
| passage_memory | passage_memory.json / DB table |
| formula_memory | formula_memory.json / DB table |
| symbol_memory | symbol_memory.json / DB table |
| session_context | session_context.json / DB table |
| user_question_memory | user_question_memory.json / DB table |
| advisor_session | advisor_session.json / DB table |

当前不落库，不改 workspace，不改数据库。实现前需要讨论 storage strategy：SQLite / JSON artifact / vector DB / hybrid。

### 边界

- 长期记忆不等于 cache
- 记忆必须可追踪来源（source_artifact, evidence_refs）
- 不保存 API key / 敏感隐私
- 用户可清除记忆
- 未确认的解释不能当成高可信记忆

### 测试要求

| 测试 | 断言 |
|------|------|
| test_memory_round_trip | 所有 Memory schema serialize → deserialize |
| test_memory_traceability | memory 包含 source_artifact + evidence_refs |
| test_memory_update_existing | 更新已有 memory |
| test_memory_delete_clear | 删除/清除 memory |
| test_memory_confidence_downgrade | 低置信 memory 降级 |
| test_memory_no_secrets | 不保存 API key / 敏感信息 |

---

## 11. M4.6 记忆优先检索与 token 节省

### 目标

优先使用已有记忆和 artifacts，减少重复 LLM 调用，降低成本，提高一致性。

### 检索顺序（固定策略）

1. SessionContext
2. UserQuestionMemory（重复问题 → 不调用 LLM）
3. PaperMemory
4. PassageMemory / FormulaMemory / SymbolMemory
5. 当前 paper artifacts（paper_card / formula_cards / teaching_cards）
6. passage_index / claim_evidence / evidence_pack
7. LLM fallback

### 输出

```python
class MemoryRetrievalResult(SenseiModel):
    matched_memory_ids: list[str] = Field(default_factory=list)
    matched_artifacts: list[str] = Field(default_factory=list)
    should_call_llm: bool = True
    reason: str = ""
    estimated_token_saved: int = 0
    confidence: float = 0.0
    warnings: list[WarningItem] = Field(default_factory=list)
```

### 边界

- memory hit 不等于一定正确
- 低置信记忆要二次验证
- 不允许为了省 token 而牺牲证据质量
- cache 是请求级复用，memory 是论文学习知识库，二者要区分

### 测试要求

| 测试 | 断言 |
|------|------|
| test_memory_hit_no_llm | should_call_llm=False |
| test_low_confidence_verify | 用 evidence 二次验证 |
| test_no_memory_use_evidence | 用 evidence pack |
| test_no_evidence_degraded | degraded |
| test_no_duplicate_llm_call | 不重复调用 |
| test_token_saved_metric | estimated_token_saved 存在 |

---

## 12. API 候选

全部标为：设计中 / 未实现。

| Endpoint | 用途 | 输入 | 输出 | 当前状态 |
|----------|------|------|------|----------|
| POST /api/v1/jobs/{job_id}/selection/explain | 选中内容解释 | selected_text + context | SelectionExplanation | 未实现 |
| POST /api/v1/jobs/{job_id}/formula/explain | 符号与公式解释 | formula_id + symbol | FormulaSymbolExplanation | 未实现 |
| POST /api/v1/jobs/{job_id}/ask | 上下文追问 | user_question + context | InteractiveAnswer | 未实现 |
| POST /api/v1/jobs/{job_id}/advisor/question | 导师追问 | advisor_mode + context | AdvisorQuestion | 未实现 |
| POST /api/v1/jobs/{job_id}/advisor/evaluate | 回答评估 | user_answer + question | AdvisorEvaluation | 未实现 |
| GET /api/v1/jobs/{job_id}/memory | 获取记忆 | — | memory list | 未实现 |
| DELETE /api/v1/jobs/{job_id}/memory | 清除记忆 | — | success | 未实现 |

---

## 13. 前端交互候选

| 交互 | 说明 | 当前状态 |
|------|------|----------|
| 文本选中 toolbar | 选中文字 → 弹出解释面板 | 组件占位，M4 逻辑未接入 |
| 公式 hover / click | 公式交互 → 显示符号解释 | 未实现 |
| 右侧 AskPanel | 追问输入框 → 发送问题 | 组件占位，M4 逻辑未接入 |
| Advisor drill panel | 导师追问面板 | 未实现 |
| Memory panel | 记忆查看面板 | 未实现 |
| patterns / drill tabs | M4 patterns/drill 功能 | tabs 显示"未开放"，后续归 M4 |

---

## 14. 状态流 / 错误策略

| 场景 | 状态 | 行为 | 调用 LLM | 写记忆 |
|------|------|------|---------|--------|
| missing selection context | degraded | 返回降级提示 | 否 | 否 |
| missing evidence_ref | degraded | 返回降级 + warning | 否 | 否 |
| missing formula context | degraded | NEEDS_HUMAN_CHECK | 否 | 否 |
| memory hit but stale | verify | evidence 二次验证 | 视情况 | 更新 |
| memory hit low confidence | verify | evidence 二次验证 | 视情况 | 更新 |
| LLM unavailable | degraded | 返回 memory/artifacts 内容 | 否 | 否 |
| token budget exceeded | degraded | 截断 context + warning | 是（截断后） | 否 |
| user asks outside paper scope | warning | "超出当前论文范围" | 否 | 否 |
| advisor question no evidence | degraded | 跳过该问题 + warning | 否 | 否 |

---

## 15. 测试要求总览

### 全局规则

- M4 validation must use real LLM and real artifacts. Mock/fake clients are not valid acceptance tests. Missing keys or unavailable external services fail validation instead of skipping.

### 每子模块测试覆盖

| 子模块 | 测试数 | 关键测试 |
|--------|--------|---------|
| M4.1 | 6 | valid/missing evidence_ref, not_in_paper, citations, failure_path |
| M4.2 | 5 | valid/unknown symbol, missing_context, evidence_ref, no_fabrication |
| M4.3 | 6 | from_memory, from_evidence, missing_evidence, has_refs, no_duplicate |
| M4.4 | 7 | has_refs, targets_concept, weak/strong answer, mode_style, no_generic |
| M4.5 | 6 | round_trip, traceability, update, delete, confidence, no_secrets |
| M4.6 | 6 | hit_no_llm, low_confidence, no_memory, no_evidence, no_duplicate, token_saved |

---

## 16. 验收标准

M4 完成后，应能做到：

1. 用户选中论文内容 → 获得 grounded 解释
2. 用户选中公式/符号 → 获得符号解释
3. 用户追问 → 结合证据和记忆回答
4. 导师式追问 → 基于论文的有深度的问题
5. 用户回答 → 评估和追问
6. 交互结果写入长期记忆
7. 重复问题不重复调用 LLM
8. 所有解释绑定 evidence_ref
9. 无证据时降级，不编造
10. 真实验收必须使用真实 LLM + 真实 paper artifacts + 真实 memory retrieval
11. 不能只用 fake conversation 作为验收依据
12. M4.1-M4.6 每个子模块都有测试覆盖

---

## 17. 当前实现状态

### 已存在（M3 前端占位）

- M3 前端中有 AskPanel / TextSelectionToolbar 组件占位
- patterns / drill tabs 显示"未开放"
- M2 artifacts 已可作为 M4 输入

### 未实现

- M4 API endpoints
- M4 schemas（全部候选 schema 未实现）
- M4 memory persistence
- M4 retrieval logic
- M4 advisor question generation
- M4 frontend integration
- M4 tests
- 当前不进入代码开发

---

## 18. External Reference Implementation Notes

ARIS is a prompt/workflow reference for advisor-style research training and memory discipline. It is not a runtime dependency and does not replace ResearchSensei interaction design.

### M4.1 Selected Text Explanation

- **Reference source**: None directly
- **Reference use**: DO_NOT_REUSE
- **Borrowed behavior**: Only borrows source/evidence discipline
- **ResearchSensei-owned target**: `SelectionExplanation`
- **Schema / artifact impact**: `answer`, `cited_evidence_refs`, `cited_passage_ids`, `relation_to_current_section`, `relation_to_paper_claim`, `confidence`, `used_memory_ids`
- **Boundary**: ARIS has no UI-level selected text explanation. Must use `selected_text` + `evidence_ref` + current paper artifacts.
- **Validation implication**: `cited_evidence_refs` non-empty. No evidence_ref = degraded / rejected.

### M4.2 Formula / Symbol Explanation

- **Reference source**: None directly
- **Reference use**: DO_NOT_REUSE, EVALUATE_OTHER_PROJECTS
- **Borrowed behavior**: None
- **ResearchSensei-owned target**: `FormulaSymbolExplanation`
- **Schema / artifact impact**: `formula_id`, `symbol`, `meaning`, `source_sentence`, `intuition`, `numeric_example`, `role_in_method`, `evidence_ref`
- **Boundary**: ARIS does not provide formula/symbol teaching. Must be self-built or evaluate other specialized projects.
- **Validation implication**: Symbol meaning must come from formula_card / passage / evidence_ref. No general LLM guessing.

### M4.3 Contextual Follow-up

- **Reference source**: ARIS `skills/idea-discovery/SKILL.md`, `skills/research-review/SKILL.md`
- **Reference use**: PROMPT_BORROW
- **Borrowed behavior**: Follow-up patterns, scope tightening, evidence-seeking questions. Ask user to focus on a problem, adjust hypothesis, ignore irrelevant direction.
- **ResearchSensei-owned target**: `InteractiveAnswer`
- **Schema / artifact impact**: `answer`, `evidence_refs`, `memory_refs`, `uncertainty`, `follow_up_suggestions`, `used_context`
- **Boundary**: ResearchSensei targets single-paper learning. Does not enter full idea-discovery pipeline.
- **Validation implication**: Answer must use memory / artifacts / evidence. `cited_evidence_refs` non-empty or explicitly degraded.

### M4.4 Advisor Questions / Research Training

- **Reference source**: ARIS `skills/research-review/SKILL.md`, `skills/research-refine-pipeline/SKILL.md`
- **Reference use**: PROMPT_BORROW, STRATEGY_BORROW
- **Borrowed behavior from research-review**: Senior reviewer mode; logical gaps; unjustified claims; missing experiments; narrative weaknesses; contribution sufficiency; mock review; results-to-claims matrix; minimum experiment package
- **Borrowed behavior from research-refine-pipeline**: Problem Anchor; dominant contribution; intentionally rejected complexity; key claims; must-run ablations; remaining risks; planning gate
- **ResearchSensei-owned target**: `AdvisorQuestion`, `AdvisorEvaluation`
- **Schema / artifact impact**: `question_type` (assumption / method / experiment / limitation / innovation / claim_evidence / ablation), `expected_answer_points`, `evidence_refs`, `follow_up_policy`, `missing_points`, `misconceptions`, `next_question`
- **Boundary**: ARIS reviewer/refine is for research idea evaluation. ResearchSensei advisor is for paper learning training. Questions must be paper-grounded. Advisor mode is not automatic paper writing.
- **Validation implication**: Every advisor question has `evidence_refs` when available. Weak answer triggers follow-up. Strong answer triggers deeper question. `question_type` covers assumption / method / experiment / limitation / innovation.

### M4.5 Long-term Memory

- **Reference source**: ARIS `tools/research_wiki.py`
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: Paper nodes; research notes; typed edges (extends / contradicts / addresses_gap / inspired_by / tested_by / supports / invalidates / supersedes); source trace; query_pack / compressed context
- **ResearchSensei-owned target**: `PaperMemory`, `PassageMemory`, `FormulaMemory`, `SymbolMemory`, `SessionContext`, `UserQuestionMemory`
- **Schema / artifact impact**: `memory_id`, `paper_id`, `source_artifact`, `evidence_refs`, `confidence`, `updated_at`, `schema_version`
- **Boundary**: Does not directly adopt ARIS wiki file structure. Cache is not memory. Memory must bind `evidence_refs`. Does not store API keys / private data.
- **Validation implication**: Memory round-trip. Memory traceability. Low-confidence memory does not override evidence. No secrets.

### M4.6 Memory-first Retrieval

- **Reference source**: ARIS `tools/research_wiki.py`, ARIS review tracing / session recovery patterns
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: First read existing notes / query_pack / paper memory; then decide whether to call LLM; reuse confirmed context; record session recovery info
- **ResearchSensei-owned target**: `MemoryRetrievalResult`
- **Schema / artifact impact**: `matched_memory_ids`, `matched_artifacts`, `should_call_llm`, `confidence`, `warnings`, `estimated_token_saved`
- **Boundary**: Memory hit does not mean correct. Low-confidence memory must be verified with evidence. Token saving cannot override evidence quality.
- **Validation implication**: Stale memory must verify. No evidence = degraded.

---

## 19. 未决问题

- PaperMemory 和 PassageMemory 的粒度
- 记忆优先检索的具体策略和阈值
- token 节省的量化指标
- 导师式追问的评分标准
- 训练题的生成策略
- 和 M2 understanding_status.downstream_gates 的衔接细节
- storage strategy：SQLite / JSON artifact / vector DB / hybrid
- DownstreamGates legacy field name（phase12_patterns / phase12_drill）是否需要重命名
