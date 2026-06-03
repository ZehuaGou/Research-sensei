# ResearchSensei Implementation Plan

This plan implements v0.5 as a direct architecture refactor.

## Phase 1: Documentation and Contracts

- Generate PRODUCT_REQUIREMENTS, REUSE_REPORT, MODULE_CONTRACTS, IMPLEMENTATION_PLAN, REVIEW_CHECKLIST, GLOSSARY, ACCEPTANCE_CRITERIA.
- Add tests that fail when required docs or module contracts are missing.

## Phase 2: New Package Skeleton

- Create `src/researchsensei` with query, acquisition, selection, source_resolver, ingestion, grounding, understanding, teaching, formula, direction, patterns, drill, interactive, context, llm, render, integrations, web.
- Add Pydantic schemas for all primary contracts.
- Keep old `research_sensei` only as migration source.

## Phase 3: Vertical Slice

- Direction mode: query plan -> candidate selection -> reading plan.
- Paper mode: text/PDF-prechecked input -> ingestion blocks -> grounding -> skeleton -> cards.
- Interactive mode: current card + selected text + evidence chunk -> prompt builder -> answer.

## Phase 4: Web Workspace

- Replace old prototype page concept with learning workspace: left navigation, center learning object, right ask panel.
- Every card can provide ask actions.

## Phase 5: Sample and Evaluation

- Build `outputs/sample` around Attention Is All You Need.
- Add golden tests for formula cards and paper skeleton quality.

## Budgets and Discipline

- Single paper deep read target: 3-5 minutes, under 50 API calls, under 200K-300K tokens.
- Every artifact includes generated_at, generator_version, and content hash when persisted.
- No module may silently fall back from missing full text to deep formula explanation.
