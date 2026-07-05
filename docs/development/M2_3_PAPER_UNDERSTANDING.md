# Paper Understanding 模块（M2.3�?
---

## 2026-06-14 Current Formula Understanding Contract

M2 formula card generation is no longer top-K-only. The current full pipeline
builds a dedicated `formula_evidence_pack.json` from every M1
`FORMULA_CONTEXT` claim and calls `build_formula_cards()` in bounded batches.

Contract:

- every M1 formula evidence item must have a corresponding entry in
  `formula_cards.json`
- LLM output must cite an allowed `evidence_ref`; invalid refs still fail closed
- if the LLM returns valid JSON but omits a formula, M2 creates an evidence-bound
  `SUMMARY_ONLY` card instead of silently dropping the formula
- raw/unknown/unresolved formulas get `BLOCKED_RAW_ONLY` / `derivation_status=blocked`
  cards and are not treated as derivable LaTeX
- formula cards carry `formula_page`, `equation_number`, `equation_group_id`,
  `group_order`, `group_crop_path`, `coverage_status`, and `derivation_status`
- QualityAuditor FSA-13 blocks SUCCESS/DEGRADED outputs when formula evidence is
  missing from `formula_cards.json`

This implements all-formula coverage for M2 handoff. It does not claim complete
symbolic proof reconstruction for every formula; advanced derivation remains
bounded by M1 LaTeX quality and available local evidence.

## 1. 模块目标

基于 `canonical_paper.md` 派生的证据生成学习卡片，LLM 输出必须绑定 evidence，无 evidence 必须进入 BLOCKED_UNDERSTANDING，不允许生成最终解释�?
## 2. 非目�?
- 不新增依�?- 不改 frontend
- 不直接读取原�?PDF / LaTeX / HTML / DeepXiv
- 不绕�?M2.1 / M2.2 �?evidence_ref
- 不解�?`unknown` 来源公式的详细推�?
## External Reference Implementation Notes

- **Reference source**: ARIS `skills/research-lit/SKILL.md`, `skills/idea-discovery/SKILL.md`
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: Problem / Method / Results / Relevance; What They Did; Key Results; Limitations & Open Questions; Potential Improvement Directions
- **ResearchSensei-owned target**: `paper_card.json`, `formula_cards.json`, `teaching_cards.json`
- **Schema / artifact impact**: paper_card should contain problem / method / results / relevance; teaching_card can absorb limitations / open_questions / potential_improvements; every core explanation must bind evidence_ref
- **Boundary**: Does not output ARIS markdown. Does not only summarize. ARIS has no formula_card capability; formula/symbol teaching remains ResearchSensei-owned or requires other specialized project evaluation.
- **Validation implication**: Real LLM + real evidence_pack. Core explanation without evidence_ref must be BLOCKED or degraded. formula_card cannot be replaced by ARIS summary.

## 3. 产品流程位置

M2.3 承接 M2.2 的证据链路，生成论文卡片�?
```text
canonical_paper.md
-> parsed_document.json
-> passage_index.json
-> claim_evidence.json
-> EvidencePack
-> LLM
-> paper_card / formula_cards / teaching_cards
```

## External Projects / Adapter Candidates

| 项目 | 对应模块 | 具体能力 | 可复用文�?函数/CLI | 接入方式 | 是否默认依赖 | 风险 | 当前状�?|
|---|---|---|---|---|---|---|---|
| PaperQA / PaperQA2 | M2.3 / M4 | evidence-grounded answer、Docs/add/query、source citation、answer provenance | PaperQA query/answer APIs；必须调�?citation schema、Docs object、local paper ingestion path | STRATEGY_BORROW | �?| �?QA 系统不是教学系统；不能用 fake agent 作为验收 | DOC_DESIGNED |
| PaperQA adapter | M2.3 / M4 | �?EvidencePack �?PaperQA citation-backed answer 互相校验 | 必须调研 PaperQA Python API、settings、citation refs、failure handling | OPTIONAL_ADAPTER | �?| 不能替代 ResearchSensei teaching schema；需 adapter 隔离 | RESEARCH_REQUIRED |
| ARIS research-review | M2.3 / M2.4 / M4 | 导师�?review、claim matrix、实�?贡献/局限审�?| `skills/research-review/SKILL.md`; 必须调研 review output、weakness、claim matrix | STRATEGY_BORROW | �?| 只能借鉴审查问题和字段；不能运行时依�?| DOC_DESIGNED |
| ARIS research-refine-pipeline | M2.3 / M4 | research question refinement、claim discipline、weak point追问 | `skills/research-refine-pipeline/SKILL.md`; 必须调研 problem anchor / dominant contribution / risk 字段 | STRATEGY_BORROW | �?| 不替�?paper_card/formula_card 生成 | DOC_DESIGNED |

