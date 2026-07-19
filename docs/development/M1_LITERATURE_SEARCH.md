# M1 Literature Search, Direction Exploration, And Seed Expansion

This is the M1 contract document. Current status and evidence live in
`docs/STATUS.md`.

## Scope

M1 is responsible for:

- direction query normalization;
- PaperSearch MCP multi-source paper discovery;
- dedup and FlashRank semantic reranking;
- deterministic concept-coverage and intent-mismatch relevance gating;
- CCF/venue-registry annotation and reporting before download;
- local paper-library reuse and duplicate avoidance;
- legal full-text discovery;
- arXiv source-first handoff;
- Direction Exploration bundle generation;
- Seed Expansion bundle generation;
- deep_read handoff into M2/M3.

It is not responsible for M4 tutoring, long-term memory, or drills.

## Current Implemented Surfaces

| Surface | Status label to use | Notes |
|---|---|---|
| Deterministic relevance benchmark | OFFLINE_VERIFIED | Fixed English, Chinese, and mixed-language cases cover task/data/method concepts and historical semantic mismatches. |
| Direction Exploration | UNIT_TESTED | Returns overview, sub-directions, method families, candidates, reading order, four-layer status, source metrics, and handoff metadata. Current live provider state is recorded separately in `docs/STATUS.md`. |
| Seed Expansion | UNIT_TESTED | Returns upstream/downstream/same-route/survey/follow-up groups; weak relation claims are explicitly marked weak when citation graph is not verified. |
| Local paper library | UNIT_TESTED | Stores downloaded paper metadata, local paths, search runs, and delete state in `workspace/sensei.sqlite3`; uses WAL, busy timeout, migrations, and guarded cleanup. |
| Legal full-text discovery | UNIT_TESTED_WITH_FIXTURES | PaperSearch MCP metadata, official/OA landing extraction, arXiv, and Unpaywall feed source resolution. Metadata-only papers stay visible with `needs_user_upload=true`; current live download status is separate. |
| deep_read handoff | UNIT_TESTED | Only relevance-gated and source-backed candidates can create PaperWorkspace jobs. Long execution has a persistent asynchronous job path; the synchronous route remains compatible. |

## Deterministic Relevance Contract

Relevance is not inferred from pipeline completion and is not delegated solely
to another LLM. For every query, M1 evaluates:

- required task, data-shape, and method concepts;
- optional concepts that improve confidence;
- forbidden intent mismatches;
- whether survey papers are allowed;
- compound-query concept coverage;
- explicit penalties for survey, forecasting, imputation, anomaly detection,
  clustering, graph, GNN, diffusion, and RCA mismatches.

Top-1 and deep-read candidates use explicit minimum thresholds. An optional LLM
judge may veto or annotate but cannot rescue a deterministic failure. If no
candidate clears the gate, M1 returns `DEGRADED` or `BLOCKED` and does not pick
an incorrect paper to keep the pipeline moving.

The maintained offline fixture has at least twenty English, Chinese, and mixed
queries. It includes acceptable/unacceptable examples and historical wrong
selections. Run it with:

```powershell
.venv\Scripts\python.exe scripts\run_m1_relevance_benchmark.py
```

## Source And Full-Text Priority

The default M1 product flow is:

1. Query PaperSearch MCP through `PaperSearchMcpAdapter`. The default source
   set is `openalex,semantic,crossref,dblp,arxiv,core`, configurable with
   `RESEARCHSENSEI_PAPER_SEARCH_SOURCES`. Google Scholar can still be added to
   that source list when a proxy/session strategy is available, but it is not
   the default because direct Scholar automation is CAPTCHA-prone.
2. Normalize each row into title, authors, year, venue/journal, URL, DOI/arXiv
   ID when present, and source metadata.
3. Deduplicate candidates and annotate the venue against the local CCF venue
   registry when a true venue/journal name is available.
4. Apply deterministic task/concept relevance scoring and mismatch penalties.
   Candidates below the query gate remain visible for diagnostics but cannot
   become Top-1 or deep-read selections.
5. Rerank the gated, deduplicated candidate pool with FlashRank
   (`ms-marco-MiniLM-L-12-v2` by default), while preserving the original
   external search rank as `search_rank`. The small in-repo quality guard only
   nudges candidates with usable legal full-text/source metadata, known CCF
   venue rank, and citation signal, while penalizing obviously weak metadata;
   it is not a hand-written relevance model.
