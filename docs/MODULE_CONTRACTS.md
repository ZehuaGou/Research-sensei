# ResearchSensei Module Contracts

> **Canonical docs**: See `docs/DESIGN.md`, `docs/DEVELOPMENT.md`, and `docs/development/*.md`.
>
> Module contracts distinguish:
> 1. **Schema / artifact contract** — what the module produces
> 2. **Live validation contract** — what real-world conditions must pass
> 3. **Failure contract** — what happens when things go wrong
> 4. **Current status** — what is implemented vs designed

---

## M1 — Literature Search, Direction Exploration, And Seed Expansion

M1 has three modes: direction exploration, focused acquisition, and seed paper expansion. The source_resolver module handles best available source resolution. See `docs/development/M1_LITERATURE_SEARCH.md`.

### Direction Exploration Mode

**Schema / artifact contract**:

Input: direction query (broad, e.g. "时间序列异常检测")
Output:
- `survey_candidates.json`
- `direction_landscape.json` — with `method_families`, `chronology_stages`, `landscape_anchors`, `representative_papers`, `recommended_reading_order`, `gaps_or_open_questions`
- `reading_plan.json`

Boundary: `direction_landscape.json` does NOT replace `reading_plan.json`. `direction_landscape.json` serves direction understanding. `reading_plan.json` serves reading plan. `A_READ_FOR_M2` serves single-paper deep reading entry.

**Live validation contract**:

- broad direction query uses real LLM and real network
- `survey_candidates.json` exists
- `direction_landscape.json` exists
- `method_families` is non-empty
- `chronology_stages` is non-empty
- `landscape_anchors` is non-empty
- `recommended_reading_order` is non-empty
- each landscape anchor has source / reason / verification status

**Failure contract**:

- no qualified survey and no staged-search result → failed direction exploration
- LLM JSON failure → failed
- source failure must be recorded, not hidden

**Current status**: NOT_IMPLEMENTED

### Focused Acquisition Mode

**Schema / artifact contract**:

Input: focused query / title / DOI / URL / arXiv ID
Output:
- `query_plan.json`
- `candidate_pool.json`
- `source_resolution.json`
- current verified artifact path: validated PDF source for selected papers
- target canonical artifact path: `canonical_paper.md` when material normalization succeeds or degrades acceptably
- `filtered_candidates.json` — final candidates with verification/LLM relevance/PDF fields
- `reading_plan.json` — with `A_READ_FOR_M2` papers

Boundary: Does not generate paper cards or teaching output. Current verified implementation gates selected papers by PDF availability and title/metadata checks. Target implementation performs material normalization for selected papers and writes the M2 canonical input.

**M1 Source Acquisition Contract**:

M1 must resolve best available source, not just PDF.

Source priority:
1. `latex_source`
2. `structured_html` / `xml` / `deepxiv_structured`
3. `pdf_parser_output`
4. `low_confidence_text_fallback`
5. `metadata_only`

`source_resolution.json` must include:
- `source_type`
- `source_priority`
- `preferred_m2_input`
- `latex_source_url`, `latex_source_downloaded`, `latex_source_path`, `latex_source_sha256`, `latex_source_format`, `latex_main_file`, `latex_aux_files`, `latex_compile_status`
- `structured_html_url`, `structured_html_downloaded`
- `pdf_url`, `pdf_downloaded`, `pdf_metadata_check`, `pdf_title_match`
- `source_confidence`, `source_warning`

**M1 Material Normalization Contract**:

Input:
- verified candidate metadata
- best available source artifact
- parser/layout output from LaTeX source, structured HTML/XML/DeepXiv, PDF parser, MinerU, Marker, or low-confidence text fallback

Output:
- `canonical_paper.md`
- canonical front matter: `paper_id`, `title`, `authors`, `year`, `venue`, `source_type`, `source_confidence`, `canonicalization_status`, `parser_used`, `m2_ready`, `degradation_reason`
- canonical sections: Title, Abstract, Introduction, Related Work, Method, Experiments, Conclusion, References when available
- formula blocks with `formula_id`, `origin`, `section`, `page`, `bbox`, `ocr_status`

Status fields:
- `canonicalization_status`: `SUCCESS`, `DEGRADED`, `BLOCKED`
- `m2_ready`: boolean
- `degradation_reason`: list or structured warning reason
- `formula_ocr_status`: `not_required`, `queued`, `success`, `failed`, `skipped_by_policy`
- `formula_origin`: `source_latex`, `parser_latex`, `ocr_latex`, `reconstructed`, `unknown`

FormulaRegionDetector:
- input: PDF parser / layout parser / MinerU / Marker blocks, page images, page metadata
- output: formula bbox, page, section, detector confidence
- failure: no bbox, bbox/page mismatch, low confidence, no section alignment
- current status: DOC_DESIGNED / NOT_IMPLEMENTED

