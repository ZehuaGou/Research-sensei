# Audit / Quality 模块（M2.4）

---

## 1. 模块目标

判断"讲得好"，不只是 schema 通过。

## 产品流程位置

M2.4 承接 M2.3 的卡片输出，进行质量审计：candidate artifacts → QualityAuditor → QualityReport → 状态覆盖。

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
- Audit 是纯逻辑模块，不依赖 WorkspaceStore，不写 artifact
- Runner 负责把 QualityReport 映射为 UnderstandingStatus，并写 understanding_status.json

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
| 输入 | card JSON + evidence_index（纯数据，不依赖 IO） |
| 输出 | QualityReport（纯数据） |
| 不写 artifact | Audit 是纯逻辑，不依赖 WorkspaceStore |
| understanding_status | 由 Runner 根据 QualityReport 映射并写入 |

## 6. Artifact

- Audit 不写 artifact，只读取
- Runner 负责把 QualityReport 映射为 UnderstandingStatus 并写 understanding_status.json

### Candidate Audit 语义

QualityReport 当前审计的是 **candidate artifacts**，即 pipeline 写盘前的内存对象。

当 audit BLOCK v2 SUCCESS / DEGRADED 时：
- `quality_report.json` 记录 candidate audit finding；
- final `understanding_status` 改为 `BLOCKED_UNDERSTANDING`；
- final artifacts **不写** `paper_card` / `formula_cards` / `teaching_cards`；
- **不会**重新审 final artifacts。

这样设计的理由：
- 避免写入不可信 card artifacts；
- 避免删除已写文件；
- 保留审计证据，说明 candidate 为什么被阻断。

**后续开发者注意**：`quality_report.json` 记录的是 candidate 阶段的审计结果，不一定等于 final written artifacts 的审计结果。例如，candidate 有 paper_card 但 audit BLOCK 后 final artifacts 不含 paper_card，此时 quality_report 中的 findings 仍引用 candidate 阶段的 paper_card。

## 7. 核心类和方法签名

### AuditFinding

使用统一 AuditFinding，而不是 hard_fails + warnings 两套结构。

```python
class AuditFinding(SenseiModel):
    code: str           # F-1, F-2, ...
    severity: str       # P0 / P1 / P2
    effect: str         # BLOCK / WARNING
    message: str
    artifact: str = ""
    field: str = ""
```

### ComponentAuditResult

```python
class ComponentAuditResult(SenseiModel):
    component: str      # "paper_card" / "formula_cards" / "teaching_cards"
    status: str         # "PASS" / "FAIL" / "SKIP"
    findings: list[AuditFinding] = Field(default_factory=list)
```

### QualityReport

```python
class QualityReport(SenseiModel):
    schema_version: str = "v2"
    paper_id: str
    findings: list[AuditFinding] = Field(default_factory=list)
    component_results: list[ComponentAuditResult] = Field(default_factory=list)
    checked_artifacts: list[str] = Field(default_factory=list)
    audit_version: str = "v1"
    created_at: str = ""
```

- QualityReport 是 audit 原始输出。
- UnderstandingStatus 是 Runner 根据 QualityReport 生成的下游状态。
- QualityReport 持久化为 `quality_report.json`。
- 不保留 score / dimension_scores（rule-based auditor 给不出有意义的分数）。

### Auditor 接口

```python
from abc import ABC, abstractmethod

class ArtifactBundle(SenseiModel):
    """Audit 读取的 artifact 集合。纯数据，不含 IO。"""
    paper_card: dict | None = None
    formula_cards: dict | None = None
    teaching_cards: dict | None = None
    evidence_index: dict | None = None
    claim_evidence: dict | None = None
    passage_index: dict | None = None
    paper_skeleton: dict | None = None
    understanding_status: dict | None = None

class Auditor(ABC):
    @abstractmethod
    def audit(self, artifacts: ArtifactBundle) -> AuditResult: ...
```

初版 audit 全部 rule-based。未来可预留 LLM-based auditor 实现同一接口。LLM auditor 必须默认 mock，不允许 pytest 真实调用 LLM。

### 可拆分子 Auditor

