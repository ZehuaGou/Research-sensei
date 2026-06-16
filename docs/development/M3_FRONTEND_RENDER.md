# M3 API And Frontend Rendering Contract

This document describes M3 rendering rules. Current status and evidence live in
`docs/STATUS.md`.

## Scope

M3 currently includes:

- `UploadView`
- `DirectionSearchView`
- `SeedExpansionPanel`
- `LearningWorkspaceView`
- `StatusBanner`
- FastAPI routes in `src/researchsensei/web/app.py`

M3 does not include M4 chat, advisor questions, drills, or long-term memory.

## API Routes

Core routes:

- `POST /api/v1/documents/parse`
- `GET /api/v1/documents/{job_id}/understanding_status`
- `GET /api/v1/documents/{job_id}/cards`
- `GET /api/v1/documents/{job_id}/artifacts` for debug/admin oriented access
- `POST /api/v1/directions/search`
- `POST /api/v1/directions/seed_expansion`
- `POST /api/v1/directions/deep_read`

`deep_read` supports arXiv ID/URL, PDF URL, candidate payload, and explicit DOI
failure when DOI handoff is not implemented.

## Rendering Rule

LearningWorkspace must request `understanding_status` before cards.

Only these statuses may request cards:

- SUCCESS
- DEGRADED_STRUCTURAL

These statuses must not show explanatory card content:

- BLOCKED_UNDERSTANDING
- BASELINE_ONLY
- FAILED

## Status Fields To Render

The frontend should expose the operational state, not just card prose:

- source type;
- canonicalization status;
- `m2_ready`;
- degradation reason;
- warnings;
- missing components;
- component status;
- allowed downstream components;
- formula origin;
- formula OCR/source status;
- evidence status.

DEGRADED_STRUCTURAL must clearly show that the page is degraded and must show
which components are unavailable.

## DirectionSearchView

DirectionSearchView must:

- accept a direction query;
- show loading, success, degraded, blocked, and empty states;
- render overview, sub-directions, method families, candidates, and reading
  order;
- display discovery sources, verification/full-text readiness, source metrics,
  and failure reasons;
- call `deep_read` for source-backed candidates and navigate to `/learn/{job_id}`
  only after a real job is created.

## SeedExpansionPanel

SeedExpansionPanel must:

- accept a typed seed or selected candidate payload;
- render upstream, downstream, same-route, survey, and follow-up groups;
- show relation reason/confidence and whether citation graph evidence is real or
  weak;
- call the same `deep_read` handoff for source-backed expansion papers;
- show DEGRADED/EMPTY_RESULT states without fake candidates.

## PaperWorkspace

PaperWorkspace may display:

- paper card;
- formula cards only when formula component succeeded;
- teaching cards only when teaching component succeeded;
- status banner and component diagnostics for DEGRADED/BLOCKED paths.

For DEGRADED_STRUCTURAL, `/cards` returns only successful components.

## Boundaries

- Do not make `/artifacts` the normal user path.
- Do not show BASELINE_ONLY cards.
- Do not show BLOCKED_UNDERSTANDING cards.
- Do not hide degradation reasons.
- Do not claim M3 product readiness from selected-paper or narrow smoke.
