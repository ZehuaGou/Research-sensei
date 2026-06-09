# M1 Literature Search, Source Acquisition, And Reading Plan

## Goal

M1 has three modes:

**Direction Exploration Mode**: Given a broad research direction, search for surveys first, then build a direction framework with method families, chronology stages, landscape anchors, and recommended reading order.

**Focused Acquisition Mode**: Given a narrow query / title / DOI / URL / arXiv ID, find verified + relevant papers, resolve best available source, normalize raw material, and produce `canonical_paper.md` for M2.

**Seed Paper Expansion Mode**: Given a seed paper (already read or being read), find upstream papers, downstream papers, related surveys, follow-up improvements, and build a local paper relation graph.

M1 does not teach the paper or generate paper/formula/drill cards. M1 does own material normalization: raw PDF / LaTeX / HTML / DeepXiv / parser output is converted into `canonical_paper.md`. M2.1 reads and validates that canonical input.

## Three Modes

### Direction Exploration Mode

Status: NOT_IMPLEMENTED

Input: research direction (e.g. "时间序列异常检测")

Behavior:
1. Search for high-quality surveys first
2. If no qualified survey found, execute staged multi-source search
3. Build direction framework

Output:
- `survey_candidates.json`
- `direction_landscape.json` — with `method_families`, `chronology_stages`, `landscape_anchors`, `representative_papers`, `recommended_reading_order`, `gaps_or_open_questions`
- `reading_plan.json`

`direction_landscape.json` does NOT replace `reading_plan.json`. `direction_landscape.json` serves direction understanding. `reading_plan.json` serves reading plan. `A_READ_FOR_M2` serves single-paper deep reading entry.

LandscapeAnchor serves direction understanding, not necessarily M2 entry. A LandscapeAnchor can temporarily lack a PDF.

### Focused Acquisition Mode

Status: PARTIAL_REAL_E2E_VERIFIED

Input: focused query / title / DOI / arXiv ID / URL

Pipeline:
```
user query
  -> real LLM query plan
  -> multi-source acquisition
  -> dedup
  -> verification
  -> LLM relevance judge
  -> quality ranking
  -> best available source resolution
  -> source download
  -> material normalization
  -> FormulaRegionDetector
  -> FormulaOCRAdapter if triggered by policy
  -> canonical_paper.md
  -> m2_ready gate
  -> reading_plan.json (A_READ_FOR_M2)
```

A_READ_FOR_M2 must satisfy ALL:
- `verification_status == verified`
- `llm_relevance_score >= 0.65`
- `llm_relevance_label in {HIGH, MEDIUM}`
- `should_a_read == true`
- `can_enter_m2 == true`
- `source_confidence in {high, medium}`
- `has_valid_deep_reading_source == true`

`has_valid_deep_reading_source` means one of:
1. `latex_source_downloaded == true` and `latex_main_file` exists
2. `structured_html_downloaded == true`
3. `pdf_downloaded == true` and `pdf_metadata_check == passed` and `pdf_title_match == match`

`metadata_only` cannot enter `A_READ_FOR_M2`.

Current implemented capability: PDF-focused focused acquisition live eval. DOC_DESIGNED / NOT_IMPLEMENTED capabilities: `canonical_paper.md` pipeline, material normalization, FormulaRegionDetector, FormulaOCRAdapter, MinerU/Marker/DeepXiv structured adapters, formula_origin full chain.

### Seed Paper Expansion Mode

Status: NOT_IMPLEMENTED

Input: seed paper metadata / paper_id / uploaded paper

Behavior:
1. Find citing papers, cited papers, related surveys, same-route papers, follow-up improvements
2. Build local paper relation graph

Output:
- `paper_relation_graph.json`
- `seed_expansion_result.json`

## Non-Negotiable Requirements

- Query planning requires a real LLM. No heuristic fallback is allowed for M1 completion.
- Search/acquisition must use mature projects or official clients through adapters.
- Thin/wrapper-style HTTP implementations without User-Agent, retry, rate-limit detection, and structured diagnostics are not allowed. arXiv uses a robust official endpoint adapter (ARIS-style) with full diagnostic discipline. OpenAlex uses `pyalex`. Semantic Scholar uses official REST API via httpx with proxy support. Crossref uses `habanero`.
- A_READ papers must be cleared for M2. Valid deep-reading source is required to enter M2: LaTeX source (preferred), structured HTML/XML/DeepXiv structured output, or validated PDF parser output. Current verified implementation uses PDF-only path; canonical material normalization is DOC_DESIGNED / NOT_IMPLEMENTED.
- M1 must produce `canonical_paper.md` before M2. `metadata_only` cannot enter M2. A raw PDF cannot bypass M1 canonicalization.
- Formula parsing, formula region detection, pix2tex/LaTeX-OCR, MinerU, Marker, and DeepXiv structured adapters are formal architecture components. They are adapter-based, status-gated, and policy-triggered; they are not default full-batch operations.
- M1 tests must run with real LLM, real network, real PDF download. Missing env/key/network = failure, not skip.
- `python -m pytest -q` must include tests_live. No more `--ignore=tests_live`.
- Mock/fake/skip are not valid test outcomes for M1.

## Reused Components

## External Projects / Adapter Candidates

