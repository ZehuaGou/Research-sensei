# Audit / Quality 模块（M2.4）

---

## 1. 模块目标

判断"讲得好"，不只是 schema 通过。

## 2. 产品流程位置

M2.4 承接 M2.3 的卡片输出，进行质量审计：candidate artifacts → QualityAuditor → QualityReport → 状态覆盖。

### "讲得好"的可检查维度

| 维度 | 定义 | 自动检测方法 | hard-fail 条件 |
|------|------|-------------|----------------|
| groundedness | 每个解释可追踪到论文证据 | evidence_ref 存在且有效 | 核心 claim 无 evidence_ref (F-1) |
| faithfulness | 不编造贡献/实验/结论 | token overlap + paper-specific terms | 输出与论文主题不符 (F-9, 未实现) |
| explainability | 用人话解释，不是复制原文 | formula char ratio + raw copy detection | human_explanation 是公式文本 (F-10, 未实现) |
| formula teaching quality | 符号有依据，作用有解释 | symbol 来自上下文或 REASONABLE_INFERENCE | symbol 解释与论文矛盾 |
| research thinking | 讲清假设/创新点/代价/边界 | claim_type 覆盖 PROBLEM/METHOD/LIMITATION | — |
| advisor readiness | 追问具体、基于证据 | drill 问题含论文特有术语 | — |
| non-genericness | 贴合具体论文 | paper-specific terms 命中 | 输出无论文特有术语 |
| uncertainty handling | 不确定时降级 | INSUFFICIENT_EVIDENCE / NEEDS_HUMAN_CHECK | — |

## 3. 非目标

- 不负责生成 LLM 输出（生成归 M2.3）
- 不替代 M2.3 card builder
- 不替代 M5 live eval
- 不新增依赖

## 4. 可复用开源项目 / 外部服务调研

| 项目 | 用途 | GitHub / 官网 | 接入方式 | 是否默认依赖 | 风险 | 当前结论 |
|------|------|---------------|----------|--------------|------|----------|
| ARIS audit chain | 5 层审计 | github.com/wanshuiyin/Auto-claude-code-research-in-sleep | REFERENCE_ONLY | 否 | — | 只借鉴 audit 分层思想 |
| ARIS reviewer independence | 审计独立性 | 同上 | REFERENCE_ONLY | 否 | — | 原则可直接应用 |
| ARIS research-review | 对抗式评估 | 同上 | REFERENCE_ONLY | 否 | — | 参考 advisor 评估 |
| OpenScholar | citation accuracy | 未确认 repo | REFERENCE_ONLY | 否 | — | 参考 evidence_ref 评估 |
| PaperQA | citation/provenance | github.com/Future-House/paper-qa | REFERENCE_ONLY | 否 | — | 参考 provenance tracking |

未完成调研不得进入代码开发。

## 5. 外部项目调研（详细）

### ARIS audit chain

- **机制**: 5 层审计 — experiment-audit → result-to-claim → paper-claim-audit → citation-audit → research-review
- **关键设计**: 每层用 fresh thread（不复用上下文）；executor 不审计自己；只传文件路径不传摘要
- **对本模块的用处**: audit 分层思想可借鉴；reviewer independence 原则可直接应用
- **当前是否接入**: 否 — 只参考设计

### ARIS reviewer independence

- **机制**: 审计者只接收文件路径，不接收 executor 的摘要或解释
- **对本模块的用处**: explanation audit 必须独立于 card builder
- **当前是否接入**: 否 — 原则可直接应用

### ARIS research-review

- **机制**: Thread 1 写最强 200 字拒稿理由；Thread 2 独立逐点辩护；第三个线程评分
- **对本模块的用处**: advisor question 质量评估可参考对抗思路
- **当前是否接入**: 否 — 参考设计
- **落地方式**: 后续 M4 advisor/drill 可以用"最强反对意见 → 逐点回应 → 未解决问题"结构

### ARIS → ResearchSensei 审计独立性落地

