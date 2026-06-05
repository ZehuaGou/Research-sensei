# ResearchSensei Module Contracts

> **Canonical docs**: See `docs/DESIGN.md`, `docs/DEVELOPMENT.md`, and `docs/development/*.md`.
>
> Module contracts distinguish:
> 1. **Schema / artifact contract** — what the module produces
> 2. **Live validation contract** — what real-world conditions must pass
> 3. **Failure contract** — what happens when things go wrong

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

**Status**: NOT_IMPLEMENTED

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

- `sources_success >= 3`
- `verified_candidate_count` exists
- `pdf_download_success_count >= 1`
- Every `A_READ` has: `verification_status == verified`, `llm_relevance_score >= 0.65`, `llm_relevance_label in {HIGH, MEDIUM}`, `should_a_read == true`, `pdf_downloaded == true`, `pdf_metadata_check == passed`, `pdf_title_match == match`, `can_enter_m2 == true`

**Failure contract**:

- Missing LLM client → `QueryPlanningError`
- LLM JSON parse failure → `QueryPlanningError`
- Source 429/503 → retry with backoff, then structured error in `source_metrics`
- PDF download failure → `FAILED_DOWNLOAD` status, not silently skipped
- Verification API failure → `verify_pending`, not `unverified`

**Status**: REAL_E2E_VERIFIED

### Seed Paper Expansion Mode

**Schema / artifact contract**:

Input: seed paper metadata / paper_id / uploaded paper
Output:
- `paper_relation_graph.json`
- `seed_expansion_result.json`
- `upstream_papers`, `downstream_papers`, `related_surveys`, `follow_up_papers`

**Status**: NOT_IMPLEMENTED

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

- Real PDF parse (not synthetic)
- `evidence_ref` exists for claims
- paper_card / formula_cards / teaching_cards generated with real LLM
- QualityAuditor runs with real artifacts

**Failure contract**:

- Parser failure → `FAILED`
- No passages → `BLOCKED_UNDERSTANDING`
- LLM failure → `BLOCKED_UNDERSTANDING`
- Audit BLOCK → `BLOCKED_UNDERSTANDING`

---

## M3 — API / Frontend

M3 has three frontend areas:

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

Status: NOT_IMPLEMENTED

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

### SeedExpansionPanel

Displays:
- upstream papers
- downstream papers
- related surveys
- follow-up improvements
- same-route papers
- one-click deep-read buttons

Status: NOT_IMPLEMENTED

DirectionWorkspace, PaperWorkspace, and SeedExpansionPanel are parallel frontend capabilities, not replacements.

**Schema / artifact contract**:

- `/understanding_status` — status gating
- `/cards` — paper cards (status-gated)
- `/artifacts` — debug/admin only
- DirectionWorkspace endpoints (future)
- SeedExpansionPanel endpoints (future)

**Live validation contract**:

- Real API smoke: upload real small PDF → backend returns job / status / cards → frontend can display status

**Failure contract**:

- BASELINE_ONLY → 403 for normal users
- BLOCKED → 403 + blocking_reason
- SENSEI_DEBUG off → /artifacts returns 403

---

## M4 — Interactive Learning & Long-term Memory

M4 has three interaction types:

### Paper-level interaction

- Selected content explanation
- Formula / symbol explanation
- Method mechanism explanation
- Single-paper Q&A

### Direction-level interaction

- Direction evolution Q&A
- Method family comparison Q&A
- Representative paper relationship Q&A
- Advisor-style research route Q&A

Example questions:
- "这个方向是怎么发展的？"
- "Transformer 相比 Autoencoder 解决了什么问题？"
- "Anomaly Transformer 后面有哪些改进？"
- "这个方向现在还有什么开放问题？"
- "如果我要找创新点，应该沿哪几条路线看？"

### Seed-expansion interaction

- "这篇论文引用了谁？"
- "谁改进了它？"
- "后续哪些论文最值得看？"
- "它属于哪条技术路线？"

Direction-level and seed-expansion interaction do NOT replace formula/symbol explanation. Formula/symbol explanation remains M4.2 core capability.

### Memory types

- `PaperMemory`
- `DirectionMemory`
- `MethodFamilyMemory`
- `StageMemory`
- `PaperRelationMemory`
- `UserLearningProgressMemory`

**Status**: DOC_REQUIRED / NOT_IMPLEMENTED

---

## M5 — Engineering Reliability

M5 defines real-validation matrix across M1-M4, but does not replace module-level tests.

### M1 Direction Exploration

- broad direction query live eval
- survey_candidates exists
- direction_landscape exists
- method families and stages sufficient

### M1 Focused Acquisition

- focused query live eval
- A_READ_FOR_M2 verified + PDF + title match

### M1 Seed Paper Expansion

- seed paper → upstream/downstream/related surveys
- paper_relation_graph exists

### M2 Paper Deep Reading

- uploaded PDF real parse
- downloaded PDF real parse
- paper/formula/teaching cards
- evidence_ref

### M2 Survey Deep Reading

- survey PDF parse
- method_taxonomy
- extracted_key_papers

### M3 Frontend

- DirectionWorkspace
- PaperWorkspace
- SeedExpansionPanel

### M4 Interactive Learning

- paper-level Q&A
- direction-level Q&A
- seed-expansion Q&A
- advisor questions

### M5 Reliability

- real tests
- secret scan
- cost control
- CI
- no PDF/report/API key committed

M5 does NOT replace M1-M4 submodule tests.

**Test policy**: `python -m pytest -q` runs all tests including `tests_live`. Missing env/key/network = failure, not skip. mock/fake/skip are not valid acceptance tests.