| 项目 | 对应模块 | 具体能力 | 可复用文件/函数/CLI | 接入方式 | 是否默认依赖 | 风险 | 当前状态 |
|---|---|---|---|---|---|---|---|
| ARIS / Auto-claude-code-research-in-sleep | M1.1-M1.5 | 科研自动化 workflow、文献搜索流程、verify_papers 三层验证、source diagnostics | `tools/arxiv_fetch.py`, `tools/semantic_scholar_fetch.py`, `tools/openalex_fetch.py`, `tools/deepxiv_fetch.py`, `tools/verify_papers.py`, `skills/research-lit/SKILL.md` | STRATEGY_BORROW | 否 | 不能把 ResearchSensei 改成 ARIS clone；只能借鉴流程、字段、失败处理 | DOC_DESIGNED |
| ARIS verify_papers | M1.4 | arXiv ID / Crossref DOI / Semantic Scholar fuzzy title 三层验证 | `tools/verify_papers.py` | OPTIONAL_ADAPTER | 否 | 需适配 ResearchSensei Candidate schema；不能直接采用 ARIS artifact | RESEARCH_REQUIRED |
| DeepXiv / deepxiv_sdk | M1.3 material normalization | arXiv 搜索、brief、head、section、raw markdown、structured JSON、progressive reading | `deepxiv_sdk/reader.py`, `deepxiv_sdk/cli.py`; 必须调研 reader 输出字段、CLI 参数、raw/json 格式 | OPTIONAL_ADAPTER | 否 | 不能作为唯一正式发表论文来源；不负责顶会顶刊质量判断；不保证 formula source fidelity | RESEARCH_REQUIRED |
| Semantic Scholar | M1.2 / M1.4 | 正式发表论文、venue、citation、publicationTypes、openAccessPdf、fieldsOfStudy | Official Graph API `/graph/v1/paper/search`, `/graph/v1/paper/{id}`; existing `SemanticScholarAdapter` | DIRECT_DEPENDENCY | 是 | 免费层限流；API key 可选；字段缺失需要降级 | IMPLEMENTED |
| OpenAlex | M1.2 / M1.4 | venue、OA URL、citation、topics、concepts、institution、metadata | `pyalex.Works`, inverted abstract reconstruction; existing `OpenAlexAdapter` | DIRECT_DEPENDENCY | 是 | topic/venue 字段需归一化；不是唯一质量源 | IMPLEMENTED |
| Crossref | M1.2 / M1.4 | DOI、publisher metadata、container-title、正式出版验证 | `habanero.Crossref.works`, DOI lookup; existing `CrossrefAdapter` | DIRECT_DEPENDENCY | 是 | 覆盖偏出版 metadata；不提供完整全文 | IMPLEMENTED |
| arXiv source/e-print | M1.3 source acquisition | LaTeX source / PDF 获取；preprint/source 获取 | arXiv API, e-print/source endpoint, PDF endpoint, existing `ArxivAdapter`; source adapter must inspect source package and main `.tex` | DIRECT_DEPENDENCY | 是 | arXiv 是 source/preprint 获取源，不是质量判断源；429/503 需要 retry/backoff | DOC_DESIGNED |
| DBLP | M1.4 quality ranking | CS venue / publication venue metadata 校验 | DBLP API / XML dumps; 必须调研 venue field、conference/journal mapping、本地化数据方式 | OPTIONAL_ADAPTER | 否 | venue 缩写与论文 title 匹配易错；需要去重 | RESEARCH_REQUIRED |
| OpenReview | M1.4 quality ranking | ICLR/NeurIPS workshop/review status、投稿/接收状态 | OpenReview API / venue group endpoints; 必须调研 forum/invitation/venueid 字段 | OPTIONAL_ADAPTER | 否 | 覆盖有限；不同 venue schema 不统一 | RESEARCH_REQUIRED |
| CORE | M1.2 / M1.3 | open access metadata / OA source discovery | CORE API / provider metadata; 必须调研 API key、rate limit、OA URL 字段 | OPTIONAL_ADAPTER | 否 | API key / coverage / quality信号有限 | RESEARCH_REQUIRED |
| CCF ranking data | M1.4 quality ranking | CCF A/B/C 会议期刊质量辅助判断 | CCF ranking dataset source; 必须调研可本地化 ranking 数据、license、更新频率 | OPTIONAL_ADAPTER | 否 | 不能凭空实现 ranking；非 CS 领域不适用 | RESEARCH_REQUIRED |

| Capability | Implementation | Adapter |
|---|---|---|
| arXiv search | httpx + Atom XML parsing (custom robust fetcher) | `ArxivAdapter` |
| OpenAlex metadata search | `pyalex` | `OpenAlexAdapter` |
| Semantic Scholar metadata/search | httpx REST API (custom adapter) | `SemanticScholarAdapter` |
| Crossref DOI metadata | `habanero` | `CrossrefAdapter` |
| Best available source resolution | arXiv source / structured HTML / PDF with retry/backoff | `PaperSourceResolver` |
| Structured paper reading | DeepXiv structured output / publisher HTML/XML through adapter | `StructuredSourceAdapter` |
| PDF/layout normalization (PRIMARY) | MinerU2.5-Pro via mineru-vl-utils | `MinerU25ProAdapter` |
| PDF/layout normalization (FALLBACK) | Marker build_document() | `MarkerDocumentFormulaDetector` |
| Structure refinement (optional) | local Llama model | `LlamaSectionRefiner` |
| Structure refinement (always) | rule-based sanity checks | `RuleBasedStructureRefiner` |
| Formula region detection | layout/parser formula bbox extraction | `FormulaRegionDetector` |
| Formula OCR | pix2tex / LaTeX-OCR through adapter | `FormulaOCRAdapter` |

All third-party packages are isolated behind adapters so the core schemas and selection logic remain replaceable.

## External Project Borrowed Strategy

ResearchSensei's arXiv access strategy borrows engineering patterns from:

`wanshuiyin/Auto-claude-code-research-in-sleep/tools/arxiv_fetch.py`

Borrowed strategies (not copied code):

- Descriptive User-Agent on all arXiv requests
- Contact email via environment variable
- 429 retry with backoff
- 503 retry with backoff
- Rate exceeded body detection
- arXiv ID normalization and id_list lookup
- PDF download file size guard
- PDF header validation

These strategies are not optional optimizations. They are part of M1 real validation. Without them, arXiv requests easily fail due to default client behavior, network exit points, or rate limiting.

## External Reference Implementation Notes

### M1.1 Query Planning

- **Reference source**: ARIS `skills/research-lit/SKILL.md`, `skills/idea-discovery/SKILL.md`
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: Split broad research direction into searchable academic queries; preserve user direction / constraints / scope; use LLM to generate structured search plan instead of keyword splitting
- **ResearchSensei-owned target**: `query_plan.json`
- **Schema / artifact impact**: `english_query`, `query_variants`, `core_terms`, `related_terms`, `exclude_terms`, `search_intents`
- **Boundary**: Does not use ARIS skill output format. ResearchSensei retains QueryPlan schema.
- **Validation implication**: Chinese query must produce English academic query via real LLM. No LLM / LLM JSON failure = M1 failure.

### M1.2 Multi-source Acquisition

