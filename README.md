# ResearchSensei

ResearchSensei is a research-reading workflow for moving from a research
direction to legal paper discovery, full-text acquisition, evidence-backed
single-paper understanding, and a Chinese PaperWorkspace with an M4 tutor.

`docs/STATUS.md` is the authoritative status file. Other docs describe design
intent and contracts; if they disagree, update `docs/STATUS.md` and then bring
the other docs back into sync.

## Current Scope

- M1: literature acquisition, direction exploration, seed expansion, legal
  full-text discovery, and deep-read handoff.
- M2: passage/claim evidence, formula provenance, paper/formula/teaching card
  generation, quality audit, and fail-closed understanding status.
- M3: Chinese Vue workspace for upload, direction search, seed expansion,
  status gating, cards, and settings.
- M4 v1: evidence-bound PaperWorkspace interactions: selected text explanation,
  formula explanation, single-paper Q&A, advisor questions/evaluation, and
  `m4_memory.json`.

Live LLM runs default to ccswitch (`cc_switch` config key). ResearchSensei calls
the local ccswitch endpoint; the request model can be selected from the settings
page.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Create a local `.env` when live LLM or external source lookups are needed. Do
not commit `.env`.

```text
RESEARCHSENSEI_ENABLE_API_LLM=1
RESEARCHSENSEI_LLM_PROVIDER=cc_switch

UNPAYWALL_EMAIL=you@example.com
RESEARCHSENSEI_CONTACT_EMAIL=you@example.com
SEMANTIC_SCHOLAR_API_KEY=...
S2_API_KEY=...
```

`config/sensei.example.toml` uses `active_provider = "cc_switch"` and points to
`http://127.0.0.1:15721/v1`. Local overrides belong in ignored
`config/local.toml`.

## Useful Commands

Backend tests:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Frontend tests and build:

```powershell
cd frontend
npm test
npm run build
```

Local backend and frontend dev servers:

```powershell
.venv\Scripts\python.exe -m uvicorn "researchsensei.web.app:create_app" --factory --host 127.0.0.1 --port 8765

cd frontend
npm run dev
```

The frontend dev server runs on port `13000` and proxies API traffic to backend
port `8765`.

Main-chain smoke with ccswitch:

```powershell
$env:RESEARCHSENSEI_ENABLE_API_LLM="1"
$env:RESEARCHSENSEI_LLM_PROVIDER="cc_switch"
.venv\Scripts\python.exe scripts\run_main_chain_smoke.py --query "time series anomaly detection" --provider cc_switch
```

## Documentation Map

- `docs/STATUS.md`: current project state, evidence, blockers, and next steps.
- `docs/DESIGN.md`: architecture overview.
- `docs/DEVELOPMENT.md`: development rules and commands.
- `docs/MODULE_CONTRACTS.md`: module input/output/boundary contracts.
- `docs/development/M3_FRONTEND_RENDER.md`: UI/API gating contract.
- `docs/development/M4_INTERACTIVE_LEARNING.md`: current M4 v1 contract.
