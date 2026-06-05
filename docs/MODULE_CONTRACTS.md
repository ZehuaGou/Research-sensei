# ResearchSensei Module Contracts

> **Canonical docs**: See `docs/DESIGN.md`, `docs/DEVELOPMENT.md`, and `docs/development/*.md`.
>
> Module contracts distinguish:
> 1. **Schema / artifact contract** — what the module produces
> 2. **Live validation contract** — what real-world conditions must pass
> 3. **Failure contract** — what happens when things go wrong

---

## M1 — Literature Search & Direction Framework

M1 has two modes. See `docs/development/M1_LITERATURE_SEARCH.md`.

### Focused Acquisition Mode (C2)

**Schema / artifact contract**:

Input: user_query (narrow, e.g. "时间序列异常检测 transformer 方法")
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

### Direction Framework Mode (C1)

**Schema / artifact contract**:

Input: user_query (broad, e.g. "时间序列异常检测")
Output:
- `direction_landscape.json` — with `chronology_stage`, `method_family`, `landscape_anchor`, `representative_papers`, `recommended_reading_order`, `gaps_or_open_questions`

Boundary: `direction_landscape.json` does NOT replace `reading_plan.json`. `direction_landscape.json` serves direction understanding (C1). `reading_plan.json` serves reading plan (C2). `A_READ_FOR_M2` serves single-paper deep reading entry (C3).

**Status**: DOC_REQUIRED / NOT_IMPLEMENTED

---

## M2 — Single Paper Deep Reading (C3, C4)

M2 remains single-paper deep reading. M2 outputs also expose direction-support fields when evidence exists.

**Schema / artifact contract**:

Input: source file (PDF)
Output:
- `parsed_document.json`
- `passage_index.json`
- `claim_evidence.json`
- `evidence_index.json` (v1 compatibility)
- `paper_skeleton.json`
- `paper_card.json` / `formula_cards.json` / `teaching_cards.json`
- `understanding_status.json`
- `quality_report.json`

M2.3 paper_card should expose direction-support fields when evidence exists:
- `method_family`
- `contribution_to_direction`
- `what_problem_it_solves`
- `what_limitation_it_leaves`
- `relation_to_previous_methods`
- `relation_to_later_methods`
- `datasets_and_metrics`
- `comparable_methods`

M2.4 audit: direction-related fields must have `evidence_ref`. Comparison claims must have `evidence_ref`. Limitation / future work claims must have `evidence_ref`.

M2.5 gates: `direction_framework_update_allowed`, `cross_paper_comparison_allowed` (in addition to existing single-paper gates).

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

## M3 — API / Frontend (C1, C3, C5)

M3 has two workspaces:

### DirectionWorkspace (C1)

Displays:
- `direction_landscape`
- chronology stages
- method families
- landscape anchors
- recommended reading order
- gaps / open questions
- current SOTA candidates

### PaperWorkspace (C3)

Displays:
- `paper_card`
- `formula_cards`
- `teaching_cards`
- `evidence_ref` (future: passage-level jump)
- quality status

DirectionWorkspace and PaperWorkspace are parallel capabilities, not replacements.

**Schema / artifact contract**:

- `/understanding_status` — status gating
- `/cards` — paper cards (status-gated)
- `/artifacts` — debug/admin only
- DirectionWorkspace endpoints (future)

**Live validation contract**:

- Real API smoke: upload real small PDF → backend returns job / status / cards → frontend can display status

**Failure contract**:

- BASELINE_ONLY → 403 for normal users
- BLOCKED → 403 + blocking_reason
- SENSEI_DEBUG off → /artifacts returns 403

---

## M4 — Interactive Learning (C3, C5, C6)

M4 has two interaction levels:

### Paper-level interaction (C3, C5)

- Selected content explanation
- Formula / symbol explanation
- Single-paper Q&A

### Direction-level interaction (C1, C5)

- Direction evolution Q&A
- Method family comparison Q&A
- Representative paper relationship Q&A
- Advisor-style research route Q&A

Example direction-level questions:
- "这个方向是怎么发展的？"
- "Transformer 相比 Autoencoder 解决了什么问题？"
- "Anomaly Transformer 后面有哪些改进？"
- "这个方向现在还有什么开放问题？"
- "如果我要找创新点，应该沿哪几条路线看？"

Direction-level interaction does NOT replace formula/symbol explanation. Formula/symbol explanation remains M4.2 core capability.

### Memory types (C6)

- `PaperMemory`
- `DirectionMemory`
- `MethodFamilyMemory`
- `StageMemory`
- `PaperRelationMemory`
- `UserLearningProgressMemory`

**Status**: DOC_REQUIRED / NOT_IMPLEMENTED

---

## M5 — Engineering Reliability (C1-C6)

M5 defines reliability matrix across C1-C6, but does not replace module-level tests.

### C1 Direction Framework

- broad query live eval
- `direction_landscape.json` exists
- stages / method_families / anchors sufficient

### C2 Focused Acquisition

- focused query live eval
- `A_READ_FOR_M2` verified + PDF + title match

### C3 Single Paper Deep Reading

- real PDF parse
- `evidence_ref`
- paper/formula/teaching cards

### C4 Cross-paper Understanding

- `relation_to_previous_methods`
- comparison claims with evidence

### C5 Interactive Learning

- paper-level Q&A
- direction-level Q&A
- advisor questions

### C6 Long-term Memory

- paper memory
- direction memory
- method family memory

**Test policy**: `python -m pytest -q` runs all tests including `tests_live`. Missing env/key/network = failure, not skip. mock/fake/skip are not valid acceptance tests.
