# M1 Literature Search, Direction Exploration, And Seed Expansion

This is the M1 contract document. Current status and evidence live in
`docs/STATUS.md`.

## Scope

M1 is responsible for:

- direction query normalization;
- PaperSearch MCP multi-source paper discovery;
- dedup and FlashRank semantic reranking;
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
| Focused acquisition / selected-paper canonical handoff | narrow real verified | Do not expand this to full M1 completion. |
| Direction Exploration | DEGRADED_SMOKE | Returns overview, sub-directions, method families, candidates, reading order, source metrics, and handoff metadata. |
| Seed Expansion | DEGRADED_SMOKE | Returns upstream/downstream/same-route/survey/follow-up groups; weak relation claims are explicitly marked weak when citation graph is not verified. |
| Local paper library | UNIT_TESTED | Stores downloaded paper metadata, local paths, search runs, and delete state in `workspace/sensei.sqlite3`; used by M1 before network download. |
| Legal full-text discovery | DEGRADED_SMOKE | PaperSearch MCP supplies multi-source discovery metadata; arXiv/source links, OA venue landing pages, OpenAlex/Semantic Scholar OA metadata already present on candidates, and Unpaywall participate as full-text resolution inputs. Metadata-only papers stay visible with `needs_user_upload=true`. |
| deep_read handoff | DEGRADED_SMOKE / partial real | Source-backed candidates can create PaperWorkspace jobs. DOI-only handoff is narrowly implemented through Unpaywall/legal OA PDF when available; broad DOI acceptance remains pending. |

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
4. Rerank the deduplicated, full-text-enriched candidate pool with FlashRank
   (`ms-marco-MiniLM-L-12-v2` by default), while preserving the original
   external search rank as `search_rank`. The small in-repo quality guard only
   nudges candidates with usable legal full-text/source metadata, known CCF
   venue rank, and citation signal, while penalizing obviously weak metadata;
   it is not a hand-written relevance model.
5. Select top reranked candidates for download attempts, defaulting to the top
   10. Runtime fields use `download_selected`, `download_decision`, and
   `download_reason`. CCF rank remains an annotation and quality hint, not a
   hard download gate.
6. Compare the selected candidates against the local paper library by DOI,
   arXiv ID, normalized title, and known URLs.
7. Preserve queue order during reuse: if a selected paper already exists in the local
   library, reuse it in place. Do not redownload just to recreate the same PDF.
8. Pass the selected download queue into the legal downloader/source
   resolver. Library hits are returned as `library_reuse`; failed downloads,
   landing-only candidates, non-PDF responses, and missing PDF URLs are recorded
   explicitly instead of being silently replaced by lower-ranked papers.
9. Normalize downloaded source/PDF material into canonical M1 artifacts and
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
5. Library hits are reused in their original selected position. New candidates
   are attempted only when their position is inside the configured attempt
   limit.
6. `PaperSourceResolver` checks the library before any external resolver or
   HTTP PDF download. A hit returns a source-resolution item with
   `metadata.resolution_strategy = "library_reuse"`.

This preserves external search quality and still avoids duplicate downloads.
Failed downloads remain visible in `search_runs`. If too many selected papers
cannot be downloaded, M1 reports the high failure rate so the next step can be a
manual upload, a different query, or a clearly labeled supplemental search.

Current known quality note: broad RCA/LLM/AIOps queries are now recoverable via
fallback discovery, but relevance is still wider than ideal. They may include
forecasting, benchmarking, or general log-analysis papers unless the query is
made more specific, for example `LLM root cause localization AIOps incident
diagnosis` or `time series anomaly attribution root cause localization`.

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
4. PaperSearch/OpenAlex/Semantic Scholar candidate PDF URLs
5. known OA venue landing extraction (AAAI OJS, ACL Anthology, CVF, PMLR, OpenReview, USENIX, JMLR, PVLDB, etc.)
6. Unpaywall DOI lookup
7. publisher/repository OA PDF
8. legal HTML such as ar5iv when implemented
9. user upload
10. metadata-only

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

## Adapter Status

| Source/tool | Runtime role | Full-text capability | Notes |
|---|---|---|---|
| PaperSearch MCP | default broad discovery via external `paper-search-mcp` package | metadata + candidate URL/PDF/resource URLs | Default source set is `openalex,semantic,crossref,dblp,arxiv,core`. The adapter invokes the external `paper-search` CLI and normalizes returned rows into `CandidatePaper`. Configure sources with `RESEARCHSENSEI_PAPER_SEARCH_SOURCES`; install/update through the project `.venv`. |
| PaperSearch `google_scholar` source | optional PaperSearch source only | metadata + candidate URL/PDF URL when PaperSearch can fetch it | Not enabled by default. If used, configure it through `RESEARCHSENSEI_PAPER_SEARCH_SOURCES` and a working proxy/session strategy rather than ResearchSensei's removed legacy adapter. |
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
- overview;
- key sub-directions;
- method families;
- candidate papers;
- recommended reading order;
- source metrics for attempted sources;
- source/full-text readiness for each candidate.

Each candidate must include source, title, authors/year, URL/DOI/arXiv ID when
known, relevance score, verification status, source confidence, and whether it
can enter M2.

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
- Do not treat DEGRADED_SMOKE as broad M1 REAL_E2E.