## 5. 外部项目调研（详细）

### PaperQA

- **机制**: evidence-constrained answer �?�?passages 注入 prompt，要�?LLM �?passages 范围内回答并 cite
- **对本模块的用�?*: evidence pack 注入 prompt 的方式可参考；citation-backed answer �?prompt 结构可借鉴
- **当前是否直接接入**: �?�?PaperQA �?QA 系统，不是教学系�?- **借鉴落地**: evidence pack 必须�?citation-backed answer 一样只包含可引�?passage；LLM 只能基于 EvidencePackItem 输出；输出必须携�?evidence_ref

### ARIS

- **机制**: reviewer independence（只传文件路径，不传摘要）；research-review（两线程对抗）；claim audit（零上下文验证）
- **对本模块的用�?*: reviewer independence 原则可直接应用（审计者独立于生成者）；claim audit 的零上下文思路可借鉴
- **当前是否直接接入**: �?�?只参考设�?- **借鉴落地**: card builder 只负责生成；audit 模块独立读取 card + evidence + source artifact；audit 不接�?card builder 的解释；audit 结果决定 understanding_status

## 6. 当前代码位置

- `src/researchsensei/m2/` �?current M2 rule-based understanding path from M1 artifacts
- `scripts/m2_run_understanding.py` �?CLI entry point that reads an M1 artifact bundle and writes `reports/m2_understanding_<paper_id>/`
- `src/researchsensei/paper_card_baseline.py` �?`build_paper_card()` (rule-based baseline)
- `src/researchsensei/paper_card.py` �?LLM card builder (fail-closed)
- `src/researchsensei/formula_card_baseline.py` �?`build_formula_cards()` (rule-based baseline)
- `src/researchsensei/formula_card.py` �?LLM card builder (fail-closed)
- `src/researchsensei/teaching_card_baseline.py` �?`build_teaching_cards()` (rule-based baseline)
- `src/researchsensei/teaching_card.py` �?LLM card builder (fail-closed)
- `src/researchsensei/llm/validator.py` �?LLM output validators
- `src/researchsensei/live_eval.py` �?opt-in real LLM smoke / live eval helper
- `src/researchsensei/schemas/llm_output.py` �?PaperCardLLMOutput, FormulaCardLLMOutput, TeachingCardLLMOutput
- `src/researchsensei/schemas/status.py` �?UnderstandingStatus, DownstreamGates, EvidencePackSummary
- `src/researchsensei/ingestion/pipeline.py` �?SinglePaperIngestionRunner (LLM card path integration)

Current M2 rule-based output is not a replacement for the future real-LLM/evidence-pack card pipeline. It establishes the M1 artifact contract, formula grouping behavior, source trace preservation, and risk handling. It writes:

- `m2_paper_understanding.md`
- `m2_formula_understanding.json`
- `m2_formula_understanding.md`
- `m2_method_graph.json`
- `m2_source_trace.json`
- `m2_risk_report.md`
- `m2_run_summary.json`

It reads only M1 artifacts and must not mutate M1 latex, bbox, page, parser source, source identity, crop path, or overlay path.

## 7. 输入输出

| �?| �?|
|----|-----|
| 输入 | paper_skeleton.json, evidence_pack, existing card baseline |
| 输出 | paper_card.json, formula_cards.json, teaching_cards.json, understanding_status.json |
| LLM prompt 只能使用 | paper title/metadata, canonical status summary, paper_skeleton, evidence_pack, existing baseline card |
| 禁止 | 直接整篇论文全文塞入 prompt |

