# ResearchSensei Backend Migration Plan

## Goal

Migrate the backend from the frozen `backend/` package to the canonical `src/researchsensei/` package while preserving the existing Vue frontend and avoiding a risky one-shot rewrite.

## Migration Principles

- Migrate one module at a time.
- Every migrated module must have tests.
- Keep `backend/` as migration reference.
- Do not delete old files during early migration.
- Do not create empty placeholder modules.
- Do not migrate high-risk LLM teaching/formula/direction logic in the first batch.
- Keep `frontend/` unchanged except future API wiring.
- Default pytest must not depend on a running server.

## Target Backend Shape

The future backend package is:

```text
src/researchsensei/
  __init__.py
  __main__.py
  config/
  schemas/
  llm/
  workspace/
  jobs/
```

Only the modules listed above are in the first migration batch.

Later phases may add:

```text
query/
acquisition/
selection/
source_resolver/
ingestion/
grounding/
understanding/
teaching/
formula/
direction/
patterns/
drill/
interactive/
context/
render/
integrations/
web/
```

These later modules must be added only when there is real implementation and test coverage for the current phase.

## First Batch Scope

The first batch migrates only low-risk infrastructure:

1. Config loading.
2. Schemas and core enums.
3. LLM client basics.
4. Workspace store.
5. Job store.

Explicitly excluded from first batch:

- Teaching engine.
- Formula tutor.
- Direction map.
- Interactive advisor state machine.
- Search/acquisition.
- Source resolver download.
- PDF parsing.
- Rendering.
- Vue frontend changes.

## Migration Steps

### Step 1: Establish Package Skeleton And CLI Healthcheck

Migration object:

- New package root only.

Target paths:

- `src/researchsensei/__init__.py`
- `src/researchsensei/__main__.py`
- `tests/test_package_healthcheck.py`

Do not migrate:

- Web routes.
- Pipeline logic.
- Frontend code.

Test requirements:

- `python -m researchsensei --help` returns success.
- `python -m researchsensei healthcheck` returns success.
- `import researchsensei` works.

Acceptance standard:

- The project has a real `researchsensei` import namespace.
- The CLI does not require API keys.
- The CLI does not touch `workspace/` unless explicitly asked.

### Step 2: Migrate Config Service

Migration object:

- `backend/config.py`, adapted and simplified.

Target paths:

- `src/researchsensei/config/__init__.py`
- `src/researchsensei/config/service.py`
- `tests/test_config_service.py`

Expected behavior:

- Load TOML config from `config/local.toml`.
- Fall back to `config/sensei.example.toml`.
- Load `.env` into process environment without logging key values.
- Support DeepSeek, MiMo, and generic OpenAI-compatible providers.
- Report missing API key clearly.

Test requirements:

- Config loads when `config/local.toml` exists.
- Example config loads when local config is absent.
- Missing API key does not crash app initialization.
- Error messages redact API key values.
- MiMo `api-key` auth header is preserved in config.

Acceptance standard:

- No business module directly reads TOML.
- No API key value appears in test output or logs.

### Step 3: Migrate Core Schemas

Migration object:

- Low-risk parts of `backend/schemas.py`.

Target paths:

- `src/researchsensei/schemas/__init__.py`
- `src/researchsensei/schemas/common.py`
- `src/researchsensei/schemas/paper.py`
- `src/researchsensei/schemas/cards.py`
- `src/researchsensei/schemas/jobs.py`
- `tests/test_schemas_core.py`

Required models:

- `StatusEnvelope`
- `WarningItem`
- `ErrorItem`
- `GeneratedMetadata`
- `EvidenceType`
- `BlockType`
- `SearchIntent`
- `PaperRole`
- `ReadingPriority`
- `ModelProviderConfig`
- `AppConfig`
- `SourceStatus`
- `DocumentBlock`
- `DocumentIngestion`
- `EvidenceClaim`
- `EvidenceIndex`
- `PaperSkeleton`
- `TeachingCard`
- `FormulaCard`
- `PatternCard`
- `DrillCard`
- `JobRecord`
- `WorkspaceArtifact`

