# Phase 10 Review - Teaching Card JSON v1

审计日期：2026-06-02
审计范围：Phase 10 teaching_cards.json 的 schema、builder、evidence、LLM、artifact、测试质量

---

## 1. Schema 审计

### 1.1 TeachingCard 字段完整性

| 字段 | 是否存在 | 类型 | 默认值 | 评估 |
|------|---------|------|--------|------|
| card_id | ✅ | str | — | 正确 |
| paper_id | ✅ | str | — | 正确 |
| target_type | ✅ | str | "concept" | 正确，支持 paper/formula/concept/method/experiment |
| target_id | ✅ | str | "" | 正确 |
| title | ✅ | str | "UNKNOWN" | 正确 |
| human_explanation | ✅ | str | "UNKNOWN" | ✅ 五层第1层 |
| analogy_explanation | ✅ | str | "UNKNOWN" | ✅ 五层第2层 |
| minimal_formula_explanation | ✅ | str | "UNKNOWN" | ✅ 五层第3层 |
| numeric_example | ✅ | str | "UNKNOWN" | ✅ 五层第4层 |
| paper_role_explanation | ✅ | str | "UNKNOWN" | ✅ 五层第5层 |
| evidence_refs | ✅ | list[str] | [] | 正确 |
| evidence_status | ✅ | EvidenceType | UNVERIFIED | 正确 |
| confidence | ✅ | float | 0.0, ge=0, le=1 | 正确 |
| warnings | ✅ | list[str] | [] | 正确 |

**结论**：五层字段完整，evidence 绑定字段完整。

### 1.2 TeachingCardBundle 字段完整性

| 字段 | 是否存在 | 评估 |
|------|---------|------|
| paper_id | ✅ | 正确 |
| teaching_cards | ✅ | 正确 |
| evidence_refs | ✅ | 正确 |
| confidence | ✅ | 正确 |
| warnings | ✅ | 正确 |
| evidence_status | ✅ | 正确 |

**结论**：Bundle schema 完整。

---

## 2. Builder 审计

### 2.1 Rule-based 教学卡实际输出

通过生成样本 teaching cards 审计实际输出质量：

**card: core_idea (concept)**
- human_explanation: "L = L_rec + lambda L_graph" ← ⚠️ 这是公式文本，不是人话解释
- analogy_explanation: "NEEDS_HUMAN_CHECK" ← ✅ 正确降级
- minimal_formula_explanation: "L = L_rec + lambda L_graph" ← ✅ 正确
- numeric_example: "NEEDS_HUMAN_CHECK" ← ✅ 正确降级
- paper_role_explanation: "这个概念是理解论文核心思想的关键" ← ⚠️ 泛泛模板

**card: problem (concept)**
- human_explanation: "Current methods miss sensor dependencies." ← ✅ 使用 claim text
- analogy_explanation: "NEEDS_HUMAN_CHECK" ← ✅ 正确降级
- paper_role_explanation: "这个概念是理解论文核心思想的关键" ← ⚠️ 泛泛模板

**card: method_overview (method)**
- human_explanation: "L = L_rec + lambda L_graph" ← ⚠️ 公式文本，不是方法概述
- paper_role_explanation: "这个方法是论文提出的核心技术方案" ← ⚠️ 泛泛模板

**card: formula teaching card**
- human_explanation: "NEEDS_HUMAN_CHECK" ← ⚠️ 应该用 formula_card.purpose 或 plain_summary
- paper_role_explanation: "此公式位于method部分，定义模型的核心优化目标或计算过程" ← ✅ 有意义

### 2.2 发现的问题

**[HIGH] core_idea 和 method_overview 的 human_explanation 是公式文本**

原因：PaperCard 的 `core_idea` claim 来自 method section 的 evidence claim，该 claim 的 text 是公式文本（"L = L_rec + lambda L_graph"）。rule-based builder 直接使用 claim.text 作为 human_explanation，导致"人话版"实际上是原始公式。

影响：用户看到的"人话版"不是人话，是原始公式。

