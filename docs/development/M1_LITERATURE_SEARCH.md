# M1 Literature Search, Source Acquisition, And Reading Plan

## Goal

M1 has three modes:

**Direction Exploration Mode**: Given a broad research direction, search for surveys first, then build a direction framework with method families, chronology stages, landscape anchors, and recommended reading order.

**Focused Acquisition Mode**: Given a narrow query / title / DOI / URL / arXiv ID, find verified + relevant + PDF downloaded papers that can enter M2 for deep reading.

**Seed Paper Expansion Mode**: Given a seed paper (already read or being read), find upstream papers, downstream papers, related surveys, follow-up improvements, and build a local paper relation graph.

M1 does not teach the paper, parse the full paper, or generate paper/formula/drill cards. Those belong to M2.

## Three Modes

### Direction Exploration Mode

Status: NOT_IMPLEMENTED

Input: research direction (e.g. "时间序列异常检测")

Behavior:
1. Search for high-quality surveys first
2. If no qualified survey found, execute staged multi-source search
3. Build direction framework

Output:
- `survey_candidates.json`
- `direction_landscape.json` — with `method_families`, `chronology_stages`, `landscape_anchors`, `representative_papers`, `recommended_reading_order`, `gaps_or_open_questions`
- `reading_plan.json`

`direction_landscape.json` does NOT replace `reading_plan.json`. `direction_landscape.json` serves direction understanding. `reading_plan.json` serves reading plan. `A_READ_FOR_M2` serves single-paper deep reading entry.

LandscapeAnchor serves direction understanding, not necessarily M2 entry. A LandscapeAnchor can temporarily lack a PDF.

### Focused Acquisition Mode

Status: REAL_E2E_VERIFIED

Input: focused query / title / DOI / arXiv ID / URL

Pipeline:
```
user query -> real LLM query plan -> multi-source acquisition -> dedup -> verification -> LLM relevance judge -> download gate -> PDF validation -> reading_plan.json (A_READ_FOR_M2)
```

A_READ_FOR_M2 must satisfy ALL:
- `verification_status == verified`
- `llm_relevance_score >= 0.65`
- `llm_relevance_label in {HIGH, MEDIUM}`
- `should_a_read == true`
- `pdf_downloaded == true`
- `pdf_metadata_check == passed`
- `pdf_title_match == match`
- `can_enter_m2 == true`

### Seed Paper Expansion Mode

Status: NOT_IMPLEMENTED

Input: seed paper metadata / paper_id / uploaded paper

Behavior:
1. Find citing papers, cited papers, related surveys, same-route papers, follow-up improvements
2. Build local paper relation graph

Output:
- `paper_relation_graph.json`
- `seed_expansion_result.json`

## Non-Negotiable Requirements

- Query planning requires a real LLM. No heuristic fallback is allowed for M1 completion.
- Search/acquisition must use mature projects or official clients through adapters.
- Thin/wrapper-style HTTP implementations without User-Agent, retry, rate-limit detection, and structured diagnostics are not allowed. arXiv uses a robust official endpoint adapter (ARIS-style) with full diagnostic discipline. OpenAlex uses `pyalex`. Semantic Scholar uses official REST API via httpx with proxy support. Crossref uses `habanero`.
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

## External Reference Implementation Notes

### M1.1 Query Planning

- **Reference source**: ARIS `skills/research-lit/SKILL.md`, `skills/idea-discovery/SKILL.md`
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: Split broad research direction into searchable academic queries; preserve user direction / constraints / scope; use LLM to generate structured search plan instead of keyword splitting
- **ResearchSensei-owned target**: `query_plan.json`
- **Schema / artifact impact**: `english_query`, `query_variants`, `core_terms`, `related_terms`, `exclude_terms`, `search_intents`
- **Boundary**: Does not use ARIS skill output format. ResearchSensei retains QueryPlan schema.
- **Validation implication**: Chinese query must produce English academic query via real LLM. No LLM / LLM JSON failure = M1 failure.

### M1.2 Multi-source Acquisition