6. Attempt every candidate that clears both the deterministic relevance gate
   and the deep-read relevance threshold. The number attempted is therefore an
   outcome (possibly 2, 7, 10, or 13), never a quota. A positive
   `search.max_download_candidates` is an optional user safety cap; its default
   `0` means unlimited, and a cap always preserves relevance order rather than
   preferring an easier-to-download but weaker paper. Runtime fields use
   `download_selected`, `download_decision`, and `download_reason`. CCF rank
   remains an annotation and quality hint, not a hard download gate.
7. Compare the selected candidates against the local paper library by DOI,
   arXiv ID, normalized title, and known URLs.
8. Preserve queue order during reuse: if a selected paper already exists in the local
   library, reuse it in place. Do not redownload just to recreate the same PDF.
9. Pass the selected download queue into the legal downloader/source
   resolver. Library hits are returned as `library_reuse`; failed downloads,
   landing-only candidates, non-PDF responses, and missing PDF URLs are recorded
   explicitly instead of being silently replaced by lower-ranked papers.
10. Normalize downloaded source/PDF material into canonical M1 artifacts and
   hand only M2-ready artifacts onward.

This design intentionally uses PaperSearch MCP as the external discovery layer
instead of maintaining separate in-repo scrapers for each paper source. The
local paper library is only the memory layer that prevents duplicate download,
supports reuse, and gives the user a manageable inventory of downloaded papers.

Downloaded direction-search material lives under:

`workspace/m1_searches/<direction-or-topic>/`

The direction folder should contain all downloaded papers for that direction.
PDF files are named from the paper title, for example
`Graph neural network-based anomaly detection in multivariate time series.pdf`,
not generic names such as `source.pdf`. Each folder also keeps `manifest.json`
and `README.md` with title, authors, venue/journal, CCF rank, download status,
SHA-256, and local path. When another nearby direction downloads the same paper
title, M1 should reuse the existing named PDF instead of downloading a duplicate.

## Local Paper Library

The paper library is stored in the same SQLite database as jobs:

`workspace/sensei.sqlite3`

Runtime module:

`src/researchsensei/library/store.py`

Tables:

- `papers`: one row per known downloaded paper, including title, authors, year,
  venue/journal, canonical venue name, CCF rank, DOI, arXiv ID, PDF URL, landing
  URL, local path, SHA-256, file size, first/last seen timestamps, and soft-delete
  timestamp.
- `paper_sources`: source IDs and URLs observed for the paper.
- `search_runs`: one row per M1 search run, including query, topic folder,
  candidate count, new download count, and reuse count.
- `search_run_papers`: per-run paper rows, including original rank/order,
  action (`downloaded`, `reused`, `failed`, `skipped`, `not_attempted`), CCF
  selection flag, venue, rank, and local path.

Reuse algorithm:

1. M1 calls PaperSearch MCP for the current query.
2. If PaperSearch returns results, M1 keeps the deduped multi-source result
   pool and uses FlashRank to build the download queue. The original external
   result position remains visible as `search_rank`.
3. If PaperSearch is unavailable or returns no candidates, M1 may use temporary
   legacy fallback adapters, but the run must be labeled as degraded primary
   discovery.
4. Each selected candidate is matched against the library by DOI, arXiv ID,
   normalized title, and known source/PDF/landing URLs.
5. Library hits are reused in their original relevance position. New candidates
   are attempted when they pass the strict relevance threshold; a configured
   positive safety cap may stop later candidates but never reorder them by
   download convenience.
6. `PaperSourceResolver` checks the library before any external resolver or
   HTTP PDF download. A hit returns a source-resolution item with
   `metadata.resolution_strategy = "library_reuse"`.

PMC articles use the official machine-access route instead of treating the
interactive article page as the download API. M1 lists the article's versioned
metadata in the PMC Cloud Service, requires the record to be open access or an
author manuscript, reads its declared `pdf_url`, and accepts the response only
after the ordinary PDF validation gates pass. This avoids the HTML
"preparing download" response returned by some direct PMC page links.

This preserves external search quality and still avoids duplicate downloads.
Failed downloads remain visible in `search_runs`. If too many selected papers
cannot be downloaded, M1 reports the high failure rate so the next step can be a
manual upload, a different query, or a clearly labeled supplemental search.