**[MEDIUM] _infer_paper_role() 返回泛泛模板**

`_infer_paper_role()` 返回固定模板如"这个概念是理解论文核心思想的关键"，不引用论文具体内容。这违反了"不能输出空泛解释"的要求。

**[MEDIUM] formula teaching card 的 human_explanation 为 NEEDS_HUMAN_CHECK**

当 `formula_card.plain_summary` 和 `formula_card.purpose` 都是 "UNKNOWN" 时，formula teaching card 的 human_explanation 降级为 "NEEDS_HUMAN_CHECK"。这在 rule-based 路径下是合理的，但用户体验不佳——应该至少用公式文本本身。

**[LOW] rule-based builder 不使用 skeleton 和 evidence_index 参数**

`build_teaching_cards()` 接收 `skeleton` 和 `evidence_index` 参数但未使用。当前只从 `paper_card` 和 `formula_cards` 提取。

---

## 3. Evidence 审计

### 3.1 evidence_ref 回指

| 卡片 | evidence_ref | 是否有效 | evidence_type |
|------|-------------|---------|---------------|
| core_idea | paper-1:eq001 | ✅ | SUPPORTED_BY_FORMULA |
| problem | paper-1:b002 | ✅ | SUPPORTED_BY_TEXT |
| method_overview | paper-1:eq001 | ✅ | SUPPORTED_BY_FORMULA |
| formula | paper-1:eq001 | ✅ | SUPPORTED_BY_FORMULA |

**结论**：所有 evidence_ref 有效，无幻觉 ref。

### 3.2 强结论检查

- 无泛泛强结论如"该方法提升了性能"
- 降级字段正确使用 NEEDS_HUMAN_CHECK
- 无证据的字段正确标注

**结论**：evidence 纪律合格。

---

## 4. LLM-enhanced 审计

| 检查项 | 状态 |
|--------|------|
| mock LLM 测试覆盖 evidence_ref 校验 | ✅ `test_llm_enhanced_teaching_cards_reject_hallucinated_refs` |
| LLM 输出缺 evidence_ref 是否降级 | ✅ 代码中 `if ref and ref not in valid_refs: ref = ""` |
| LLM 输出 schema 错误是否降级 | ✅ `test_llm_enhanced_teaching_cards_fall_back_on_failure` |
| 真实 LLM 默认测试 | ✅ 无，全部 mock |

**结论**：LLM 审计合格。

---

## 5. Artifact 审计

### 5.1 Parse flow 生成的 7 个 artifact

| Artifact | 是否生成 | 测试覆盖 |
|----------|---------|---------|
| source_status.json | ✅ | ✅ |
| parsed_document.json | ✅ | ✅ |
| evidence_index.json | ✅ | ✅ |
| paper_skeleton.json | ✅ | ✅ |
| paper_card.json | ✅ | ✅ |
| formula_cards.json | ✅ | ✅ |
| teaching_cards.json | ✅ | ✅ |

### 5.2 Artifact 查询 API

`GET /api/v1/jobs/{job_id}/artifacts` 能读取 teaching_cards.json。✅

**结论**：Artifact 审计合格。

---

## 6. 测试质量审计

### 6.1 测试结果

```
195 passed in 2.12s
```

### 6.2 测试覆盖评估

| 测试 | 覆盖内容 | 质量 |
|------|---------|------|
| test_rule_based_teaching_cards_from_full_document | 生成 cards | ✅ 测存在 |
| test_rule_based_teaching_cards_have_five_layers | 五层字段非空 | ⚠️ 只测非空，不测内容质量 |
| test_rule_based_teaching_cards_bind_evidence_refs | evidence_ref 有效性 | ✅ 测逻辑 |
| test_rule_based_teaching_cards_degraded_when_no_content | 空内容降级 | ✅ 测逻辑 |
| test_rule_based_formula_teaching_card | formula card 生成 | ✅ 测逻辑 |
| test_rule_based_teaching_cards_evidence_status | evidence_status | ✅ 测逻辑 |
| test_llm_enhanced_teaching_cards_use_mock_llm | LLM 增强 | ✅ 测逻辑 |
| test_llm_enhanced_teaching_cards_reject_hallucinated_refs | 幻 ref 检测 | ✅ 测逻辑 |
| test_llm_enhanced_teaching_cards_fall_back_on_failure | LLM 失败降级 | ✅ 测逻辑 |

