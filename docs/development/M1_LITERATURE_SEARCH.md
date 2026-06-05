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

| Capability | Implementation | Adapter |
|---|---|---|
| arXiv search | httpx + Atom XML parsing (custom robust fetcher) | `ArxivAdapter` |
| OpenAlex metadata search | `pyalex` | `OpenAlexAdapter` |
| Semantic Scholar metadata/search | httpx REST API (custom adapter) | `SemanticScholarAdapter` |
| Crossref DOI metadata | `habanero` | `CrossrefAdapter` |
| PDF download/validation | `httpx` with retry/backoff | `PaperSourceResolver` |

All third-party packages are isolated behind adapters so the core schemas and selection logic remain replaceable.

## External Project Borrowed Strategy

ResearchSensei's arXiv access strategy borrows engineering patterns from:

`wanshuiyin/Auto-claude-code-research-in-sleep/tools/arxiv_fetch.py`

Borrowed strategies (not copied code):

- Descriptive User-Agent on all arXiv requests
- Contact email via environment variable
- 429 retry with backoff
- 503 retry with backoff
- Rate exceeded body detection
- arXiv ID normalization and id_list lookup
- PDF download file size guard
- PDF header validation

These strategies are not optional optimizations. They are part of M1 real validation. Without them, arXiv requests easily fail due to default client behavior, network exit points, or rate limiting.

## ARIS Alignment

ARIS (`wanshuiyin/Auto-claude-code-research-in-sleep`) overlaps with M1 at high level. The following ARIS capabilities are relevant:

| ARIS Capability | Reuse Mode | Application in M1 |
|---|---|---|
| `arxiv_fetch.py` robust fetch | STRATEGY_BORROW | Already adopted: User-Agent, retry/backoff, id_list, PDF validation |
| `semantic_scholar_fetch.py` REST API | STRATEGY_BORROW | Already adopted: httpx adapter, API key, proxy support |
| `openalex_fetch.py` polite pool | STRATEGY_BORROW | Already adopted: pyalex with mailto |
| `verify_papers.py` 3-layer verification | STRATEGY_BORROW | Candidate verification against arXiv/Crossref/S2 catalogs |
| `research-lit` multi-source aggregation | STRATEGY_BORROW | Multi-source dedup and contribution tracking |
| Source verification status | STRATEGY_BORROW | `RESOLVED_PDF_DOWNLOADED` / `METADATA_ONLY` / `FAILED_DOWNLOAD` |
| `deepxiv_fetch.py` | EVALUATE_OTHER_PROJECTS | Optional future adapter for section-level paper access |

**Why not ARIS-only search**: ARIS's search capabilities are designed for workflow/skill execution and may not cover all use cases as well as ResearchSensei's best-of-breed multi-source approach. ResearchSensei retains OpenAlex, Semantic Scholar, Crossref, and arXiv as independent adapters, each optimized for its domain.

**Final M1 route**: best-of-breed multi-source search + ARIS verification/download discipline. M1 does not treat "found a PDF" as success; it must verify relevance, authenticity, and PDF consistency.

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

### arXiv Adapter

