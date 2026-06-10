# ResearchSensei Status

## Current Gate

本文件只记录真实工程状态。

M1 测试必须真实运行：真实 LLM、真实 arXiv、真实 OpenAlex/pyalex、真实 Semantic Scholar、真实 Crossref、真实 PDF 下载。mock/fake/skip 不作为有效测试。缺 key、缺网络、API 限流、PDF 下载失败均视为失败。

## Status Levels

| Level | Meaning |
|---|---|
| NOT_STARTED | 没有代码或文档 |
| DOC_ONLY | 只有文档 |
| DOC_DESIGNED | 工程规格已写清输入、输出、状态字段、失败条件、gate 和测试要求，但代码未实现 |
| DOC_REQUIRED | 文档待补充，代码未实现 |
| IMPLEMENTED | 有代码能力，但不代表真实验收完成 |
| UNIT_TESTED | 有单元测试，但没有真实外部链路验证 |
| REAL_E2E_VERIFIED | 真实端到端通过 |
| PARTIAL_REAL_E2E_VERIFIED | 部分模式真实端到端通过，其他模式未实现 |
| PRODUCTION_READY | 可用于稳定生产环境 |

## Module Matrix

| Module | Mode | Code Status | Test Status | Real Status | Notes |
|---|---|---|---|---|---|
| M1 | Focused Acquisition | implemented | real tested | REAL_E2E_VERIFIED | 窄 query 真实链路通过 |
| M1 | Direction Exploration | not implemented | — | DOC_DESIGNED, NOT_IMPLEMENTED | 宽 query 方向框架文档已设计，代码未实现 |
| M1 | Seed Paper Expansion | not implemented | — | DOC_DESIGNED, NOT_IMPLEMENTED | seed paper 扩展文档已设计，代码未实现 |
| M1 | Source-aware acquisition (LaTeX/HTML priority) | implemented | unit tested | IMPLEMENTED | LaTeX/HTML/PDF source priority 已实现，arXiv source 下载已实现，PDF fallback 已实现 |
| M1 | canonical_paper.md pipeline | implemented | unit tested | PARTIAL_REAL_E2E_VERIFIED | MinerU2.5-Pro primary route verified with two unseen papers; Marker fallback retained for audit |
| M1 | MarkItDownAdapter (fallback) | implemented | live tested | IMPLEMENTED | markitdown 已安装 (MIT)，fallback/debug only，不是主线 |
| M1 | MarkerPdfAdapter (fallback) | implemented | live tested | IMPLEMENTED | marker-pdf 已安装 (GPL-3.0)，fallback/audit baseline |
| M1 | MinerU25ProAdapter (PRIMARY) | implemented | unit tested + real two-paper acceptance | REAL_E2E_VERIFIED | MinerU2.5-Pro via mineru-vl-utils is the primary M1 parser; two unseen papers (DDMT, TPIDM) passed in `reports/m1_canonical_acceptance/` |
| M1 | OllamaSectionRefiner | implemented | unit tested + local compare | OPTIONAL_REFINER_NOT_DEFAULT | Ollama is an optional structured refiner, default OFF; must not modify latex/bbox/page/source |
| M1 | RuleBasedStructureRefiner | implemented | unit tested | IMPLEMENTED | Always runs; assigns sections, normalizes headings, detects risks |
| M1 | M1 Quality Gate | implemented | unit tested + acceptance enforced | IMPLEMENTED, REAL_E2E_VERIFIED | Blocks: all-formulas-in-Abstract, section contradiction, source/title mismatch, missing latex/crop/overlay, dense raw-only formulas |
| M1 | MarkerDocumentFormulaDetector | implemented | unit tested | IMPLEMENTED | 使用 Marker build_document() 获取 Equation blocks with bbox，输出 FormulaSlot 列表 |
| M1 | FormulaCropper | implemented | unit tested | IMPLEMENTED | PyMuPDF crop with padding，bbox in PDF points，输出 cropped formula images |
| M1 | FormulaRegionDetector | superseded | — | SUPERSEDED | 已被 MinerU25ProAdapter (primary) 和 MarkerDocumentFormulaDetector (fallback) 取代 |
| M1 | FormulaOCRAdapter / pix2tex | interface exists | — | FALLBACK_ONLY | pix2tex adapter 接口存在但模型未集成；仅作为 unresolved formula crops 的 fallback，不是默认主线 |
| M1 | DeepXiv | — | — | BLOCKED | pip 包不存在，无确认的公开 API |
| M1 | Overall | implemented | unit tested | PARTIAL_REAL_E2E_VERIFIED | Focused acquisition 通过，source-aware 和 canonical_paper.md 已实现，direction / seed 尚未实现 |
| M2 | Paper Deep Reading | partial code exists | structural tests exist, not completion | NOT_REAL_E2E_VERIFIED | 文档存在，部分代码存在，结构性测试不能替代验收；真实 PDF + 真实 LLM + 真实 audit e2e 尚未验证 |
| M2 | canonical input reader / validator | not implemented | — | DOC_DESIGNED, NOT_IMPLEMENTED | M2.1 读取并校验 canonical_paper.md、转换 evidence-ready blocks，代码未实现 |
| M2 | formula_origin full chain | not implemented | — | DOC_DESIGNED, NOT_IMPLEMENTED | source_latex/parser_latex/ocr_latex/reconstructed/unknown 规则已设计，端到端未实现 |
| M2 | LaTeXSourceParser | not implemented | — | DOC_DESIGNED, NOT_IMPLEMENTED | 职责前移到 M1 material normalization，文档已设计，代码未实现 |
| M2 | MinerUAdapter / MarkerAdapter / DoclingAdapter | not implemented | — | DOC_DESIGNED, NOT_IMPLEMENTED | 作为 M1 normalization 候选 adapter 评估，代码未实现 |
| M2 | Source-aware parser selection | not implemented | — | DOC_DESIGNED, NOT_IMPLEMENTED | 职责调整为 M1 source/material selection，M2 不直接处理混乱原始输入 |
| M2 | Survey Deep Reading | not implemented | — | DOC_DESIGNED, NOT_IMPLEMENTED | 综述论文精读文档已设计，代码未实现 |
| M3 | PaperWorkspace | partial API/frontend code | component tests | PARTIAL_CODE_NOT_REAL_VALIDATED | 部分 API/前端代码存在，StatusBanner 测试存在，页面级真实后端验证缺失 |
| M3 | DirectionWorkspace | not implemented | — | DOC_DESIGNED, NOT_IMPLEMENTED | 文档已设计，代码未实现 |
| M3 | SeedExpansionPanel | not implemented | — | DOC_DESIGNED, NOT_IMPLEMENTED | 文档已设计，代码未实现 |
| M4 | Interactive Learning | not implemented | — | DOC_DESIGNED, NOT_IMPLEMENTED | 文档已设计，schema 为候选设计，API / memory / retrieval / 前端集成未实现 |
| M5 | Reliability | partial infra | — | PARTIAL_INFRA, NOT_PRODUCTION_READY | 真实验收规则已文档化，live eval 基础设施部分存在，secret scan / CI / debug/admin 生产鉴权未实现 |