### 6.3 测试薄弱点

**[MEDIUM] 缺少内容质量测试**

现有测试只验证字段非空，不验证内容是否真的有意义。例如：
- 不检查 human_explanation 是否真的是"人话"而非公式文本
- 不检查 paper_role_explanation 是否引用了论文内容
- 不检查 analogy_explanation 是否真的是类比

**[LOW] 测试文档过于简单**

所有测试使用同一个 "Tiny TSAD Paper" fixture（6 个 blocks）。缺少：
- 只有 abstract 没有 method 的文档
- 有多个公式的文档
- 只有标题的文档

---

## 7. 风险分级

### BLOCKER

无。

### HIGH

**H1: core_idea 和 method_overview 的 human_explanation 是公式文本**

rule-based builder 直接使用 claim.text 作为 human_explanation。当 claim 来自 method section 且包含公式时，"人话版"变成了原始公式。

**[已修复]** 新增 `_is_formula_heavy()` 检测公式密集文本，当检测到时：
- human_explanation 使用保守 fallback（"该部分涉及论文的核心机制，但当前证据主要为公式形式，需要进一步解释"）
- confidence 降至 ≤ 0.3
- 添加 `FORMULA_HEAVY_TEXT_NEEDS_HUMAN_EXPLANATION` warning

### MEDIUM

**M1: _infer_paper_role() 返回泛泛模板**

不引用论文具体内容，违反"不能输出空泛解释"的要求。

**[已修复]** 更新为更具体但保守的表达：
- concept: "此内容用于理解论文要解决的问题或核心思路"
- method: "此内容用于理解作者提出的技术方案"
- experiment: "此内容用于理解实验设计和评估方式"
- formula: "此内容用于理解论文中的数学目标或计算机制"

**M2: formula teaching card 的 human_explanation 降级为 NEEDS_HUMAN_CHECK**

当 formula_card 的 plain_summary 和 purpose 都是 UNKNOWN 时，human_explanation 降级为 NEEDS_HUMAN_CHECK。应至少用公式文本本身。

**[已修复]** fallback 顺序改为：`plain_summary → purpose → formula_raw[:100] + disclaimer → NEEDS_HUMAN_CHECK`

**M3: 缺少内容质量测试**

现有测试只测字段非空，不测内容质量。

**[已修复]** 新增 7 个内容质量测试：
- human_explanation 不应是纯公式文本
- 公式密集文本应有降级 confidence
- 公式密集文本应有 warning
- formula card 应保留公式文本
- paper_role_explanation 不使用泛泛模板
- paper_role_explanation 使用具体语言
- evidence_ref 仍然有效

### LOW

**L1: rule-based builder 不使用 skeleton 和 evidence_index 参数**

**L2: 测试文档过于简单，缺少边界情况**

---

## 8. 结论

### Phase 10 是否合格

**有条件合格。** 核心架构（schema、evidence binding、LLM fallback、artifact integration）合格。但 rule-based builder 的内容质量有 HIGH 级问题需要修复。

### 是否建议进入 Phase 11

**建议先修复 H1，再进入 Phase 11。**

H1 的修复工作量小（~10 行代码），但影响核心用户体验——用户看到的"人话版"不应该是原始公式。

### 进入 Phase 11 前必须处理的问题

1. **H1**：修复 core_idea/method_overview 的 human_explanation 公式文本问题
2. **M2**：修复 formula teaching card 的 human_explanation fallback

### 是否需要 cleanup / refactor

不需要大 refactor。H1 和 M2 是小修复。

### 是否需要增加真实论文样例 golden test

**建议后续增加，但不阻塞 Phase 11。** 当前测试 fixture 过于简单，真实论文测试能暴露更多 edge case。