FormulaOCRAdapter:
- input: formula region image, bbox, page, context, OCR config
- output: OCR LaTeX, OCR confidence, `formula_origin=ocr_latex`, warnings
- candidates: pix2tex / LaTeX-OCR through adapter
- failure: timeout, GPU/resource error, low confidence, malformed LaTeX, context mismatch
- run policy: `formula_ocr_enabled=true`, `default_formula_ocr_mode=on_demand`, `max_formula_ocr_per_paper=3`, `max_formula_ocr_batch=10`
- current status: DOC_DESIGNED / NOT_IMPLEMENTED

**Failure contract (source-aware)**:
- If LaTeX source exists but download fails, record `latex_source_error` and continue to structured_html/pdf only as degraded path.
- If only PDF is available, M2 must mark `parser_input_type=pdf` and cannot claim source-level formula fidelity.
- `metadata_only` cannot enter M2 deep reading.
- If `canonical_paper.md` cannot be produced with title, source status, and at least abstract or body text, set `m2_ready=false` and do not enter M2.
- If formula source is unknown, the paper may enter M2, but formula explanation gates must be degraded.

**Current verified PDF-only gate**:

- focused query uses real LLM and real network
- `sources_success >= 3`
- `verified_candidate_count` exists
- `llm_judged_candidate_count` exists
- `pdf_download_success_count >= 1`
- every `A_READ_FOR_M2` has: `verification_status == verified`, `llm_relevance_score >= 0.65`, `llm_relevance_label in {HIGH, MEDIUM}`, `should_a_read == true`, `pdf_downloaded == true`, `pdf_metadata_check == passed`, `pdf_title_match == match`, `can_enter_m2 == true`

This PDF-only gate is the current live-verified gate. It must not be treated as the future M1→M2 canonical contract.

---

## M2 — Single Paper Deep Reading & Survey Deep Reading

M2 supports two types of papers: ordinary research papers and survey/review papers. The ingestion module handles canonical_paper.md reading and evidence-ready block building. The grounding module builds evidence chains from parsed content.

### Ordinary Research Paper

**Schema / artifact contract**:

Input: canonical_paper.md (from M1)
Output:
- `parsed_document.json`
- `passage_index.json`
- `claim_evidence.json`
- `evidence_index.json` (v1 compatibility)
- `paper_skeleton.json`
- `paper_card.json` / `formula_cards.json` / `teaching_cards.json`
- `understanding_status.json`
- `quality_report.json`

M2.3 paper_card exposes direction-support fields when evidence exists:
- `method_family`
- `contribution_to_direction`
- `what_problem_it_solves`
- `what_limitation_it_leaves`
- `relation_to_previous_methods`
- `relation_to_later_methods`
- `datasets_and_metrics`
- `comparable_methods`

**Live validation contract**:

- real canonical_paper.md input
- real parser output
- real LLM card generation
- `evidence_ref` traceable
- QualityAuditor runs on real artifacts

**Failure contract**:

- parser failure → `FAILED`
- no passages / no claims / empty evidence pack → `BLOCKED_UNDERSTANDING`
- LLM failure / invalid JSON / invalid evidence_ref → `BLOCKED_UNDERSTANDING`
- audit BLOCK → `BLOCKED_UNDERSTANDING`

**Current status**: partial code exists; real canonical_paper.md + real LLM + real audit e2e not yet verified

### Survey / Review Paper

**Schema / artifact contract**:

Input: survey canonical_paper.md
Output (in addition to ordinary paper outputs):
- `survey_landscape`
- `method_taxonomy`
- `extracted_key_papers`
- `survey_claims`

`survey_landscape` does NOT replace `paper_card`. `formula_card` is NOT replaced by survey summary.

**Live validation contract**:

- real survey canonical_paper.md
- `method_taxonomy` extracted with `evidence_ref`
- `extracted_key_papers` traceable to survey passages
- `survey_landscape` does not replace `paper_card`

**Failure contract**:

- no taxonomy evidence → no trusted `survey_landscape`
- extracted paper without source passage → cannot become key paper

**Current status**: NOT_IMPLEMENTED

---

## M3 — API / Frontend

M3 has three frontend areas. See `docs/development/M3_FRONTEND_RENDER.md`.

### DirectionWorkspace

Displays:
- direction search input
- survey candidates
- direction framework
- method families
- chronology stages
- landscape anchors
- recommended reading order
- deep-read buttons

**Schema / artifact contract**:

Consumes M1 direction artifacts: `survey_candidates.json`, `direction_landscape.json`, `reading_plan.json`.

Future APIs:
- `POST /api/v1/directions/search` — input: direction_query, max_surveys, max_papers, prefer_surveys; output: job_id, status, survey_candidates, direction_landscape_status
- `GET /api/v1/directions/{direction_job_id}/landscape` — output: direction_landscape, survey_candidates, method_families, chronology_stages, landscape_anchors, recommended_reading_order