Test requirements:

- Models serialize to JSON.
- Models validate from JSON.
- Enum values are closed.
- Missing required fields fail validation.
- `extra="forbid"` remains active.

Acceptance standard:

- Schema imports use `researchsensei.schemas`, not `backend.schemas`.
- No high-risk generation logic is added.

### Step 4: Migrate LLM Client Basics

Migration object:

- `backend/llm/client.py`.
- Safe parts of `backend/llm/prompt_builder.py`.
- Safe parts of `backend/llm/response_cache.py`.

Target paths:

- `src/researchsensei/llm/__init__.py`
- `src/researchsensei/llm/client.py`
- `src/researchsensei/llm/prompt_builder.py`
- `src/researchsensei/llm/response_cache.py`
- `tests/test_llm_client_core.py`
- `tests/test_prompt_builder_core.py`
- `tests/test_response_cache_core.py`

Expected behavior:

- OpenAI-compatible chat endpoint.
- OpenAI-compatible JSON response parsing.
- MiMo `api-key` header support.
- Authorization bearer header support.
- Prompt sections for system/context/evidence/user question.
- Instruction isolation for user question.
- In-memory response cache with version and TTL.

Test requirements:

- All external HTTP calls mocked.
- No real API key required.
- API key value is never logged or returned.
- Prompt includes isolated user question marker.
- Cache invalidates by version and TTL.

Acceptance standard:

- Business modules do not call provider HTTP APIs directly.
- LLM layer can run in mock tests without network.

### Step 5: Migrate Workspace Store

Migration object:

- `backend/workspace.py`.

Target paths:

- `src/researchsensei/workspace/__init__.py`
- `src/researchsensei/workspace/store.py`
- `tests/test_workspace_store.py`

Expected behavior:

- Create `workspace/runs/<job_id>/`.
- Create `workspace/searches/<search_id>/`.
- Write JSON using schema-safe serialization.
- Write text with UTF-8.

Test requirements:

- Run directory creation is deterministic when job_id is passed.
- Search directory creation creates unique directories.
- JSON output preserves Chinese text.
- Text output uses UTF-8.

Acceptance standard:

- Workspace store does not know about FastAPI.
- Workspace store does not generate teaching content.

### Step 6: Migrate Job Store

Migration object:

- `backend/jobs.py`.

Target paths:

- `src/researchsensei/jobs/__init__.py`
- `src/researchsensei/jobs/store.py`
- `tests/test_job_store.py`

Expected behavior:

- SQLite-backed job persistence.
- Create/get/list/update job records.
- Store warnings and artifact metadata.
- Keep job status enum strict.

Test requirements:

- Create job.
- Get job by id.
- Update status/current_step/error/warnings/artifacts.
- Missing job raises a clear exception.
- List recent jobs sorted by created time.

Acceptance standard:

- Job store is independent from web routes.
- Job store does not run pipeline steps.

## After First Batch

Only after Steps 1-6 pass should Phase 1 continue to:

- Update packaging metadata to point to `src`.
- Decide how the new backend will be served.
- Create a minimal API compatibility layer for the Vue frontend.

Do not migrate these until the first batch is stable:

- `query`
- `selection`
- `acquisition`
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
- `render`
- `web`

## Test Policy

Default test command for migrated backend:

```powershell
pytest -q
```

The default suite must not require:

- A running backend server.
- A running frontend dev server.
- Real API keys.
- Live external search APIs.

Live smoke tests must be moved out of default pytest or marked explicitly.

## Legacy Policy During Migration

Keep:

- `backend/`
- `frontend/`
- `config/`
- old docs and samples

Do not delete:

- `backend/web.py`
- `backend/render.py`
- `frontend/`
- `tests/smoke_test.py`

But do not expand:

- `backend/web.py`
- `backend/render.py`
- `tests/smoke_test.py`

## Stop Conditions

Stop migration and ask for confirmation if:

- A test requires a real API key.
- A dependency install is needed.
- A schema decision conflicts with existing frontend API needs.
- A migrated module needs behavior that is not specified in the full development docs.
- Any step would require deleting old code.

