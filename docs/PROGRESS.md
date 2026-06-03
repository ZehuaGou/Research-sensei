# ResearchSensei Progress

## Current Phase

Phase 1-11 complete as baseline infrastructure. Phase 12 frozen.
Pre-Phase12 technology route reset in progress. No Phase 12 code authorized.

## Current Status

- Project audit completed.
- Recommended route accepted: B - keep useful code, rebuild backend core architecture.
- Current `backend/` is frozen as migration source.
- Current `frontend/` is preserved as the Vue learning workspace.
- New backend target package: `src/researchsensei/`.
- Phase 1 package skeleton, CLI healthcheck, and basic FastAPI health app are implemented and tested.
- Phase 2 config service, safe logging/error types, base schemas, and `StatusEnvelope` are implemented and tested.
- Phase 3 workspace store, artifact writing, run/search directory management, and SQLite job store are implemented and tested.
- Phase 4 local `.md`, `.txt`, and `.pdf` lightweight ingestion is implemented and tested.
- Single-paper ingestion runner now creates a run directory, copies the source file, writes `parsed_document.json`, and updates SQLite job state.
- Default `pytest -q` no longer collects the legacy live `tests/smoke_test.py`.
- Phase 5.1 FastAPI `POST /api/v1/documents/parse` upload parsing is implemented and tested.
- Phase 5 upload API was corrected to use standard FastAPI `UploadFile = File(...)` multipart handling.
- Project-local `.venv` was created for dependency installation and testing.
- `python-multipart` is now recorded as a project dependency.
- Phase 5.2 job and artifact query APIs are implemented and tested.
- Phase 5.3 minimal source resolver is implemented and tested for local files, mocked PDF URLs, and arXiv IDs/URLs.
- Phase 5.4 parse flow is integrated with source resolver for upload, local_path, pdf_url, arxiv_id, and arxiv_url inputs.
- Every successful parse now writes both `source_status.json` and `parsed_document.json`.
- Source resolution failures write `source_status.json` and record a failed job without entering ingestion.
- Default `.venv` test command completed successfully: `111 passed`.
- Global reuse-first gate added: before any new major Phase, `docs/REUSE_REPORT.md` must be updated with candidate tool/API evaluation before business code is authorized.
- Phase 6 reuse gate completed; no new hard dependencies were authorized.
- Phase 6.1 evidence schemas are implemented: `EvidenceType`, `ClaimEvidence`, `EvidenceIndex`, and `PaperSkeleton`.
- Phase 6.2 lightweight grounding is implemented: `DocumentIngestion.blocks` now produce conservative `evidence_index.json`.
- Phase 6.3/6.4 conservative paper skeleton generation is implemented: missing or unsupported fields are marked `UNKNOWN`, `INSUFFICIENT_EVIDENCE`, or `NEEDS_HUMAN_CHECK`.
- Phase 6.5 parse flow now writes four artifacts for successful parses: `source_status.json`, `parsed_document.json`, `evidence_index.json`, and `paper_skeleton.json`.
- Phase 6 avoids LLM, RAG, vector databases, teaching, formula tutoring, direction maps, drills, interactive advisor logic, and frontend changes.
- Final Phase 6 verification in the project `.venv`: `python -m pytest -q` returned `122 passed`.

## Current Technical Decisions

- Backend will be rebuilt as a standard Python package under `src/researchsensei/`.
- Vue 3 + Vite + TypeScript + Pinia + TailwindCSS + KaTeX frontend remains.
- Architecture remains frontend/backend separated.
- React will not be introduced.
- Old `backend/` will not receive new product features.
- Old `frontend/` will not be rewritten during backend migration.
- Old `backend/web.py`, `backend/render.py`, old README sections, and default live smoke test are replacement targets, not expansion targets.

## Completed Tasks