- **Reference source**: ARIS `tools/arxiv_fetch.py`, `tools/semantic_scholar_fetch.py`, `tools/openalex_fetch.py`, `skills/research-lit/SKILL.md`
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: arXiv User-Agent / contact email / rate-limit handling; source contribution tracking; source success/failure diagnostics; do not hide source failures
- **ResearchSensei-owned target**: `candidate_pool.json`, `source_metrics`
- **Schema / artifact impact**: `sources_attempted`, `sources_success`, `source_failures`, `source_contribution`, `candidate.source_ids`, `candidate.raw_source_metadata`
- **Boundary**: Does not adopt ARIS-only search. ResearchSensei retains best-of-breed source set: arXiv robust official endpoint adapter, OpenAlex/pyalex, Semantic Scholar official REST, Crossref/habanero. Other projects open for evaluation: Unpaywall, PaperQA, STORM, DeepXiv, Exa.
- **Validation implication**: `sources_attempted >= 4`. Source failure must have structured error. One source success does not mean multi-source stability.

### M1.3 论文原始材料获取 / Best Available Source Resolution

- **Reference source**: ARIS `tools/arxiv_fetch.py`, `skills/research-lit/SKILL.md`
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: Download only top-relevant PDFs; PDF download uses User-Agent / retry / backoff; PDF size guard; PDF header validation
- **ResearchSensei-owned target**: `source_resolution.json`
- **Schema / artifact impact**: `source_type`, `source_priority`, `preferred_m2_input`, `latex_source_url`, `latex_source_downloaded`, `latex_source_path`, `latex_source_sha256`, `latex_source_format`, `latex_main_file`, `structured_html_url`, `structured_html_downloaded`, `pdf_url`, `pdf_downloaded`, `pdf_metadata_check`, `pdf_title_match`, `source_confidence`, `source_warning`
- **Boundary**: M1 does lightweight source validation only, not M2 full-text parsing. Source files not committed to git. Does not download all candidates.
- **Validation implication**: M1 must try LaTeX source first, then structured HTML, then PDF. At least one deep-reading source downloaded. Metadata-only cannot enter M2.

M1.3 不只下载 PDF。M1.3 必须优先尝试获取 LaTeX source / arXiv source。如果 source 不可得，再尝试 structured HTML / XML。最后才是 PDF。

### M1.4 Dedup / Verification / Relevance

- **Reference source**: ARIS `tools/verify_papers.py`, `skills/research-lit/SKILL.md`
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: Three-layer candidate verification: (1) arXiv ID verification, (2) CrossRef DOI verification, (3) Semantic Scholar fuzzy title verification. Candidate status uses: `verified`, `unverified`, `verify_pending`, `error`. Transient API failure is `verify_pending`, not hallucination. Unverified candidates cannot enter A_READ. `verification_method` and `verification_reason` preserved.
- **ResearchSensei-owned target**: `filtered_candidates.json`
- **Schema / artifact impact**: `verification_status`, `verification_method`, `verification_reason`, `verification_confidence`, `rule_relevance_score`, `llm_relevance_score`, `llm_relevance_label`, `matched_concepts`, `missing_concepts`, `relevance_reason`, `should_download`, `should_a_read`
- **Boundary**: Does not vendor ARIS `verify_papers.py`. Does not treat ARIS CLI output as ResearchSensei artifact. ResearchSensei implements its own schema conversion and gate.
- **Validation implication**: `verified_candidate_count` must exist. `unverified_candidate_count` must exist. `verify_pending_count` must exist. `llm_judged_candidate_count` must exist. `relevance_filtered_count` must exist. A_READ must be verified + relevant + PDF validated.

### M1.5 Reading Plan

- **Reference source**: ARIS `skills/research-lit/SKILL.md`
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: Each recommended paper must state: Problem, Method, Results, Relevance, Source, Verification status. Only top-relevant papers enter the reading plan.
- **ResearchSensei-owned target**: `reading_plan.json`
- **Schema / artifact impact**: `role`, `selection_reason`, `relevance_reason`, `verification_status`, `source_confidence`, `metadata_confidence`, `risk_note`, `can_enter_m2`
- **Boundary**: Does not reuse ARIS markdown table. ReadingPlan is a ResearchSensei artifact. A_READ serves M2 downstream.
- **Validation implication**: `A_READ count >= 1`. Every A_READ has `can_enter_m2=true`. Every A_READ has `verification_status`, validated PDF, `relevance_reason`.