**Current status**: DOC_DESIGNED / NOT_IMPLEMENTED

### PaperWorkspace

Displays:
- upload PDF
- input paper title / DOI / arXiv / URL
- download/verification status
- paper_card
- formula_cards
- teaching_cards
- evidence_refs
- quality status
- find-upstream/downstream button

**Schema / artifact contract**:

Existing APIs:
- `POST /api/v1/documents/parse` — accepts: file upload, local_path, pdf_url, arxiv_id, arxiv_url

Future accepted inputs: title, DOI, publisher URL

M3 must show: `download_status`, `verification_status`, `pdf_metadata_check`, `pdf_title_match`, `can_enter_m2`

**Live validation contract**:

- real backend API smoke: upload real small PDF → backend returns job / status / cards → frontend can display status

**Failure contract**:

- missing status → show pending/error
- blocked status → do not show card content
- API failure → visible error

**Current status**: PARTIAL_CODE / PAGE_REAL_VALIDATION_MISSING

### SeedExpansionPanel

Displays:
- upstream papers
- downstream papers
- related surveys
- follow-up improvements
- same-route papers
- one-click deep-read buttons

**Schema / artifact contract**:

Consumes M1 seed expansion artifacts: `paper_relation_graph.json`, `seed_expansion_result.json`.

Future APIs:
- `POST /api/v1/papers/{paper_id}/expand` — input: paper_id, expansion_types (cited_by / references / related_surveys / follow_up / same_route); output: seed_expansion_result, paper_relation_graph

**Current status**: DOC_DESIGNED / NOT_IMPLEMENTED

DirectionWorkspace, PaperWorkspace, and SeedExpansionPanel are parallel frontend capabilities, not replacements.

---

## M4 — Interactive Learning & Long-term Memory

M4 is entered from three frontend contexts:

1. **PaperWorkspace**: M2 artifacts → paper-level selection explanation / formula explanation / single-paper Q&A / advisor drill
2. **DirectionWorkspace**: M1 direction_landscape + selected survey / anchors → direction-level Q&A / method-family comparison / reading-order explanation
3. **SeedExpansionPanel**: M1 paper_relation_graph → upstream/downstream explanation / follow-up paper recommendation / route explanation

### Paper-level interaction

**Schema / artifact contract**:
- `SelectionExplanation`
- `FormulaSymbolExplanation`
- `InteractiveAnswer`
- `AdvisorQuestion`
- `AdvisorEvaluation`

**Live validation contract**:
- real LLM
- real M2 artifacts
- real `evidence_ref` / memory references

### Direction-level interaction

Example questions:
- "这个方向是怎么发展的？"
- "Transformer 相比 Autoencoder 解决了什么问题？"
- "Anomaly Transformer 后面有哪些改进？"
- "这个方向现在还有什么开放问题？"
- "如果我要找创新点，应该沿哪几条路线看？"

**Live validation contract**:
- real LLM
- real direction_landscape artifact
- real survey_landscape if available

### Seed-expansion interaction

Example questions:
- "这篇论文引用了谁？"
- "谁改进了它？"
- "后续哪些论文最值得看？"
- "它属于哪条技术路线？"

**Live validation contract**:
- real LLM
- real paper_relation_graph
- real seed paper metadata

Direction-level and seed-expansion interaction do NOT replace formula/symbol explanation. Formula/symbol explanation remains M4.2 core capability.

### Memory types

- `PaperMemory`
- `DirectionMemory`
- `MethodFamilyMemory`
- `StageMemory`
- `PaperRelationMemory`
- `UserLearningProgressMemory`

**Failure contract**:
- no evidence → degraded / rejected
- stale memory → verify before use
- no LLM → fail validation, not pass

**Current status**: DOC_DESIGNED / NOT_IMPLEMENTED

---

## M5 — Engineering Reliability

M5 defines the real-validation matrix for M1-M4 and the engineering rules for reliability, security, cost, debug/admin, and CI. M5 does not replace M1-M4 module-level tests.

### M1 Direction Exploration

**Schema / artifact contract**:
- `survey_candidates.json`
- `direction_landscape.json`
- `reading_plan.json`

**Live validation contract**:
- broad direction query uses real LLM and real network
- `survey_candidates` exists
- `direction_landscape` exists
- `method_families` is non-empty
- `chronology_stages` is non-empty
- `landscape_anchors` is non-empty
- `recommended_reading_order` is non-empty
- each landscape anchor has source / reason / verification status

**Failure contract**:
- no qualified survey and no staged-search result → failed direction exploration
- LLM JSON failure → failed
- source failure must be recorded, not hidden

**Current status**: NOT_IMPLEMENTED

### M1 Focused Acquisition

**Schema / artifact contract**:
- `query_plan.json`
- `candidate_pool.json`
- `source_resolution.json`
- `filtered_candidates.json`
- `reading_plan.json` with `A_READ_FOR_M2`