Broad RCA/LLM/AIOps queries remain difficult for live discovery, but the
deterministic gate now blocks forecasting, generic benchmarking, or unrelated
log-analysis candidates when required RCA/AIOps concepts are missing. A live
provider may still return no acceptable candidate; that outcome is an explicit
relevance degradation, not a reason to lower the threshold.

Management API:

- `GET /api/v1/library/papers?query=&limit=100`
- `GET /api/v1/library/search_runs?limit=50`
- `DELETE /api/v1/library/papers/{paper_id}?remove_file=true`

Management UI:

- `/papers/library` lists downloaded papers, shows local paths and recent M1
  search runs, supports title/venue filtering, and can delete a paper record plus
  its local PDF.

On app startup, M1 imports existing `workspace/m1_searches/*/manifest.json`
files into the library, so previously downloaded direction folders become
searchable without redownloading.

For each candidate, FullTextResolver should evaluate legal full-text options in
this order:

1. arXiv source/e-print
2. arXiv PDF
3. OpenAlex/Semantic Scholar hidden arXiv crosslink
4. official versioned PMC Cloud PDF for identified PMC articles
5. PaperSearch/OpenAlex/Semantic Scholar candidate PDF URLs
6. known OA venue landing extraction (AAAI OJS, ACL Anthology, CVF, PMLR, OpenReview, USENIX, JMLR, PVLDB, etc.)
7. Unpaywall DOI lookup
8. publisher/repository OA PDF
9. legal HTML such as ar5iv when implemented
10. user upload
11. metadata-only

Candidate output must preserve:

- `discovery_sources`
- DOI and arXiv ID when known
- landing URL
- candidate source/PDF URLs
- selected full-text source
- `fulltext_status`
- `fulltext_failure_reason`
- `can_deep_read`
- `needs_user_upload`

`can_deep_read=true` is allowed only for legal source/PDF/HTML-ready candidates.

## Optional Authorized Browser Session

Some publisher sites serve a PDF in a normal, verified Chrome session while
rejecting backend HTTP clients or browsers launched with automation flags.
ResearchSensei therefore starts a dedicated installed-Chrome profile without a
Playwright launch marker. Only after the user completes legitimate verification
does the helper connect locally and save an explicit storage-state file. This
is a last download fallback for papers that already passed strict relevance; it
does not inspect the user's normal Chrome profile and does not bypass CAPTCHA,
subscription, or institutional-access controls.

Create or refresh the dedicated session from the repository root:

```powershell
node frontend/scripts/browser_fulltext.mjs capture-session workspace/browser-session.json https://dl.acm.org/
```

If an older helper window loops on the human-verification page, stop that
command with `Ctrl+C`, close the old window, update the checkout, and rerun the
same command. The current helper uses the installed Chrome plus the dedicated
`workspace/browser-profile/`; it does not launch the verification page through
Playwright.

Complete any legitimate login/security check in the opened Chrome window, then
return to the terminal and press Enter. Enable the fallback in
`config/local.toml`:

```toml
[search]
browser_download_enabled = true
browser_session_state = "workspace/browser-session.json"
browser_headless = false
max_download_candidates = 0
```

The storage state and its paired `workspace/browser-profile/` live under the
ignored `workspace/` directory and must never be committed or shared. The
dedicated profile persists the browser trust/session data while remaining
separate from the user's everyday Chrome profile. Keep visible mode for ACM or
other security-sensitive publishers; headless mode is an opt-in after live
validation. Normal legal OA URLs are still tried first. The browser is used
only after ordinary HTTP candidates fail or a publisher landing page has no
extractable PDF URL; the resulting file must still pass the same PDF magic,
size, SHA-256, and metadata checks before M2 can use it.

This is a publisher-agnostic fallback, not an ACM-specific branch. ACM, IEEE,
Springer, Elsevier, or another site can use it when a legitimate user session
can access the paper and the ordinary machine route fails. Conversely, arXiv,
PMC Cloud, repository PDFs, and other direct OA responses never open Chrome
when their normal download succeeds. The runtime records
`resolution_strategy=authorized_browser_session` and
`browser_mode=native_chrome_cdp` when this final fallback is actually used.

## Adapter Status

