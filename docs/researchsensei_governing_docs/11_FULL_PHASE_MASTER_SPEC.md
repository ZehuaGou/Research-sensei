# ResearchSensei Full Phase Master Spec

> **This document defines the complete phase lifecycle of ResearchSensei.**
> It is the authoritative reference for what each phase does, did, and will do.

---

## 1. Current Phase Status

| Phase | Status | Meaning |
|-------|--------|---------|
| Phase 1-11 | **baseline infrastructure complete** | Working code, 281 tests, rule-based baseline |
| Phase 11.5 | **route review complete** | External projects evaluated, architecture confirmed |
| Phase 11.6 | **detailed playbook ready** | Not yet authorized for code |
| Phase 11.7-11.9 | **playbook drafts ready** | Not yet authorized for code |
| Phase 12 | **frozen** | Patterns + Drill, requires 11.6-11.9 first |
| Phase 13+ | **roadmap only** | No code, no detailed playbooks |

---

## 2. Phase Classification Principles

| Phase Type | Documentation Level | Code Authorization |
|------------|--------------------|--------------------|
| Completed baseline (1-11) | Retrospective contract | N/A — already done |
| Immediate next (11.6) | Detailed playbook | Only after user confirms execution template |
| Near-future (11.7-11.9) | Playbook drafts | Not authorized — drafts only |
| Frozen (12) | Design-level spec | Not authorized — frozen |
| Far-future (13+) | Roadmap-level spec | Not authorized — roadmap only |

**Rule**: Every phase must have its detailed playbook written BEFORE code begins. The playbook must be filled into `06_PHASE_EXECUTION_TEMPLATE.md` and confirmed by the user.

---

## 3. Phase 1-11 Retrospective Baseline Contract

### Phase 1: Project Skeleton / CLI / FastAPI Health

| Item | Content |
|------|---------|
| Status | complete |
| Core files | `__init__.py`, `__main__.py` |
| Artifacts | N/A |
| Tests | `test_package_healthcheck.py` (4 tests) |
| Invariants | `python -m researchsensei` must work; `/health` endpoint must exist |
| Known limitations | CLI only has healthcheck subcommand |
| Future upgrade | No — sufficient as-is |
| Phase 12 blocker | No |

### Phase 2: Config / Logging / Errors / Schemas

| Item | Content |
|------|---------|
| Status | complete |
| Core files | `core/config.py`, `core/errors.py`, `core/logging.py`, `schemas/common.py`, `schemas/enums.py` |
| Artifacts | N/A |
| Tests | `test_core_config.py` (5), `test_core_errors_logging.py` (4), `test_schemas_core.py` (6) |
| Invariants | `StatusEnvelope` must serialize; API keys must not appear in logs |
| Known limitations | None |
| Future upgrade | No |
| Phase 12 blocker | No |

### Phase 3: Workspace / Job Store / Artifact Writing

| Item | Content |
|------|---------|
| Status | complete |
| Core files | `workspace/store.py`, `jobs/store.py` |
| Artifacts | workspace directory structure |
| Tests | `test_workspace_store.py` (4), `test_job_store.py` (4) |
| Invariants | `WorkspaceStore` creates run dirs; `JobStore` persists to SQLite |
| Known limitations | `aiosqlite` declared but unused (sync sqlite3 used) |
| Future upgrade | Remove unused aiosqlite dependency |
| Phase 12 blocker | No |

### Phase 4: Single Document Lightweight Parsing

| Item | Content |
|------|---------|
| Status | complete |
| Core files | `ingestion/lightweight.py` |
| Artifacts | `parsed_document.json` |
| Tests | `test_lightweight_ingestion.py` (4 tests) |
| Invariants | `.md`/`.txt`/`.pdf` must parse; unsupported types must degrade |
| Known limitations | PyMuPDF fallback quality low; no layout/table/formula extraction |
| Future upgrade | Phase 11.6 ParserAdapter |
| Phase 12 blocker | **YES** — better parsing needed for quality cards |

### Phase 5: Source Resolver + Parse API + Job/Artifact Query