- **Reference source**: ARIS `tools/arxiv_fetch.py`, `tools/semantic_scholar_fetch.py`, `tools/openalex_fetch.py`, `skills/research-lit/SKILL.md`
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: arXiv User-Agent / contact email / rate-limit handling; source contribution tracking; source success/failure diagnostics; do not hide source failures
- **ResearchSensei-owned target**: `candidate_pool.json`, `source_metrics`
- **Schema / artifact impact**: `sources_attempted`, `sources_success`, `source_failures`, `source_contribution`, `candidate.source_ids`, `candidate.raw_source_metadata`
- **Boundary**: Does not adopt ARIS-only search. ResearchSensei retains best-of-breed source set: arXiv robust official endpoint adapter, OpenAlex/pyalex, Semantic Scholar official REST, Crossref/habanero. Other projects open for evaluation: Unpaywall, PaperQA, STORM, DeepXiv, Exa.
- **Validation implication**: `sources_attempted >= 4`. Source failure must have structured error. One source success does not mean multi-source stability.

### M1.3 论文原始材料获取 / Best Available Source Resolution

- **Reference source**: ARIS `tools/arxiv_fetch.py`, `skills/research-lit/SKILL.md`
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: Download only top-relevant PDFs; PDF download uses User-Agent / retry / backoff; PDF size guard; PDF header validation
- **ResearchSensei-owned target**: `source_resolution.json`
- **Schema / artifact impact**: `source_type`, `source_priority`, `preferred_m2_input=canonical_paper.md`, `latex_source_url`, `latex_source_downloaded`, `latex_source_path`, `latex_source_sha256`, `latex_source_format`, `latex_main_file`, `structured_html_url`, `structured_html_downloaded`, `pdf_url`, `pdf_downloaded`, `pdf_metadata_check`, `pdf_title_match`, `source_confidence`, `canonicalization_status`, `m2_ready`, `source_warning`
- **Boundary**: M1 does lightweight source validation only, not M2 full-text parsing. Source files not committed to git. Does not download all candidates.
- **Validation implication**: M1 must try LaTeX source first, then structured HTML, then PDF. At least one deep-reading source downloaded. Metadata-only cannot enter M2.

M1.3 不只下载 PDF。M1.3 必须优先尝试获取 LaTeX source / arXiv source。如果 source 不可得，再尝试 structured HTML / XML。最后才是 PDF。

### M1.3.5 Material Normalization / canonical_paper.md

- **Reference source**: DeepXiv structured reading ideas, MinerU / Marker layout extraction, pix2tex / LaTeX-OCR formula OCR, ARIS source verification discipline
- **Reference use**: OPTIONAL_ADAPTER / STRATEGY_BORROW
- **ResearchSensei-owned target**: `canonical_paper.md`
- **Schema / artifact impact**: YAML front matter, normalized sections, formula blocks, source/confidence/status fields
- **Boundary**: Does not force all papers into true LaTeX. LaTeX source yields `source_latex`; parser/OCR/reconstruction must be labelled.
- **Validation implication**: M2 may only consume `canonical_paper.md` with `m2_ready=true` or explicit override. Metadata-only cannot enter M2.

### M1.4 Dedup / Verification / Relevance

- **Reference source**: ARIS `tools/verify_papers.py`, `skills/research-lit/SKILL.md`
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: Three-layer candidate verification: (1) arXiv ID verification, (2) CrossRef DOI verification, (3) Semantic Scholar fuzzy title verification. Candidate status uses: `verified`, `unverified`, `verify_pending`, `error`. Transient API failure is `verify_pending`, not hallucination. Unverified candidates cannot enter A_READ. `verification_method` and `verification_reason` preserved.
- **ResearchSensei-owned target**: `filtered_candidates.json`
- **Schema / artifact impact**: `verification_status`, `verification_method`, `verification_reason`, `verification_confidence`, `rule_relevance_score`, `llm_relevance_score`, `llm_relevance_label`, `matched_concepts`, `missing_concepts`, `relevance_reason`, `should_download`, `should_a_read`
- **Boundary**: Does not vendor ARIS `verify_papers.py`. Does not treat ARIS CLI output as ResearchSensei artifact. ResearchSensei implements its own schema conversion and gate.
- **Validation implication**: `verified_candidate_count` must exist. `unverified_candidate_count` must exist. `verify_pending_count` must exist. `llm_judged_candidate_count` must exist. `relevance_filtered_count` must exist. A_READ_FOR_M2 must be verified + relevant + valid deep-reading source. Valid deep-reading source can be LaTeX source, structured HTML, or validated PDF. PDF is fallback, not the only valid input.

### M1.5 Reading Plan

- **Reference source**: ARIS `skills/research-lit/SKILL.md`
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: Each recommended paper must state: Problem, Method, Results, Relevance, Source, Verification status. Only top-relevant papers enter the reading plan.
- **ResearchSensei-owned target**: `reading_plan.json`
- **Schema / artifact impact**: `role`, `selection_reason`, `relevance_reason`, `verification_status`, `source_confidence`, `metadata_confidence`, `risk_note`, `can_enter_m2`
- **Boundary**: Does not reuse ARIS markdown table. ReadingPlan is a ResearchSensei artifact. A_READ serves M2 downstream.
- **Validation implication**: `A_READ count >= 1`. Every A_READ has `can_enter_m2=true`. Every A_READ has `verification_status`, validated PDF, `relevance_reason`.

### General M1 Boundary

ARIS is one external reference. ResearchSensei retains its own module boundaries, schemas, artifacts, gates, APIs, frontend, and validation rules. Other external projects remain open for evaluation (Unpaywall, PaperQA, STORM, DeepXiv, Exa).

## Pipeline

```text
QueryPlanner.plan()
  -> query_plan.json
DirectionRunner._acquire()
  -> candidate_pool.json
SelectionService.deduplicate()
  -> deduplicated candidates
CandidateVerifier.verify_many()
  -> verification fields
RelevanceJudge.judge_many()
  -> LLM relevance fields
DirectionRunner._should_download()
  -> download/source decision
PaperSourceResolver.resolve_many()
  -> try latex_source first
  -> then structured_html
  -> then pdf
  -> source_resolution.json
MaterialNormalizationService.normalize()
  -> read best available source
  -> generate normalized Markdown sections
  -> detect formula regions
  -> run FormulaOCRAdapter when policy triggers
  -> canonical_paper.md
  -> canonicalization_status + m2_ready
SelectionService.build_reading_plan()
  -> filtered_candidates.json + reading_plan.json
```