| Source/tool | Runtime role | Full-text capability | Notes |
|---|---|---|---|
| PaperSearch MCP | default broad discovery via external `paper-search-mcp` package | metadata + candidate URL/PDF/resource URLs | Default source set is `openalex,semantic,crossref,dblp,arxiv,core`. The adapter invokes the external `paper-search` CLI and normalizes returned rows into `CandidatePaper`. Configure sources with `RESEARCHSENSEI_PAPER_SEARCH_SOURCES`; install/update through the project `.venv`. |
| PaperSearch `google_scholar` source | optional PaperSearch source only | metadata + candidate URL/PDF URL when PaperSearch can fetch it | Not enabled by default. If used, configure it through `RESEARCHSENSEI_PAPER_SEARCH_SOURCES`; publisher download can separately use the explicit authorized-browser fallback above. |
| arXiv | full-text resolution when URL/arXiv ID is found | source_ready/pdf_ready | Source/e-print is preferred over PDF. Can arrive through PaperSearch MCP or explicit diagnostics. |
| OpenAlex | PaperSearch source and OA metadata enrichment | OA URL/PDF metadata | Used through PaperSearch MCP by default. Existing in-repo adapter is legacy fallback/test support until the PaperSearch path is fully proven. |
| Semantic Scholar | PaperSearch source and OA metadata enrichment | `openAccessPdf` | Used through PaperSearch MCP by default. A free `SEMANTIC_SCHOLAR_API_KEY` / `S2_API_KEY` improves rate-limit reliability. |
| Crossref | PaperSearch DOI/venue metadata source | metadata-only | Do not pretend Crossref alone gives full text. |
| DBLP | PaperSearch CS venue metadata source | metadata-only | Useful for CS conference/journal metadata; not a full-text source. |
| Unpaywall | DOI -> legal OA lookup | publisher/repository OA PDF or landing | Requires `UNPAYWALL_EMAIL` or `RESEARCHSENSEI_CONTACT_EMAIL`. |
| local upload | user-provided full text | PDF/canonical | Fallback for valuable metadata-only papers. |

## DirectionBundle Requirements

Direction Exploration output must include:

- status: SUCCESS, DEGRADED, EMPTY_RESULT, or BLOCKED;
- `pipeline_status`: whether search/source/M2/card execution completed;
- `relevance_status`: whether the selected candidate cleared the deterministic
  query gate;
- `source_status`: whether legal verified full text can enter M2;
- `understanding_status`: whether cards/evidence are safe for user display;
- overview;
- key sub-directions;
- method families;
- candidate papers;
- recommended reading order;
- source metrics for attempted sources;
- source/full-text readiness for each candidate.

Each candidate must include source, title, authors/year, URL/DOI/arXiv ID when
known, relevance score, verification status, source confidence, and whether it
can enter M2. The four status dimensions are independent; a pipeline success
does not erase a relevance, source, or understanding failure.

## SeedExpansionBundle Requirements

Seed Expansion output must include:

- upstream papers;
- downstream papers;
- same-route papers;
- related surveys;
- follow-up improvements;
- recommended expansion order;
- relation reason, relation type, confidence, source, and full-text readiness
  per paper.

When real citation data is unavailable, relation reasons must say weak
query/title-similarity or metadata relation. Do not fake a citation graph.

## Acceptance Command

```powershell
.venv\Scripts\python.exe scripts\run_literature_acquisition_acceptance.py --query "time series anomaly detection" --max-results 80 --download-top-n 10
```

The default acceptance command searches through PaperSearch MCP,
normalizes paper metadata, applies CCF venue annotation, then
reranks with FlashRank, and resolves/downloads only the selected candidates
through official/OA download paths. Legacy source adapters may still be passed
explicitly for diagnostics, but they are not the product default.

The acceptance command prints source metrics, dedup totals, non-arXiv counts, legal full-text
counts, source/PDF/metadata-only counts, and top failure reasons. It writes no
report files.

## Boundaries

- No pirate sources or paywall bypass.
- Broad discovery is routed through PaperSearch MCP. ResearchSensei normalizes
  returned result rows and feeds URLs into official/OA full-text resolvers.
- Do not reintroduce the removed native Google Scholar scraper as the product
  default. Scholar-style discovery, when needed, should go through PaperSearch
  MCP or another explicit external provider with a working anti-bot strategy.
- No fake PDF, DOI, arXiv ID, OA status, or citation relation.
- Do not hide metadata-only high-value papers.
- Do not treat offline fixtures or a completed pipeline as broad M1 REAL_E2E.