LLM prompt 额外约束�?
- prompt 中必须列出“允许的 evidence_ref”清单�?- LLM 输出�?evidence_ref 必须从“允许的 evidence_ref”清单中精确选择一个�?- 不允许把多个 evidence_ref 用逗号、空格或列表拼接�?- 如果证据不足，文本写 `INSUFFICIENT_EVIDENCE` 或不生成对应 card，不能编�?evidence_ref�?- formula_card 只能基于 EvidencePack 中的 formula block / formula context�?- formula_card 必须读取并输�?`formula_origin`、`formula_ocr_status`、`formula_explanation_status`�?- M2 formula_cards 必须覆盖所�?M1 `FORMULA_CONTEXT` 公式证据；可深挖的公式生�?LLM card，证据不足或 LLM 遗漏的公式生�?summary-only / blocked card，不允许静默跳过�?
## 8. Artifact

- `paper_card.json`, `formula_cards.json`, `teaching_cards.json` 格式不变
- `understanding_status.json` 承载理解状�?- `quality_report.json` 承载审计结果
- 如果状态不�?SUCCESS，不得把 card 当最终用户结�?
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

### EvidencePackSummary（持久化�?UnderstandingStatus 中）

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
    learning_patterns: bool = False
    learning_drills: bool = False
    learning_drills_degraded: bool = False
    advisor_questions: bool = False

class UnderstandingStatus(SenseiModel):
    schema_version: str = "current"
    paper_id: str
    status: str  # SUCCESS / DEGRADED_STRUCTURAL / BLOCKED_UNDERSTANDING / FAILED / BASELINE_ONLY
    blocking_reason: str = ""
    warnings: list[WarningItem] = Field(default_factory=list)
    allowed_for_user_display: bool
    allowed_for_learning: bool
    checked_artifacts: list[str] = Field(default_factory=list)
    component_status: dict[str, str] = Field(default_factory=dict)
    evidence_pack_summary: EvidencePackSummary | None = None
    allowed_downstream: DownstreamGates = Field(default_factory=DownstreamGates)
```

### 主状态定�?
| 状�?| 含义 | allowed_for_user_display | downstream gating |
|------|------|--------------------------|-------------------|
| SUCCESS | LLM cards 生成成功，audit 通过 | True | �?DownstreamGates 决定（全�?True�?|
| DEGRADED_STRUCTURAL | 论文理解成功，但存在�?LLM 卡片失败的结构性限制（例如公式 provenance 不可推导�?| True | �?DownstreamGates 决定 |
| BASELINE_ONLY | �?LLM 或仅 rule-based baseline | False | 全部 False |
| BLOCKED_UNDERSTANDING | evidence / LLM / audit 导致理解不可�?| False | 全部 False |
| FAILED | 系统级异常（pipeline crash / 文件系统错误�?| False | 全部 False |

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
    formula_id: str = ""
    formula_origin: str = ""  # source_latex | parser_latex | ocr_latex | reconstructed | unknown
    formula_ocr_status: str = ""
    formula_explanation_status: str = ""
    confidence_policy: str = ""

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
    def __init__(self, ..., llm_client: LLMClient | None = None):
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
| LLM client 不存�?| BASELINE_ONLY，不得标记为 LLM understanding |
| LLM 调用失败 | BLOCKED_UNDERSTANDING，warning: "LLM_UNAVAILABLE" |
| LLM 输出 evidence_ref 不存�?| 丢弃，BLOCKED_UNDERSTANDING，warning: "INVALID_EVIDENCE_REF" |
| LLM 输出�?evidence_ref | 丢弃，BLOCKED_UNDERSTANDING，warning: "MISSING_EVIDENCE_REF" |
| LLM invalid JSON | BLOCKED_UNDERSTANDING，warning: "LLM_INVALID_JSON" |
| LLM timeout | BLOCKED_UNDERSTANDING，warning: "LLM_TIMEOUT" |
| evidence 不足 | INSUFFICIENT_EVIDENCE，不生成解释 |
| canonical_paper.md 缺失或无�?| BLOCKED_UNDERSTANDING |
| formula_origin == source_latex | 可高置信解释，但仍需 evidence_ref |
| formula_origin == parser_latex | 可解释，必须保留 parser warning |
| formula_origin == ocr_latex | 可解释，必须标注 OCR 来源，confidence 不得无依据升�?|
| formula_origin == reconstructed | 只能作为推测解释，必须明确标�?|
| formula_origin == unknown | 不能做详细公式推�?|
| 非核心或 LLM 遗漏公式 | 生成 evidence-bound summary-only formula_card，不允许静默跳过 |
| rule-based baseline | 只能作为 diagnostic，标�?BASELINE_ONLY |
| paper_card 成功 + teaching_cards 失败 | BLOCKED_UNDERSTANDING |
| paper_card 成功 + formula_cards 失败（公式核心） | BLOCKED_UNDERSTANDING |
| paper_card 成功 + formula_cards SKIPPED（无公式�?| 不阻�?|
| paper_card 失败 | BLOCKED |
| audit hard-fail (effect=BLOCK) | BLOCKED_UNDERSTANDING |
| audit warning only (effect=WARNING) | 不阻断，warning 写入 warnings |
| parser degraded | 不是 hard-fail，DEGRADED_STRUCTURAL（如果理解成功） |

BLOCKED_UNDERSTANDING 只能展示 status/blocking_reason/warnings/diagnostic metadata，不能包含论文解释、教学内容、核心思想推断或公式讲解�?
## 12. M4 Downstream Gates

Current code note (2026-06-27): M4 v1 is implemented for PaperWorkspace.
SUCCESS enables `reading_display`, `learning_patterns`, `learning_drills`, and
`advisor_questions`. DEGRADED_STRUCTURAL enables M4 v1 when paper/formula
artifacts are user-facing; `learning_drills` requires successful teaching cards
and otherwise records `learning_drills_degraded`.

DownstreamGates 控制下游 M4 互动式学习的访问权限，不再用 `status != SUCCESS` 作为唯一判断�?
> 注意：DownstreamGates 字段�?`learning_patterns` / `learning_drills` 等是 legacy 命名，语义归�?M4 互动式学习�?
| 状�?| paper_card | teaching_cards | reading_display | learning_patterns | learning_drills | advisor_questions |
|------|-----------|----------------|-----------------|-----------------|---------------|-------------------|
| SUCCESS | SUCCESS | SUCCESS | True | True | True | True |
| DEGRADED | SUCCESS | SUCCESS | True | True | True | True |
| DEGRADED | SUCCESS | FAILED | True | True | True（降级） | False |
| BASELINE | �?| �?| False | False | False | False |
| BLOCKED | �?| �?| False | False | False | False |
| FAILED | �?| �?| False | False | False | False |

```python
if not understanding_status.allowed_downstream.learning_patterns:
    raise GatingError("M4 patterns not allowed")

