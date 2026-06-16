# ResearchSensei

ResearchSensei is a research-reading workflow for moving from a research
direction to legal paper discovery, full-text acquisition, evidence-backed
single-paper understanding, and a controlled PaperWorkspace UI.

`docs/STATUS.md` is the only authoritative status file. Other docs describe
contracts, design intent, or historical context; when they disagree, update
`docs/STATUS.md` first and treat it as the source of truth.

## Current Strict Scope

- M1 covers literature acquisition, Direction Exploration, Seed Expansion, legal
  full-text discovery, and deep-read handoff into PaperWorkspace.
- M2 covers evidence-backed paper understanding, passage and claim evidence,
  formula provenance, quality audit, and card generation.
- M3 covers API/UI rendering for DirectionSearchView, SeedExpansionPanel, and
  PaperWorkspace with strict `/cards` gating.
- M4 interactive tutoring, long-term memory, drills, and advisor chat are not
  implemented and must not be started during M1/M2/M3 readiness work.

Do not claim broad `REAL_E2E` or product readiness unless a real smoke or
acceptance run proves that exact scope. Mock, fake, skipped, or baseline-only
results are not real acceptance.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Create a local `.env` file when live LLM or external source lookups are needed.
Never commit `.env`.

```text
RESEARCHSENSEI_ENABLE_API_LLM=1
RESEARCHSENSEI_LLM_PROVIDER=mimo
MIMO_API_KEY=...
UNPAYWALL_EMAIL=you@example.com
RESEARCHSENSEI_CONTACT_EMAIL=you@example.com
SEMANTIC_SCHOLAR_API_KEY=...
OPENAI_COMPATIBLE_API_KEY=...
```

`config/sensei.example.toml` documents the Mimo/Xiaomi-compatible provider and a
generic OpenAI-compatible provider. Local overrides belong in ignored
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

Literature acquisition smoke:

```powershell
.venv\Scripts\python.exe scripts\run_literature_acquisition_smoke.py --query "time series anomaly detection" --max-results 80 --download-top-n 10
```

M1 -> M2 -> M3 main-chain smoke with Mimo:

```powershell
$env:RESEARCHSENSEI_ENABLE_API_LLM="1"
$env:RESEARCHSENSEI_LLM_PROVIDER="mimo"
.venv\Scripts\python.exe scripts\run_main_chain_smoke.py --query "time series anomaly detection" --provider mimo
```

## Documentation Map

- `docs/STATUS.md`: single authoritative project state, evidence, blockers, and
  next steps.
- `docs/DEVELOPMENT.md`: development rules and commands.
- `docs/DESIGN.md`: current architecture overview; not an independent status
  source.
- `docs/MODULE_CONTRACTS.md`: module input/output/boundary contracts.
- `docs/development/M1_LITERATURE_SEARCH.md`: M1 acquisition and direction
  contract.
- `docs/development/M2_5_FULL_PIPELINE.md`: M2 full pipeline and gating
  contract.
- `docs/development/M3_FRONTEND_RENDER.md`: M3 API/UI gating contract.

Historical docs are retained only for background and must not override
`docs/STATUS.md`.
