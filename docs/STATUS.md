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
| M1 | canonical_paper.md pipeline | implemented | unit tested + M1/M2 contract tested | PARTIAL_REAL_E2E_VERIFIED | M1 canonical artifacts are M2-readable; MinerU route is verified on paper_4 only, multi-paper MinerU acceptance remains pending; fallback reports are audit/debug only |
| M1 | MarkItDownAdapter (fallback) | implemented | live tested | IMPLEMENTED | markitdown 已安装 (MIT)，fallback/debug only，不是主线 |
| M1 | MarkerPdfAdapter (fallback) | implemented | live tested | IMPLEMENTED | marker-pdf 已安装 (GPL-3.0)，fallback/audit baseline |
| M1 | MinerU25ProAdapter (PRIMARY) | implemented | unit tested + paper_4 real acceptance | PARTIAL_REAL_E2E_VERIFIED | MinerU2.5-Pro via mineru-vl-utils is the primary M1 parser candidate; verified on paper_4 only, multi-paper MinerU acceptance remains pending |
| M1 | OllamaSectionRefiner | implemented | unit tested + local compare | OPTIONAL_REFINER_NOT_DEFAULT | Ollama is an optional structured refiner, default OFF; must not modify latex/bbox/page/source |
| M1 | RuleBasedStructureRefiner | implemented | unit tested | IMPLEMENTED | Always runs; assigns sections, normalizes headings, detects risks |
| M1 | M1 Quality Gate | implemented | unit tested + acceptance enforced | IMPLEMENTED, REAL_E2E_VERIFIED | Blocks: all-formulas-in-Abstract, section contradiction, source/title mismatch, missing latex/crop/overlay, dense raw-only formulas |
| M1 | MarkerDocumentFormulaDetector | implemented | unit tested | IMPLEMENTED | 使用 Marker build_document() 获取 Equation blocks with bbox，输出 FormulaSlot 列表 |
| M1 | FormulaCropper | implemented | unit tested | IMPLEMENTED | PyMuPDF crop with padding，bbox in PDF points，输出 cropped formula images |
| M1 | FormulaRegionDetector | superseded | — | SUPERSEDED | 已被 MinerU25ProAdapter (primary) 和 MarkerDocumentFormulaDetector (fallback) 取代 |
| M1 | FormulaOCRAdapter / pix2tex | interface exists | — | FALLBACK_ONLY | pix2tex adapter 接口存在但模型未集成；仅作为 unresolved formula crops 的 fallback，不是默认主线 |
| M1 | DeepXiv | — | — | BLOCKED | pip 包不存在，无确认的公开 API |
| M1 | Overall | implemented | unit tested | PARTIAL_REAL_E2E_VERIFIED | Focused acquisition 通过，source-aware 和 canonical_paper.md 已实现，direction / seed 尚未实现 |
| M2 | Paper Deep Reading | implemented | unit tested + real M1/M2 e2e | REAL_E2E_VERIFIED_ON_ONE_PAPER | `2312_01729v1` completed M1 canonical handoff + real Mimo LLM + QualityAuditor with SUCCESS; all-formula derivation remains pending |
| M2 | canonical input reader / validator | implemented | unit tested + real M1/M2 e2e | IMPLEMENTED | M2 reads current M1 canonical bundle and builds parsed document, passages, claims, evidence pack, and status artifacts |
| M2 | formula_origin full chain | implemented | unit tested + real M1/M2 e2e | IMPLEMENTED_FOR_TOP_K | formula_origin / formula_ocr_status / original_latex are propagated to formula cards; detailed derivation is top-K only |
| M2 | LaTeXSourceParser | not implemented | — | DOC_DESIGNED, NOT_IMPLEMENTED | 职责前移到 M1 material normalization，文档已设计，代码未实现 |
| M2 | MinerUAdapter / MarkerAdapter / DoclingAdapter | not implemented | — | DOC_DESIGNED, NOT_IMPLEMENTED | 作为 M1 normalization 候选 adapter 评估，代码未实现 |
| M2 | Source-aware parser selection | not implemented | — | DOC_DESIGNED, NOT_IMPLEMENTED | 职责调整为 M1 source/material selection，M2 不直接处理混乱原始输入 |
| M2 | Survey Deep Reading | implemented | unit tested + pipeline artifact tested | IMPLEMENTED_RULE_BASED, LIVE_PENDING | Writes evidence-bound survey_status, survey_landscape, method_taxonomy, extracted_key_papers, survey_claims; real survey PDF live acceptance remains pending |
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

### Historical Acceptance Samples

| Paper | arXiv | Status | Formulas | Body | Ref | LaTeX | Crops | Overlays | High Risk | M2 Ready |
|-------|-------|--------|----------|------|-----|-------|-------|----------|-----------|----------|
| DDMT | 2310.08800 | PASS | 7 | 7 | 0 | 7 | 7 | 7 | 0 | true |
| TPIDM | 2508.11528 | PASS | 17 | 12 | 5 | 17 | 17 | 17 | 0 | true |