- Audit 函数不能调用 card builder
- Audit 输入只能是 artifacts 路径或已序列化 JSON
- Audit 不接收生成器的自然语言解释
- Audit 输出 `QualityReport`
- Audit 是纯逻辑模块，不依赖 WorkspaceStore，不写 artifact
- Runner 负责把 QualityReport 映射为 UnderstandingStatus，并写 understanding_status.json

## 6. 当前代码位置

- `src/researchsensei/audit/quality_auditor.py` — `QualityAuditor`（F-1 到 F-6 规则）
- `src/researchsensei/audit/__init__.py` — 模块导出
- `src/researchsensei/schemas/audit.py` — AuditFinding, ComponentAuditResult, ArtifactBundle, QualityReport
- `src/researchsensei/ingestion/pipeline.py` — QualityAuditor 调用位置、quality_report.json 写入位置
- `tests/test_quality_grounding.py` — evidence grounding tests
- `tests/test_quality_hallucination.py` — anti-hallucination tests
- `tests/test_quality_formula.py` — formula quality tests
- `tests/test_quality_smoke.py` — full chain smoke tests
- `tests/test_quality_auditor.py` — QualityAuditor unit tests
- `tests/test_pipeline_audit.py` — pipeline audit integration tests

## 7. 输入输出

| 项 | 值 |
|----|-----|
| 输入 | card JSON + evidence_index + passage_index + claim_evidence（纯数据，不依赖 IO） |
| 输出 | QualityReport（纯数据） |
| 不写 artifact | Audit 是纯逻辑，不依赖 WorkspaceStore |
| understanding_status | 由 Runner 根据 QualityReport 映射并写入 |

## 8. Artifact

- Audit 不写 artifact，只读取
- Runner 负责把 QualityReport 映射为 UnderstandingStatus 并写 understanding_status.json
- QualityReport 持久化为 `quality_report.json`

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

**后续开发者注意**：`quality_report.json` 记录的是 candidate 阶段的审计结果，不一定等于 final written artifacts 的审计结果。

## 9. Schema / 数据结构

### AuditFinding

> 注：以下 severity 中的 P0/P1/P2 是 **audit severity**，不是项目推进优先级。项目推进只按 M1 → M5。

```python
class AuditFinding(SenseiModel):
    code: str           # F-1, F-2, ...
    severity: str       # P0 / P1 / P2 (audit severity)
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

### ArtifactBundle（Audit 读取的 artifact 集合）

```python
class ArtifactBundle(SenseiModel):
    paper_card: dict | None = None
    formula_cards: dict | None = None
    teaching_cards: dict | None = None
    evidence_index: dict | None = None
    claim_evidence: dict | None = None
    passage_index: dict | None = None
    paper_skeleton: dict | None = None
    understanding_status: dict | None = None
```

### Auditor 接口

```python
from abc import ABC, abstractmethod

class Auditor(ABC):
    @abstractmethod
    def audit(self, artifacts: ArtifactBundle) -> AuditResult: ...