| Item | Content |
|------|---------|
| Status | complete |
| Core files | `source_resolver.py`, `web/app.py` |
| Artifacts | `source_status.json` |
| Tests | `test_source_resolver.py` (10), `test_api_parse_sources.py` (8), `test_api_documents_parse.py` (5), `test_api_jobs_artifacts.py` (4) |
| Invariants | Path traversal must be rejected; URL scheme must be validated |
| Known limitations | None |
| Future upgrade | No |
| Phase 12 blocker | No |

### Phase 6: Grounding / Evidence Index + Paper Skeleton

| Item | Content |
|------|---------|
| Status | complete |
| Core files | `grounding.py`, `paper_skeleton.py`, `schemas/evidence.py`, `schemas/skeleton.py` |
| Artifacts | `evidence_index.json`, `paper_skeleton.json` |
| Tests | `test_phase6_evidence_schemas.py` (4), `test_phase6_grounding.py` (2), `test_phase6_paper_skeleton.py` (2) |
| Invariants | Claims must have evidence_type; missing evidence must be `INSUFFICIENT_EVIDENCE` |
| Known limitations | **Block-level evidence only — NOT claim-level grounding** |
| Future upgrade | Phase 11.7 PassageIndex + ClaimEvidence v2 |
| Phase 12 blocker | **YES** — block-level too coarse for quality patterns/drill |

### Phase 7: LLM Infrastructure

| Item | Content |
|------|---------|
| Status | complete |
| Core files | `llm/client.py`, `llm/prompt_builder.py`, `llm/response_cache.py`, `llm/token_budget.py`, `llm/types.py` |
| Artifacts | N/A |
| Tests | `test_llm_client.py` (24), `test_prompt_builder.py` (13), `test_response_cache.py` (18), `test_token_budget.py` (8), `test_llm_config.py` (7) |
| Invariants | All LLM calls through `llm/client.py`; MockLLMClient must be drop-in replacement |
| Known limitations | No real LLM integration tests |
| Future upgrade | No — infrastructure is complete |
| Phase 12 blocker | No |

### Phase 8: Evidence-Constrained Paper Card JSON v1

| Item | Content |
|------|---------|
| Status | **baseline complete** |
| Core files | `paper_card.py`, `schemas/cards.py` |
| Artifacts | `paper_card.json` |
| Tests | `test_paper_card_schema.py` (7), `test_paper_card_builder.py` (11) |
| Invariants | `core_idea` must have `evidence_ref` or degrade; LLM output must bind evidence |
| Known limitations | **Rule-based baseline only — NOT advisor-level teaching**; LLM-enhanced not in main pipeline |
| Future upgrade | Phase 11.8 evidence-constrained LLM |
| Phase 12 blocker | **YES** — rule-based baseline insufficient for quality patterns |

### Phase 9: Formula Card JSON v1

| Item | Content |
|------|---------|
| Status | **baseline complete** |
| Core files | `formula_card.py` |
| Artifacts | `formula_cards.json` |
| Tests | `test_formula_card_schema.py` (7), `test_formula_card_builder.py` (10) |
| Invariants | Symbols from generic dict must be `REASONABLE_INFERENCE`; FORMULA_UNAVAILABLE when no formulas |
| Known limitations | **Generic symbol dictionary — not paper-context grounding**; LLM-enhanced not in main pipeline |
| Future upgrade | Phase 11.8 paper-context symbol grounding |
| Phase 12 blocker | **YES** — generic symbols insufficient |

### Phase 10: Teaching Card JSON v1

| Item | Content |
|------|---------|
| Status | **baseline complete** |
| Core files | `teaching_card.py` |
| Artifacts | `teaching_cards.json` |
| Tests | `test_teaching_card_schema.py` (5), `test_teaching_card_builder.py` (17) |
| Invariants | `human_explanation` must not be formula text; formula-heavy must trigger conservative fallback |
| Known limitations | **Rule-based baseline only — NOT advisor-level teaching**; LLM-enhanced not in main pipeline |
| Future upgrade | Phase 11.8 evidence-constrained five-layer |
| Phase 12 blocker | **YES** — rule-based baseline insufficient |

### Phase 11: Query / Acquisition / Selection / Reading Plan v1