if not understanding_status.allowed_downstream.learning_drills:
    if not understanding_status.allowed_downstream.learning_drills_degraded:
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

### LLM card builder fail-closed 测试

| 测试 | 断言 |
|------|------|
| test_no_llm_client_produces_baseline_only | status == "BASELINE_ONLY" |
| test_real_llm_client_produces_evidence_bound_card | 真实 LLM 输出必须可解析；输出必须绑定 allowed evidence_ref；invalid JSON / missing evidence_ref / invalid evidence_ref 必须 BLOCKED_UNDERSTANDING |
| test_llm_failure_blocks_understanding | BLOCKED_UNDERSTANDING, warning "LLM_UNAVAILABLE" |
| test_invalid_evidence_ref_blocks | BLOCKED_UNDERSTANDING, warning "INVALID_EVIDENCE_REF" |
| test_missing_evidence_ref_blocks | BLOCKED_UNDERSTANDING, warning "MISSING_EVIDENCE_REF" |
| test_baseline_only_not_allowed_for_downstream | allowed_for_user_display is False |

### LLM output validator 测试

| 测试 | 断言 |
|------|------|
| test_validate_paper_card_llm_output_valid | valid output passes |
| test_validate_paper_card_llm_output_missing_evidence_ref | missing evidence_ref �?BLOCKED |
| test_validate_formula_cards_llm_output_valid | valid output passes |
| test_validate_teaching_cards_llm_output_valid | valid output passes |
| test_llm_invalid_json_blocks | invalid JSON �?BLOCKED_UNDERSTANDING |
| test_formula_output_requires_formula_origin | formula output must include formula_origin |
| test_source_latex_allows_high_confidence_with_evidence | source_latex + valid evidence can be high confidence |
| test_parser_latex_keeps_warning | parser_latex formula includes parser warning |
| test_ocr_latex_keeps_ocr_warning | ocr_latex formula includes OCR warning |
| test_reconstructed_formula_is_speculative | reconstructed formula marked speculative |
| test_unknown_formula_blocks_derivation | unknown origin blocks detailed derivation |
| test_formula_top_k_only | non-core formula is skipped or summarized |