These rows are historical report snapshots. Current audit shows the stored DDMT/TPIDM artifacts are stale for the M2 contract (missing current metadata/performance/quality files and formula slot fields), so they must not be used as formal multi-paper MinerU acceptance evidence until regenerated with current M1.

Current formal statement: M1 canonical artifacts are M2-readable when generated with the current pipeline, crop/overlay review is enforced, dense raw-only formula outputs are blocked/degraded for formula understanding, and the primary MinerU route remains verified on paper_4 only. Multi-paper MinerU acceptance remains pending.

### Ollama Status

- OllamaSectionRefiner: optional, default OFF.
- qwen2.5:0.5b: not recommended (timeout/unstable on real FormulaSlot prompts).
- qwen2.5:7b-instruct: passed native `/api/chat` + JSON Schema real_slot smoke (JSON valid=YES, 3-11s latency).
- OllamaSectionRefiner may only modify section/context/risk fields and must not modify latex/bbox/page/source. Ollama formula polish is a separate explicit path that may update `final_latex` only after crop-based validation and guard checks.
- Default remains OFF unless user configures a 7B+ model.

### Historical Notes

Marker/MarkItDown/PyMuPDF fallback experiments are allowed as review/debug artifacts only. They do not prove the primary MinerU route is stable.

## M2 Rule-Based Understanding Start (2026-06-11)

Implemented M2 artifact path:

- code: `src/researchsensei/m2/`
- CLI: `scripts/m2_run_understanding.py`
- report: `reports/m2_understanding_2510_18998/`

Current M2 mode is deterministic/rule-based and evidence-bounded. It reads only M1 artifacts (`canonical_paper.md`, `document_blocks.json`, `formula_slots.json`, `formula_slots.md`, `paper_metadata.json`, `quality_report.md`, `performance_report.json`, `visual_audit/`) and writes M2 artifacts to a separate report directory. It does not read raw PDF, does not run a parser, and does not modify M1 latex/bbox/page/source/crop/overlay identity.

Generated outputs:

- `m2_paper_understanding.md`
- `m2_formula_understanding.json`
- `m2_formula_understanding.md`
- `m2_method_graph.json`
- `m2_source_trace.json`
- `m2_risk_report.md`
- `m2_run_summary.json`

M2 formula understanding uses `equation_group_id`, `group_order`, `group_crop_path`, `final_latex`, `nearby_text_before`, `nearby_text_after`, `risk_flags`, `final_origin`, and `block_source`. If a formula has `m2_ready=false` or no `final_latex`, M2 skips deep explanation and records the reason. Crop/group/source risk flags lower confidence; nearby_text gaps are reported as `unknown`.

## M1 Target-Mode Eval (2026-06-11)

Implemented target-mode generalization check:

- script: `scripts/m1_target_mode_eval.py`
- report: `reports/m1_target_mode_eval/`
- default: metadata/static checks only; full MinerU is disabled
- live eval: not run by default; page-level parse limitation is recorded instead of being treated as tested

Current run found two new unseen candidates:

- `2312.01729` EdgeConvFormer: Dynamic Graph CNN and Transformer based Anomaly Detection in Multivariate Time Series
- `1610.06761` Maximally Divergent Intervals for Anomaly Detection

Static checks cover candidate exclusion, formula_slots schema, final_latex, equation group fields, nearby_text, crop/overlay path existence, reference formula exclusion, performance WARNING wording, and production hardcode detection. This target-mode run reduces overfit risk, but it is not proof that M1 perfectly generalizes and it does not promote the performance gate from WARNING to PASS.

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

目标态 `A_READ_FOR_M2` 必须通过 canonical gate 后才能进入 M2 deep reading。该 gate 已在当前 M1 canonical pipeline 与 M2 reader 中实现，并在 `2312_01729v1` 上完成真实 M1->M2 验证；多论文 MinerU acceptance 仍 pending。

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
- 当前未实现能力包含：M2 all-formula advanced derivation、M1 direction exploration、M1 seed paper expansion；M2 survey deep reading 已有规则版证据链路但真实 survey PDF live acceptance 仍 pending；M1 MinerU primary route 的 multi-paper acceptance 仍 pending。
- MinerU2.5-Pro via mineru-vl-utils is the primary M1 parser。Marker is fallback/audit baseline。PyMuPDF/MarkItDown are lightweight fallback/debug。
- OllamaSectionRefiner is optional/default OFF and must not modify latex, bbox, page, or source identity. Ollama formula polish is a separate explicit path for guarded `final_latex` cleanup only.
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

## 2026-06-13 M1 Ollama Formula Polish

Ollama section refinement and Ollama formula LaTeX polish are separate paths. Section refinement remains optional/default-off and is not part of the formal M1->M2 handoff path. Formula polish is enabled explicitly with `--enable-ollama-latex` and runs after MinerU plus deterministic regex cleanup, before M2 consumes canonical artifacts. The formula path checks that the configured Ollama model exists and advertises vision capability, prefers group crops over individual crops as visual context only, sends `think=false`, requires JSON schema output and confidence >= 0.8 by default, preserves page/bbox/crop/overlay/source identity, restores original equation tags if the model drops them, and rejects low-confidence, malformed, over-expanded, or left-hand-side-mismatched outputs.