```

初版 audit 全部 rule-based。未来可预留 LLM-based auditor 实现同一接口。如果未来引入 LLM-based auditor，验收必须使用真实 LLM 和真实 artifacts。rule-based auditor 可以做结构检查，但不能把结构检查冒充为真实质量验收。

## 10. 检测算法

### 已实现：evidence_ref validity（F-1, F-2, F-6）

- F-1: 检查 paper_card 核心字段是否有 evidence_ref
- F-2: 检查 evidence_ref 是否存在于 evidence_index / claim_evidence
- F-6: 检查 ClaimEvidence.passage_id 是否存在于 PassageIndex

### 设计中 / 未实现

以下算法已设计但未实现：

**formula char ratio（F-10）**:
```
formula_chars = sum(1 for c in text if c in "=\\_^{}")
ratio = formula_chars / len(text) if text else 0
# F-10 trigger: ratio >= 0.3
```

**token overlap / raw copy（F-8）**:
```
tokens_a = set(text_a.lower().split())
tokens_b = set(text_b.lower().split())
overlap = len(tokens_a & tokens_b) / max(len(tokens_a), 1)
```

**paper-specific terms（F-9）**:
```
title_words = set(title.lower().split()) - stopwords
abstract_words = set(abstract.lower().split()) - stopwords
paper_terms = title_words | abstract_words
```

## 11. AuditFinding 规则

> 注：severity 中的 P0/P1/P2 是 audit severity，不是项目推进优先级。

### 已实现（F-1 到 F-6）

| ID | 条件 | severity | effect |
|----|------|----------|--------|
| F-1 | 核心 paper_card 字段（problem / core_idea / method_overview / experiment_summary）缺 evidence_ref（仅当 status 为 SUCCESS 或 DEGRADED_STRUCTURAL 时检查） | P0 | BLOCK |
| F-2 | card 中的 evidence_ref 不存在于 evidence_index / claim_evidence | P0 | BLOCK |
| F-3 | BLOCKED_UNDERSTANDING 状态下仍存在 paper_card / formula_cards / teaching_cards artifact | P0 | BLOCK |
| F-4 | BASELINE_ONLY 状态却 allowed_for_user_display=True | P0 | BLOCK |
| F-5 | component_status / allowed_downstream 与 status 矛盾（含 DEGRADED_STRUCTURAL 时 allowed_for_user_display 必须为 True、advisor_questions 必须为 False） | P1 | BLOCK |
| F-6 | ClaimEvidence.passage_id 不存在于 PassageIndex | P0 | BLOCK |

### 设计中 / 未实现（F-7 以后）

| ID | 条件 | severity | effect | 状态 |
|----|------|----------|--------|------|
| F-7 | warnings 不是 WarningItem | P0 | BLOCK | 设计中 |
| F-8 | core_idea / problem / method raw copy (overlap > 0.8) | P0 | BLOCK | 未实现（raw-copy 检测） |
| F-9 | generic output（无 paper-specific terms） | P1 | BLOCK | 未实现（generic-output 检测） |
| F-10 | teaching human_explanation formula-heavy (ratio >= 0.3) | P0 | BLOCK | 未实现（formula-heavy 检测） |
| F-11 | limitations / quote 高重合 | P2 | WARNING | 未实现 |
| F-12 | teaching analogy 与 source 中等重合 | P2 | WARNING | 未实现 |

### severity / effect 规则

- P0 一定 BLOCK
- P1 可能 BLOCK，也可能 WARNING
- P2 通常 WARNING

### QualityReport → UnderstandingStatus 映射

- findings 中存在 effect=BLOCK → BLOCKED_UNDERSTANDING
- findings 只有 WARNING → 不阻断
- teaching_cards FAILED → DEGRADED_STRUCTURAL
- formula_cards FAILED 需要根据 formula 是否核心判断（formula_is_core 算法未决）
- parser degraded 不是 hard-fail
- F-5 检查 component_status / allowed_downstream 与 status 的一致性

## 12. 测试要求

### QualityAuditor isolated 测试

| 测试 | 断言 |
|------|------|
| test_hard_fail_core_claim_without_evidence | F-1 triggered |
| test_hard_fail_formula_text_as_explanation | F-10 (formula char ratio >= 0.3, 未实现) |
| test_hard_fail_generic_output | F-9 (generic-output / no paper-specific terms, 未实现) |
| test_raw_abstract_copy_detected | F-8 warning or block |
| test_invalid_evidence_ref_detected | F-2 |
| test_quality_report_json_round_trip | all fields preserved |
| test_no_builder_import | quality_auditor does not import paper_card / formula_card / teaching_card |
| test_no_artifact_write | audit function does not create files |

### Pipeline audit integration 测试

| 测试 | 断言 |
|------|------|
| test_audit_block_overrides_success | audit BLOCK → BLOCKED_UNDERSTANDING even if v2 SUCCESS |
| test_audit_block_overrides_degraded | audit BLOCK → BLOCKED_UNDERSTANDING even if DEGRADED |
| test_audit_warning_does_not_block | audit WARNING only → not blocked, warning in warnings |
| test_quality_report_written | quality_report.json exists after pipeline run |
| test_audit_candidate_semantics | quality_report references candidate artifacts |

### F-1 到 F-6 测试

| 测试 | 断言 |
|------|------|
| test_f1_core_field_missing_evidence_ref | F-1 triggered when status is SUCCESS/DEGRADED and paper_card problem/core_idea/method_overview/experiment_summary has no evidence_ref |
| test_f2_evidence_ref_not_in_sources | F-2 triggered when evidence_ref not in evidence_index or claim_evidence |
| test_f3_blocked_has_card_artifact | F-3 triggered when BLOCKED_UNDERSTANDING but paper_card/formula_cards/teaching_cards exists |
| test_f4_baseline_user_display_true | F-4 triggered when BASELINE_ONLY but allowed_for_user_display=True |
| test_f5_component_status_conflict | F-5 triggered when component_status contradicts status |
| test_f6_passage_id_not_in_index | F-6 triggered when ClaimEvidence.passage_id not found in PassageIndex |

### 全局规则

- QualityAuditor 的纯规则测试只能证明规则触发正确，不能证明真实讲解质量。M2.4 验收必须审计真实 LLM 生成的 paper_card / formula_cards / teaching_cards，并验证 BLOCK / WARNING / DEGRADED / SUCCESS 状态映射正确
- 不新增依赖

## 13. 验收标准

- QualityAuditor 只读 artifacts，不写 artifact
- 不 import card builder
- F-1 到 F-6 正确触发
- candidate audit 语义正确

## 14. 当前实现状态

- QualityAuditor 已实现并接入 pipeline
- quality_report.json 已写入
- F-1 到 F-6 已实现
- AuditFinding, ComponentAuditResult, QualityReport schema 已实现
- 测试已覆盖：20+ tests
- F-7 以后规则未实现（设计中）
- formula-heavy / raw-copy / generic-output 未实现

## 15. External Reference Implementation Notes

- **Reference source**: ARIS `tools/verify_papers.py`, `skills/research-review/SKILL.md`
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: Hallucinated paper protection; source verification gate; reviewer-style weakness detection (logical gaps, missing experiments, narrative weakness, contribution sufficiency)
- **ResearchSensei-owned target**: `quality_report.json`
- **Schema / artifact impact**: `source_verification_checks`, `hallucinated_source_risk`, `unsupported_claim_risk`, `generic_summary_risk`, `missing_evidence_ref_risk`
- **Boundary**: ARIS reviewer opinion cannot replace evidence. QualityAuditor still checks by ResearchSensei artifacts.
- **Validation implication**: Missing evidence_ref must fail. BLOCKED status cannot display cards. BASELINE_ONLY cannot be user-displayed.

## 16. Direction & Survey Audit Rules

M2.4 audit must additionally verify:

- Direction-related fields (`method_family`, `contribution_to_direction`, `what_problem_it_solves`, `what_limitation_it_leaves`, `relation_to_previous_methods`, `relation_to_later_methods`, `datasets_and_metrics`, `comparable_methods`) must have `evidence_ref`.
- Comparison claims must have `evidence_ref`.
- Limitation / future work claims must have `evidence_ref`.
- Survey extracted key papers must be traceable to survey passages.
- Paper relation claims must be evidence-grounded.

If evidence is insufficient, direction-related fields must NOT be used to update `direction_landscape`.

## 16. 当前未解决问题

- formula char ratio 阈值是否需要调优
- token overlap 阈值是否需要调优
- formula_is_core 的具体判断算法
- score / dimension_scores 未来 LLM auditor 是否引入
- "讲得好"的自动检测边界
- 是否需要人工评估集
- QualityReport 是否需要脱敏版