### Pipeline LLM card path 测试

| 测试 | 断言 |
|------|------|
| test_pipeline_accepts_optional_llm_client | no error, status is BASELINE_ONLY |
| test_pipeline_success_artifacts | SUCCESS �?paper_card + formula_cards + teaching_cards + understanding_status + quality_report written |
| test_pipeline_degraded_artifacts | DEGRADED �?teaching_cards not written |
| test_pipeline_blocked_artifacts | BLOCKED �?no card artifacts written |
| test_blocked_understanding_no_user_facing_content | no paper explanation text in blocked output |
| test_success_status_for_final_display | status == "SUCCESS", allowed_for_user_display is True |
| test_m2_real_llm_smoke | opt-in real LLM 生成可解析输出，并验�?evidence_ref 可追�?|

### 全局规则

- M2.3 结构检查不能替代验收。M2.3 验收必须使用 M1 生成的真�?`canonical_paper.md` + 真实 LLM + 真实 EvidencePack + QualityAuditor。任�?simulated / synthetic / fake conversation 都不能作�?M2.3 完成依据
- BASELINE_ONLY is diagnostic only and is never user-facing completion
- 不新增依�?- M2 真实验收入口：`RUN_LLM_TESTS=1 RESEARCHSENSEI_LIVE_EVAL=1 python scripts/run_live_eval.py`

## 14. 验收标准

- LLM 输出必须绑定 evidence_ref
- 无效 evidence_ref �?BLOCKED
- empty evidence_pack �?BLOCKED
- baseline path 输出 BASELINE_ONLY
- LLM card path fail-closed，不 fallback
- 真实验收必须使用真实 `canonical_paper.md` 输入（不能只�?synthetic markdown�?- 真实验收必须真实调用 LLM，生�?paper/formula/teaching cards
- 真实验收必须通过 QualityAuditor 审计
- 真实验收必须生成 understanding_status.json
- evidence_ref 必须可追�?- formula_card 必须保留 formula_origin / formula_ocr_status / formula_explanation_status
- formula_cards 必须覆盖所�?M1 formula evidence；详细推导按 `derivation_status` 标记�?source_grounded / parser_derived / summary_only / blocked
- DEGRADED / BLOCKED 必须真实反映质量，不允许为通过测试放宽
- real LLM smoke 必须记录 model、prompt version、schema version、token、cost、latency、失败原�?- real LLM smoke 失败不能伪装成普�?mock 测试通过

## 15. 当前实现状�?
- baseline builders 已实现（paper_card_baseline.py, formula_card_baseline.py, teaching_card_baseline.py�?- LLM output schema 已实现（schemas/llm_output.py�?- LLM card builders 已实现（paper_card.py, formula_card.py, teaching_card.py�?- LLM output validator 已实现（llm/validator.py�?- LLM card path 已接入（SUCCESS / DEGRADED / BLOCKED�?- EvidencePack 已实�?- UnderstandingStatus / DownstreamGates 已实�?- QualityAuditor 已接�?- understanding_status.json / quality_report.json 已写�?- 测试已覆盖：15+ tests
- Real LLM smoke 已实�?opt-in 入口：`tests_live/test_m2_real_llm_smoke.py` �?`scripts/run_live_eval.py`
- LLM prompts 已加�?evidence_ref 精确选择约束，防止模型拼接多�?evidence_ref
- formula_is_core heuristic 已在 EvidencePack 中实现：核心公式按公式长度、核心关键词、section/claim context、helper/where-clause demotion 排序
- canonical_paper.md 输入、formula_origin 全链路、formula_ocr_status、all-formula coverage 策略已接�?`src/researchsensei/m2/full_pipeline.py`

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

## 17. Direction-Support Fields

M2.3 paper_card should expose direction-support fields when evidence exists. These fields support direction exploration and cross-paper understanding.