**Live validation contract**:
- focused query uses real LLM and real network
- `sources_success >= 3`
- `pdf_download_success_count >= 1`
- every `A_READ_FOR_M2` is verified, relevant, PDF downloaded, `pdf_metadata_check=passed`, `pdf_title_match=match`, `can_enter_m2=true`

**Failure contract**:
- missing LLM client → fail
- no verified relevant PDF → fail
- API 429/503 must be recorded with source metrics
- PDF mismatch cannot enter `A_READ_FOR_M2`

**Current status**: REAL_E2E_VERIFIED

### M1 Seed Paper Expansion

**Schema / artifact contract**:
- `seed_expansion_result.json`
- `paper_relation_graph.json`
- `upstream_papers`, `downstream_papers`, `related_surveys`, `follow_up_papers`

**Live validation contract**:
- real seed paper metadata
- real citation / reference / related-paper sources
- `paper_relation_graph` exists
- relations have `relation_type` and source evidence

**Failure contract**:
- no seed metadata → fail
- no relation evidence → degraded / failed, not fabricated

**Current status**: NOT_IMPLEMENTED

### M2 Paper Deep Reading

**Schema / artifact contract**:
- `parsed_document.json`
- `passage_index.json`
- `claim_evidence.json`
- `evidence_index.json`
- `paper_skeleton.json`
- `paper_card.json`
- `formula_cards.json`
- `teaching_cards.json`
- `understanding_status.json`
- `quality_report.json`

**Live validation contract**:
- real PDF input
- real parser output
- real LLM card generation
- `evidence_ref` traceable
- QualityAuditor runs on real artifacts

**Failure contract**:
- parser failure → `FAILED`
- no passages / no claims / empty evidence pack → `BLOCKED_UNDERSTANDING`
- LLM failure / invalid JSON / invalid evidence_ref → `BLOCKED_UNDERSTANDING`
- audit BLOCK → `BLOCKED_UNDERSTANDING`

**Current status**: NOT_REAL_E2E_VERIFIED

### M2 Survey Deep Reading

**Schema / artifact contract**:
- ordinary M2 artifacts
- `survey_landscape`
- `method_taxonomy`
- `extracted_key_papers`
- `survey_claims`

**Live validation contract**:
- real survey PDF
- `method_taxonomy` extracted with `evidence_ref`
- `extracted_key_papers` traceable to survey passages
- `survey_landscape` does not replace `paper_card`

**Failure contract**:
- no taxonomy evidence → no trusted `survey_landscape`
- extracted paper without source passage → cannot become key paper

**Current status**: NOT_IMPLEMENTED

### M3 Frontend

**Schema / artifact contract**:
- DirectionWorkspace consumes M1 direction artifacts
- PaperWorkspace consumes M2 understanding artifacts
- SeedExpansionPanel consumes M1 seed expansion artifacts

**Live validation contract**:
- real backend API smoke
- real PDF upload or real paper input
- status gating works
- blocked/baseline outputs do not expose cards
- direction and seed panels do not display unverified relations as trusted

**Failure contract**:
- missing status → show pending/error
- blocked status → do not show card content
- API failure → visible error

**Current status**: PARTIAL_CODE / PAGE_REAL_VALIDATION_MISSING

### M4 Interactive Learning

**Schema / artifact contract**:
- `SelectionExplanation`
- `FormulaSymbolExplanation`
- `InteractiveAnswer`
- `AdvisorQuestion`
- `AdvisorEvaluation`
- `PaperMemory` / `DirectionMemory` / `MethodFamilyMemory` / `StageMemory` / `PaperRelationMemory` / `UserLearningProgressMemory`

**Live validation contract**:
- real LLM
- real M2 artifacts
- real `evidence_ref` / memory references
- paper-level, direction-level, seed-expansion interactions tested separately

**Failure contract**:
- no evidence → degraded / rejected
- stale memory → verify before use
- no LLM → fail validation, not pass

**Current status**: DOC_DESIGNED / NOT_IMPLEMENTED

### M5 Reliability

**Schema / artifact contract**:
- `live_eval_report.json`
- test reports
- secret scan report
- CI release check result

**Live validation contract**:
- `python -m pytest -q` includes `tests_live`
- real LLM tests run with real env
- real network tests run with real network
- frontend build and tests pass
- secret scan passes
- no PDF / report / API key committed

**Failure contract**:
- missing key / network / quota → failure, not pass
- API limit → recorded failure / degraded, not hidden
- secret found → release blocked
- CI not configured → not production ready

**Current status**: PARTIAL_INFRA / NOT_PRODUCTION_READY

**Test policy**: `python -m pytest -q` runs all tests including `tests_live`. Missing env/key/network = failure, not skip. mock/fake/skip are not valid acceptance tests.

---

## Module Index

