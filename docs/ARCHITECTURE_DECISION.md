# ResearchSensei Architecture Decision

## Status

Accepted on 2026-06-02.

## Decision

ResearchSensei adopts route B from the current project audit:

> Keep useful existing code as migration source, rebuild the backend core architecture into a clean Python package, and preserve the existing Vue frontend workspace.

This means:

- Keep `frontend/` as the primary web workspace.
- Freeze `backend/` as migration source.
- Create the new backend package under `src/researchsensei/` in Phase 1.
- Migrate one backend capability at a time with tests.
- Do not delete old code during migration.
- Do not introduce React.
- Do not continue adding new product features to `backend/`.

## Why Route B

Route A, continuing to refactor the current old code in place, is not recommended because the current backend structure conflicts with the full development documents:

- The development documents require `src/researchsensei/`, while current code lives in `backend/`.
- The current `backend/web.py` combines API routes, HTML rendering, pipeline orchestration, and server startup.
- `backend/render.py` renders large HTML strings directly instead of following a clean presentation boundary.
- Current tests include a live-server smoke test that blocks default `pytest`.
- README, config, startup scripts, and actual package names are inconsistent.

Route C, moving all old code into `legacy/` and starting from a completely clean skeleton, is also not recommended yet because some existing code is useful and already tested:

- Configuration loading and provider switching.
- LLM client and prompt builder ideas.
- Pydantic schema definitions.
- Workspace and job persistence basics.
- Source resolver PDF/arXiv download logic.
- Metadata-only evidence downgrade behavior.
- A usable Vue workspace foundation.

Route B keeps the useful pieces while preventing the old architecture from shaping the new one.

## Why Keep Vue Frontend

The existing frontend is based on:

- Vue 3
- Vite
- TypeScript
- Pinia
- TailwindCSS
- KaTeX
- Mermaid/D3 dependencies

This frontend should be preserved because:

- It already exists and builds successfully.
- It supports a proper separated frontend/backend direction.
- It is closer to a real learning workspace than string-rendered backend HTML.
- Replacing it with React would create churn without solving the backend architecture problem.
- The current priority is backend correctness, evidence discipline, and module contracts.

Frontend policy:

- Keep `frontend/` in place.
- Do not rewrite it wholesale.
- Do not create a React project.
- Future frontend changes should focus on API compatibility and learning-workspace UX.
- Vue components can be improved later after the backend API is stable.

## Why Move Backend To `src/researchsensei/`

The development documents define `src/researchsensei/` as the canonical backend package.

Moving the backend there gives the project:

- A conventional Python package layout.
- A stable import namespace: `researchsensei`.
- Room to split schemas into focused modules.
- A clean CLI entry point.
- A clear separation from frozen legacy code.
- A better test target for phased migration.

The new backend package should follow the documented module boundaries:

- `query`
- `acquisition`
- `selection`
- `source_resolver`
- `ingestion`
- `grounding`
- `understanding`
- `teaching`
- `formula`
- `direction`
- `patterns`
- `drill`
- `interactive`
- `context`
- `llm`
- `render`
- `integrations`
- `web`

However, these modules must not be created as empty shells. A module is created only when its current phase needs real code and tests.

## Legacy Backend Policy

`backend/` is now frozen.

Allowed:

- Read code from `backend/` as migration reference.
- Copy or adapt small, tested logic into `src/researchsensei/`.
- Keep old routes available temporarily if needed for comparison.
- Add documentation explaining migration status.

Not allowed:

- Add new product features to `backend/`.
- Expand `backend/web.py`.
- Expand `backend/render.py`.
- Move high-risk LLM teaching/formula/direction logic before core infrastructure is stable.
- Delete `backend/` during early migration.

Files currently considered migration references:

- `backend/config.py`
- `backend/schemas.py`
- `backend/llm/client.py`
- `backend/llm/prompt_builder.py`
- `backend/llm/response_cache.py`
- `backend/workspace.py`
- `backend/jobs.py`
- `backend/source_resolver.py`
- `backend/grounding.py`

Files currently considered replacement targets:

- `backend/web.py`
- `backend/render.py`
- `tests/smoke_test.py`
- old README startup sections

## Legacy Frontend Policy

`frontend/` remains active.

Allowed:

- Keep the Vue app.
- Keep existing routes and components while backend API evolves.
- Adjust API calls when new `src/researchsensei` backend routes are introduced.
- Add tests later around critical UI/API flows.

Not allowed in the current migration phase:

- Rewrite frontend architecture.
- Replace Vue with React.
- Make large UI redesigns.
- Add new frontend feature scope before backend contracts are stable.

## Migration Rule

Each migration step must satisfy:

1. Migrate one capability only.
2. Write or update tests first.
3. Keep old code untouched unless explicitly moving it to `legacy/`.
4. Do not delete `backend/` or `frontend/`.
5. Do not create empty modules.
6. Do not migrate teaching, formula, direction, or other high-risk LLM logic in the first batch.
7. Run the relevant tests before moving to the next step.

## Current Phase

The project remains in Phase 0:

- Audit completed.
- Architecture decision recorded.
- Migration plan prepared.
- Phase 1 code development not started.