| Auditor | 检查内容 |
|---------|---------|
| EvidenceAuditor | evidence_ref 有效性、passage_id 存在性、claim-evidence binding |
| FormulaAuditor | formula char ratio、symbol 解释一致性 |
| GenericnessAuditor | paper-specific terms、通用性检测 |
| CopyAuditor | token overlap、raw copy 检测 |
| AdvisorReadinessAuditor | cards 是否足够支撑 Phase 12 drill |

`QualityAuditor` 作为 orchestrator / aggregator，综合所有子 auditor 的结果，生成 `QualityReport`。

### Audit 约束

- auditor 不能 import card builder
- auditor 不能调用 card builder
- auditor 不能写 artifact
- auditor 不依赖 WorkspaceStore
- auditor 只读取 artifacts 或序列化 JSON

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
# High overlap → raw copy
```

**raw copy 分类**:
- core_idea / problem / method raw copy (overlap > 0.8) → **BLOCK**
- limitations / quote 高重合 → **WARNING**
- teaching analogy raw copy → **BLOCK**

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

## 11. AuditFinding 规则

| ID | 条件 | severity | effect |
|----|------|----------|--------|
| F-1 | 核心 claim 无 evidence_ref 且未标 INSUFFICIENT_EVIDENCE | P0 | BLOCK |
| F-2 | evidence_ref 在 evidence_index 中不存在 | P0 | BLOCK |
| F-3 | LLM 输出包含 evidence pack 之外的 claim | P0 | BLOCK |
| F-4 | teaching human_explanation formula-heavy (ratio >= 0.3) | P0 | BLOCK |
| F-5 | BASELINE_ONLY 被当作 final understanding | P0 | BLOCK |
| F-6 | BLOCKED_UNDERSTANDING 包含解释性内容 | P0 | BLOCK |
| F-7 | warnings 不是 WarningItem | P0 | BLOCK |
| F-8 | core_idea / problem / method raw copy (overlap > 0.8) | P0 | BLOCK |
| F-9 | ClaimEvidence.passage_id 在 passage_index 中不存在 | P0 | BLOCK |
| F-10 | component_status 与 status 矛盾 | P1 | BLOCK |
| F-11 | generic output（无 paper-specific terms） | P1 | BLOCK |
| F-12 | missing passage_id for claim_evidence v2 | P0 | BLOCK |
| F-13 | limitations / quote 高重合 | P2 | WARNING |
| F-14 | teaching analogy 与 source 中等重合 | P2 | WARNING |

### severity / effect 规则

- P0 一定 BLOCK
- P1 可能 BLOCK，也可能 WARNING
- P2 通常 WARNING

### missing passage_id for claim_evidence v2

倾向 BLOCK。原因：claim_evidence v2 依赖 passage_id，缺 passage_id 会破坏 passage 追踪链路，audit 无法确认 claim 是否有 passage 支持。

### QualityReport → UnderstandingStatus 映射

- findings 中存在 effect=BLOCK → BLOCKED_UNDERSTANDING
- findings 只有 WARNING → 不阻断
- teaching_cards FAILED → DEGRADED_STRUCTURAL
- formula_cards FAILED 需要根据 formula 是否核心判断（formula_is_core 算法未决）
- parser degraded 不是 hard-fail

### test_quality_*.py 与 product auditor 边界

- 现有 test_quality_*.py 继续作为 pytest 层质量门
- 产品级 auditor 后续新增测试
- 不能把 pytest quality tests 误当成产品级 audit
- 未来需要新增：QualityReport round-trip、invalid evidence_ref finding、missing passage_id finding、status mapping tests

## 13. 验收标准

- QualityAuditor 只读 artifacts，不写 artifact
- 不 import card builder
- F-1 到 F-6 正确触发
- candidate audit 语义正确
- 默认测试不真实调用 LLM

## 14. 当前实现状态

- 代码已实现：QualityAuditor, QualityReport, AuditFinding, F-1 到 F-6
- pipeline 已接入
- 测试已覆盖：20+ tests
- formula-heavy / raw-copy / generic-output 未实现

## 15. 当前未解决问题

- formula char ratio 阈值是否需要调优
- token overlap 阈值是否需要调优
- formula_is_core 的具体判断算法
- AuditFinding 和 WarningItem 是否全局统一
- score / dimension_scores 未来 LLM auditor 是否引入
- "讲得好"的自动检测边界
- 是否需要人工评估集
- QualityReport 是否需要脱敏版