## M1 Focused Acquisition Live Result (2026-06-05, HEAD fc7d494)

Focused query: "时间序列异常检测 transformer 方法"

- sources_success: arXiv / OpenAlex / Crossref (3 sources). Semantic Scholar rate limited (429).
- candidate_count: 10
- verified_candidate_count: 10
- verify_pending_count: 0
- pdf_download_success_count: 2
- A_READ_FOR_M2: 2
- All A_READ have: `verification_status == verified`, `llm_relevance_score >= 0.65`, `llm_relevance_label in {HIGH, MEDIUM}`, `should_a_read == true`, `pdf_downloaded == true`, `pdf_metadata_check == passed`, `pdf_title_match == match`, `can_enter_m2 == true`
- A_READ papers:
  1. Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT (verified via crossref_doi_lookup, llm_relevance=HIGH)
  2. Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy (verified via s2_title_search, llm_relevance=HIGH)
- Classification paper "Improving position encoding of transformers for multivariate time series classification" was excluded from A_READ by LLM relevance judge
- LLM: mimo-v2.5-pro, 3265 tokens (3 calls: query planning + relevance judge)

## M1 Canonical Acceptance (2026-06-10)

Report path: `reports/m1_canonical_acceptance/`

Pipeline: MinerU2.5-Pro via mineru-vl-utils → CanonicalDocumentBlock → RuleBasedStructureRefiner → optional OllamaSectionRefiner → CanonicalBuilder → M1QualityGate → visual audit.

