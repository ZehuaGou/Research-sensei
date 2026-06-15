# Technical Discussion — 历史归档

> **本文档是历史技术讨论归档，不作为当前开发依据。**
> 当前正式开发依据是：DESIGN.md、DEVELOPMENT.md、STATUS.md、docs/development/*.md。
> 本文档保留外部项目调研和历史共识参考，但不再指导开发。

---

## 1. Purpose

本文档用于记录 ResearchSensei 全项目技术讨论中的共识、分歧、问题和下一步讨论方向。

覆盖范围包括但不限于：

- 整体架构
- 精读链路
- 搜索链路
- Parser
- Evidence
- Paper Understanding
- Audit / Quality
- Frontend Render
- Workspace / API
- Engineering Reliability
- 外部项目复用
- 测试策略
- fail-closed 策略
- Phase 12 解冻条件

本文档不是正式开发文档。
正式开发依据仍然是：

- docs/DESIGN.md
- docs/DEVELOPMENT.md
- docs/development/*.md

---

## 2. Historical Snapshot / 早期讨论快照

> 本节记录早期讨论时的项目状态，**已过时**，不代表当前项目状态。
> 当前状态以 docs/STATUS.md 和 M1-M5 模块文档为准。

- ResearchSensei 是论文研读导师系统。
- 当时 Phase 1-11 是 baseline，不是最终导师级论文理解。
- 当时 evidence 仍偏 block-level。
- 当时 card builders 仍存在 rule-based fallback。
- 当时尚未实现 understanding_status.json。
- 当时尚未实现 QualityReport。
- 当时尚未实现独立 audit。
- 当时 pipeline 在 LLM 失败时 fallback 到 rule-based，而不是 fail-closed。
- Phase 12 暂不进入。

---

## 3. Global Technical Consensus

1. ResearchSensei 主路线是 Python / FastAPI / Pydantic / JSON artifacts / Vue frontend。
2. ARIS-style skills 不作为主执行方式。
3. ARIS 只参考 audit chain、reviewer independence、claim audit、research-review 等思想。
4. 外部项目不能直接污染主流程，必须通过 adapter 或独立模块接入。
5. fail-closed 是最终质量策略：宁可不输出，也不输出低可信解释。
6. BASELINE_ONLY 不能作为最终理解，不能作为 Phase 12 输入。
7. BLOCKED_UNDERSTANDING 不能包含解释性内容。
8. Audit 必须独立于 card builder。
9. Phase 12 只有在 evidence、understanding_status、audit、quality gate 完成后才允许继续。

---

## 4. Reading Pipeline Discussion

### 当前倾向路线

```
source / selected paper
→ ParserAdapter
→ DocumentIngestion
→ PassageIndex
→ ClaimEvidence
→ EvidencePack
→ evidence-constrained LLM
→ cards
→ independent audit
→ QualityReport
→ understanding_status
→ frontend/API display
```

### 已达成共识

- LLM 不能直接吃全文。
- LLM 只能基于 EvidencePack 输出解释。
- invalid evidence_ref / missing evidence_ref / empty evidence_pack / LLM failure 都不能生成最终解释。
- EvidencePack 倾向作为运行时对象，不作为持久 artifact。
- understanding_status 倾向由 audit 或 runner 基于 audit 结果生成，不能由 card builder 自我放行。

### 未决问题

- EvidencePack 是否完全不持久化。
- understanding_status 由 audit 直接写，还是 runner 汇总 audit 后写。
- BASELINE_ONLY 是否写到 baseline_cards/ 目录。
- 旧 rule-based builders 如何迁移。

---

## 5. Parser Discussion

### 已达成共识

- Parser 层采用 adapter-first。
- 当前先验证 LightweightParserAdapter。
- 外部 parser 通过 ParserAdapter 接入。
- Docling 是第一个真实外部 parser adapter 候选。
- Marker 因 GPL/license 风险暂不接入。
- MinerU 能力强但依赖重。
- Nougat 适合公式密集论文但依赖重。

### 未决问题

- ParserAdapter.parse() 是否继续返回 DocumentIngestion，还是返回 ParserResult。
- 是否需要 ParseMetadata。
- DocumentBlock 是否现在扩展 bbox、table_html、figure_caption、reference_entries。
- 如果未来接 Docling，如何保留 page/layout/table/formula metadata。
- Docling 本地样例验证需要哪些论文。

---

## 6. Evidence Discussion

### 已达成共识

- 当前 block-level evidence 太粗。
- 需要 PassageIndex。
- 需要 ClaimEvidence。
- 不允许 section label 直接当 claim。
- claim 必须能回指 passage/block。
- PaperQA 不整包接入，只借鉴 passage retrieval / citation-backed answer 思想。
- 初版不引入 embedding model / vector DB。

### 未决问题

- passage_index.json 和 claim_evidence.json 是否作为独立 artifact。
- evidence_index.json 是否作为兼容 wrapper 保留。
- EvidenceRetriever 初版用 simple overlap 还是 BM25。
- BM25 是否自实现。
- claim_id / passage_id / evidence_ref 命名规范。
- ClaimExtractor 的规则复杂度到什么程度。

---

## 7. Paper Understanding Discussion

### 已达成共识

- LLM 输出必须受 evidence 约束。
- paper_card / formula_cards / teaching_cards 不能无 evidence 生成最终解释。
- rule-based baseline 只能作为 diagnostic / BASELINE_ONLY。
- fail-closed 策略优先于"勉强输出"。

### 未决问题

- LLM 输出 schema 是否拆成 PaperCardLLMOutput / FormulaCardsLLMOutput / TeachingCardsLLMOutput。
- BASELINE_ONLY 是否写正式 card 文件，还是写 baseline_cards/。
- 旧 Phase 8-10 代码如何迁移。
- 旧测试中 fallback 断言如何迁移。
- 如果 audit warning 但无 hard-fail，是否仍然 SUCCESS。

---

## 8. Audit / Quality Discussion

### 已达成共识

- Audit 不能调用 card builder。
- Audit 不能接收 card builder 的自然语言解释。
- Audit 只能读取 artifacts 或序列化 JSON。
- Audit 输出 QualityReport。
- QualityReport 决定 understanding_status。
- ARIS 的 reviewer independence、claim audit、research-review 思想值得参考。

### 未决问题

- Audit 初版是否完全 rule-based。
- 是否预留 LLM-based auditor 接口。
- 是否拆分 EvidenceAuditor、FormulaAuditor、GenericnessAuditor、CopyAuditor、AdvisorReadinessAuditor。
- QualityReport 到 understanding_status 的映射规则。
- "讲得好"的自动检测边界。
- 是否需要人工评估集。

---

## 9. Literature Search Discussion

### 已达成共识

- arXiv / OpenAlex 是当前 direct adapter。
- Semantic Scholar / Crossref 是 optional adapter。
- PaperQA 不作为搜索源。
- Crossref 主要用于 DOI metadata。
- Literature Search 和单篇 Evidence Retrieval 不应混为一谈。
- STORM / ResearchPilot / ARIS research-lit 更适合未来 cross-paper / advisor / outline / novelty 方向。

### 未决问题

- Semantic Scholar 是否应优先于 OpenAlex。
- reading_plan 是否直接触发单篇精读。
- A_READ papers 进入精读前需要哪些过滤。
- 低召回如何标记。
- selection_reason / risk_note 如何避免模板化。

---

## 10. Frontend / API Discussion

### 已达成共识

- Vue 前端保留。
- 前端只消费 artifact，不重新推理。
- 非 SUCCESS 不展示导师级解释。
- BASELINE_ONLY 只能作为 diagnostic。
- BLOCKED_UNDERSTANDING 只展示阻塞原因。

### 未决问题

- 前端如何展示 evidence_ref。
- 是否支持点击 evidence_ref 回原文。
- formula_cards 如何展示公式、符号、解释。
- blocked 状态的用户文案如何写。
- API 如何返回 understanding_status。

---

## 11. Workspace / Engineering Discussion

### 已达成共识

- 默认 pytest 不联网。
- 默认 pytest 不真实调用 LLM。
- warnings 必须是 WarningItem，不是字符串。
- 不提交 .env、key、缓存、大文件。
- live smoke 必须独立隔离。
- artifact 必须可读、可追踪、可重新加载。

### 未决问题

- artifact versioning 怎么设计。
- rerun / resume 怎么做。
- cache 策略怎么做。
- CI 如何约束 no-network / no-real-LLM。
- secret scanning 是否加入自动检查。

---

## 12. External Project Notes

| 项目 | 角色 | 当前状态 |
|------|------|----------|
| Docling | ParserAdapter 候选，优先级最高 | GitHub 已确认，MIT license，待本地验证 |
| Marker | 能力强，但 GPL-3.0 license 风险 | 暂不接入，除非 license 变更 |
| MinerU | 能力强但依赖重 | GitHub 已确认，Apache 2.0 自定义 license (v3.1.0+)，暂不默认接入 |
| Nougat | 公式密集 PDF 候选，但依赖重 | GitHub 已确认，MIT license，暂不默认接入 |
| PaperQA | 不整包接入，只借鉴 grounded RAG / citation-backed answer | GitHub 已确认，Apache-2.0 license |
| ARIS | 不接入 skills 主流程，只借鉴 audit 思想 | GitHub 已确认，MIT license |
| STORM | 未来 advisor / outline / multi-perspective 参考 | GitHub 已确认，MIT license |
| ResearchPilot | repo 未确认 | 暂作 reference-only |
| OpenScholar | repo 未确认 | citation accuracy 方向可参考 |
| Semantic Scholar | optional adapter | 免费 API，有 rate limit |
| Crossref | optional adapter，DOI metadata | 免费 API |

---

## 13. Five Key Questions Discussion Conclusions

**本节只是第一批已收敛的基础共识。不代表全项目技术讨论完成。**

仍需继续讨论 Evidence、Paper Understanding、Audit、Frontend/API、Engineering Reliability、Literature Search 等关键模块。未讨论完成前，不允许开始代码开发。

ParserAdapter 只是候选第一个代码任务，不是已授权任务。

---

以下五个问题已在技术讨论中形成初步共识，同步到对应模块开发文档。

### Q1: ParserAdapter.parse() 返回类型

**共识：返回 ParserResult。**

```python
class ParseMetadata(SenseiModel):
    parser_name: str
    parser_version: str = ""
    source_format: str = ""
    page_count: int = 0
    extra: dict = {}

class ParserResult(SenseiModel):
    document: DocumentIngestion
    metadata: ParseMetadata
```

- DocumentIngestion 负责统一文档内容。
- ParseMetadata 负责 parser 运行元数据。
- LightweightParserAdapter 把现有 DocumentIngestion 包装成 ParserResult。
- 下游只消费 `result.document`，不影响现有逻辑。

### Q2: DocumentBlock 扩展字段

**共识：现在加 Optional 字段。**

```python
bbox: tuple[float, float, float, float] | None = None
table_html: str = ""
figure_caption: str = ""
reference_entries: list[str] = Field(default_factory=list)
```

- Optional 默认值保证向后兼容。
- Docling / MinerU 的结构化输出可以保留。
- 不会破坏现有 parsed_document.json 反序列化。

### Q3: EvidenceRetriever 策略

**共识：自实现 BM25，不新增依赖。**

- simple overlap 太弱，不考虑 IDF / 词频 / 文档长度。
- BM25 纯 Python 实现，约 30 行核心代码。
- 默认 pytest 可直接用 fixture 测试。

### Q4: understanding_status 由谁写

**共识：Runner 根据 QualityReport 写。**

- QualityAuditor.audit(...) 是纯逻辑，输出 QualityReport。
- Audit 不依赖 WorkspaceStore，不写 artifact。
- Runner 负责读取 QualityReport，映射成 UnderstandingStatus，写 understanding_status.json。
- Card builder 不能参与 understanding_status 生成。

### Q5: BASELINE_ONLY 放哪里

**共识：写正式 card 文件，用 understanding_status 标记。**

- BASELINE_ONLY 时仍然写 paper_card.json / formula_cards.json / teaching_cards.json。
- understanding_status.status = "BASELINE_ONLY"。
- 前端/API/Phase 12 必须先读 understanding_status.json。
- status != SUCCESS 时不展示导师级解释，不进入 Phase 12。

---

## 14. Next Discussion Topics

以下为下一轮技术讨论重点，未完成前不允许开始代码开发。

### 14.1 Evidence + Paper Understanding 深入设计

- PassageIndex 构建算法（section 分段 vs paragraph 分段 vs 句子分段）
- ClaimEvidence 从 passage 提取的规则复杂度
- EvidenceRetriever BM25 参数调优
- EvidencePack 构建流程（过滤、截断、token budget）
- LLM prompt 结构（system / user / 输出约束）
- LLM 输出 schema（是否拆成 PaperCardLLMOutput / FormulaCardsLLMOutput / TeachingCardsLLMOutput）
- fail-closed 状态决策树（哪些场景 → BLOCKED / BASELINE_ONLY / FAILED）
- Phase 8-10 rule-based builders 如何迁移
- 旧测试中 fallback 断言如何迁移

### 14.2 Audit / Quality 深入设计

- QualityReport schema 定义
- Auditor 接口设计
- 子 auditor 拆分（EvidenceAuditor / FormulaAuditor / GenericnessAuditor / CopyAuditor / AdvisorReadinessAuditor）
- hard-fail 映射规则（多少 hard_fail → BLOCKED，多少 warning 仍算 SUCCESS）
- 是否允许 LLM-based auditor
- 人工评估集设计

### 14.3 Frontend / API 状态展示

- SUCCESS / BASELINE_ONLY / BLOCKED_UNDERSTANDING 的 UI 展示规则
- evidence_ref 跳转（点击 evidence_ref 回原文）
- formula_cards 如何展示公式、符号、解释
- blocked 状态的用户文案
- API 如何返回 understanding_status
- Phase 12 gating 在 API 层如何实现

### 14.4 Engineering Reliability

- artifact versioning 设计
- rerun / resume 机制
- cache 策略
- CI 约束（no-network / no-real-LLM）
- secret scanning

---

## 16. Evidence + Paper Understanding Deep Discussion

以下为第二批讨论结论，基于六大争议点辩论。

### 16.1 新增共识

**1. PassageIndex 应持久化为 passage_index.json。**

理由：
- artifact-driven 系统需要可审计、可复现、可调试；
- audit 需要独立读取 passage 构建结果；
- 前端 evidence 跳转需要 passage 层信息；
- ClaimEvidence.passage_id 不能指向不存在的运行时对象。

**2. ClaimEvidence v2 应持久化为 claim_evidence.json。**

- evidence_index.json 保留 v1 兼容；
- claim_evidence.json 承载 v2 字段（passage_id, claim_type, semantic_support, source_sentence, generated_by）；
- audit 和未来 Phase 12 读取 claim_evidence.json。

**3. UnderstandingStatus 使用 5 个主状态。**

- SUCCESS
- DEGRADED_STRUCTURAL
- BASELINE_ONLY
- BLOCKED_UNDERSTANDING
- FAILED

**4. 不引入 SUCCESS_WITH_WARNINGS。** warnings 统一放在 warnings 字段。

**5. BLOCKED_UNDERSTANDING 与 FAILED 的边界。**

- BLOCKED_UNDERSTANDING = 理解失败：evidence 不足、LLM 输出无效、audit hard-fail。
- FAILED = 系统异常：文件系统错误、Pydantic 崩溃、pipeline 异常。

**6. BASELINE_ONLY 与 DEGRADED_STRUCTURAL 的边界。**

- BASELINE_ONLY = 无 LLM 或只有 rule-based baseline。
- DEGRADED_STRUCTURAL = LLM 理解成功，但某些结构/组件降级。

**7. UnderstandingStatus 需要 component_status。**

```
component_status:
  paper_card: SUCCESS / FAILED / BASELINE
  formula_cards: SUCCESS / SKIPPED / FAILED / BASELINE
  teaching_cards: SUCCESS / FAILED / BASELINE
  audit: SUCCESS / FAILED
```

**8. formula_cards 失败不能一律 BLOCKED。** 需要区分：

- FORMULA_ABSENT：论文无公式，SKIPPED，不阻断；
- FORMULA_OPTIONAL_FAILED：公式非核心，warning，不阻断；
- CORE_FORMULA_FAILED：核心公式失败，BLOCKED。

**9. teaching_cards 失败不能简单视为 SUCCESS。**

ResearchSensei 是研读导师系统，teaching 是核心价值。当前倾向：paper_card 成功但 teaching_cards 失败 → DEGRADED_STRUCTURAL。

**10. EvidencePack 不完整持久化，但 UnderstandingStatus 中保存 EvidencePackSummary。**

```
EvidencePackSummary:
  included_claim_ids: list[str]
  excluded_claim_ids: list[str]
  total_tokens: int
  claim_type_counts: dict[str, int]
  truncated_passage_ids: list[str]
```

**11. 精读链路关键新增 artifact：** passage_index.json, claim_evidence.json, understanding_status.json。

### 16.2 保留的旧共识

1. LLM 三次调用：paper_card, formula_cards, teaching_cards。
2. EvidencePack 仍然主要是运行时对象。
3. Audit warning 不阻断，进入 SUCCESS + warnings。
4. Phase 8-10 迁移方向仍是 baseline_builder + LLM card builder，文件名尽量保持兼容。

### 16.3 需要继续讨论的问题

1. DEGRADED_STRUCTURAL 是否允许进入 Phase 12。建议继续讨论是否需要 allowed_for_phase12 或更细的 capability gates。
2. formula_is_core 如何判断：规则？LLM？skeleton.formulas？formula purpose != UNKNOWN？当前不能强行定。
3. EvidencePackSummary 是否足够复现 LLM 输入。如果 passage_text 被 token budget 裁剪，仅保存 truncated_passage_ids 是否足够？
4. component_status 的值是否够用：SUCCESS / SKIPPED / FAILED / BASELINE，是否还需要 DEGRADED？
5. passage_index.json 和 claim_evidence.json 的生成顺序：parsed_document → passage_index → claim_evidence → evidence_index wrapper？还是保留旧 evidence_index 先生成？
6. teaching_cards 失败后前端到底展示什么：paper_card 可以展示吗？是否必须标注"讲解层降级"？是否影响 advisor/drill？
7. allowed_for_phase12 是否太粗，需要改为更细的 downstream gate。

---

## 17. Audit / Quality + Frontend / API Deep Discussion

以下为第三批讨论结论，基于 Audit / Quality + Frontend / API 六大争议点辩论。

### 17.1 新增倾向共识

**1. QualityReport 使用统一 AuditFinding。**

```python
class AuditFinding(SenseiModel):
    code: str           # F-1, F-2, ...
    severity: str       # P0 / P1 / P2
    effect: str         # BLOCK / WARNING
    message: str
    artifact: str = ""
    field: str = ""
```

不使用 hard_fails + warnings 两套结构。

**2. QualityReport 建议结构。**

```python
class QualityReport(SenseiModel):
    paper_id: str
    findings: list[AuditFinding] = []
    component_results: list[ComponentAuditResult] = []
    checked_artifacts: list[str] = []
    audit_version: str = "v1"
    created_at: str = ""
```

**3. QualityReport 应持久化为 quality_report.json。**

**4. QualityReport 是 audit 原始输出；UnderstandingStatus 是 Runner 根据 QualityReport 生成的下游状态。**

**5. AuditFinding 的 severity/effect 规则。**

- P0 一定 BLOCK
- P1 可能 BLOCK，也可能 WARNING
- P2 通常 WARNING

**6. raw copy 不能一刀切。**

- core_idea / problem / method raw copy → BLOCK
- limitations / quote 高重合 → WARNING
- teaching analogy raw copy → BLOCK

**7. missing passage_id for claim_evidence v2 倾向 BLOCK。** 因为会破坏 passage 追踪链路。

**8. DEGRADED_STRUCTURAL 前端展示必须按 component_status 过滤。**

- 成功组件可以展示
- 失败组件不展示
- 必须显示明显降级提示
- 不能笼统称为"导师级解释"

**9. "导师级解释"只有在 paper_card、formula_cards、teaching_cards 都成功时才成立。** 缺 teaching_cards 时，只能称为"论文理解"或"结构化理解"。

**10. DownstreamGates 倾向替代 allowed_for_phase12。**

```python
class DownstreamGates(SenseiModel):
    reading_display: bool = False
    phase12_patterns: bool = False
    phase12_drill: bool = False
    phase12_drill_degraded: bool = False
    advisor_questions: bool = False
```

**11. teaching_cards 失败时。**

- reading_display 可以 True
- phase12_patterns 可以 True
- phase12_drill 可以降级运行
- advisor_questions 不允许

**12. formula_cards SKIPPED 不影响 drill。** 无公式论文不需要公式追问。

**13. /cards API 应按 understanding_status + component_status 返回内容。**

- SUCCESS：返回全部成功 cards
- DEGRADED_STRUCTURAL：只返回成功组件，失败组件隐藏并给出降级提示
- BASELINE_ONLY：普通用户不返回 cards，debug/admin 可查看 baseline cards
- BLOCKED_UNDERSTANDING：不返回 card 内容，只返回 blocking_reason
- FAILED：只返回系统错误

**14. QualityReport 只给 debug/admin，不给普通用户。**

**15. 现有 test_quality_*.py 继续作为 pytest 层质量门，同时新增产品级 auditor 测试。**

### 17.2 重要修正 / 不能定死的点

**1. /artifacts 是否过滤不能直接定死。**

候选方案：

- 方案 A：/cards 是用户端受控 API，按 status 过滤；/artifacts 是 debug/admin raw API，只给开发/管理端使用；普通前端不直接用 /artifacts 展示 cards。
- 方案 B：/artifacts 也过滤 cards，避免 blocked cards 泄露；但这会让 artifacts API 语义变混。

当前倾向：不要让普通用户直接访问 raw /artifacts；新增或约束 debug/admin 权限。此点仍列为未决。

**2. debug=true 不能默认给所有用户使用。** 必须是 admin/dev only。认证方式未定。

**3. AuditFinding 是否完全替代 WarningItem 未定。** QualityReport 内部倾向用 AuditFinding；其他模块 warnings 是否继续用 WarningItem 需要继续讨论。

**4. score / dimension_scores 当前不放入 rule-based QualityReport。** 未来如果引入 LLM auditor，是否重新引入 score 仍未定。

**5. QualityReport 暴露范围未定。** 普通用户是否完全不可见？debug/admin 如何鉴权？是否需要脱敏版本？

### 17.3 仍未决问题

1. AuditFinding 和 WarningItem 是否统一，还是各自保留边界。
2. debug/admin 鉴权机制。
3. /artifacts 是 raw debug API，还是 filtered user API。
4. evidence_ref 跳转优先级。
5. fake artifacts fixtures 的具体设计。
6. DEGRADED_STRUCTURAL 的前端提示文案。
7. DownstreamGates 的最终字段是否足够。
8. phase12_drill_degraded 是否需要单独 reason 字段。
9. QualityReport 是否需要脱敏版。
10. 产品级 auditor 和 pytest quality tests 的边界。

### 17.4 下一轮讨论建议

最后一轮讨论 Engineering Reliability，重点：

- artifact versioning
- artifact schema migration
- rerun / resume
- cache strategy
- CI no-network / no-real-LLM
- secret scanning
- debug/admin API 权限
- raw artifacts access policy
- live smoke test 隔离

---

## 18. Engineering Reliability Discussion

以下为第四批讨论结论，基于 Engineering Reliability 九大问题讨论。

### 18.1 新增倾向共识

**1. Artifact versioning。**

- 每个 artifact 顶层应有 `schema_version`。
- 旧 artifact 没有 `schema_version` 时按 v1 读取。
- 新 v2 artifact 写出时必须显式写 `schema_version="v2"`。
- additive schema change 通过 Pydantic 默认值兼容。
- breaking change 未来再引入 migration，不在初版实现。
- 暂不引入 `artifact_manifest.json`。

**2. Artifact 原子写入。**

- `WorkspaceStore.write_json` 应采用 tmp + rename 原子写入。
- 写入失败时 `job.status=FAILED`。
- 部分 artifact 写成功后不回滚，用于 debug。
- 已写 artifact 不覆盖。rerun 创建新 run_id，resume 才复用已有 artifact。

**3. rerun / resume。**

- resume 必须显式开启，默认 `resume=False`。
- resume 按 artifact 是否存在 + schema_version 是否匹配决定是否跳过。
- schema_version 不匹配时强制重跑。
- resume 和 LLM cache 是两个独立机制。
- resume 的具体 run_id 复用规则仍需继续讨论。

**4. Cache strategy。**

- 初版只 cache LLM。Parser / BM25 / EvidenceRetriever 不 cache。
- LLM cache key 应包含：model, prompt_version, prompt_hash, schema_version, temperature。
- cache 不进 Git。
- 测试环境默认关闭 cache，生产/本地可开启。

**5. CI / pytest。**

- 默认 pytest 不联网、不真实调用 LLM。
- 需要 pytest markers：live, network, llm, slow。
- 必须在默认 pytest/CI 命令中排除：`pytest -m "not live and not network and not llm and not slow"`
- live smoke 放 `tests_live/`，默认不跑。
- live / network / llm 测试必须通过环境变量显式开启：`RUN_LIVE_TESTS=1`, `RUN_LLM_TESTS=1`
- 外部 adapter 测试默认用 MockTransport。

**6. Secret scanning / repo hygiene。**

- 项目有过真实 key 泄露历史，必须加入 secret scan 规则。
- 扫描关键词：`sk-`, `api_key`, `DEEPSEEK_API_KEY=`, `MIMO_API_KEY=`, `OPENAI_API_KEY=`, `ANTHROPIC_API_KEY=`。
- `.env.example` 只能放 placeholder。
- `.env`、`.env.*`、cache、runs、artifacts、大模型文件、数据库文件不得提交。
- commit message 不允许 Claude / Happy / Anthropic contributor 信息。
- 是否使用 pre-commit / CI gitleaks / trufflehog 仍需后续实现时确认。

**7. debug/admin 权限和 raw artifacts。**

- `/cards` 是用户端受控 API，按 understanding_status + component_status 过滤。
- `/understanding_status` 是用户端状态 API。
- `/artifacts` 应定位为 debug/admin raw API，不给普通用户直接使用。
- `/quality_report` 应定位为 debug/admin API。
- 普通前端不应直接用 `/artifacts` 展示 cards。
- 本地开发可用 `SENSEI_DEBUG=1`，生产环境必须有鉴权。
- debug/admin 鉴权机制仍未定。

**8. Error taxonomy。**

- 需要统一 error code taxonomy。
- Parser: PARSER_FAILED, PDF_PARSE_FAILED, UNSUPPORTED_FILE_TYPE
- Evidence: NO_PASSAGES, NO_CLAIMS, MISSING_METHOD_EVIDENCE
- LLM: LLM_UNAVAILABLE, LLM_TIMEOUT, LLM_INVALID_JSON, LLM_INVALID_EVIDENCE_REF
- Audit: AUDIT_HARD_FAIL, AUDIT_INTERNAL_ERROR
- API: UNAUTHORIZED_DEBUG_ACCESS, STATUS_BLOCKED
- pipeline 层 warnings 用 WarningItem。audit 层 findings 用 AuditFinding。job 层错误写 Job.error。
- 日志应包含 job_id / run_id / artifact_name。日志禁止打印 API key、prompt 全文、过长论文文本。

**9. live smoke / external adapter validation。**

- live smoke 独立 `tests_live/`。默认不跑，不阻塞普通 CI。
- 通过 `RUN_LIVE_TESTS=1` 显式开启。
- Docling adapter 接入前至少需要样例：simple PDF, formula-heavy PDF, table-heavy PDF, scanned PDF。
- 需要记录外部项目版本和验证日期。
- 样例 PDF 来源和版权仍需确认。

### 18.2 需要修正或不能定死的点

1. "全项目技术路线讨论可以收尾"不能直接写成最终结论。更准确说法：Engineering Reliability 已形成第一批倾向共识；全项目主要路线已基本收敛；仍需把共识同步到正式模块文档，并在同步时发现冲突再讨论。
2. `artifact_manifest.json` 暂不引入，但 content_hash / dependencies 未来可能需要。不要永久否定 artifact_manifest。
3. resume 语义仍需继续确认：是同一 run 继续？还是新 run 复用旧 artifact？与"不覆盖 artifact"的关系还需细化。
4. debug/admin 鉴权机制未定：环境变量只适合本地开发；production 必须另设鉴权策略。
5. secret scanning 的具体工具未定：pre-commit / gitleaks / trufflehog，后续实现阶段再选。
6. live smoke 样例 PDF 来源未定。

### 18.3 仍未决问题

1. artifact_manifest 是否未来需要。
2. content_hash 是否在 v2 初版加入。
3. resume 与 rerun 的 run_id 语义。
4. cache 默认开启策略。
5. debug/admin 鉴权机制。
6. /artifacts 是否需要脱敏版本。
7. secret scan 工具选型。
8. live smoke 样例 PDF 来源。
9. external_versions.json 手动维护还是自动生成。
10. CI 是否强制 no-network monkeypatch。

### 18.4 下一步建议

1. 保存本轮讨论后，不直接写代码。
2. 下一步任务：把 TECHNICAL_DISCUSSION.md 中已经稳定的共识同步到正式模块文档。
   - 同步范围：PARSER.md, EVIDENCE.md, PAPER_UNDERSTANDING.md, AUDIT_QUALITY.md, FULL_PIPELINE.md
   - 可能新增：FRONTEND_RENDER.md, ENGINEERING_RELIABILITY.md
   - 同步前先给出同步计划，不直接修改。
3. 正式开发文档同步完成后，再考虑 ParserAdapter 代码实现。

---

## 19. How to Use This Document

- 本文档保存讨论，不直接作为开发依据。
- 达成稳定共识后，再同步到 DESIGN.md、DEVELOPMENT.md 或 docs/development/*.md。
- 未决问题不能写成结论。
- 每轮讨论后，只把新增共识和新增未决问题追加到本文档。
- 不要把本文档变成进度日志。