- [x] Read full development documentation package.
- [x] Audit current project state.
- [x] Identify mismatch between docs and current package layout.
- [x] Select migration route B.
- [x] Record architecture decision in `docs/ARCHITECTURE_DECISION.md`.
- [x] Record migration plan in `docs/MIGRATION_PLAN.md`.
- [x] Create `src/researchsensei/` package skeleton.
- [x] Add `python -m researchsensei` CLI healthcheck.
- [x] Add basic FastAPI app factory with `/health`.
- [x] Add package healthcheck tests.
- [x] Migrate config loading to `src/researchsensei/core/config.py`.
- [x] Add safe error types and logging redaction helpers.
- [x] Add base schema package and `StatusEnvelope`.
- [x] Add Phase 2 unit tests.
- [x] Add workspace store under `src/researchsensei/workspace/`.
- [x] Add SQLite job store under `src/researchsensei/jobs/`.
- [x] Add Phase 3 unit tests.
- [x] Add lightweight local file ingestion under `src/researchsensei/ingestion/`.
- [x] Add single-paper ingestion runner for source copy, parsed artifact, and job update.
- [x] Exclude legacy live smoke test from default pytest collection.
- [x] Run default `pytest -q`: 84 passed.
- [x] Phase 5.1: add upload parse API around the Phase 4 ingestion runner.
- [x] Correct Phase 5.1 upload implementation to standard FastAPI multipart upload.
- [x] Add `python-multipart` to `pyproject.toml`.
- [x] Create project-local `.venv` and install `.[dev]`.
- [x] Phase 5.2: add `GET /api/v1/jobs`, `GET /api/v1/jobs/{job_id}`, and `GET /api/v1/jobs/{job_id}/artifacts`.
- [x] Add artifact path traversal protection.
- [x] Run default `.venv` pytest command: 92 passed.
- [x] Phase 5.3: add `SourceResolver` with local path, PDF URL, arXiv ID, and arXiv URL support.
- [x] Add `SourceStatus` schema and `source_status.json` artifact.
- [x] Phase 5.4: connect source resolver to `POST /api/v1/documents/parse`.
- [x] Add mocked network tests for PDF URL and arXiv download paths.
- [x] Add parse API tests for upload, local_path, pdf_url, arxiv_id, arxiv_url, and path traversal rejection.
- [x] Final Phase 5 verification: `.venv` `python -m pytest -q` returned 111 passed.
- [x] Add global no-rebuilding-mature-wheels gate to `docs/REUSE_REPORT.md`.
- [x] Complete Phase 6 reuse gate with no new hard dependencies.
- [x] Add strict Phase 6 evidence and skeleton schemas.
- [x] Add lightweight rule-based grounding over parsed document blocks.
- [x] Add conservative paper skeleton generation over parsed document blocks and evidence index.
- [x] Integrate `evidence_index.json` and `paper_skeleton.json` into successful parse flow.
- [x] Add Phase 6 schema, grounding, skeleton, runner, and API tests.
- [x] Final Phase 6 verification: `.venv` `python -m pytest -q` returned 122 passed.
- [x] Takeover audit completed: all Phase 6 code verified, tests pass, no half-finished modules.
- [x] Created `docs/OPEN_QUESTIONS.md` with pending decisions.
- [x] Created `docs/PHASE_MAPPING.md` documenting migration Phase numbering vs original docs.
- [x] Updated `.gitignore` with `node_modules/`, `frontend/node_modules/`, `dist/`, `outputs/`.
- [x] Committed Phase 6 code to git.
- [x] Phase 7 reuse gate completed: evaluated OpenAI SDK, LiteLLM, tenacity, tiktoken, httpx, old backend/llm code.
- [x] Phase 7 decision: migrate old backend/llm with httpx + pydantic; no new dependencies; defer tenacity/tiktoken/LiteLLM/OpenAI SDK.
- [x] Phase 7.1: LLM types (ChatMessage, ChatResponse, LLMConfig) and provider config.
- [x] Phase 7.2: LLMClient with chat/chat_json/chat_stream, OpenAI-compatible, httpx, retry, mock mode, JSON repair.
- [x] Phase 7.3: PromptBuilder with system/context/evidence/user sections and instruction isolation.
- [x] Phase 7.4: ResponseCache with SHA256 keys, TTL, version/model invalidation, hit/miss stats.
- [x] Phase 7.5: TokenBudget with character-based estimation and truncation suggestions.
- [x] Phase 7.6: MockLLMClient for downstream testing.
- [x] Phase 7.7: 48 new tests covering all LLM components; total 170 passed.
- [x] Phase 1-7 comprehensive audit completed: `docs/PHASE_1_7_REVIEW.md` generated.
- [x] Pre-Phase 8 cleanup: moved 12 old backend tests to `legacy_tests/`, smoke_test to `tests_e2e/`.
- [x] Pre-Phase 8 cleanup: fixed `source_resolver.py` exception handling (capture + log).
- [x] Pre-Phase 8 cleanup: cleaned 91 stale .pyc files from `tests/__pycache__/`.
- [x] Pre-Phase 8 cleanup: added explicit `--ignore` for legacy_tests/ and tests_e2e/ in pyproject.toml.
- [x] Phase 8 reuse gate completed: evaluated old backend/understanding.py, backend/teaching.py, no new dependencies.
- [x] Phase 8.1: PaperCard and CardClaim schemas with evidence binding.
- [x] Phase 8.2: Rule-based build_paper_card() from skeleton + evidence_index.
- [x] Phase 8.3: LLM-enhanced build_paper_card_with_llm() with evidence constraint enforcement.
- [x] Phase 8.4: Integrated paper_card.json into parse flow (5th artifact).
- [x] Phase 8.5: 17 new tests covering schema, rule-based, LLM-enhanced, fallback, evidence binding.
- [x] Phase 8.6: Final verification: 161 passed.
- [x] Phase 9 reuse gate completed: evaluated old backend/formula.py, no new dependencies.
- [x] Phase 9.1: FormulaCard, FormulaSymbol, FormulaTerm, FormulaCardBundle schemas.
- [x] Phase 9.2: Rule-based build_formula_cards() from parsed document blocks.
- [x] Phase 9.3: LLM-enhanced build_formula_cards_with_llm() with evidence constraint enforcement.
- [x] Phase 9.4: Integrated formula_cards.json into parse flow (6th artifact).
- [x] Phase 9.5: 19 new tests covering schema, rule-based, LLM-enhanced, fallback, FORMULA_UNAVAILABLE.
- [x] Phase 9.6: Final verification: 180 passed.
- [x] Phase 10 reuse gate completed: evaluated old backend/teaching.py, no new dependencies.
- [x] Phase 10.1: TeachingCard and TeachingCardBundle schemas with 5-layer structure.
- [x] Phase 10.2: Rule-based build_teaching_cards() from paper_card + formula_cards + skeleton.
- [x] Phase 10.3: LLM-enhanced build_teaching_cards_with_llm() with evidence constraint enforcement.
- [x] Phase 10.4: Integrated teaching_cards.json into parse flow (7th artifact).
- [x] Phase 10.5: 15 new tests covering schema, rule-based, LLM-enhanced, fallback, 5-layer completeness.
- [x] Phase 10.6: Final verification: 195 passed.
- [x] Phase 10 focused review: identified H1/M1/M2/M3 issues in `docs/PHASE_10_REVIEW.md`.
- [x] Phase 10 fix: H1 formula-heavy human_explanation detection and conservative fallback.
- [x] Phase 10 fix: M1 specific paper_role_explanation templates.
- [x] Phase 10 fix: M2 formula teaching card human_explanation fallback chain.
- [x] Phase 10 fix: M3 added 7 content quality tests; total 202 passed.
- [x] **Note**: Phase 8-10 main pipeline (SinglePaperIngestionRunner) uses **rule-based builders only**. LLM-enhanced functions (`build_paper_card_with_llm`, `build_formula_cards_with_llm`, `build_teaching_cards_with_llm`) exist and are tested with MockLLMClient, but are **not wired into the main pipeline**. LLM integration into the pipeline is deferred to a future phase.
- [x] Phase 11 reuse gate completed: evaluated arXiv/OpenAlex adapters, no new dependencies.
- [x] Phase 11.1: QueryPlan, CandidatePaper, CandidatePool, ReadingPlan, ScoringBreakdown schemas.
- [x] Phase 11.2: QueryPlanner with rule-based + LLM-enhanced query planning.
- [x] Phase 11.3: ArxivAdapter with mock transport tests.
- [x] Phase 11.4: OpenAlexAdapter with mock transport tests.
- [x] Phase 11.5: SelectionService with scoring, role classification, venue prestige, recency bonus.
- [x] Phase 11.6: DirectionRunner orchestrating query → acquisition → selection → reading plan.
- [x] Phase 11.7: 29 new tests covering schemas, adapters, selection, runner; total 231 passed.
- [x] Phase 11.8: Three-way dedup (DOI / arXiv ID / normalized_title) with metadata merge.
- [x] Phase 11.9: filtered_candidates.json artifact between candidate_pool and reading_plan.
- [x] Phase 11.10: SearchIntent converted to real str Enum (GENERAL/SURVEY/FOUNDATIONAL/SOTA/BENCHMARK/CODE).
- [x] Phase 11.11: DirectionBundle updated with filtered_candidates field.
- [x] Phase 11.12: python-multipart installed; full test suite 246 passed, 0 failed.

