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
- Do not let M4 answers bypass M2 artifacts, evidence refs, or explicit
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
| M1 acquisition and legal full text | `src/researchsensei/acquisition/`, `src/researchsensei/source_resolver.py`, `src/researchsensei/direction/` | `docs/development/M1_LITERATURE_SEARCH.md` |
| M2 parser/evidence/cards/audit | `src/researchsensei/parser/`, `src/researchsensei/evidence/`, `src/researchsensei/ingestion/`, `src/researchsensei/audit/` | `docs/development/M2_5_FULL_PIPELINE.md` |
| M3 API/UI | `src/researchsensei/web/app.py`, `frontend/src/views/`, `frontend/src/components/` | `docs/development/M3_FRONTEND_RENDER.md` |
| M4 interactive learning v1 | `src/researchsensei/m4/`, `src/researchsensei/schemas/m4.py`, PaperWorkspace M4 components | `docs/development/M4_INTERACTIVE_LEARNING.md` |
| Reliability and acceptance checks | `scripts/`, `tests/`, `frontend/src/**/tests/` | `docs/STATUS.md` |

## Configuration

Live LLM runs default to ccswitch:

```text
RESEARCHSENSEI_ENABLE_API_LLM=1
RESEARCHSENSEI_LLM_PROVIDER=cc_switch
```

`config/sensei.example.toml` has `active_provider = "cc_switch"` and points to
`http://127.0.0.1:15721/v1`. The request model is selected from the settings page; the
project should not require a Xiaomi/MiMo token for normal local runs.

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
npm run build
```

Local development servers:

```powershell
.venv\Scripts\python.exe -m uvicorn "researchsensei.web.app:create_app" --factory --host 127.0.0.1 --port 8765

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
