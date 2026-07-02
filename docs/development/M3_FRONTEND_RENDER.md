# M3 API And Frontend Rendering Contract

Current status and evidence live in `docs/STATUS.md`.

## Scope

M3 includes:

- `HomeView`
- `UploadView`
- `DirectionSearchView`
- `SeedExpansionPanel`
- `SettingsView`
- `LearningWorkspaceView`
- `StatusBanner`
- FastAPI routes in `src/researchsensei/web/app.py`

M3 also mounts M4 v1 controls inside PaperWorkspace when the job is allowed to
show cards.

## Core API Routes

- `POST /api/v1/documents/parse`
- `GET /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/understanding_status`
- `GET /api/v1/jobs/{job_id}/cards`
- `POST /api/v1/jobs/{job_id}/selection/explain`
- `POST /api/v1/jobs/{job_id}/formula/explain`
- `POST /api/v1/jobs/{job_id}/ask`
- `POST /api/v1/jobs/{job_id}/advisor/question`
- `POST /api/v1/jobs/{job_id}/advisor/evaluate`
- `GET /api/v1/jobs/{job_id}/memory`
- `DELETE /api/v1/jobs/{job_id}/memory`
- `GET /api/v1/settings`
- `POST /api/v1/settings/test`
- `POST /api/v1/directions/search`
- `POST /api/v1/directions/seed_expansion`
- `POST /api/v1/directions/deep_read`

## Rendering Rules

- Always request `/understanding_status` before `/cards`.
- Request `/cards` only for `SUCCESS` or `DEGRADED_STRUCTURAL`.
- Do not show explanatory cards for `BASELINE_ONLY`, `BLOCKED_UNDERSTANDING`,
  or `FAILED`.
- Do not mount M4 controls for statuses that cannot show cards.
- In `DEGRADED_STRUCTURAL`, show only successful components and clearly state
  which structural component is unavailable.
- User-facing copy should be Chinese; raw status codes may remain visible in
  compact technical fields.

## PaperWorkspace Layout

- Left rail: reading tabs and job identity.
- Center pane: status banner, collapsed technical status, paper/formula/teaching
  cards.
- Right pane: M4 tutor chat/advisor/memory.
- Text selection toolbar: Chinese actions (`追问`, `讲简单点`, `举例`) positioned
  from the selected range and clamped to the viewport.

## Settings

Settings is ccswitch focused:

- Show `active_provider`, base URL, model placeholder, and readiness.
- Explain that model selection is read from ccswitch and saved through the settings page.
- Do not guide users toward Xiaomi/MiMo token setup as the default path.