| Item | Content |
|------|---------|
| Status | complete |
| Core files | `query/planner.py`, `acquisition/arxiv_adapter.py`, `acquisition/openalex_adapter.py`, `selection/service.py`, `direction/runner.py` |
| Artifacts | `query_plan.json`, `candidate_pool.json`, `filtered_candidates.json`, `reading_plan.json` |
| Tests | `test_query_planner.py` (5), `test_acquisition_adapters.py` (7), `test_direction_runner.py` (7), `test_direction_schemas.py` (10), `test_selection_service.py` (16) |
| Invariants | Three-way dedup (DOI/arXiv/title); A_READ ≤ 12; filtered_candidates.json written |
| Known limitations | **Direction pipeline v1 — NOT complete literature review**; Chinese fallback degrades |
| Future upgrade | Phase 13 cross-paper synthesis |
| Phase 12 blocker | No |

---

## 4. Phase 11.6-11.9 Detailed Upgrade Plan

### Phase 11.6: ParserAdapter Design

**Detailed playbook**: `17_PHASE_11_6_DETAILED_PLAYBOOK.md`

| Item | Content |
|------|---------|
| Goal | ParserAdapter interface + LightweightParserAdapter wrapper |
| Non-goal | No new dependencies, no Docling/Nougat/Marker, no pipeline changes |
| Allowed files | `src/researchsensei/parser/__init__.py`, `adapter.py`, `lightweight_adapter.py`, `tests/test_parser_adapter.py` |
| Forbidden files | `ingestion/`, `web/`, `frontend/`, `backend/`, `pyproject.toml` |
| New classes | `ParserAdapter` (ABC), `LightweightParserAdapter` |
| Input | Source file (PDF/MD/TXT) |
| Output | `parsed_document.json` (backward compatible) |
| Compatibility | `DocumentIngestion.model_dump()` must match original parser |
| Tests | 10 tests: abstract check, supports, reject unsupported, match original output, round-trip, no artifacts, injected service, degraded behavior |
| Hard-fail | New dependency, modify ingestion, output incompatible, real network/LLM |

### Phase 11.7: PassageIndex + ClaimEvidence v2

**Detailed playbook draft**: `13_PHASE_11_7_DETAILED_PLAYBOOK_DRAFT.md`

| Item | Content |
|------|---------|
| Goal | Upgrade evidence from block-level to passage-level with claim extraction |
| Non-goal | No LLM-based claim extraction, no vector DB, no new dependencies |
| Allowed files | `src/researchsensei/evidence/` (new), `schemas/evidence.py` (modify), tests |
| Forbidden files | `ingestion/`, `web/`, `frontend/`, `backend/` |
| New classes | `PassageIndex`, `ClaimExtractor`, `EvidenceRetriever` |
| Schema changes | `ClaimEvidence` gets optional v2 fields: `passage_id`, `semantic_type`, `claim_type` |
| Input | `parsed_document.json` |
| Output | `evidence_index.json` (v2, backward compatible) |
| claim_type candidates | `HYPOTHESIS`, `METHOD`, `RESULT`, `LIMITATION`, `CONTRIBUTION`, `DEFINITION` |
| semantic_support | Claim text semantically related to passage text (not just block_id match) |
| Tests | Passage indexing, claim extraction, retrieval, backward compatibility |
| Hard-fail | Block-level only, no claim extraction, modify parser |

### Phase 11.8: Evidence-constrained LLM Paper Understanding

**Detailed playbook draft**: `14_PHASE_11_8_DETAILED_PLAYBOOK_DRAFT.md`

| Item | Content |
|------|---------|
| Goal | Wire LLM-enhanced card builders into main pipeline with evidence constraints |
| Non-goal | No real LLM in default tests, no new dependencies |
| Allowed files | `ingestion/pipeline.py` (modify), `paper_card.py`, `formula_card.py`, `teaching_card.py` (modify), tests |
| Forbidden files | `web/`, `frontend/`, `backend/` |
| Changes | Add LLM path to SinglePaperIngestionRunner; strengthen evidence_ref validation |
| LLM policy | MockLLMClient only in default tests; real LLM separate mark |
| Evidence constraint | All LLM output must have valid evidence_ref; hallucinated refs rejected |
| Fallback | LLM failure → rule-based baseline |
| v2 quality | paper_card: core_idea ≠ method_overview; formula: symbols from context; teaching: no formula-as-explanation |
| Tests | MockLLMClient tests, evidence constraint, fallback, hard-fail conditions |
| Hard-fail | Real LLM in default tests, invalid evidence_ref accepted, no fallback |