The following modules are part of the ResearchSensei system:

- **query**: QueryPlanner — generates structured search plans from user direction input
- **acquisition**: Multi-source paper acquisition adapters (arXiv, OpenAlex, Semantic Scholar, Crossref)
- **selection**: SelectionService — deduplicates, scores, and prioritizes candidate papers
- **source_resolver**: PaperSourceResolver — resolves best available source (LaTeX, HTML, PDF)
- **ingestion**: SinglePaperIngestionRunner — canonical_paper.md reading and evidence-ready block building
- **grounding**: Evidence chain construction from parsed content
- **understanding**: Paper understanding and card generation
- **teaching**: Teaching card generation with formula/symbol explanation
- **formula**: Formula detection, OCR, and explanation
- **direction**: DirectionRunner — orchestrates M1 pipeline
- **patterns**: Pattern recognition in research directions
- **drill**: Advisor-style research training
- **interactive**: Interactive Q&A and learning
- **context**: Session context and memory management
- **llm**: LLM client, prompt building, and response caching
- **render**: Frontend rendering and API endpoints

**Target canonical_paper.md gate**:

- focused query uses real LLM and real network
- `sources_success >= 3`
- `verified_candidate_count` exists
- `llm_judged_candidate_count` exists
- every `A_READ_FOR_M2` has: `verification_status == verified`, `llm_relevance_score >= 0.65`, `llm_relevance_label in {HIGH, MEDIUM}`, `should_a_read == true`, `source_type != metadata_only`, `canonical_paper.md exists`, `canonicalization_status in {success, degraded}`, `m2_ready==true`

This target gate is DOC_DESIGNED / NOT_IMPLEMENTED.

**Failure contract**:

- Missing LLM client → `QueryPlanningError`
- LLM JSON parse failure → `QueryPlanningError`
- Source 429/503 → retry with backoff, then structured error in `source_metrics`
- PDF download failure → `FAILED_DOWNLOAD` status, not silently skipped
- Verification API failure → `verify_pending`, not `unverified`
- PDF mismatch cannot enter `A_READ_FOR_M2`
- canonical target failure (`metadata_only`, missing `canonical_paper.md`, `canonicalization_status=blocked`, or `m2_ready=false`) cannot enter M2

**Current status**: REAL_E2E_VERIFIED

### Seed Paper Expansion Mode

**Schema / artifact contract**:

Input: seed paper metadata / paper_id / uploaded paper
Output:
- `seed_expansion_result.json`
- `paper_relation_graph.json`
- `upstream_papers`, `downstream_papers`, `related_surveys`, `follow_up_papers`

**Live validation contract**:

- real seed paper metadata
- real citation / reference / related-paper sources
- `paper_relation_graph.json` exists
- relations have `relation_type` and source evidence

**Failure contract**:

- no seed metadata → fail
- no relation evidence → degraded / failed, not fabricated

**Current status**: NOT_IMPLEMENTED

---

## M2 — Single Paper Deep Reading & Survey Deep Reading

M2 supports two types of papers: ordinary research papers and survey/review papers.

### Ordinary Research Paper

**Schema / artifact contract**:

Input: `canonical_paper.md` produced by M1 material normalization, or a user-upload path that first passes through M1 canonicalization.
Output:
- `canonical_paper.md` (read-only input artifact retained)
- `parsed_document.json`
- `passage_index.json`
- `claim_evidence.json`
- `evidence_index.json` (v1 compatibility)
- `paper_skeleton.json`
- `paper_card.json` / `formula_cards.json` / `teaching_cards.json`
- `understanding_status.json`
- `quality_report.json`

M2.3 paper_card exposes direction-support fields when evidence exists:
- `method_family`
- `contribution_to_direction`
- `what_problem_it_solves`
- `what_limitation_it_leaves`
- `relation_to_previous_methods`
- `relation_to_later_methods`
- `datasets_and_metrics`
- `comparable_methods`

**M2.1 canonical input reader / validator**:

M2 does not directly process raw PDF / LaTeX / HTML / DeepXiv input. M2.1 reads `canonical_paper.md`, validates the front matter and formula blocks, then converts Markdown sections, paragraphs, tables, figures, and formulas into `DocumentBlock` / evidence-ready blocks.

Required formula fields passed into M2:
- `formula_id`
- `formula_latex`
- `formula_origin`
- `formula_bbox`
- `formula_page`
- `formula_context_before`
- `formula_context_after`
- `formula_ocr_status`
- `formula_explanation_status`

Formula explanation rules:
- `source_latex`: high-confidence explanation allowed when evidence context exists
- `parser_latex`: explanation allowed with parser warning
- `ocr_latex`: explanation allowed with OCR warning and non-high confidence unless verified
- `reconstructed`: speculative explanation only, must be clearly marked
- `unknown`: detailed derivation is blocked

**Live validation contract**:

