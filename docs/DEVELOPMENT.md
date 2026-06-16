# ResearchSensei Development Rules

`docs/STATUS.md` is the single authority for current implementation status,
evidence, blockers, and next steps. This file contains development discipline
only. Design or module docs must not contradict `docs/STATUS.md`.

## Non-Negotiable Rules

- Do not commit `.env`, API keys, downloaded PDFs/source archives, caches, model
  weights, or generated report files.
- Do not enter M4 while working on M1/M2/M3 readiness.
- Do not relax QualityAuditor, FSA-5, evidence gates, or `/cards` gating to make
  a smoke pass.
- Do not fake evidence, DOI, PDF, arXiv source, citation graph, or full-text
  readiness.
- Do not report mock, fake, skipped, or baseline-only results as real
  acceptance.
- Do not claim broad `REAL_E2E` or product readiness without real validation for
  that exact scope.
- New external capabilities must go through adapters and must not turn
  ResearchSensei into a clone of another project.

## Current Module Ownership

| Area | Main code | Contract doc |
|---|---|---|
| M1 acquisition and legal fulltext | `src/researchsensei/acquisition/`, `src/researchsensei/source_resolver.py`, `src/researchsensei/direction/` | `docs/development/M1_LITERATURE_SEARCH.md` |
| M2 parser/evidence/understanding/audit | `src/researchsensei/parser/`, `src/researchsensei/evidence/`, `src/researchsensei/ingestion/`, `src/researchsensei/audit/` | `docs/development/M2_5_FULL_PIPELINE.md` |
| M3 API/UI | `src/researchsensei/web/app.py`, `frontend/src/views/`, `frontend/src/components/` | `docs/development/M3_FRONTEND_RENDER.md` |
| Reliability and smoke scripts | `scripts/`, `tests/`, `frontend/src/**/tests/` | `docs/STATUS.md` |

## Parser And Canonical Invariants

- MinerU2.5-Pro via mineru-vl-utils is the primary M1 parser.
- Marker is fallback/audit baseline.
- Ollama is an optional structured refiner.
- Ollama must not modify latex, bbox, page, or source identity.
- M1 gate blocks all-formulas-in-Abstract.
- M1 gate blocks section contradiction.
- M1 gate blocks missing latex/crop/overlay.
- Formula provenance must be preserved; do not label unknown source as
  `source_latex`.
- Unknown or weak formula provenance may degrade or block formula cards, but it
  must not produce detailed derivations.

## Configuration

Local live configuration belongs in `.env` and ignored `config/local.toml`.
`config/sensei.example.toml` is the committed template. It documents Mimo,
DeepSeek, Semantic Scholar, Unpaywall/contact email, and a generic
OpenAI-compatible provider.

Required live LLM env for Mimo:

```text
RESEARCHSENSEI_ENABLE_API_LLM=1
RESEARCHSENSEI_LLM_PROVIDER=mimo
MIMO_API_KEY=...
```

Required DOI-to-OA lookup env:

```text
UNPAYWALL_EMAIL=you@example.com
RESEARCHSENSEI_CONTACT_EMAIL=you@example.com
```

Do not print full keys or full private emails in logs.

## Test Commands

Always run backend tests after code or contract changes:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Run frontend tests/build after frontend changes or broad readiness changes:

```powershell
cd frontend
npm test
npm run build
```

Real smokes are manual and must be reported with scope:

```powershell
.venv\Scripts\python.exe scripts\run_literature_acquisition_smoke.py --query "time series anomaly detection" --max-results 80 --download-top-n 10

$env:RESEARCHSENSEI_ENABLE_API_LLM="1"
$env:RESEARCHSENSEI_LLM_PROVIDER="mimo"
.venv\Scripts\python.exe scripts\run_main_chain_smoke.py --query "time series anomaly detection" --provider mimo
```

## Weak-Model Continuation Discipline

Future work may be handled by weaker models. Start by reading
`docs/STATUS.md`, then run the smoke commands above. Avoid broad refactors. If a
model emits malformed JSON, let schema validation fail closed or degrade the
component; do not coerce unsafe output into evidence-backed cards.