### Phase 11.9: Paper Understanding Quality Benchmark

**Detailed playbook draft**: `15_PHASE_11_9_DETAILED_PLAYBOOK_DRAFT.md`

| Item | Content |
|------|---------|
| Goal | Quality benchmark with fixtures, audits, hard-fail tests |
| Non-goal | No real LLM, no new dependencies |
| Allowed files | `tests/fixtures/quality/` (extend), `tests/test_*_audit.py` (new), docs |
| Forbidden files | `src/` (except if needed for audit helpers), `frontend/`, `backend/` |
| Benchmark fixtures | method paper, formula-heavy paper, minimal paper |
| Audits | explanation audit, formula audit, evidence audit |
| Hard-fail conditions | HF-1 through HF-6 (see `07_TEST_AND_QUALITY_PLAN.md`) |
| Audit report | JSON + human-readable summary |
| Gate | All hard-fail tests must pass before Phase 12 unfreezes |

---

## 5. Phase 12+ Future Roadmap

### Phase 12: Patterns + Drill (FROZEN)

| Item | Content |
|------|---------|
| Status | **frozen** |
| Unfreeze condition | Phase 11.6-11.9 complete + quality gates pass + user confirms |
| Goal | PatternCard + DrillCard generation |
| Non-goal | No spaced repetition scheduling (deferred) |
| Input artifacts | `paper_skeleton.json` (v2), `paper_card.json` (v2), `formula_cards.json` (v2) |
| Output artifacts | `pattern_cards.json`, `drill_cards.json` |
| Constraint | Must use v2 paper understanding, NOT rule-based baseline |
| Pre-authorization | Must write detailed playbook before code |
| Pattern categories | Representation, Objective, Structure, Generation, Retrieval/Memory, Reasoning/Planning, Causal/Counterfactual, Evaluation, System Pipeline |
| Drill categories | immediate_recall, advisor_questions, error_attribution_prompts |

### Phase 13: Direction Map / Cross-paper Understanding

| Item | Content |
|------|---------|
| Status | roadmap only |
| Goal | Problem-driven direction map from multiple paper skeletons |
| Dependencies | Phase 11 direction pipeline + A_READ paper understanding |
| Output | `direction_map.json` |
| Constraint | Must be problem-driven evolution chain, not just paper list |
| Reference | STORM outline-guided design |

### Phase 14: Frontend / Render Integration

| Item | Content |
|------|---------|
| Status | roadmap only |
| Goal | Backend artifact → Vue frontend page mapping |
| Dependencies | Stable backend API |
| Scope | Formula rendering (KaTeX), evidence display, card layout |
| Constraint | Do not rewrite frontend before backend is stable |

### Phase 15: Advisor / Interactive QA

| Item | Content |
|------|---------|
| Status | roadmap only |
| Goal | Context-aware Q&A with evidence grounding |
| Dependencies | Evidence pack, audit layer |
| Constraint | Do not send entire paper to prompt; use evidence retriever |
| Reference | ARIS reviewer independence concept |

### Phase 16: Engineering Reliability

| Item | Content |
|------|---------|
| Status | roadmap only |
| Goal | Checkpoint resume, caching, logging, artifact versioning, security |
| Constraint | Original Phase 12 from dev docs, deferred here |

### Phase 17: Live Smoke / Real Paper Benchmark

| Item | Content |
|------|---------|
| Status | roadmap only |
| Goal | Real paper end-to-end evaluation |
| Constraint | Must be separate from default pytest; `@pytest.mark.live` |

### Phase 18: Packaging / Deployment

| Item | Content |
|------|---------|
| Status | roadmap only |
| Goal | README, CLI, Windows PowerShell, local run, deployment docs |