- real `canonical_paper.md`
- real M1 canonicalization status
- real M2 canonical reader output
- real LLM card generation
- `evidence_ref` traceable
- QualityAuditor runs on real artifacts

**Failure contract**:

- missing or invalid `canonical_paper.md` → `BLOCKED_UNDERSTANDING`
- missing required front matter → `BLOCKED_UNDERSTANDING`
- formula block without `formula_origin` → formula explanation degraded or blocked
- no passages / no claims / empty evidence pack → `BLOCKED_UNDERSTANDING`
- LLM failure / invalid JSON / invalid evidence_ref → `BLOCKED_UNDERSTANDING`
- audit BLOCK → `BLOCKED_UNDERSTANDING`
- `ocr_latex`, `reconstructed`, and `unknown` cannot produce high-confidence formula explanation without explicit verification

**Current status**: partial code exists; canonical input reader / validator is DOC_DESIGNED / NOT_IMPLEMENTED; real canonical Markdown + real LLM + real audit e2e not yet verified

### Survey / Review Paper

**Schema / artifact contract**:

Input: survey PDF
Output (in addition to ordinary paper outputs):
- `survey_landscape`
- `method_taxonomy`
- `extracted_key_papers`
- `survey_claims`

`survey_landscape` does NOT replace `paper_card`. `formula_card` is NOT replaced by survey summary.

**Live validation contract**:

- real survey PDF
- `method_taxonomy` extracted with `evidence_ref`
- `extracted_key_papers` traceable to survey passages
- `survey_landscape` does not replace `paper_card`

**Failure contract**:

- no taxonomy evidence → no trusted `survey_landscape`
- extracted paper without source passage → cannot become key paper

**Current status**: NOT_IMPLEMENTED

---

## M3 — API / Frontend

M3 has three frontend areas. See `docs/development/M3_FRONTEND_RENDER.md`.

### DirectionWorkspace

Displays:
- direction search input
- survey candidates
- direction framework
- method families
- chronology stages
- landscape anchors
- recommended reading order
- deep-read buttons

**Schema / artifact contract**:

Consumes M1 direction artifacts: `survey_candidates.json`, `direction_landscape.json`, `reading_plan.json`.

Future APIs:
- `POST /api/v1/directions/search` — input: direction_query, max_surveys, max_papers, prefer_surveys; output: job_id, status, survey_candidates, direction_landscape_status
- `GET /api/v1/directions/{direction_job_id}/landscape` — output: direction_landscape, survey_candidates, method_families, chronology_stages, landscape_anchors, recommended_reading_order

**Current status**: DOC_DESIGNED / NOT_IMPLEMENTED

### PaperWorkspace

Displays:
- upload PDF
- input paper title / DOI / arXiv / URL
- download/verification status
- paper_card
- formula_cards
- teaching_cards
- evidence_refs
- quality status
- find-upstream/downstream button

**Schema / artifact contract**:

Existing APIs:
- `POST /api/v1/documents/parse` — accepts: file upload, local_path, pdf_url, arxiv_id, arxiv_url

Future accepted inputs: title, DOI, publisher URL

M3 must show: `download_status`, `verification_status`, `pdf_metadata_check`, `pdf_title_match`, `can_enter_m2`, `source_type`, `canonicalization_status`, `m2_ready`, `formula_origin`, `formula_ocr_status`, `degradation_reason`, `evidence_status`

**Live validation contract**:

- real backend API smoke: upload real small PDF → backend returns job / status / cards → frontend can display status

**Failure contract**:

- missing status → show pending/error
- blocked status → do not show card content
- API failure → visible error

**Current status**: PARTIAL_CODE / PAGE_REAL_VALIDATION_MISSING

### SeedExpansionPanel

Displays:
- upstream papers
- downstream papers
- related surveys
- follow-up improvements
- same-route papers
- one-click deep-read buttons

**Schema / artifact contract**:

Consumes M1 seed expansion artifacts: `paper_relation_graph.json`, `seed_expansion_result.json`.

Future APIs:
- `POST /api/v1/papers/{paper_id}/expand` — input: paper_id, expansion_types (cited_by / references / related_surveys / follow_up / same_route); output: seed_expansion_result, paper_relation_graph

**Current status**: DOC_DESIGNED / NOT_IMPLEMENTED

DirectionWorkspace, PaperWorkspace, and SeedExpansionPanel are parallel frontend capabilities, not replacements.

---

## M4 — Interactive Learning & Long-term Memory

M4 is entered from three frontend contexts:

1. **PaperWorkspace**: `canonical_paper.md` + M2 artifacts → paper-level selection explanation / formula explanation / single-paper Q&A / advisor drill
2. **DirectionWorkspace**: M1 direction_landscape + selected survey / anchors → direction-level Q&A / method-family comparison / reading-order explanation
3. **SeedExpansionPanel**: M1 paper_relation_graph → upstream/downstream explanation / follow-up paper recommendation / route explanation