### Acceptance Samples

| Paper | arXiv | Status | Formulas | Body | Ref | LaTeX | Crops | Overlays | High Risk | M2 Ready |
|-------|-------|--------|----------|------|-----|-------|-------|----------|-----------|----------|
| DDMT | 2310.08800 | PASS | 7 | 7 | 0 | 7 | 7 | 7 | 0 | true |
| TPIDM | 2508.11528 | PASS | 17 | 12 | 5 | 17 | 17 | 17 | 0 | true |

Both papers: primary_parser=mineru25pro, fallback=false, title_ok=true, all criteria PASS.

### Ollama Status

- OllamaSectionRefiner: optional, default OFF.
- qwen2.5:0.5b: not recommended (timeout/unstable on real FormulaSlot prompts).
- qwen2.5:7b-instruct: passed native `/api/chat` + JSON Schema real_slot smoke (JSON valid=YES, 3-11s latency).
- Ollama may only modify section/context/risk fields; must not modify latex/bbox/page/source.
- Default remains OFF unless user configures a 7B+ model.

### Historical Notes

Old Marker/MarkItDown/PyMuPDF fallback experiments have been cleaned. Only the primary MinerU2.5-Pro acceptance above is the formal M1 acceptance evidence.

## Current verified PDF-only A_READ Gate

当前已真实验证的 Focused Acquisition gate 是 PDF-only gate。它证明系统能完成窄 query 的多源检索、候选验证、LLM 相关性判断和 PDF 下载校验；它不是目标态 M1→M2 `canonical_paper.md` 契约。

Every current PDF-only A_READ must satisfy ALL:

- `verification_status == verified`
- `scoring_breakdown.relevance_score >= 0.45` (rule-based)
- `llm_relevance_score >= 0.65` (LLM-based)
- `llm_relevance_label in {HIGH, MEDIUM}`
- `should_a_read == true`
- `pdf_downloaded == true`
- `can_enter_m2 == true`
- `pdf_metadata_check == passed`
- `pdf_title_match == match`
- `source_confidence >= medium`
- `metadata_confidence >= medium`
- `role != IRRELEVANT`

## Target canonical A_READ_FOR_M2 Gate

目标态 `A_READ_FOR_M2` 必须通过 canonical gate 后才能进入 M2 deep reading。该 gate 目前为 DOC_DESIGNED / NOT_IMPLEMENTED。

Every target canonical A_READ_FOR_M2 must satisfy ALL:

- `verification_status == verified`
- `scoring_breakdown.relevance_score >= 0.45` (rule-based)
- `llm_relevance_score >= 0.65` (LLM-based)
- `llm_relevance_label in {HIGH, MEDIUM}`
- `should_a_read == true`
- `source_type != metadata_only`
- `source_confidence >= medium`
- `metadata_confidence >= medium`
- `role != IRRELEVANT`
- `canonical_paper.md exists`
- `canonicalization_status in {success, degraded}`
- `m2_ready == true`
- `degradation_reason` is empty or explicitly acceptable for M2 evidence-only/degraded mode

## Hard Rules