`ArxivAdapter` uses httpx with a custom robust fetch strategy (not the `arxiv` Python package's default client).

**User-Agent**:

```
ResearchSensei/0.5 (+https://github.com/ZehuaGou/Research-sensei)
```

If `RESEARCHSENSEI_CONTACT_EMAIL` is set, the User-Agent includes `mailto:<email>`.

**Query strategy** — at least three query forms are attempted:

1. `all:"<query>"` — all-fields exact phrase
2. `ti:"<query>"` — title-only exact phrase
3. raw query — fallback

If any form returns results, no further forms are tried.

**arXiv ID lookup** — when a candidate has an arXiv ID from another source (OpenAlex, Crossref, Semantic Scholar), `ArxivAdapter.search_by_id(arxiv_id)` uses the `id_list` parameter instead of `search_query`, bypassing the search endpoint entirely.

**Retry/backoff** — applies to both API search and PDF download:

| Error | Backoff sequence | Max retries |
|---|---|---|
| HTTP 429 | 5s, 10s, 15s | 3 |
| HTTP 503 | 2s, 4s, 8s | 3 |
| Rate exceeded (body) | 5s, 10s, 15s | 3 |
| Timeout / ConnectionError | 2s, 4s, 8s | 3 |

Body detection checks for `"Rate exceeded"` and `"Please reduce"` in the response text.

**Diagnostics recorded per attempt**:

- status code
- exception type
- query string
- attempt count
- retry/backoff wait time
- rate-limit body content

### Semantic Scholar Adapter

`SemanticScholarAdapter` uses the official Semantic Scholar REST API via httpx (not the `semanticscholar` Python package).

**Endpoint**: `https://api.semanticscholar.org/graph/v1/paper/search`

**Proxy support**: `httpx.Client(..., trust_env=True)` reads `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` from the environment. This allows Clash or other local proxies to route Semantic Scholar traffic.

**API key**: reads `SEMANTIC_SCHOLAR_API_KEY` from environment. When set, sends `x-api-key` header. Without a key, the free tier rate limit (currently ~100 requests/5min) applies.

**Retry/backoff**:

| Error | Backoff sequence | Max retries |
|---|---|---|
| HTTP 429 | 3s, 6s, 12s | 3 |
| HTTP 503 | 2s, 4s, 8s | 3 |
| Timeout / ConnectionError | 2s, 4s, 8s | 3 |

**Known limitation**: if Clash or the local proxy does not route `api.semanticscholar.org`, `ConnectionRefusedError` may occur even with `trust_env=True`. This is a runtime environment issue, not a code bug. The error is structured and recorded in source metrics.

### Crossref Adapter

`CrossrefAdapter` uses `habanero` for DOI metadata retrieval.

### OpenAlex Adapter

`OpenAlexAdapter` uses `pyalex` for metadata search with inverted-index abstract reconstruction.

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

### PDF Download Strategy

PDF downloads use:

- ResearchSensei User-Agent (same as arXiv adapter)
- `httpx.Client(trust_env=True)` for proxy support
- Retry/backoff on 429, 503, timeout, connection error (2s, 4s, 8s; max 3 retries)

After download, validation includes:

- content-type check
- `%PDF` magic header check (first 5 bytes)
- minimum file size (10 KB) to reject HTML error pages
- maximum file size (80 MB default)
- sha256 hash computation
- local_path recording

PDF files are not committed to git.

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

python -m pytest -q
python scripts/run_live_eval.py
```

### M1 Live Status Levels

**passed**:

- `sources_success >= 3`
- `pdf_download_success_count >= 1`
- `A_READ count >= 1`
- every A_READ has `can_enter_m2=true`

**degraded_passed**:

- `sources_success = 2`
- `pdf_download_success_count >= 1`
- `A_READ count >= 1`
- every A_READ has `can_enter_m2=true`
- failed sources have structured diagnostics (status code, exception type, retry count)

**failed**:

- `sources_success < 2`
- or no validated PDF downloaded
- or no A_READ paper
- or any A_READ has `can_enter_m2=false`

### Additional Checks

- `real_llm_query_planning=true`
- `english_query` is present
- generated report contains no API keys or bearer tokens
- downloaded PDF files are not committed to git

## Known Runtime Limitations

M1 real validation has observed:

- arXiv may return 429 or 503. Requires descriptive User-Agent, contact email, and retry/backoff to recover.
- Semantic Scholar without an API key may trigger free-tier rate limits. Setting `SEMANTIC_SCHOLAR_API_KEY` raises the limit.
- Clash or local proxy rules affect Semantic Scholar and arXiv access. If `api.semanticscholar.org` or `export.arxiv.org` is not routed through the proxy, `ConnectionRefusedError` or timeout may occur.
- OpenAlex and Crossref serve as stable supplementary sources but do not replace arXiv or Semantic Scholar for coverage and diagnostics.

## Current Boundary

M1 still does not perform:

- full PDF parsing
- paper understanding
- teaching card generation
- formula explanation
- direction synthesis
- advisor/drill/interactive learning

Those are later phases and must not be counted as completed by M1 live validation.
