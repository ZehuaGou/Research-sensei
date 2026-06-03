# ResearchSensei Implementation Roadmap

---

## Current State

- Phase 1-11: baseline infrastructure complete
- Phase 11.5: route review complete
- Phase 12: frozen

---

## Phase 11.6: ParserAdapter Design

**Goal**: Design ParserAdapter interface, wrap existing parser as default adapter.

**What to build**:
- `ParserAdapter` interface (abstract base class)
- `LightweightParserAdapter` wrapping existing `LightweightIngestionService`
- Contract tests for the interface
- No new dependencies

**What NOT to build**:
- No Docling/Nougat/Marker real integration
- No new dependencies
- No changes to existing parser behavior
- No frontend changes
- No old backend changes

**Authorized files**:
- `src/researchsensei/parser/__init__.py` (new)
- `src/researchsensei/parser/adapter.py` (new — interface)
- `src/researchsensei/parser/lightweight_adapter.py` (new — wrapper)
- `tests/test_parser_adapter.py` (new)
- `docs/` updates

**Forbidden files**:
- `src/researchsensei/ingestion/` (do not modify existing)
- `src/researchsensei/web/` (do not modify)
- `frontend/` (do not modify)
- `backend/` (do not modify)

**Input artifacts**: parsed_document.json (existing format)
**Output artifacts**: parsed_document.json (same format, different generator)
**Schema changes**: none — output must be compatible
**Tests**: contract tests proving interface works with existing parser
**Quality gate**: existing 281 tests still pass
**Completion criteria**: ParserAdapter interface defined, LightweightParserAdapter wraps existing parser, contract tests pass

---

## Phase 11.7: PassageIndex + ClaimEvidence v2

**Goal**: Upgrade evidence from block-level to passage-level with claim extraction.

**What to build**:
- PassageIndex (passage-level text indexing)
- ClaimExtractor (rule-based claim extraction)
- ClaimEvidence v2 (semantic support)
- EvidenceRetriever (claim → passage retrieval)

**What NOT to build**:
- No LLM-based claim extraction
- No vector database
- No new dependencies

**Authorized files**:
- `src/researchsensei/evidence/__init__.py` (new)
- `src/researchsensei/evidence/passage_index.py` (new)
- `src/researchsensei/evidence/claim_extractor.py` (new)
- `src/researchsensei/evidence/retriever.py` (new)
- `src/researchsensei/schemas/evidence.py` (modify — add v2 fields)
- `tests/test_passage_index.py` (new)
- `tests/test_claim_extractor.py` (new)
- `tests/test_evidence_retriever.py` (new)
- `docs/` updates

**Input artifacts**: parsed_document.json
**Output artifacts**: evidence_index.json (v2 format, backward compatible)
**Schema changes**: ClaimEvidence gets optional v2 fields (passage_id, semantic_type)
**Tests**: claim extraction tests, passage retrieval tests
**Quality gate**: existing tests still pass, new tests cover claim extraction

---

## Phase 11.8: Evidence-constrained LLM Paper Understanding

**Goal**: Wire LLM-enhanced card builders into main pipeline with evidence constraints.

**What to build**:
- Connect `build_paper_card_with_llm` to SinglePaperIngestionRunner
- Connect `build_formula_cards_with_llm` to SinglePaperIngestionRunner
- Connect `build_teaching_cards_with_llm` to SinglePaperIngestionRunner
- Evidence constraint enforcement (all LLM output must have valid evidence_ref)
- Fallback to rule-based on LLM failure

**What NOT to build**:
- No real LLM calls in default tests
- No new dependencies
- No frontend changes

**Authorized files**:
- `src/researchsensei/ingestion/pipeline.py` (modify — add LLM path)
- `src/researchsensei/paper_card.py` (modify — strengthen evidence constraint)
- `src/researchsensei/formula_card.py` (modify — strengthen evidence constraint)
- `src/researchsensei/teaching_card.py` (modify — strengthen evidence constraint)
- `tests/test_llm_paper_understanding.py` (new)
- `docs/` updates

**Input artifacts**: evidence_index.json, paper_skeleton.json
**Output artifacts**: paper_card.json, formula_cards.json, teaching_cards.json (v2 quality)
**Schema changes**: none — same schema, better content
**Tests**: MockLLMClient tests, evidence constraint tests, fallback tests
**Quality gate**: hard-fail conditions pass, existing tests still pass

---

## Phase 11.9: Paper Understanding Quality Benchmark

**Goal**: Establish quality benchmark with fixtures and audit tests.

**What to build**:
- Fixture papers (method, formula-heavy, minimal)
- Explanation audit tests
- Formula audit tests
- Evidence audit tests
- Quality benchmark report

**What NOT to build**:
- No real LLM calls
- No new dependencies

**Authorized files**:
- `tests/fixtures/quality/` (extend)
- `tests/test_explanation_audit.py` (new)
- `tests/test_formula_audit.py` (new)
- `tests/test_evidence_audit.py` (new)
- `docs/QUALITY_EVALUATION_SPEC.md` (update)
- `docs/` updates

**Input artifacts**: all card artifacts
**Output artifacts**: audit reports
**Schema changes**: none
**Tests**: audit tests covering all hard-fail conditions
**Quality gate**: all hard-fail tests pass

---

## Phase 12: Patterns + Drill (FROZEN)

**Goal**: PatternCard and DrillCard generation.

**Status**: FROZEN. Only resumes after Phase 11.6-11.9 complete and quality gates pass.

**Why frozen**: Patterns and drill need good paper understanding. Rule-based baseline is insufficient. Phase 11.6-11.9 upgrades the understanding core first.

**When unfrozen**:
- Phase 11.6-11.9 all complete
- Quality gates pass
- User confirms
- Reuse gate updated

**What to build** (when unfrozen):
- PatternCard schema + builder
- DrillCard schema + builder
- Integration into SinglePaperIngestionRunner
- Quality tests

---

## Execution Rules

1. **Every phase must use the execution template** (`06_PHASE_EXECUTION_TEMPLATE.md`).
2. **Every phase must have a reuse gate** before code.
3. **Every phase must have tests** before moving to next.
4. **Every phase must update docs** before moving to next.
5. **No phase may modify files not authorized.**
6. **No phase may introduce dependencies without reuse gate.**
7. **No phase may use real network/LLM in default tests.**