| Field | Description | Evidence requirement |
|-------|-------------|---------------------|
| `method_family` | Which method family this paper belongs to | Must have evidence_ref |
| `contribution_to_direction` | How this paper advances the research direction | Must have evidence_ref |
| `what_problem_it_solves` | What specific problem it addresses | Must have evidence_ref |
| `what_limitation_it_leaves` | What limitations remain | Must have evidence_ref |
| `relation_to_previous_methods` | How it relates to prior work | Must have evidence_ref |
| `relation_to_later_methods` | How later work improved on it | Must have evidence_ref |
| `datasets_and_metrics` | Datasets and metrics used | Must have evidence_ref |
| `comparable_methods` | Directly comparable methods | Must have evidence_ref |

These fields are optional in paper_card but required for direction framework updates. M2.4 audit must verify evidence_ref for direction-related claims.

## 17.5 Source-Aware Formula Preference

formula_card and teaching_card must prefer `source_latex` formulas.

Rules:
- If `formula_origin == source_latex`: formula_card should include `original_latex`; symbol explanation can be high confidence if evidence_ref valid
- If `formula_origin == parser_latex`: formula_card must include parser/source warning
- If `formula_origin == ocr_latex`: formula_card must include `ocr_warning`; confidence cannot be high unless verified by additional evidence
- If `formula_origin == reconstructed`: formula_card must mark explanation as speculative
- If `formula_origin == unknown`: do not generate detailed formula derivation; mark formula explanation as degraded or blocked

Survey Deep Reading should extract method_taxonomy and key papers preferably from LaTeX/HTML structure when available; PDF-only extraction must record lower source confidence.

## 18. Survey Paper Support

For survey/review papers, M2.3 additionally outputs:

| Output | Description |
|--------|-------------|
| `survey_landscape` | Overall landscape of the surveyed field |
| `method_taxonomy` | Taxonomy of methods covered |
| `extracted_key_papers` | Key papers identified in the survey |
| `survey_claims` | Claims made by the survey about the field |

`survey_landscape` does NOT replace `paper_card`. `formula_card` is NOT replaced by survey summary.

Status: IMPLEMENTED_RULE_BASED / UNIT_TESTED; real survey PDF live acceptance remains pending.

## 2026-06-14 Implementation Update

- Implemented real evidence-constrained M2 card generation through `src/researchsensei/m2/full_pipeline.py`.
- Real LLM path uses `build_paper_card`, `build_formula_cards`, and `build_teaching_cards`; all outputs must validate against the exact EvidencePack `evidence_ref` set.
- Formula evidence now carries M1 provenance into the LLM/card layer: `formula_raw`, `original_latex`, `formula_origin`, `formula_ocr_status`, and `formula_explanation_status`.
- `validate_formula_cards_llm_output` fails if formula evidence exists but the LLM returns no formula cards.
- Teaching-card prompt is compact enough for ccswitch live runs: short fields, valid JSON only, no markdown.
- Current live verification should use `RESEARCHSENSEI_LLM_PROVIDER=cc_switch`; Xiaomi/MiMo is no longer the default local path.
- Formula evidence selection for the ordinary evidence pack is still heuristic, but `formula_cards.json` now uses a dedicated all-formula evidence pack and must cover every M1 formula evidence ref.
- Survey/review support now emits evidence-bound `survey_status.json`, `survey_landscape.json`, `method_taxonomy.json`, `extracted_key_papers.json`, and `survey_claims.json` from canonical passages. Non-survey papers get `survey_status=NOT_APPLICABLE`; survey outputs require passage/evidence trace and do not replace `paper_card` or `formula_cards`.
- Limitation: all-formula coverage is implemented, but advanced symbolic derivation is only as strong as M1 LaTeX and nearby evidence. Raw/unknown formulas remain blocked for derivation.

## 19. 当前未解决问�?
- formula_is_core heuristic 已实现；仍需要更多论文调参验�?- EvidencePackSummary 是否足够复现 LLM 输入
- component_status 的值是否还需�?DEGRADED
- �?rule-based baseline builders �?current builders 的边界仍需确认（old `*_with_llm` 函数可能仍有 fallback，但 pipeline 不走它们�?- DownstreamGates 的最终字段是否足�?- 当前 real LLM smoke 只有一�?synthetic paper 样例，不能代表真实论文质�?- 当前成本估算依赖价格环境变量；未配置时报�?cost=0，但 token limit 仍生�?> Current implementation status is authoritative only in `docs/STATUS.md`.
> Historical status rows in this detailed planning note may be older than the
> current M1/M2/M3 readiness state.
