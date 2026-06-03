# Technical Discussion

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

## 2. Current Project Facts

- ResearchSensei 是论文研读导师系统。
- 当前 Phase 1-11 是 baseline，不是最终导师级论文理解。
- 当前 evidence 仍偏 block-level。
- 当前 card builders 仍存在 rule-based fallback。
- 当前尚未实现 understanding_status.json。
- 当前尚未实现 QualityReport。
- 当前尚未实现独立 audit。
- 当前 pipeline 在 LLM 失败时 fallback 到 rule-based，而不是 fail-closed。
- Phase 12 暂不进入。

---

## 3. Global Technical Consensus

1. ResearchSensei 主路线是 Python / FastAPI / Pydantic / JSON artifacts / Vue frontend。
2. ARIS-style skills 不作为主执行方式。
3. ARIS 只参考 audit chain、reviewer independence、claim audit、kill-argument 等思想。
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
- ARIS 的 reviewer independence、claim audit、kill-argument 思想值得参考。

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

## 13. How to Use This Document

- 本文档保存讨论，不直接作为开发依据。
- 达成稳定共识后，再同步到 DESIGN.md、DEVELOPMENT.md 或 docs/development/*.md。
- 未决问题不能写成结论。
- 每轮讨论后，只把新增共识和新增未决问题追加到本文档。
- 不要把本文档变成进度日志。
