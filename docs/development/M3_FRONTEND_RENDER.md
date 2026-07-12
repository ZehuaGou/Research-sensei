# M3 API and Frontend Rendering Contract

Current status and exact verification evidence live in `docs/STATUS.md`.
ResearchSensei remains a Chinese research-learning workspace, not a marketing
site.

## Runtime Structure

`researchsensei.web.app:create_app` remains compatible with existing uvicorn
commands. It delegates to:

- `web/app_factory.py`: one-time configuration and dependency composition;
- `web/dependencies.py`: runtime dependency container;
- `web/request_models.py`: bounded Pydantic inputs;
- `web/routers/settings.py`, `jobs.py`, `library.py`, `directions.py`, `m4.py`;
- `web/services/upload_service.py`, `job_service.py`, `task_service.py`.

The Vue app centralizes HTTP access in `frontend/src/api/client.ts` and uses
typed API/workspace models. Core workspace structures must not use `any`.

## Core API Routes

Documents and learner workspace:

- `POST /api/v1/documents/parse`
- `GET /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `DELETE /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/understanding_status`
- `GET /api/v1/jobs/{job_id}/cards`

Direction operations:

- `POST /api/v1/directions/search` (synchronous compatibility path)
- `POST /api/v1/directions/deep_read` (synchronous compatibility path)
- `POST /api/v1/directions/seed_expansion`
- `POST /api/v1/directions/jobs/search` (preferred asynchronous path)
- `POST /api/v1/directions/jobs/deep_read` (preferred asynchronous path)
- `GET /api/v1/directions/jobs/{task_id}`
- `DELETE /api/v1/directions/jobs/{task_id}`

Settings and management:

- `GET /api/v1/settings`
- `PATCH /api/v1/settings`
- `POST /api/v1/settings/validate`
- `POST /api/v1/settings/test` (deprecated compatibility alias)
- `GET /api/v1/library/papers`
- `GET /api/v1/library/search_runs`
- `DELETE /api/v1/library/papers/{paper_id}`
- `GET /api/v1/maintenance/orphan-runs`
- `POST /api/v1/maintenance/orphan-runs/cleanup`

M4 routes are listed in `M4_INTERACTIVE_LEARNING.md`.

## Request and Error Contract

- Unknown request fields are rejected unless a documented compatibility payload
  explicitly preserves extra candidate metadata.
- Text length, conversation count/item length, enum values, limits, and timeout
  values are bounded.
- Validation, gate, conflict, cancellation, timeout, network, and provider
  failures expose stable machine-readable error codes.
- The typed client normalizes HTTP 422, 403 gate, 409 conflict, timeout,
  cancellation, and network failure without requiring each view to reimplement
  error parsing.

## Upload Contract

The backend reads uploads in fixed chunks and enforces maximum bytes while
writing. It validates extension, declared MIME, and a basic file signature,
rejects empty/forged files, and uses a generated final path. The user filename
never becomes the server path. Temporary files are removed on validation,
parse, interruption, cancellation, and request-failure paths.

## Rendering Rules

- Always request `/understanding_status` before `/cards`.
- Request `/cards` only for `SUCCESS` or `DEGRADED_STRUCTURAL`.
- Do not show explanatory cards for `BASELINE_ONLY`,
  `BLOCKED_UNDERSTANDING`, or `FAILED`.
- Do not mount M4 controls for statuses that cannot show cards.
- Display `pipeline_status`, `relevance_status`, `source_status`, and
  `understanding_status` independently. Pipeline success must not hide a
  relevance or source failure.
- In `DEGRADED_STRUCTURAL`, show only passed components and name the unavailable
  component.
- User-facing copy remains Chinese; compact raw status codes may support
  diagnostics.

## PaperWorkspace Structure

`LearningWorkspaceView.vue` composes focused units:

- `useWorkspaceData`
- `useWorkspaceTabs`
- `useFormulaDock`
- `useChatPaneResize`
- `useWorkspaceScrollMemory`
- `FormulaWorkspace`
- `FormulaDock`
- `WorkspaceStatusPanel`

The central pane renders paper, formula, and teaching cards. The M4 pane is
width-bounded against the actual viewport and becomes an overlay/drawer on
small screens. Formula and chat surfaces must not rely on an escalating z-index
patch stack to avoid one another.

## Formula Dock and Scroll

- Persisted x/y coordinates are clamped to the visible viewport when read.
- Drag updates, browser resize, zoom/layout change, and old local-storage
  coordinates trigger a new clamp.
- Pointer release or lost pointer capture ends dragging.
- Keyboard movement and restore-default-position are available.
- Tab scroll restoration waits for the committed render rather than assigning
  `scrollTop` multiple times.
- Rapid tab changes and route-return restoration preserve the correct tab's
  position.

## Accessibility

- Tabs expose tab/tabpanel semantics and selected state.
- Dialog/drawer flows trap focus and close on Escape.
- Expanded/collapsed controls expose `aria-expanded`.
- Drag and resize controls provide keyboard alternatives.
- The resize separator is focusable and supports keyboard resizing.

## Settings

Settings identifies provider, model, and actual request route. The default
ccswitch provider uses the Anthropic-compatible `/v1/messages` path. Local
validation does not claim connectivity; a live probe is explicit, time-bounded,
redacted, and typed.

## Validation

Vitest covers the typed client, workspace tabs/scroll, formula dock clamp, and
component behavior. Playwright E2E uses fixed local paper fixtures and mocked
search/LLM responses; external APIs and live LLMs are opt-in only. Exact current
commands and counts are recorded in `docs/STATUS.md`.
