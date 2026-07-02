# M5 Engineering Reliability

This file is a reliability contract, not a current status table.
`docs/STATUS.md` is authoritative for module state and evidence.

M5 itself does not implement business features. It defines testing, smoke,
security, configuration, and reporting discipline for implemented surfaces.
M4 v1 is covered by local regression tests, including evidence-validated LLM
answer handling. PaperQA/vector-memory M4 reliability remains future work.

## Goals

- Keep local regression commands repeatable.
- Keep live smokes explicit and scoped.
- Prevent `.env`, keys, downloaded papers, source archives, cache, and generated
  report files from entering git.
- Keep source/adapters replaceable.
- Make failure modes visible enough for weaker models to continue safely.

## Parser And Canonical Invariants

- MinerU2.5-Pro via mineru-vl-utils is the primary M1 parser.
- Marker is fallback/audit baseline.
- Ollama is an optional structured refiner.
- Ollama must not modify latex, bbox, page, or source identity.
- M1 gate blocks all-formulas-in-Abstract.
- M1 gate blocks section contradiction.
- M1 gate blocks missing latex/crop/overlay.

## Required Regression Commands

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

Literature acquisition live smoke:

```powershell
.venv\Scripts\python.exe scripts\run_literature_acquisition_smoke.py --query "time series anomaly detection" --max-results 80 --download-top-n 10
```

Main-chain live smoke with ccswitch:

```powershell
$env:RESEARCHSENSEI_ENABLE_API_LLM="1"
$env:RESEARCHSENSEI_LLM_PROVIDER="cc_switch"
.venv\Scripts\python.exe scripts\run_main_chain_smoke.py --query "time series anomaly detection" --provider cc_switch
```

## Smoke Reporting Contract

Do not write new report files for routine readiness smokes. Console output and a
brief scoped update in `docs/STATUS.md` are enough.

Literature smoke must show:

- attempted sources;
- returned count by source;
- total deduplicated candidates;
- non-arXiv count;
- DOI count;
- legal fulltext count;
- source_ready/pdf_ready/html_ready/metadata_only counts;
- Unpaywall success/failure counts when email is configured;
- top failure reasons.

Main-chain smoke must show:

- selected candidate title and source IDs;
- selected input type and source strategy;
- source metrics;
- seed expansion status and group counts;
- handoff job ID;
- final understanding status;
- `/cards` status code;
- returned card components;
- warnings and final verdict.

## Security And Secrets

- `.env` must be ignored.
- `config/local.toml` must be ignored.
- Do not print API keys.
- Do not print full private email addresses in logs.
- Do not commit downloaded PDFs, arXiv source archives, workspace caches, or live
  generated artifacts.

## Weak-Model Reliability Rules

- Prefer small local patches over broad refactors.
- If a provider emits malformed JSON, record an LLM/validation failure and
  degrade/block the affected component.
- Do not lower QualityAuditor, FSA-5, evidence gates, or `/cards` gating.
- If live keys/network are missing, write "not live verified" instead of
  claiming a pass.
