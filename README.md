# ResearchSensei v0.6 Reliability Baseline

ResearchSensei is a research-reading workflow for moving from a research
direction to legal paper discovery, full-text acquisition, evidence-backed
single-paper understanding, and a Chinese PaperWorkspace with an M4 tutor.

`docs/STATUS.md` is the authoritative status file. Other docs describe design
intent and contracts; if they disagree, update `docs/STATUS.md` and then bring
the other docs back into sync.

The v0.6 baseline separates pipeline completion, semantic relevance, legal
source readiness, and learner-facing understanding. See `docs/STATUS.md` for
the exact final commit, commands, pass/fail counts, and live-verification state.

## Current Scope

- M1: literature acquisition, direction exploration, seed expansion, legal
  full-text discovery, and deep-read handoff.
- M2: page-preserving PDF ingestion, optional OpenCode visual paper analysis,
  passage/claim evidence, formula provenance, paper/formula/teaching card
  generation, quality audit, and fail-closed understanding status.
- M3: typed Chinese Vue workspace for streamed upload, asynchronous direction
  jobs, seed expansion, four-layer status gating, cards, and settings.
- M4 v1: claim-level evidence-bound interactions plus full-paper tutoring that
  can continue the persistent OpenCode paper session; selected-text and formula
  explanation, single-paper Q&A, advisor questions/evaluation, and atomic
  bounded `m4_memory.json` remain available.

Live LLM runs default to ccswitch (`cc_switch` config key). ResearchSensei calls
the local ccswitch endpoint; the request model can be selected from the settings
page.

When the active CC Switch Claude provider itself forwards to an OpenAI-format
OpenCode Go endpoint, use the checked-in `opencode_go` provider for low-latency
M4 chat. If `OPENCODE_GO_API_KEY` is not set, ResearchSensei can read the key
from the active matching CC Switch provider in read-only mode. The configured
HTTPS upstream must match exactly; the key stays in memory and is never copied
to project files or settings responses. Set
`RESEARCHSENSEI_CCSWITCH_CREDENTIAL_BRIDGE=0` to disable this local bridge.

For PDF-aware M2, install the OpenCode CLI and enable `[opencode]` in the local
configuration. This is a separate Server/Agent integration, not the text-only
OpenCode Go provider. The project starts `opencode serve` on localhost when
needed, renders the PDF page by page, and uses an attachment-capable model such
as `qwen3.7-plus`. Chat and PDF-vision models can be selected independently on
the settings page. `deepseek-v4-flash` remains suitable for text chat but does
not currently accept PDF or image input.

## Setup

Backend:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Frontend:

```powershell
cd frontend
npm ci
```

Create a local `.env` when live LLM or external source lookups are needed. Do
not commit `.env`.

```text
RESEARCHSENSEI_ENABLE_API_LLM=1
RESEARCHSENSEI_LLM_PROVIDER=opencode_go

UNPAYWALL_EMAIL=you@example.com
RESEARCHSENSEI_CONTACT_EMAIL=you@example.com
SEMANTIC_SCHOLAR_API_KEY=...
S2_API_KEY=...
```

`config/sensei.example.toml` defines both `cc_switch` and `opencode_go`. Local
overrides belong in ignored `config/local.toml`. The `cc_switch` provider uses
the Anthropic-compatible `/v1/messages` route. The `opencode_go` provider uses
the upstream OpenAI-compatible `/chat/completions` route and explicitly disables
model thinking for interactive M4 requests; this avoids a CC Switch transform
that can drop the upstream's `thinking: disabled` control and spend the entire
output budget on hidden reasoning.

Configuration precedence is: explicit constructor/app-factory override,
environment variable, ignored `config/local.toml`, checked-in
`config/sensei.example.toml`, then code defaults. The app factory loads the
configuration once and injects it into search, parsing, upload, server, and LLM
services. `GET /api/v1/settings` is secret-safe; use
`POST /api/v1/settings/validate` for local validation and opt in explicitly to
the bounded live provider probe.

## Useful Commands

Default backend tests, excluding opt-in live runs:

```powershell
.venv\Scripts\python.exe -m pytest tests -q
```

All configured tests, including `tests_live` skip checks:

```powershell
.venv\Scripts\python.exe -m pytest -q --maxfail=1
```

Frontend tests and build:

```powershell
cd frontend
npm test
npm run typecheck
npm run build
npm run test:e2e
```

Local backend and frontend dev servers:

```powershell
.venv\Scripts\python.exe -m researchsensei serve

cd frontend
npm run dev
```

The frontend dev server runs on port `13000` and proxies API traffic to backend
port `8765`.

Direction search and deep-read have persistent local task endpoints that return
a job id and expose stage, progress, result, typed failure, and cancellation.
The synchronous endpoints remain compatibility paths, while the frontend uses
the asynchronous task flow for long operations.

Main-chain acceptance with ccswitch:

```powershell
$env:RESEARCHSENSEI_ENABLE_API_LLM="1"
$env:RESEARCHSENSEI_LLM_PROVIDER="cc_switch"
.venv\Scripts\python.exe scripts\run_main_chain_acceptance.py --query "time series anomaly detection" --provider cc_switch
```

Live tests are opt-in. They require explicit environment gates:

```powershell
$env:RUN_LIVE_TESTS="1"
$env:RUN_LLM_TESTS="1"
$env:RESEARCHSENSEI_LIVE_EVAL="1"
.venv\Scripts\python.exe -m pytest tests_live -q
```

## Repository Hygiene

Keep generated and machine-local files out of git. The root `.gitignore` covers
`.env`, `.agents/`, `.codex/`, `.superpowers/`, `.vscode/`, `.cache/`,
`output/`, `outputs/`, `reports/`, `artifacts/`, virtual environments, and
database/checkpoint files. Do not commit local run output, screenshots, caches,
or provider secrets.

## Documentation Map

- `docs/STATUS.md`: current project state, evidence, blockers, and next steps.
- `docs/DESIGN.md`: architecture overview.
- `docs/DEVELOPMENT.md`: development rules and commands.
- `docs/MODULE_CONTRACTS.md`: module input/output/boundary contracts.
- `docs/development/M3_FRONTEND_RENDER.md`: UI/API gating contract.
- `docs/development/M4_INTERACTIVE_LEARNING.md`: current M4 v1 contract.