## Not Started

- [ ] Phase 11.6: ParserAdapter Design
- [ ] Phase 11.7: PassageIndex + ClaimEvidence v2
- [ ] Phase 11.8: Evidence-constrained LLM Paper Understanding
- [ ] Phase 11.9: Paper Understanding Quality Benchmark
- [ ] Phase 12: Patterns + Drill (frozen, waiting for 11.6-11.9)

## Technology Route Status

- Phase 11.5: Technology Route Review completed (see `docs/RESEARCHSENSEI_TECH_ROUTE_REVIEW.md`).
- External projects evaluated: ARIS, PaperQA, OpenScholar, ResearchPilot, STORM, Docling, Nougat, Marker.
- Key decisions: keep Python/FastAPI/Pydantic, upgrade Parser/Evidence/Audit layers, no ARIS-style skills.
- Phase 12 frozen until route reset is confirmed.

## Current Risks

- README currently describes a package layout that does not match the actual project.
- Existing `backend/` mixes multiple concerns and should not be expanded.
- Existing frontend API assumptions may need adjustment when the new backend package becomes active.
- [RESOLVED] H1: old backend tests moved to `legacy_tests/`, no longer collected by default pytest.
- [RESOLVED] M1: smoke_test moved to `tests_e2e/`, explicitly excluded via pyproject.toml.
- [RESOLVED] M2: `source_resolver.py` now captures and logs exception details.

## Next Safe Task

Phase 11.5 technology route review completed. Phase 12 frozen.

Next step: confirm route reset, then proceed to Phase 11.6 (ParserAdapter Design) or Phase 12 (Patterns + Drill).

See `docs/RESEARCHSENSEI_TECH_ROUTE_REVIEW.md` for full analysis and recommended sub-phases.

Do not enter Phase 12 (patterns/drill/batch pipeline) without a separate reuse gate.