### Paper-level interaction

**Schema / artifact contract**:
- `SelectionExplanation`
- `FormulaSymbolExplanation`
- `InteractiveAnswer`
- `AdvisorQuestion`
- `AdvisorEvaluation`

**Live validation contract**:
- real LLM
- real M2 artifacts
- real `evidence_ref` / memory references
- M4 paper-level answers must use M2 outputs and canonical evidence; they must not bypass M2 to read raw PDF and produce ungrounded answers

### Direction-level interaction

Example questions:
- "这个方向是怎么发展的？"
- "Transformer 相比 Autoencoder 解决了什么问题？"
- "Anomaly Transformer 后面有哪些改进？"
- "这个方向现在还有什么开放问题？"
- "如果我要找创新点，应该沿哪几条路线看？"

**Live validation contract**:
- real LLM
- real direction_landscape artifact
- real survey_landscape if available
- when direction-level Q&A drills into a concrete paper, that paper must enter M1 canonicalization and M2 evidence pipeline before paper-level explanation

### Seed-expansion interaction

Example questions:
- "这篇论文引用了谁？"
- "谁改进了它？"
- "后续哪些论文最值得看？"
- "它属于哪条技术路线？"

**Live validation contract**:
- real LLM
- real paper_relation_graph
- real seed paper metadata
- when seed-expansion Q&A drills into a concrete paper, that paper must enter M1 canonicalization and M2 evidence pipeline before paper-level explanation

Direction-level and seed-expansion interaction do NOT replace formula/symbol explanation. Formula/symbol explanation remains M4.2 core capability.

### Memory types

- `PaperMemory`
- `DirectionMemory`
- `MethodFamilyMemory`
- `StageMemory`
- `PaperRelationMemory`
- `UserLearningProgressMemory`

**Failure contract**:
- no evidence → degraded / rejected
- stale memory → verify before use
- no LLM → fail validation, not pass

**Current status**: DOC_DESIGNED / NOT_IMPLEMENTED

---

## M5 — Engineering Reliability

M5 defines the real-validation matrix for M1-M4 and the engineering rules for reliability, security, cost, debug/admin, and CI. M5 does not replace M1-M4 module-level tests.

### M1 Direction Exploration

**Schema / artifact contract**:
- `survey_candidates.json`
- `direction_landscape.json`
- `reading_plan.json`

**Live validation contract**:
- broad direction query uses real LLM and real network
- `survey_candidates` exists
- `direction_landscape` exists
- `method_families` is non-empty
- `chronology_stages` is non-empty
- `landscape_anchors` is non-empty
- `recommended_reading_order` is non-empty
- each landscape anchor has source / reason / verification status

**Failure contract**:
- no qualified survey and no staged-search result → failed direction exploration
- LLM JSON failure → failed
- source failure must be recorded, not hidden

**Current status**: NOT_IMPLEMENTED

### M1 Focused Acquisition

**Schema / artifact contract**:
- `query_plan.json`
- `candidate_pool.json`
- `source_resolution.json`
- current verified artifact path: validated PDF source for selected papers
- target canonical artifact path: `canonical_paper.md`
- `filtered_candidates.json`
- `reading_plan.json` with `A_READ_FOR_M2`

**Current verified PDF-only gate**:
- focused query uses real LLM and real network
- `sources_success >= 3`
- `pdf_download_success_count >= 1`
- every `A_READ_FOR_M2` is verified, relevant, PDF downloaded, `pdf_metadata_check=passed`, `pdf_title_match=match`, `can_enter_m2=true`

**Target canonical_paper.md gate**:
- focused query uses real LLM and real network
- `sources_success >= 3`
- every `A_READ_FOR_M2` is verified and relevant
- `source_type != metadata_only`
- `canonical_paper.md exists`
- `canonicalization_status in {success, degraded}`
- `m2_ready==true`

This target gate is DOC_DESIGNED / NOT_IMPLEMENTED.

**Failure contract**:
- missing LLM client → fail
- no verified relevant PDF → fail
- API 429/503 must be recorded with source metrics
- PDF mismatch cannot enter `A_READ_FOR_M2`
- canonical target failure (`metadata_only`, missing `canonical_paper.md`, `canonicalization_status=blocked`, or `m2_ready=false`) cannot enter M2

**Current status**: REAL_E2E_VERIFIED

### M1 Seed Paper Expansion

**Schema / artifact contract**:
- `seed_expansion_result.json`
- `paper_relation_graph.json`
- `upstream_papers`, `downstream_papers`, `related_surveys`, `follow_up_papers`

**Live validation contract**:
- real seed paper metadata
- real citation / reference / related-paper sources
- `paper_relation_graph` exists
- relations have `relation_type` and source evidence

**Failure contract**:
- no seed metadata → fail
- no relation evidence → degraded / failed, not fabricated