### General M1 Boundary

ARIS is one external reference. ResearchSensei retains its own module boundaries, schemas, artifacts, gates, APIs, frontend, and validation rules. Other external projects remain open for evaluation (Unpaywall, PaperQA, STORM, DeepXiv, Exa).

## Pipeline

```text
QueryPlanner.plan()
  -> query_plan.json
DirectionRunner._acquire()
  -> candidate_pool.json
SelectionService.deduplicate()
  -> deduplicated candidates
CandidateVerifier.verify_many()
  -> verification fields
RelevanceJudge.judge_many()
  -> LLM relevance fields
DirectionRunner._should_download()
  -> download/source decision
PaperSourceResolver.resolve_many()
  -> try latex_source first
  -> then structured_html
  -> then pdf
  -> source_resolution.json
SelectionService.build_reading_plan()
  -> filtered_candidates.json + reading_plan.json
```

Note: verification + LLM relevance judge happen before download. Candidates with `should_download=false` are not downloaded. `filtered_candidates.json` contains post-verify + post-relevance + post-source-resolution final candidates. M1 must not stop at PDF if LaTeX source is available. PDF success is not the best possible result when source is available.

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

`PaperSourceResolver` resolves best available source for each candidate. M1 不只下载 PDF，必须优先尝试获取 LaTeX source。

### M1.3 Source Priority

1. **latex_source** — preferred when arXiv source / LaTeX source package is available; best for formulas, citations, section hierarchy, labels, references, and bibliography
2. **structured_html** — preferred when publisher/arXiv HTML is available; useful for reading order and MathML/HTML structure
3. **pdf** — acceptable for M2 only when source is unavailable; must pass PDF validation and title match; formula fidelity is lower than source
4. **metadata_only** — can be used for landscape anchor or reference; cannot enter M2 deep reading

### source_resolution.json Schema

```json
{
  "paper_id": "",
  "title": "",
  "source_type": "latex_source | structured_html | pdf | metadata_only",
  "source_priority": 1,
  "preferred_m2_input": "latex_source | structured_html | pdf | none",

  "latex_source_url": "",
  "latex_source_downloaded": false,
  "latex_source_path": "",
  "latex_source_sha256": "",
  "latex_source_format": "tar | gz | zip | tex | unknown",
  "latex_main_file": "",
  "latex_aux_files": [],
  "latex_compile_status": "not_checked | compile_ok | compile_failed | not_applicable",
  "latex_source_error": "",

  "structured_html_url": "",
  "structured_html_downloaded": false,
  "structured_html_path": "",
  "structured_html_error": "",

  "pdf_url": "",
  "pdf_downloaded": false,
  "pdf_path": "",
  "pdf_sha256": "",
  "pdf_metadata_check": "passed | mismatch | unknown | not_applicable",
  "pdf_title_match": "match | mismatch | unknown | not_applicable",
  "pdf_error": "",

  "source_confidence": "high | medium | low",
  "source_warning": []
}
```

### Source Resolution Strategy

`PaperSourceResolver` records source resolution status for each type.

For downloaded sources it records:

- `download_status`
- `final_url`
- `content_type`
- `file_size`
- `sha256`
- `local_path`
- `error_code`

Supported status values include:

- `RESOLVED_LATEX_SOURCE_DOWNLOADED`
- `RESOLVED_STRUCTURED_HTML_DOWNLOADED`
- `RESOLVED_PDF_DOWNLOADED`
- `RESOLVED_PDF_URL_ONLY`
- `RESOLVED_LANDING_ONLY`
- `METADATA_ONLY`
- `FAILED_DOWNLOAD`
- `NO_SOURCE_FOUND`

`RESOLVED_LATEX_SOURCE_DOWNLOADED` or `RESOLVED_STRUCTURED_HTML_DOWNLOADED` or `RESOLVED_PDF_DOWNLOADED` can clear a paper for M2. LaTeX source is preferred over PDF.

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

