# ResearchSensei Module Contracts

每个模块只负责一个任务，通过 JSON/Pydantic 契约交互。所有模块输出应包含可追踪 artifact，失败时返回明确 warnings 或降级状态。

## query
Input: `{"user_query": "...", "language": "zh|en|auto"}`
Output: `QueryPlan`，包含 `direction_zh`、`direction_en`、`core_terms`、`related_terms`、`exclude_terms`、枚举化 `search_intents`、跨领域标记。
Errors: 无法理解方向时返回 BACKGROUND_KNOWLEDGE intent。
Dependencies: none / optional LLM later.
Boundary: 不搜索论文，不筛选论文。
Acceptance: search_intents 必须来自封闭枚举。

## acquisition
Input: `QueryPlan`
Output: `CandidatePaper[]` with metadata, retrieval sources, raw relevance reason.
Errors: Adapter failure recorded per source.
Dependencies: paper-search-mcp, arXiv, OpenAlex, Semantic Scholar, Crossref, Papers With Code.
Boundary: 不决定 A_READ，不生成卡片。
Acceptance: 搜索结果必须先交给 selection。

## selection
Input: candidate pool.
Output: `ReadingPlan` with `ReadingPlanItem`, `scoring_breakdown`, reason, risk note.
Errors: metadata missing lowers confidence, not fatal.
Dependencies: venue/citation/code hints.
Boundary: 不下载全文，不讲解论文。
Acceptance: D_IGNORE 不进入深读，survey 不当 baseline，A_READ 默认不超过 12。

## source_resolver
Input: A_READ `CandidatePaper`.
Output: `SourceStatus` and local source path/status.
Errors: `ABSTRACT_ONLY`, `FULL_TEXT_MISSING`, `FORMULA_UNAVAILABLE`.
Dependencies: arXiv source/PDF, OA PDF, publisher PDF, user upload.
Boundary: 不解析正文。
Acceptance: 缺全文时禁止深度公式讲解。

## ingestion
Input: LaTeX/PDF/HTML/Markdown/text source.
Output: `DocumentIngestion` with sections, formulas, figures, tables, references, extraction warnings, `blocks`.
Errors: unsafe command or low extraction quality becomes warning/degraded mode.
Dependencies: safe LaTeX parser, Docling/Marker/MinerU/GROBID/PyMuPDF.
Boundary: 不解释论文，不判断 claim。
Acceptance: every block has `block_id`, `type`, `section`, `evidence_ref`.

## grounding
Input: `DocumentIngestion`
Output: `EvidenceIndex` with evidence type, quote/summary, confidence.
Errors: evidence not found becomes INSUFFICIENT_EVIDENCE.
Dependencies: optional PaperQA2/RAG.
Boundary: 不教学化表达。
Acceptance: claims never lose evidence status.

## understanding
Input: `DocumentIngestion`, `EvidenceIndex`
Output: `PaperSkeleton`.
Errors: missing method/experiments becomes explicit limitation.
Dependencies: LLM/prompt builder later.
Boundary: 不渲染 cards.
Acceptance: includes Problem, Old Methods, Bottleneck, Assumption, Representation, Mechanism, Objective, Evidence, Limitation, Transfer.

## teaching
Input: `PaperSkeleton`.
Output: `TeachingCard`.
Errors: unsupported claim marked UNVERIFIED.
Dependencies: LLM.
Boundary: 不 retrieve evidence itself.
Acceptance: uses five-layer explanation style and Chinese-first output.

## formula
Input: formula block and nearby text.
Output: `FormulaCard`.
Errors: missing nearby context marks NEEDS_HUMAN_CHECK.
Dependencies: optional SymPy/MathJax/KaTeX.
Boundary: 不 invent derivation.
Acceptance: includes symbols, numeric example, remove effect, weight effect.

## direction
Input: `ReadingPlan`.
Output: method evolution chain and direction map.
Errors: insufficient A_READ returns a degraded route.
Dependencies: selection.
Boundary: 不 search.
Acceptance: not a random list; role-based evolution.

## patterns
Input: `PaperSkeleton`.
Output: `PatternCard`.
Errors: ambiguous pattern produces candidates and manual check.
Dependencies: Research Pattern Library.
Boundary: 不 score paper quality.
Acceptance: pattern classification supports transfer.

## drill
Input: cards/skeleton/memory.
Output: `DrillCard`.
Errors: weak evidence produces evidence-check questions.
Dependencies: optional FSRS.
Boundary: 不 schedule without review adapter.
Acceptance: includes recall, review, advisor questions, error attribution.

## interactive
Input: `InteractiveContextPackage`.
Output: contextual answer and optional review-card suggestion.
Errors: missing context returns clarification/degraded answer.
Dependencies: context, llm.
Boundary: never sends only raw user question.
Acceptance: answer knows current card and selected text.

## context
Input: session state, current card, selected text, user question.
Output: compact context package.
Errors: missing session starts cold memory.
Dependencies: memory store, retrieval cache.
Boundary: does not call model.
Acceptance: no full paper in prompt; includes evidence chunks and history summary.

## llm
Input: task request and prompt package.
Output: model response with token/cost/log metadata.
Errors: timeout/retry/key missing.
Dependencies: DeepSeek/MiMo/OpenAI-compatible/local model.
Boundary: no product logic.
Acceptance: API key never logged; supports task-specific model config.

## render
Input: cards and reading plans.
Output: HTML/Markdown/JSON artifacts.
Errors: missing card field fails validation.
Dependencies: Jinja2/HTMX/MathJax or KaTeX.
Boundary: no content generation.
Acceptance: pages include 30秒/5分钟/深挖/证据状态/追问入口.