- mock/fake/skip 不是模块完成依据。全项目测试策略：真实优先。
- `python -m pytest -q` 默认运行稳定小样本真实链路。
- manual / nightly live validation 覆盖联网、真实 LLM、OCR/parser heavy cases。
- live validation 中缺 key / 缺网络 / 额度不足 / API 限流 / PDF 下载失败 = 测试失败，不能汇报为通过。
- MockLLMClient 已从 src/ 和 tests/ 中删除。
- M2 mock 测试已删除。M2 必须真实 PDF + 真实 LLM 验收。
- API keys, `.env`, reports, downloaded PDFs, and large generated files must not be committed.
- M1 focused acquisition is complete only if live validation shows real LLM query planning, at least one mature source success, real candidate metadata, at least one valid deep-reading source download, and at least one A_READ item that passes the strict gate above. Current verified implementation uses PDF-only path; LaTeX/HTML source priority is designed but not yet implemented.
- 当前已实现能力包含：source-aware acquisition（LaTeX/HTML/PDF priority）、M1 canonical pipeline（MinerU25ProAdapter → RuleBasedStructureRefiner → optional OllamaSectionRefiner → CanonicalBuilder → M1QualityGate → visual audit）、MaterialNormalizer（fallback/debug）、MarkerDocumentFormulaDetector、FormulaCropper、A_READ canonical gate、section inference (nearby_text heading detection)。
- 当前未实现能力包含：M2 canonical input reader；M1 MinerU primary route 已有两篇 unseen multi-paper acceptance report，可作为 M2.1 canonical input contract 的上游样本。
- MinerU2.5-Pro via mineru-vl-utils is the primary M1 parser。Marker is fallback/audit baseline。PyMuPDF/MarkItDown are lightweight fallback/debug。
- Ollama is an optional structured refiner, default OFF。Ollama must not modify latex, bbox, page, or source identity。
- M1 gate blocks: all-formulas-in-Abstract, section contradiction, source/title mismatch, missing latex/crop/overlay, dense raw-only formulas from formula understanding.
- References formulas are excluded from formula understanding (formula_m2_ready=false).
- FormulaOCRAdapter 接口存在但模型未集成，仅作为 unresolved formula crops 的 fallback。
- MarkerDocumentFormulaDetector 使用 Marker build_document() 获取 Equation blocks with bbox，已实现并测试。
- FormulaCropper 使用 PyMuPDF crop formula regions，已实现并测试。
- M1 direction exploration and seed paper expansion are NOT complete.

## External Reference Boundary

ARIS (`wanshuiyin/Auto-claude-code-research-in-sleep`) is one external reference, not a runtime dependency, not a replacement architecture, and not the only source of design ideas. ResearchSensei remains an independent product with its own module boundaries, schemas, artifacts, gates, APIs, frontend, and validation rules.

| Module | ARIS overlap | Reference use | ResearchSensei-owned boundary |
|---|---|---|---|
| M1 | High | STRATEGY_BORROW | Search remains best-of-breed. ARIS only informs verification, source discipline, and download discipline. |
| M2 | Medium-High | STRATEGY_BORROW | Parser, evidence_ref, formula_card, QualityAuditor, and artifacts remain ResearchSensei-owned. |
| M3 | Low code, medium schema | STRATEGY_BORROW | No ARIS UI dependency. Only source/relevance/verification display concepts are referenced. |
| M4 | High for advisor/memory, low for formula UI | STRATEGY_BORROW | M4 remains a paper-learning interaction module. ARIS informs advisor/review/memory patterns only. |
| M5 | Medium | STRATEGY_BORROW | Run discipline can be referenced. ResearchSensei keeps stricter real-test policy. |

Other external projects remain open for evaluation. For example, M2 parser quality may require Docling / Marker / DeepXiv; M4 formula teaching may require a different specialized reference. ARIS must not block evaluation of better-fit projects.

Implementation tasks must read the matching module's External Reference Implementation Notes before coding. External references constrain specific strategies only; they do not replace ResearchSensei-owned schemas, artifacts, gates, tests, or product boundaries.