**Current status**: NOT_IMPLEMENTED

### M2 Paper Deep Reading

**Schema / artifact contract**:
- `canonical_paper.md`
- `parsed_document.json`
- `passage_index.json`
- `claim_evidence.json`
- `evidence_index.json`
- `paper_skeleton.json`
- `paper_card.json`
- `formula_cards.json`
- `teaching_cards.json`
- `understanding_status.json`
- `quality_report.json`

**Live validation contract**:
- real `canonical_paper.md`
- real M2 canonical reader output
- real LLM card generation
- `evidence_ref` traceable
- QualityAuditor runs on real artifacts
- formula_origin / formula_ocr_status preserved when formulas exist

**Failure contract**:
- missing or invalid canonical input → `BLOCKED_UNDERSTANDING`
- no passages / no claims / empty evidence pack → `BLOCKED_UNDERSTANDING`
- LLM failure / invalid JSON / invalid evidence_ref → `BLOCKED_UNDERSTANDING`
- audit BLOCK → `BLOCKED_UNDERSTANDING`

**Current status**: NOT_REAL_E2E_VERIFIED

### M1 / M2 Canonical Formula Chain

**Schema / artifact contract**:
- `canonical_paper.md`
- formula block metadata: `formula_id`, `formula_latex`, `formula_origin`, `formula_bbox`, `formula_page`, `formula_context_before`, `formula_context_after`, `formula_ocr_status`, `formula_explanation_status`

**Live validation contract**:
- one real paper
- one real formula region
- FormulaRegionDetector output when parser/layout source provides bbox
- FormulaOCRAdapter output when policy triggers
- M2 reads formula block and preserves origin

**Failure contract**:
- missing formula origin → formula explanation degraded or blocked
- OCR failure → `formula_ocr_status=failed`, not silent success
- `unknown` origin → detailed derivation blocked

**Current status**: DOC_DESIGNED / NOT_IMPLEMENTED

### M2 Survey Deep Reading

**Schema / artifact contract**:
- ordinary M2 artifacts
- `survey_landscape`
- `method_taxonomy`
- `extracted_key_papers`
- `survey_claims`

**Live validation contract**:
- real survey PDF
- `method_taxonomy` extracted with `evidence_ref`
- `extracted_key_papers` traceable to survey passages
- `survey_landscape` does not replace `paper_card`

**Failure contract**:
- no taxonomy evidence → no trusted `survey_landscape`
- extracted paper without source passage → cannot become key paper

**Current status**: NOT_IMPLEMENTED

### M3 Frontend

**Schema / artifact contract**:
- DirectionWorkspace consumes M1 direction artifacts
- PaperWorkspace consumes M2 understanding artifacts
- SeedExpansionPanel consumes M1 seed expansion artifacts

**Live validation contract**:
- real backend API smoke
- real PDF upload or real paper input
- status gating works
- blocked/baseline outputs do not expose cards
- direction and seed panels do not display unverified relations as trusted

**Failure contract**:
- missing status → show pending/error
- blocked status → do not show card content
- API failure → visible error

**Current status**: PARTIAL_CODE / PAGE_REAL_VALIDATION_MISSING

### M4 Interactive Learning

**Schema / artifact contract**:
- `SelectionExplanation`
- `FormulaSymbolExplanation`
- `InteractiveAnswer`
- `AdvisorQuestion`
- `AdvisorEvaluation`
- `PaperMemory` / `DirectionMemory` / `MethodFamilyMemory` / `StageMemory` / `PaperRelationMemory` / `UserLearningProgressMemory`

**Live validation contract**:
- real LLM
- real M2 artifacts
- real `evidence_ref` / memory references
- paper-level, direction-level, seed-expansion interactions tested separately

**Failure contract**:
- no evidence → degraded / rejected
- stale memory → verify before use
- no LLM → fail validation, not pass

**Current status**: DOC_DESIGNED / NOT_IMPLEMENTED

### M5 Reliability

**Schema / artifact contract**:
- `live_eval_report.json`
- test reports
- secret scan report
- CI release check result

**Live validation contract**:
- `python -m pytest -q` includes stable small real chain
- manual / nightly live validation covers network, LLM, OCR/parser heavy cases
- real LLM tests run with real env
- real network tests run with real network
- frontend build and tests pass
- secret scan passes
- no PDF / report / API key committed

**Failure contract**:
- missing key / network / quota → failure, not pass
- API limit → recorded failure / degraded, not hidden
- secret found → release blocked
- CI not configured → not production ready

**Current status**: PARTIAL_INFRA / NOT_PRODUCTION_READY

**Test policy**: `python -m pytest -q` runs stable small real chain. Manual / nightly live validation runs network, LLM, OCR/parser heavy cases. Missing env/key/network in live validation = failure, not skip. mock/fake/skip are not valid module completion evidence.