`A_READ` requires ALL of (AND logic):

- `verification_status == verified`
- `scoring_breakdown.relevance_score >= 0.45` (rule-based)
- `llm_relevance_score >= 0.65` (LLM-based)
- `llm_relevance_label in {HIGH, MEDIUM}`
- `should_a_read == true`
- `can_enter_m2 == true`
- `source_confidence >= medium`
- `metadata_confidence >= medium`
- `role != IRRELEVANT`

A_READ_FOR_M2 must have one valid deep-reading input:

**Either** (preferred):
- `preferred_m2_input == latex_source`
- `latex_source_downloaded == true`
- `latex_main_file` exists
- `source_confidence in {high, medium}`

**Or**:
- `preferred_m2_input == structured_html`
- `structured_html_downloaded == true`
- `source_confidence in {high, medium}`

**Or** (fallback):
- `preferred_m2_input == pdf`
- `pdf_downloaded == true`
- `pdf_metadata_check == passed`
- `pdf_title_match == match`
- `source_confidence in {high, medium}`

`metadata_only` cannot enter `A_READ_FOR_M2`.

If no paper satisfies this, `reading_plan.status` becomes `DEGRADED` or `FAILED`, not a fake success.

## Artifacts

### Direction Exploration Mode

| Artifact | Description |
|---|---|
| `survey_candidates.json` | Survey candidates found by search |
| `direction_landscape.json` | Direction framework with method families, chronology stages, landscape anchors, recommended reading order, gaps |
| `reading_plan.json` | Reading plan derived from direction framework |

### Focused Acquisition Mode

| Artifact | Description |
|---|---|
| `query_plan.json` | Real LLM-generated query plan |
| `candidate_pool.json` | Raw candidate pool and source metrics |
| `source_resolution.json` | PDF/source acquisition status and download metadata |
| `filtered_candidates.json` | Final candidates with verification/LLM relevance/PDF fields |
| `reading_plan.json` | Prioritized plan with A_READ_FOR_M2/B_SKIM/C_REFERENCE and warnings |

### Seed Paper Expansion Mode

| Artifact | Description |
|---|---|
| `paper_relation_graph.json` | Graph of upstream/downstream/related papers |
| `seed_expansion_result.json` | Structured expansion result |

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

### Direction Exploration Mode 验收

当前状态：DOC_DESIGNED / NOT_IMPLEMENTED。

未来验收必须满足：

- broad direction query uses real LLM and real network
- `survey_candidates.json` exists
- `direction_landscape.json` exists
- `method_families` non-empty
- `chronology_stages` non-empty
- `landscape_anchors` non-empty
- `recommended_reading_order` non-empty
- every survey candidate has quality reason
- every landscape anchor has source, reason, verification status

### Focused Acquisition Mode 验收

当前状态：REAL_E2E_VERIFIED。

验收必须满足：

- `query_plan.json` exists
- `candidate_pool.json` exists
- `source_resolution.json` exists
- `filtered_candidates.json` exists
- `reading_plan.json` exists
- `sources_success >= 3`
- `verified_candidate_count` exists
- `llm_judged_candidate_count` exists
- at least one deep-reading source downloaded (latex_source or structured_html or pdf)
- every `A_READ_FOR_M2` satisfies:
  - `verification_status == verified`
  - `llm_relevance_score >= 0.65`
  - `llm_relevance_label in {HIGH, MEDIUM}`
  - `should_a_read == true`
  - has one valid deep-reading input (latex_source or structured_html or pdf with title match)
  - `can_enter_m2 == true`

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

### Seed Paper Expansion Mode 验收

当前状态：DOC_DESIGNED / NOT_IMPLEMENTED。

未来验收必须满足：

- seed paper metadata exists
- `paper_relation_graph.json` exists
- `seed_expansion_result.json` exists
- `upstream_papers` / `downstream_papers` / `related_surveys` / `follow_up_papers` present
- every relation has `relation_type`, evidence source, confidence
- unverified relation cannot be shown as trusted

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
