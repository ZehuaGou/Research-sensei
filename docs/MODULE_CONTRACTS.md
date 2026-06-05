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

M1 has three modes. See `docs/development/M1_LITERATURE_SEARCH.md`.

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
- `filtered_candidates.json` — final candidates with verification/LLM relevance/PDF fields
- `reading_plan.json` — with `A_READ_FOR_M2` papers

Boundary: Does not parse full papers. Does not generate paper cards.

**Live validation contract**:

- focused query uses real LLM and real network
- `sources_success >= 3`
- `verified_candidate_count` exists
- `llm_judged_candidate_count` exists
- `pdf_download_success_count >= 1`
- every `A_READ_FOR_M2` has: `verification_status == verified`, `llm_relevance_score >= 0.65`, `llm_relevance_label in {HIGH, MEDIUM}`, `should_a_read == true`, `pdf_downloaded == true`, `pdf_metadata_check == passed`, `pdf_title_match == match`, `can_enter_m2 == true`

**Failure contract**:

- Missing LLM client → `QueryPlanningError`
- LLM JSON parse failure → `QueryPlanningError`
- Source 429/503 → retry with backoff, then structured error in `source_metrics`
- PDF download failure → `FAILED_DOWNLOAD` status, not silently skipped
- Verification API failure → `verify_pending`, not `unverified`
- PDF mismatch cannot enter `A_READ_FOR_M2`

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

Input: uploaded PDF / downloaded PDF / paper URL / paper metadata
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

- real PDF input (not synthetic)
- real parser output
- real LLM card generation
- `evidence_ref` traceable
- QualityAuditor runs on real artifacts

**Failure contract**:

- parser failure → `FAILED`
- no passages / no claims / empty evidence pack → `BLOCKED_UNDERSTANDING`
- LLM failure / invalid JSON / invalid evidence_ref → `BLOCKED_UNDERSTANDING`
- audit BLOCK → `BLOCKED_UNDERSTANDING`

**Current status**: partial code exists; real PDF + real LLM + real audit e2e not yet verified

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
