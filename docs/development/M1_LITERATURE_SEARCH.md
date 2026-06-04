# M1 Literature Search, Source Acquisition, And Reading Plan

## Goal

M1 is the entry point for a research direction. It must turn a user's direction into a small, evidence-aware reading plan:

`user query -> real LLM query plan -> mature source acquisition -> dedup/score -> real source acquisition -> reading_plan.json`

M1 does not teach the paper, parse the full paper, or generate paper/formula/drill cards. Those belong to M2+.

## Non-Negotiable Requirements

- Query planning requires a real LLM. No heuristic fallback is allowed for M1 completion.
- Search/acquisition must use mature projects or official clients through adapters.
- arXiv and OpenAlex must not be implemented through self-written HTTP/XML/JSON wrappers.
- Semantic Scholar and Crossref are adapter-backed sources.
- A_READ papers must be cleared for M2, which currently means a validated PDF was downloaded and has a local path, file size, and sha256.
- M1 tests must run with real LLM, real network, real PDF download. Missing env/key/network = failure, not skip.
- `python -m pytest -q` must include tests_live. No more `--ignore=tests_live`.
- Mock/fake/skip are not valid test outcomes for M1.

## Reused Components

| Capability | Reused Tool | Dependency | Adapter |
|---|---|---|---|
| arXiv search | `arxiv` Python package | `arxiv>=2.1` | `ArxivAdapter` |
| OpenAlex metadata search | `pyalex` | `pyalex>=0.15` | `OpenAlexAdapter` |
| Semantic Scholar metadata/search | `semanticscholar` | `semanticscholar>=0.8` | `SemanticScholarAdapter` |
| Crossref DOI metadata | `habanero` | `habanero>=1.2` | `CrossrefAdapter` |
| PDF download/validation | `httpx` client already in project | existing | `PaperSourceResolver` |

All third-party packages are isolated behind adapters so the core schemas and selection logic remain replaceable.

## Pipeline

```text
QueryPlanner.plan()
  -> query_plan.json
DirectionRunner._acquire()
  -> candidate_pool.json
PaperSourceResolver.resolve_many()
  -> source_resolution.json
SelectionService.deduplicate()
  -> filtered_candidates.json
SelectionService.build_reading_plan()
  -> reading_plan.json
```

## M1.1 Query Planning

`QueryPlanner.plan(user_query)` now requires an injected LLM client. If no LLM is available, or if the LLM output is not valid JSON, it raises `QueryPlanningError`.

Required fields:

- `direction_en`
- `english_query`
- `query_variants`
- `core_terms`
- `related_terms`
- `exclude_terms`
- `search_intents`

This prevents Chinese directions from being searched with poor heuristic English terms.

## M1.2 Acquisition

`DirectionRunner` defaults to four sources:

- `arxiv`
- `openalex`
- `semantic_scholar`
- `crossref`

Each source records source metrics:

- `source`
- `attempted`
- `success`
- `count`
- `latency_ms`
- `error`

Source failure is recorded in warnings and does not hide other source results.

## M1.3 Source Acquisition

`PaperSourceResolver` records whether a candidate only has metadata, a landing page, a PDF URL, or a validated downloaded PDF.

For downloaded PDFs it records:

- `download_status`
- `final_url`
- `content_type`
- `file_size`
- `sha256`
- `local_path`
- `error_code`

Supported status values include:

- `RESOLVED_PDF_DOWNLOADED`
- `RESOLVED_PDF_URL_ONLY`
- `RESOLVED_LANDING_ONLY`
- `METADATA_ONLY`
- `FAILED_DOWNLOAD`
- `NO_SOURCE_FOUND`

Only `RESOLVED_PDF_DOWNLOADED` can clear a paper for M2.

## M1.4 Dedup And Scoring

Dedup priority:

1. DOI
2. arXiv ID
3. Semantic Scholar ID
4. normalized title
5. normalized title + year

Metadata merge keeps source lists and fills missing DOI/arXiv/PDF/landing/citation/abstract fields from duplicates.

Scoring uses real metadata fields:

- relevance score
- venue prestige signal
- citation count
- code availability
- method representativeness
- source reliability
- open-access signal
- PDF availability
- metadata completeness
- recency
- noise penalty

## M1.5 Reading Plan Gate

Priorities:

- `A_READ`: deep reading candidate. Must have `can_enter_m2=true`.
- `B_SKIM`: useful background but not cleared for deep-card generation.
- `C_REFERENCE`: metadata-only reference.
- `D_IGNORE`: filtered out of the returned learning plan.

`A_READ` requires:

- sufficient relevance
- medium-or-better metadata confidence
- medium-or-better source confidence
- PDF available and actually downloaded/validated
- `can_enter_m2=true`

If no paper satisfies this, `reading_plan.status` becomes `DEGRADED` or `FAILED`, not a fake success.

## Artifacts

| Artifact | Description |
|---|---|
| `query_plan.json` | Real LLM-generated query plan |
| `candidate_pool.json` | Raw candidate pool and source metrics |
| `source_resolution.json` | PDF/source acquisition status and download metadata |
| `filtered_candidates.json` | Deduplicated candidate pool |
| `reading_plan.json` | Prioritized plan with A_READ/B_SKIM/C_REFERENCE and warnings |

## Live Acceptance

Run:

```powershell
$env:RUN_LIVE_TESTS="1"
$env:RUN_LLM_TESTS="1"
$env:RESEARCHSENSEI_LIVE_EVAL="1"
$env:RESEARCHSENSEI_MAX_LIVE_CASES="5"
$env:RESEARCHSENSEI_MAX_LLM_COST_USD="1.00"
$env:RESEARCHSENSEI_MAX_LLM_TOKENS="30000"

python -m pytest -q tests_live
python scripts/run_live_eval.py
```

M1 passes only if:

- `real_llm_query_planning=true`
- `english_query` is present
- at least one mature source succeeds
- at least one candidate is retrieved
- at least one PDF is downloaded and validated
- at least one A_READ paper exists
- every A_READ paper has `can_enter_m2=true`
- generated report contains no API keys or bearer tokens

## Current Boundary

M1 still does not perform:

- full PDF parsing
- paper understanding
- teaching card generation
- formula explanation
- direction synthesis
- advisor/drill/interactive learning

Those are later phases and must not be counted as completed by M1 live validation.
