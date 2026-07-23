# ResearchSensei Development Rules

`docs/STATUS.md` is the single authority for current implementation status,
evidence, blockers, and next steps. This file records development discipline.

## Non-Negotiable Rules

- Do not commit `.env`, API keys, downloaded PDFs/source archives, caches, model
  weights, or generated report files.
- Do not relax QualityAuditor, FSA-5, evidence validation, or `/cards` gating to
  make an acceptance pass.
- Do not expose partial user-facing cards when a core LLM card builder fails.
  `paper_card`, `formula_cards`, and `teaching_cards` failures must fail closed.
- Do not let Paper Tutor answers bypass Paper Analysis artifacts, evidence refs, or explicit
  no-answer/degraded behavior.
- Do not fake evidence, DOI, PDF, arXiv source, citation graph, or full-text
  readiness.
- Do not report mock, fake, skipped, or baseline-only results as real
  acceptance.
- Do not claim broad `REAL_E2E` or product readiness without real validation for
  that exact scope.

## Current Module Ownership

| Area | Main code | Contract doc |
|---|---|---|
| Literature Discovery acquisition and legal full text | `src/researchsensei/acquisition/`, `src/researchsensei/source_resolver.py`, `src/researchsensei/direction/` | `docs/development/LITERATURE_DISCOVERY.md` |
| Paper Analysis parser/evidence/cards/audit | `src/researchsensei/parser/`, `src/researchsensei/evidence/`, `src/researchsensei/ingestion/`, `src/researchsensei/audit/` | `docs/development/PAPER_ANALYSIS_PIPELINE.md` |
| Reader Workspace API/UI | `src/researchsensei/web/app_factory.py`, `src/researchsensei/web/routers/`, `src/researchsensei/web/services/`, `frontend/src/api/`, workspace composables/components | `docs/development/READER_WORKSPACE.md` |
| Paper Tutor interactive learning v1 | `src/researchsensei/tutor/`, `src/researchsensei/schemas/tutor.py`, PaperWorkspace Paper Tutor components | `docs/development/PAPER_TUTOR.md` |
| Reliability and acceptance checks | `scripts/`, `tests/`, `frontend/src/**/tests/` | `docs/STATUS.md` |

## Configuration

Live LLM runs default to OpenCode Go:

```text
RESEARCHSENSEI_ENABLE_API_LLM=1
RESEARCHSENSEI_LLM_PROVIDER=opencode_go
```

`config/sensei.example.toml` defines `opencode_go` as the default provider and
keeps `cc_switch` as a compatibility option. Models are selected from the
settings page; credentials remain in environment variables.

Runtime precedence is fixed: explicit constructor or app-factory override,
environment variable, ignored `config/local.toml`, checked-in
`config/sensei.example.toml`, then code default. Add a configuration option only
when a contract test proves it changes the real injected dependency. Search
sources, result limits, timeouts, parser backend, upload limit, workspace,
server, and provider all follow this path.

`POST /api/v1/settings/validate` validates the resolved configuration without a
network call. A live provider probe must be explicitly requested and must keep
its timeout, redaction, and typed failure behavior.

Required DOI-to-OA lookup env:

```text
UNPAYWALL_EMAIL=you@example.com
RESEARCHSENSEI_CONTACT_EMAIL=you@example.com
```

Do not print full keys or private emails in logs.

## Test Commands

Backend:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Frontend:

```powershell
cd frontend
npm test
npm run typecheck
npm run build
npm run test:e2e
```

Local development servers:

```powershell
.venv\Scripts\python.exe -m researchsensei serve

cd frontend
npm run dev
```

Main-chain acceptance with ccswitch:

```powershell
$env:RESEARCHSENSEI_ENABLE_API_LLM="1"
$env:RESEARCHSENSEI_LLM_PROVIDER="cc_switch"
.venv\Scripts\python.exe scripts\run_main_chain_acceptance.py --query "time series anomaly detection" --provider cc_switch
```

## Continuation Discipline

Start by reading `docs/STATUS.md`, then run targeted tests before broad
refactors. If a model emits malformed JSON, let schema validation fail closed;
do not coerce unsafe output into evidence-backed cards.

## API and Persistence Discipline

- New request models reject unknown fields unless a compatibility boundary is
  explicitly documented; always bound text, history, enum, and limit fields.
- Return stable machine-readable error codes for validation, gates, conflicts,
  timeouts, cancellation, and provider failures.
- Read uploads in fixed chunks, enforce the limit while writing, validate
  extension/MIME/signature, use generated final paths, and clean temporary
  files on every exit path.
- Prefer persistent local jobs for long operations. A restart must identify
  stale work rather than leaving it permanently `RUNNING`.
- SQLite changes require a schema-version/migration test, explicit transaction
  boundaries, and a failure message that preserves recoverability.
- Never recursively delete a path until it has been resolved and proven to be
  under a ResearchSensei-managed workspace root.

Browser E2E defaults to fixed local paper fixtures and mocked provider/search
responses. Real network and LLM checks remain opt-in and must be labeled
`NOT_LIVE_VERIFIED` when not run.