Note: verification + LLM relevance judge happen before download. Candidates with `should_download=false` are not downloaded. `filtered_candidates.json` contains post-verify + post-relevance + post-source-resolution final candidates. M1 must not stop at PDF if LaTeX source is available. PDF success is not the best possible result when source is available.

## M1.1 Query Planning

`QueryPlanner.plan(user_query)` now requires an injected LLM client. If no LLM is available, or if the LLM output is not valid JSON, it raises `QueryPlanningError`.

Required fields:

- `direction_en`
- `english_query`
- `query_variants`
- `core_terms`
- `related_terms`
- `exclude_terms`
- `search_intents`

This prevents Chinese directions from being searched with poor heuristic English terms.

## M1.2 Acquisition

`DirectionRunner` defaults to four sources:

- `arxiv`
- `openalex`
- `semantic_scholar`
- `crossref`

Each source records source metrics:

- `source`
- `attempted`
- `success`
- `count`
- `latency_ms`
- `error`

Source failure is recorded in warnings and does not hide other source results.

### arXiv Adapter

`ArxivAdapter` uses httpx with a custom robust fetch strategy (not the `arxiv` Python package's default client).

**User-Agent**:

```
ResearchSensei/0.5 (+https://github.com/ZehuaGou/Research-sensei)
```

If `RESEARCHSENSEI_CONTACT_EMAIL` is set, the User-Agent includes `mailto:<email>`.

**Query strategy** — at least three query forms are attempted:

1. `all:"<query>"` — all-fields exact phrase
2. `ti:"<query>"` — title-only exact phrase
3. raw query — fallback

If any form returns results, no further forms are tried.

**arXiv ID lookup** — when a candidate has an arXiv ID from another source (OpenAlex, Crossref, Semantic Scholar), `ArxivAdapter.search_by_id(arxiv_id)` uses the `id_list` parameter instead of `search_query`, bypassing the search endpoint entirely.

**Retry/backoff** — applies to both API search and PDF download:

| Error | Backoff sequence | Max retries |
|---|---|---|
| HTTP 429 | 5s, 10s, 15s | 3 |
| HTTP 503 | 2s, 4s, 8s | 3 |
| Rate exceeded (body) | 5s, 10s, 15s | 3 |
| Timeout / ConnectionError | 2s, 4s, 8s | 3 |

Body detection checks for `"Rate exceeded"` and `"Please reduce"` in the response text.

**Diagnostics recorded per attempt**:

- status code
- exception type
- query string
- attempt count
- retry/backoff wait time
- rate-limit body content

### Semantic Scholar Adapter

`SemanticScholarAdapter` uses the official Semantic Scholar REST API via httpx (not the `semanticscholar` Python package).

**Endpoint**: `https://api.semanticscholar.org/graph/v1/paper/search`

**Proxy support**: `httpx.Client(..., trust_env=True)` reads `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` from the environment. This allows Clash or other local proxies to route Semantic Scholar traffic.

**API key**: reads `SEMANTIC_SCHOLAR_API_KEY` from environment. When set, sends `x-api-key` header. Without a key, the free tier rate limit (currently ~100 requests/5min) applies.

**Retry/backoff**:

| Error | Backoff sequence | Max retries |
|---|---|---|
| HTTP 429 | 3s, 6s, 12s | 3 |
| HTTP 503 | 2s, 4s, 8s | 3 |
| Timeout / ConnectionError | 2s, 4s, 8s | 3 |

**Known limitation**: if Clash or the local proxy does not route `api.semanticscholar.org`, `ConnectionRefusedError` may occur even with `trust_env=True`. This is a runtime environment issue, not a code bug. The error is structured and recorded in source metrics.

### Crossref Adapter

`CrossrefAdapter` uses `habanero` for DOI metadata retrieval.

### OpenAlex Adapter

`OpenAlexAdapter` uses `pyalex` for metadata search with inverted-index abstract reconstruction.

## M1.3 Source Acquisition

`PaperSourceResolver` resolves best available source for each candidate. M1 不只下载 PDF，必须优先尝试获取 LaTeX source。

### M1.3 Source Priority

1. **latex_source** — preferred when arXiv source / LaTeX source package is available; best for formulas, citations, section hierarchy, labels, references, and bibliography
2. **structured_html / xml / deepxiv_structured** — preferred when publisher/arXiv HTML/XML or DeepXiv structured output is available; useful for reading order and MathML/HTML structure
3. **pdf_parser_output** — acceptable for M2 only when source is unavailable; must pass PDF validation, title match, parser status, and canonicalization gate
4. **low_confidence_text_fallback** — can produce degraded `canonical_paper.md` only when sufficient body text exists; formula explanation is blocked or degraded
5. **metadata_only** — can be used for landscape anchor or reference; cannot enter M2 deep reading

### source_resolution.json Schema

```json
{
  "paper_id": "",
  "title": "",
  "source_type": "latex_source | structured_html | xml | deepxiv_structured | pdf_parser_output | low_confidence_text_fallback | metadata_only",
  "source_priority": 1,
  "preferred_m2_input": "canonical_paper.md | none",

  "latex_source_url": "",
  "latex_source_downloaded": false,
  "latex_source_path": "",
  "latex_source_sha256": "",
  "latex_source_format": "tar | gz | zip | tex | unknown",
  "latex_main_file": "",
  "latex_aux_files": [],
  "latex_compile_status": "not_checked | compile_ok | compile_failed | not_applicable",
  "latex_source_error": "",

  "structured_html_url": "",
  "structured_html_downloaded": false,
  "structured_html_path": "",
  "structured_html_error": "",

  "pdf_url": "",
  "pdf_downloaded": false,
  "pdf_path": "",
  "pdf_sha256": "",
  "pdf_metadata_check": "passed | mismatch | unknown | not_applicable",
  "pdf_title_match": "match | mismatch | unknown | not_applicable",
  "pdf_error": "",

  "source_confidence": "high | medium | low",
  "canonicalization_status": "not_started | success | degraded | blocked",
  "m2_ready": false,
  "degradation_reason": [],
  "source_warning": []
}
```

## M1.3.5 Material Normalization

M1 Material Normalization converts the best available source into `canonical_paper.md`. This is the M1→M2 core contract.

### Architecture v2 (2026-06-09)

M1 PDF canonicalization v2: MinerU2.5-Pro primary + Llama structure refiner + Marker fallback.

```
PDF
  -> MinerU2.5-Pro adapter (PRIMARY)
       mineru-vl-utils
       opendatalab/MinerU2.5-Pro-2604-1.2B
       output: page/block JSON
       blocks: title / text / formula / table / figure
       bbox / page / latex / reading_order
  -> StructureRefiner
       RuleBasedStructureRefiner (always)
         section hierarchy sanity
         reading_order validation
         formula context checks
       LlamaSectionRefiner (optional, local)
         section / context / reading_order refinement
         strict JSON output only
         forbidden: modify formula_latex, bbox, page, paper metadata
  -> CanonicalBuilder
       canonical_paper.md
       formula_slots.json
       visual audit artifacts
  -> M1 Quality Gate
       source/title verification
       formula bbox / crop / overlay
       latex / canonical match
       section contradiction detection
       all_formulas_same_section_suspicious
       abstract_formula_overload
       nearby_heading_conflict
       fallback_used flag
       llama_refined flag
```

### Architecture v1 (fallback / audit baseline)

v1 is the Marker three-pipeline architecture, retained as fallback when MinerU2.5-Pro is unavailable.

**IMPORTANT**: The current code uses `magic_pdf.tools.common.do_parse` via `MinerUPdfAdapter`. This is the OLD MinerU CLI (magic-pdf package). It is NOT equivalent to `mineru-vl-utils` + `opendatalab/MinerU2.5-Pro-2604-1.2B`. The v2 adapter must use the new MinerU2.5-Pro model via `mineru-vl-utils`.

```
PDF (v1 fallback)
  -> Body pipeline
       MarkItDown / PyMuPDF / optional Marker body output
       parser quality scoring
       body_selected_parser
       sections
  -> Formula pipeline
       Marker build_document()
       Equation/TextInlineMath blocks
       FormulaSlot(page, bbox, marker_latex/text)
       FormulaCropper(PyMuPDF crop)
       FormulaOCRAdapter if needed
  -> FormulaMerger
       sections + FormulaSlot + final_latex/unresolved
       canonical_paper.md
```

### Parser positioning

| Component | Role in v2 | Role in v1 fallback |
|---|---|---|
| MinerU2.5-Pro | **PRIMARY** canonical parser | not available |
| MarkerDocumentFormulaDetector | fallback formula bbox/LaTeX detector, audit baseline | primary formula detector |
| MarkItDown | fast text fallback, source/title verification | default body parser |
| PyMuPDF | page text extraction, crop, overlay, debug/audit | text fallback, crop engine |
| LlamaSectionRefiner | optional structure refinement | not available |
| RuleBasedStructureRefiner | always-on sanity checks | always-on sanity checks |

### Inputs

- verified candidate metadata
- `source_resolution.json`
- downloaded LaTeX source / structured HTML / XML / DeepXiv structured output / validated PDF / parser output
- optional parser/layout outputs from MinerU, Marker, Docling, GROBID, PyMuPDF
- formula OCR policy config

### Outputs

- `canonical_paper.md`
- normalization warnings
- `canonicalization_status`
- `m2_ready`
- formula slot metadata

### FormulaSlot

FormulaSlot is the core data structure for the formula pipeline. It represents a detected formula region with position, source, and resolution status.

```python
class FormulaSlot(SenseiModel):
    formula_id: str                    # unique ID, e.g. "eq_001"
    page: int                          # 0-indexed page number
    bbox: list[float]                  # [x1, y1, x2, y2] in PDF points
    polygon: list[list[float]] | None  # 4-corner coords if available
    block_type: str                    # "Equation" | "TextInlineMath" | "Math" | "Formula"
    detection_source: str              # "marker_document" | "mineru25pro" | "pymupdf"
    detection_confidence: float        # 0-1
    marker_text: str                   # raw text from Marker block (if any)
    marker_latex: str                  # LaTeX from Marker block (if any)
    mineru_latex: str                  # LaTeX from MinerU2.5-Pro (if any)
    nearby_text_before: str            # text context before the formula
    nearby_text_after: str             # text context after the formula
    section: str                       # matched section name
    section_confidence: str            # "high" | "medium" | "low"
    section_source: str                # "heading_above" | "nearby_heading" | "nearby_after_heading" | "llama_refined" | "unknown"
    section_reason: str                # human-readable explanation
    slot_marker: str                   # "marker_equation" | "marker_inlinemath" | "regex" | etc.
    block_source: str                  # "mineru25pro" | "marker_document" | "ocr" | "latex_source"
    crop_path: str | None              # path to cropped formula image
    overlay_path: str | None           # path to overlay image
    ocr_latex: str                     # OCR result (if OCR was run)
    ocr_status: str                    # "not_required" | "success" | "failed" | "skipped_by_policy"
    final_latex: str                   # final resolved LaTeX
    final_origin: str                  # "source_latex" | "mineru_latex" | "marker_latex" | "ocr_latex" | "raw_formula_text" | "unresolved"
    unresolved_reason: str             # why it couldn't be resolved (if unresolved)
    risk_flags: list[str]              # e.g. ["SECTION_CONTRADICTION", "ABSTRACT_OVERLOAD"]
```

### Formula origin priority

```
source_latex > mineru_latex > marker_latex > ocr_latex > raw_formula_text > unresolved
```

- `source_latex`: From original LaTeX source (highest confidence)
- `mineru_latex`: From MinerU2.5-Pro (primary parser, reliable when block has LaTeX)
- `marker_latex`: From Marker `build_document()` Equation block (fallback)
- `ocr_latex`: From FormulaOCRAdapter on cropped image
- `raw_formula_text`: Extracted from text but no reliable LaTeX
- `unresolved`: Formula detected but could not be resolved

### DocumentBlock (M2.1 input)

```python
class DocumentBlock(SenseiModel):
    block_id: str                    # unique block ID
    page: int                        # page number
    bbox: list[float]                # [x1, y1, x2, y2]
    block_type: str                  # title / text / formula / table / figure / caption / reference / unknown
    text: str                        # plain text content
    latex: str                       # LaTeX if applicable
    html: str                        # HTML if applicable
    reading_order: int               # reading order within document
    source: str                      # mineru25pro / marker_document / pymupdf / markitdown
    confidence: float                # 0-1
    parent_section: str              # section name
    raw_payload_ref: str             # reference to raw parser output
```

### MinerU25ProAdapter contract

- Uses `mineru-vl-utils` to call `opendatalab/MinerU2.5-Pro-2604-1.2B`
- Input: PDF path or page image
- Output: normalized document JSON with blocks
- Must preserve: page, bbox, block_type, text, latex, reading_order, confidence, source=mineru25pro
- **NOT** the same as old `magic_pdf.tools.common.do_parse` (magic-pdf package)
- The old MinerUPdfAdapter uses `magic_pdf` CLI; the new adapter uses `mineru-vl-utils` + the MinerU2.5-Pro model

### LlamaSectionRefiner contract

- Only refines document structure and formula context
- Input: blocks from MinerU / Marker / PyMuPDF
- Output: strict JSON
- May modify: section, section_confidence, section_reason, reading_order_warning, formula_context_reason, risk_flags
- **Forbidden**: modify formula_latex, bbox, page, source_pdf identity, paper metadata
- If Llama output is invalid JSON: fallback to RuleBasedStructureRefiner, record risk

### StructureRefiner contract

Two layers:

1. **RuleBasedStructureRefiner** (always active)
   - Section hierarchy sanity checks
   - Reading order validation
   - Formula context checks
   - Abstract overload detection

2. **LlamaSectionRefiner** (optional, local)
   - Section / context / reading_order refinement
   - Requires local Llama model
   - Strict JSON output only

Priority: MinerU sections/layout → rule-based sanity → optional Llama → audit gate. Llama cannot decide alone.

### canonical_paper.md front matter

```yaml
---
paper_id:
title:
authors:
year:
venue:
source_type:
source_confidence:
canonicalization_status:
parser_used:                    # legacy, kept for compatibility
m2_ready:
degradation_reason:

# Body pipeline
body_selected_parser:           # "markitdown" | "pymupdf" | "marker"
body_parser_quality_score:      # 0-100
body_parser_selection_reason:   # why this parser was selected

# Formula pipeline
formula_detector:               # "marker_document" | "regex" | "none"
formula_selected_parser:        # which parser produced the final formula LaTeX
formula_slot_count:             # total FormulaSlot count
formula_crop_count:             # how many were cropped
parser_latex_count:             # formulas with parser-provided LaTeX
ocr_latex_count:                # formulas resolved via OCR
raw_formula_text_count:         # formulas with raw text only
unresolved_formula_count:       # formulas that couldn't be resolved

canonical_quality_status:       # "PASS" | "DEGRADED" | "BLOCKED"
---
```

### canonical body

The body should preserve these sections when available:

- Title
- Abstract
- Introduction
- Related Work
- Method
- Experiments
- Conclusion
- References

Missing sections remain missing with warnings. Empty generated placeholders are not allowed.

### Formula block format in canonical_paper.md

Formulas with resolved LaTeX:

````markdown
<!-- formula_id: eq_001 | page: 3 | bbox: [x1,y1,x2,y2] | source: marker_document | origin: parser_latex | confidence: 0.8 -->
```latex
\mathcal{L} = ...
```
````

Unresolved formulas:

```markdown
<!-- formula_id: eq_001 | page: 3 | bbox: [...] | source: marker_document | origin: unresolved | reason: OCR failed or disabled -->
{{FORMULA:eq_001 unresolved}}
```

### Marker new role

Marker is no longer just a Markdown parser. Its primary value in M1 is as a **formula position detector**:

**MarkerDocumentFormulaDetector**:
- Uses `converter.build_document(pdf_path)` to get the internal `Document`
- Iterates `Page.children` to find `Equation` / `TextInlineMath` / `Math` / `Formula` blocks
- Extracts `page_id` and `block.polygon.bbox`
- Extracts `marker_latex` / `marker_text` when available

**Key finding**: `MarkdownOutput` and `JSONRenderer` both discard Equation block positions. The internal `Document` object is the only source of formula position data. The `MarkdownOutput` flattens equations to `$...$` text; `JSONRenderer` inlines them into parent Text blocks.

### OCR strategy

OCR is not run by default on all formulas:

1. **Marker block has reliable LaTeX** → `final_origin = parser_latex` → no OCR needed
2. **Marker block has bbox but no reliable LaTeX** → crop → OCR:
   - OCR succeeds → `final_origin = ocr_latex`
   - OCR fails → `final_origin = unresolved`
3. **OCR result must never be labeled as `source_latex`** — OCR is a fallback, not a source-quality signal

### FormulaRegionDetector (legacy, superseded by MarkerDocumentFormulaDetector)

Input:
- parser/layout blocks
- page images if available
- page size / text region metadata
- section context

Output:
- `formula_id`
- `formula_bbox`
- `formula_page`
- `formula_context_before`
- `formula_context_after`
- `detector_confidence`
- warnings

Failure conditions:
- no bbox
- bbox outside page bounds
- duplicate or unstable formula_id
- no section alignment
- confidence below configured threshold

Gate rules:
- detector failure does not block `canonical_paper.md` when text is sufficient
- detector failure sets formula extraction status degraded
- formula explanation is blocked unless a reliable LaTeX source exists from another path

Current status: Superseded by MarkerDocumentFormulaDetector for PDF sources.

### FormulaOCRAdapter

Input:
- formula region image
- bbox
- page number
- surrounding text
- OCR config

Output:
- `formula_latex`
- `formula_origin=ocr_latex`
- `formula_ocr_status`
- `ocr_confidence`
- warnings

Candidate implementations:
- pix2tex / LaTeX-OCR

Trigger conditions (OCR is NOT automatic):
- Marker block has bbox but no reliable LaTeX
- user requests formula explanation
- M2 marks formula as core top-K
- deep reading mode requests formula-level explanation

Run policy:

```yaml
formula_ocr_enabled: true
default_formula_ocr_mode: on_demand
max_formula_ocr_per_paper: 3
max_formula_ocr_batch: 10
formula_ocr_timeout_seconds: configurable
```

Failure conditions:
- timeout
- GPU/resource error
- low OCR confidence
- malformed LaTeX
- context mismatch

Gate rules:
- failed OCR writes `formula_ocr_status=failed`
- OCR result never becomes `source_latex`
- OCR result cannot silently upgrade to high-confidence explanation

Current status: IMPLEMENTED (pix2tex adapter exists, model weight download slow).

### m2_ready gate

`m2_ready=true` requires:

- front matter contains `paper_id`, `title`, `source_type`, `source_confidence`, `canonicalization_status`
- canonical body has abstract or enough body text
- source is not `metadata_only`
- formula blocks, if present, include `formula_id` and `origin`
- degradation reasons are explicit

Blocked conditions:

- metadata-only input
- missing title or paper identity
- empty body
- no source status
- formula blocks without origin
- security rejection or parser corruption

### Source Resolution Strategy

`PaperSourceResolver` records source resolution status for each type.

For downloaded sources it records:

- `download_status`
- `final_url`
- `content_type`
- `file_size`
- `sha256`
- `local_path`
- `error_code`

Supported status values include:

- `RESOLVED_LATEX_SOURCE_DOWNLOADED`
- `RESOLVED_STRUCTURED_HTML_DOWNLOADED`
- `RESOLVED_PDF_DOWNLOADED`
- `RESOLVED_PDF_URL_ONLY`
- `RESOLVED_LANDING_ONLY`
- `METADATA_ONLY`
- `FAILED_DOWNLOAD`
- `NO_SOURCE_FOUND`

`RESOLVED_LATEX_SOURCE_DOWNLOADED` or `RESOLVED_STRUCTURED_HTML_DOWNLOADED` or `RESOLVED_PDF_DOWNLOADED` can clear a paper for M2. LaTeX source is preferred over PDF.

### PDF Download Strategy

PDF downloads use:

- ResearchSensei User-Agent (same as arXiv adapter)
- `httpx.Client(trust_env=True)` for proxy support
- Retry/backoff on 429, 503, timeout, connection error (2s, 4s, 8s; max 3 retries)

After download, validation includes:

- content-type check
- `%PDF` magic header check (first 5 bytes)
- minimum file size (10 KB) to reject HTML error pages
- maximum file size (80 MB default)
- sha256 hash computation
- local_path recording

PDF files are not committed to git.

## M1.4 Dedup And Scoring

Dedup priority:

1. DOI
2. arXiv ID
3. Semantic Scholar ID
4. normalized title
5. normalized title + year

Metadata merge keeps source lists and fills missing DOI/arXiv/PDF/landing/citation/abstract fields from duplicates.

Scoring uses real metadata fields:

- relevance score
- venue prestige signal
- citation count
- code availability
- method representativeness
- source reliability
- open-access signal
- PDF availability
- metadata completeness
- recency
- noise penalty

## M1.5 Reading Plan Gate

Priorities:

- `A_READ`: deep reading candidate. Must have `can_enter_m2=true`.
- `B_SKIM`: useful background but not cleared for deep-card generation.
- `C_REFERENCE`: metadata-only reference.
- `D_IGNORE`: filtered out of the returned learning plan.

`A_READ` requires ALL of (AND logic):

- `verification_status == verified`
- `scoring_breakdown.relevance_score >= 0.45` (rule-based)
- `llm_relevance_score >= 0.65` (LLM-based)
- `llm_relevance_label in {HIGH, MEDIUM}`
- `should_a_read == true`
- `can_enter_m2 == true`
- `source_confidence >= medium`
- `metadata_confidence >= medium`
- `role != IRRELEVANT`

A_READ_FOR_M2 must have one valid deep-reading input:

**Either** (preferred):
- `source_type == latex_source`
- `latex_source_downloaded == true`
- `latex_main_file` exists
- `source_confidence in {high, medium}`

**Or**:
- `source_type in {structured_html, xml, deepxiv_structured}`
- `structured_html_downloaded == true`
- `source_confidence in {high, medium}`

**Or** (fallback):
- `source_type == pdf_parser_output`
- `pdf_downloaded == true`
- `pdf_metadata_check == passed`
- `pdf_title_match == match`
- `source_confidence in {high, medium}`

And in all cases:
- `canonicalization_status in {success, degraded}`
- `m2_ready == true`
- `canonical_paper.md` exists

`metadata_only` cannot enter `A_READ_FOR_M2`.

If no paper satisfies this, `reading_plan.status` becomes `DEGRADED` or `FAILED`, not a fake success.

## Artifacts

### Direction Exploration Mode

| Artifact | Description |
|---|---|
| `survey_candidates.json` | Survey candidates found by search |
| `direction_landscape.json` | Direction framework with method families, chronology stages, landscape anchors, recommended reading order, gaps |
| `reading_plan.json` | Reading plan derived from direction framework |

### Focused Acquisition Mode

| Artifact | Description |
|---|---|
| `query_plan.json` | Real LLM-generated query plan |
| `candidate_pool.json` | Raw candidate pool and source metrics |
| `source_resolution.json` | PDF/source acquisition status and download metadata |
| `canonical_paper.md` | Markdown-first canonical input for M2 |
| `filtered_candidates.json` | Final candidates with verification/LLM relevance/PDF fields |
| `reading_plan.json` | Prioritized plan with A_READ_FOR_M2/B_SKIM/C_REFERENCE and warnings |

### Seed Paper Expansion Mode

| Artifact | Description |
|---|---|
| `paper_relation_graph.json` | Graph of upstream/downstream/related papers |
| `seed_expansion_result.json` | Structured expansion result |

## M1 Quality Gate

M1 quality gate validates the canonical output before M2 consumption. The gate checks both artifact completeness and semantic correctness.

### Gate checks

| Check | Severity | Condition |
|---|---|---|
| source/title verified | BLOCKING | `title_verified in {YES, YES_WITH_BAD_METADATA}` |
| formula_slot_count | BLOCKING | `>= 5` for method papers |
| crop_exists | BLOCKING | 100% of formula slots |
| overlay_exists | BLOCKING | 100% of formula slots |
| latex_non_empty | BLOCKING | 100% of formula slots |
| final_vs_canonical_match | BLOCKING | 100% of formula slots |
| polluted_section | BLOCKING | must be 0 |
| section_contradiction_count | HIGH | must be 0 for PASSED |
| all_formulas_same_section_suspicious | HIGH | if 5+ formulas all in Abstract for a method paper → BLOCKED |
| abstract_formula_overload | HIGH | formulas on Method/Experiment pages labeled Abstract |
| nearby_heading_conflict | MEDIUM | section and nearby text disagree |
| reading_order_conflict | MEDIUM | MinerU reading_order inconsistent |
| llama_json_invalid_count | HIGH | Llama output not valid JSON |
| mineru_parse_failed | HIGH | MinerU2.5-Pro returned error |
| fallback_used | INFO | Marker fallback was used instead of MinerU |

### Hard rules

1. If 5+ formulas in a method paper are all assigned to Abstract: must be HIGH risk, cannot be PASSED.
2. If section=Abstract but nearby_text contains Method / Experiments / Conclusion / References: must be SECTION_CONTRADICTION, cannot be high confidence.
3. If MinerU2.5-Pro is unavailable and fallback to Marker: must record `fallback_used`, cannot claim primary success.
4. If Llama participates in refinement: must record model name, base_url type, JSON valid count. Never record API key.
5. If Llama modifies formula_latex / page / bbox: must be BLOCKED (越权).

## Live Acceptance

Run:

```powershell
$env:RUN_LIVE_TESTS="1"
$env:RUN_LLM_TESTS="1"
$env:RESEARCHSENSEI_LIVE_EVAL="1"
$env:RESEARCHSENSEI_MAX_LIVE_CASES="5"
$env:RESEARCHSENSEI_MAX_LLM_COST_USD="1.00"
$env:RESEARCHSENSEI_MAX_LLM_TOKENS="30000"

python -m pytest -q
python scripts/run_live_eval.py
```

### Direction Exploration Mode 验收

当前状态：DOC_DESIGNED / NOT_IMPLEMENTED。

DOC_DESIGNED 验收要求：

- broad direction query uses real LLM and real network
- `survey_candidates.json` exists
- `direction_landscape.json` exists
- `method_families` non-empty
- `chronology_stages` non-empty
- `landscape_anchors` non-empty
- `recommended_reading_order` non-empty
- every survey candidate has quality reason
- every landscape anchor has source, reason, verification status

### Focused Acquisition Mode 验收

当前状态：PARTIAL_REAL_E2E_VERIFIED。

当前 IMPLEMENTED 范围：PDF-focused focused acquisition live eval。完整 focused acquisition 的 canonical material normalization 能力为 DOC_DESIGNED / NOT_IMPLEMENTED。

验收必须满足：

- `query_plan.json` exists
- `candidate_pool.json` exists
- `source_resolution.json` exists
- `canonical_paper.md` exists for each A_READ entering M2
- `filtered_candidates.json` exists
- `reading_plan.json` exists
- `sources_success >= 3`
- `verified_candidate_count` exists
- `llm_judged_candidate_count` exists
- at least one deep-reading source downloaded (latex_source or structured_html or pdf)
- `canonicalization_status` recorded
- `m2_ready=true` for every A_READ entering M2
- every `A_READ_FOR_M2` satisfies:
  - `verification_status == verified`
  - `llm_relevance_score >= 0.65`
  - `llm_relevance_label in {HIGH, MEDIUM}`
  - `should_a_read == true`
  - has one valid deep-reading input (latex_source or structured_html/deepxiv_structured/xml or pdf_parser_output with title match)
  - has `canonical_paper.md`
  - has explicit `source_type`, `source_confidence`, `canonicalization_status`, `m2_ready`
  - `can_enter_m2 == true`

**degraded_passed**:

- `sources_success = 2`
- `pdf_download_success_count >= 1`
- `A_READ count >= 1`
- every A_READ has `can_enter_m2=true`
- failed sources have structured diagnostics (status code, exception type, retry count)

**failed**:

- `sources_success < 2`
- or no valid deep-reading source downloaded
- or no `canonical_paper.md` for A_READ
- or no A_READ paper
- or any A_READ has `can_enter_m2=false`

### Seed Paper Expansion Mode 验收

当前状态：DOC_DESIGNED / NOT_IMPLEMENTED。

DOC_DESIGNED 验收要求：

- seed paper metadata exists
- `paper_relation_graph.json` exists
- `seed_expansion_result.json` exists
- `upstream_papers` / `downstream_papers` / `related_surveys` / `follow_up_papers` present
- every relation has `relation_type`, evidence source, confidence
- unverified relation cannot be shown as trusted

### Additional Checks

- `real_llm_query_planning=true`
- `english_query` is present
- generated report contains no API keys or bearer tokens
- downloaded PDF files are not committed to git

## Known Runtime Limitations

M1 real validation has observed:

- arXiv may return 429 or 503. Requires descriptive User-Agent, contact email, and retry/backoff to recover.
- Semantic Scholar without an API key may trigger free-tier rate limits. Setting `SEMANTIC_SCHOLAR_API_KEY` raises the limit.
- Clash or local proxy rules affect Semantic Scholar and arXiv access. If `api.semanticscholar.org` or `export.arxiv.org` is not routed through the proxy, `ConnectionRefusedError` or timeout may occur.
- OpenAlex and Crossref serve as stable supplementary sources but do not replace arXiv or Semantic Scholar for coverage and diagnostics.

## Current Boundary

M1 still does not perform:

- M2 evidence parsing
- paper understanding
- teaching card generation
- formula explanation
- direction synthesis
- advisor/drill/interactive learning

M1 DOC_DESIGNED / NOT_IMPLEMENTED capabilities:

- `canonical_paper.md` generation
- material normalization from LaTeX / structured HTML / XML / DeepXiv / PDF parser output
- FormulaRegionDetector
- FormulaOCRAdapter
- MinerU / Marker / DeepXiv structured adapters
- formula_origin full-chain propagation

Those are later phases and must not be counted as completed by M1 live validation.