Local `qwen3.5:4b` smoke on `reports/m1_acceptance_manual_review_2510_18998` checked five real formula crops. Accepted: `formula_004`, `formula_018`, `formula_025` after deterministic cleanup. Rejected/unchanged: `formula_009` because group context returned the wrong left-hand side (`Q` instead of original `S`), and `formula_016` because the model returned malformed JSON. A full MinerU reparse acceptance with Ollama is a heavy/review run and must not be treated as a default live eval.

## 2026-06-14 M1 -> M2 Canonical Verification

Current clean verification used `2312_01729v1` (`EdgeConvFormer: Dynamic Graph CNN and Transformer based Anomaly Detection in Multivariate Time Series`).

- M1 command: `python scripts/run_m1_v2_mineru_primary_acceptance.py --limit 1 --keys 2312_01729v1 --force --enable-ollama-latex --ollama-latex-model qwen3.5:4b --ollama-timeout 30`.
- M1 output: `reports/m1_canonical_acceptance/2312_01729v1`.
- M1 status: PASS, `m2_ready=true`, `m2_ready_for_formula_understanding=true`, primary parser `mineru25pro`, fallback `false`.
- M1 formula status: 19 formula blocks, 19 parser LaTeX, 0 raw-only formulas, 19 bbox/crop/overlay/canonical matches, 0 high-risk formulas.
- M1 structural status: no page header/footer contamination in canonical output, no `## Unknown`, no reference pollution in Introduction/Method/Experiments, PDF-token presence check about 0.95 against PyMuPDF text extraction.
- M1 visual audit: sampled PDF pages and formula overlays/crops for Time2Vec, EdgeConv, attention, anomaly score, and metric formulas; sampled crop/overlay boxes matched the original PDF.
- M1 LaTeX cleanup: deterministic postprocessing now runs both before and after guarded Ollama formula validation, so Ollama cannot reintroduce `$...$` wrappers or over-escaped norm delimiters into final formula slots.
- M2 command: `python scripts/m2_run_understanding.py --mode full --enable-llm --provider mimo --input-dir reports/m1_canonical_acceptance/2312_01729v1 --output-dir reports/m2_full_2312_01729v1_mimo --llm-timeout 90`.
- M2 output: `reports/m2_full_2312_01729v1_mimo`.
- M2 status: SUCCESS, audit findings empty, M1 artifacts unmodified, real Mimo provider `mimo-v2.5-pro`, 3 LLM calls, 8011 total tokens after survey-artifact rerun.
- M2 artifacts generated: `parsed_document.json`, `passage_index.json`, `claim_evidence.json`, `evidence_index.json`, `paper_skeleton.json`, `evidence_pack.json`, `paper_card.json`, `formula_cards.json`, `teaching_cards.json`, `quality_report.json`, `understanding_status.json`.
- Limitation: M2 formula explanation currently generates top-K formula cards, not full derivations for all 19 formulas. This is sufficient for canonical M1->M2 handoff validation but not final "all formulas advanced math reasoning" completion.
- Scope not proven by this run: multi-paper MinerU acceptance, real survey-paper live acceptance, and frontend/M3/M4/M5 integration.

## 2026-06-14 M2 Audit and Formula Top-K Update

- QualityAuditor now implements F-8/F-9/F-10/F-13/F-14/F-15/F-16 plus core Formula Source Audit checks for parser provenance, source_latex/raw mismatch, OCR failure visibility, section contradiction, Abstract formula overload, fallback provenance, and Llama/Ollama provenance.
- EvidencePack formula selection is no longer input-order based. Formula contexts are ranked by formula shape, section/claim context, core method keywords, and helper-line demotion; real `2312_01729v1` M2 selected Attention, MultiHead attention, Gaussian kernel, final anomaly score, and dynamic Gaussian score context.
- Deterministic M1 LaTeX postprocessing additionally normalizes OCR-spaced `w h e r e` to `where`, including a post-Ollama cleanup pass so guarded formula polish cannot reintroduce wrapped or malformed LaTeX.
- Validation after this change: `python -m pytest -q` passed with 421 passed, 15 skipped; real M1 rerun on cached MinerU pages remained PASS; real M2 Mimo rerun remained SUCCESS with no audit findings.

## 2026-06-14 M2 Survey Artifact Update

- Added rule-based survey/review support inside M2 full pipeline. The pipeline now writes `survey_status.json`, `survey_landscape.json`, `method_taxonomy.json`, `extracted_key_papers.json`, and `survey_claims.json` for every run.
- Non-survey papers are explicitly marked `survey_status=NOT_APPLICABLE`; survey/review papers are detected from title/abstract survey signals and only produce trusted landscape output when taxonomy evidence exists.
- Survey artifacts are evidence-bound: taxonomy entries, extracted key papers, and survey claims carry `evidence_ref` and `passage_id`; QualityAuditor blocks untraceable survey entries (`S-1`/`S-2`/`S-3`).
- Current validation is unit/pipeline fixture based. A real survey PDF live acceptance run is still required before claiming broad survey-paper quality.
