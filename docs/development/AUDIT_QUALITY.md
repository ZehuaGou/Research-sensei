# Audit / Quality 模块

---

## 1. 模块目标

判断"讲得好"，不只是 schema 通过。

### "讲得好"的可检查维度

| 维度 | 定义 | 自动检测方法 | hard-fail 条件 |
|------|------|-------------|----------------|
| groundedness | 每个解释可追踪到论文证据 | evidence_ref 存在且有效 | 核心 claim 无 evidence_ref (HF-1, HF-4) |
| faithfulness | 不编造贡献/实验/结论 | token overlap + paper-specific terms | 输出与论文主题不符 (HF-6) |
| explainability | 用人话解释，不是复制原文 | formula char ratio + raw copy detection | human_explanation 是公式文本 (HF-2) |
| formula teaching quality | 符号有依据，作用有解释 | symbol 来自上下文或 REASONABLE_INFERENCE | symbol 解释与论文矛盾 (HF-3) |
| research thinking | 讲清假设/创新点/代价/边界 | claim_type 覆盖 PROBLEM/METHOD/LIMITATION | — |
| advisor readiness | 追问具体、基于证据 | drill 问题含论文特有术语 | — |
| non-genericness | 贴合具体论文 | paper-specific terms 命中 | 输出无论文特有术语 (HF-5) |
| uncertainty handling | 不确定时降级 | INSUFFICIENT_EVIDENCE / NEEDS_HUMAN_CHECK | — |

## 2. 非目标

- 不用真实 LLM
- 不新增依赖

## 3. 外部项目调研

### ARIS audit chain

- **机制**: 5 层审计 — experiment-audit → result-to-claim → paper-claim-audit → citation-audit → kill-argument
- **关键设计**: 每层用 fresh thread（不复用上下文）；executor 不审计自己；只传文件路径不传摘要
- **对本模块的用处**: audit 分层思想可借鉴；reviewer independence 原则可直接应用
- **当前是否接入**: 否 — 只参考设计

### ARIS reviewer independence

- **机制**: 审计者只接收文件路径，不接收 executor 的摘要或解释
- **对本模块的用处**: explanation audit 必须独立于 card builder
- **当前是否接入**: 否 — 原则可直接应用

### ARIS kill-argument

- **机制**: Thread 1 写最强 200 字拒稿理由；Thread 2 独立逐点辩护；第三个线程评分
- **对本模块的用处**: advisor question 质量评估可参考对抗思路
- **当前是否接入**: 否 — 参考设计
- **落地方式**: 后续 advisor/drill 可以用"最强反对意见 → 逐点回应 → 未解决问题"结构。当前阶段只记录为未来扩展，不写代码。

### ARIS → ResearchSensei 审计独立性落地

- Audit 函数不能调用 card builder
- Audit 输入只能是 artifacts 路径或已序列化 JSON
- Audit 不接收生成器的自然语言解释
- Audit 输出 `QualityReport`

### OpenScholar citation accuracy

- **机制**: 评估 citation 是否准确支持 claim
- **GitHub repo**: 未验证；保持 REFERENCE_ONLY 直到 repo/paper 实现确认
- **对本模块的用处**: evidence_ref 有效性评估可参考
- **当前是否接入**: 否

### PaperQA citation/provenance

- **机制**: answer 必须 cite passages
- **对本模块的用处**: provenance tracking 思路可借鉴
- **当前是否接入**: 否 — REFERENCE_ONLY

## 4. 当前代码位置

- `tests/test_quality_grounding.py` — evidence grounding tests
- `tests/test_quality_hallucination.py` — anti-hallucination tests
- `tests/test_quality_formula.py` — formula quality tests
- `tests/test_quality_smoke.py` — full chain smoke tests
- `tests/fixtures/quality/` — fixture papers

## 5. 输入输出

| 项 | 值 |
|----|-----|
| 输入 | card JSON + evidence_index |
| 输出 | quality report (JSON) |
| 用于 | pytest tests |

## 6. Artifact

- 不修改 artifact，只读取

## 7. 核心类和方法签名

```python
class QualityReport(SenseiModel):
    paper_id: str
    score: float
    hard_fails: list[str]
    warnings: list[WarningItem]
    checked_artifacts: list[str]
```

## 8. 检测算法

### formula char ratio

统计公式相关字符比例：`=`, `\`, `_`, `^`, `{`, `}`, `sum`, `argmin`, `lambda`, `frac`, `sqrt`, `int`, `prod`

```
formula_chars = sum(1 for c in text if c in "=\\_^{}")
ratio = formula_chars / len(text) if text else 0
# HF-2 trigger: ratio >= 0.3
```

### token overlap (raw copy detection)

```
tokens_a = set(text_a.lower().split())
tokens_b = set(text_b.lower().split())
overlap = len(tokens_a & tokens_b) / max(len(tokens_a), 1)
# High overlap → raw copy warning
```

### paper-specific terms 提取

```
title_words = set(title.lower().split()) - stopwords
abstract_words = set(abstract.lower().split()) - stopwords
method_words = set(method_section.lower().split()) - stopwords
paper_terms = title_words | abstract_words | method_words
# Output must contain at least one term from paper_terms
```

### evidence_ref validity

```
for each claim in card:
    if claim.evidence_ref:
        assert claim.evidence_ref in evidence_index.claims[].evidence_ref
    else:
        assert claim.evidence_type in (INSUFFICIENT_EVIDENCE, NEEDS_HUMAN_CHECK)
```

### core_idea vs method_overview

```
if core_idea.text == method_overview.text:
    hard_fail (HF-4 variant)
if token_overlap(core_idea.text, method_overview.text) > 0.8:
    warning
```

## 9. 错误/失败策略

不适用 — audit 是只读检查，不修改 artifact。

## 10. 测试断言

| 测试 | 断言 |
|------|------|
| test_hard_fail_core_claim_without_evidence | hard_fail triggered |
| test_hard_fail_formula_text_as_explanation | hard_fail (formula char ratio >= 0.3) |
| test_hard_fail_generic_output | hard_fail (no paper-specific terms) |
| test_raw_abstract_copy_detected | warning or hard_fail |
| test_invalid_evidence_ref_detected | hard_fail |
| test_quality_report_json_round_trip | all fields preserved |

## 11. Hard-Fail

| ID | 条件 |
|----|------|
| HF-1 | 核心 claim 无 evidence_ref 且未标 INSUFFICIENT_EVIDENCE |
| HF-2 | human_explanation 是公式文本（formula char ratio >= 0.3） |
| HF-3 | formula symbol 解释与论文矛盾 |
| HF-4 | core_idea / problem 缺 evidence_ref |
| HF-5 | 输出无论文特有术语 |
| HF-6 | 输出与论文主题不符 |
| HF-7 | LLM failure produces final-looking cards |
| HF-8 | BASELINE_ONLY card used as v2/final understanding |
| HF-9 | BLOCKED_UNDERSTANDING still contains user-facing explanation text |
| HF-10 | warnings are strings instead of WarningItem |

## 12. 当前未解决问题

- QualityReport schema 未实现（只有测试中的检查逻辑）
- formula char ratio 阈值是否需要调优
- token overlap 阈值是否需要调优
- 是否需要生成 audit report artifact
