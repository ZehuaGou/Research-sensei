# M1 Literature Search, Direction Exploration, And Seed Expansion

This is the M1 contract document. Current status and evidence live in
`docs/STATUS.md`.

## Scope

M1 is responsible for:

- direction query normalization;
- Google Scholar MCP paper discovery;
- dedup and relevance scoring;
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
| Legal full-text discovery | DEGRADED_SMOKE | Google Scholar MCP supplies discovery URLs; arXiv/source links, OA venue landing pages, OpenAlex/Semantic Scholar OA metadata already present on candidates, and Unpaywall participate only as full-text resolution inputs. Metadata-only papers stay visible with `needs_user_upload=true`. |
| deep_read handoff | DEGRADED_SMOKE / partial real | Source-backed candidates can create PaperWorkspace jobs. DOI-only handoff is narrowly implemented through Unpaywall/legal OA PDF when available; broad DOI acceptance remains pending. |

## Source And Full-Text Priority

For each candidate, FullTextResolver should evaluate legal full-text options in
this order:

1. arXiv source/e-print
2. arXiv PDF
3. OpenAlex/Semantic Scholar hidden arXiv crosslink
4. Google Scholar/OpenAlex/Semantic Scholar candidate PDF URLs
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
| Google Scholar | default broad discovery via `JackKuo666/Google-Scholar-MCP-Server` | metadata + candidate URL/PDF URL | This is the default M1 discovery path. ResearchSensei wraps that MCP project's `google_scholar_search` and does not own custom Scholar scraping logic. Because the upstream repo currently fails direct `pip install` packaging, the adapter loads `google_scholar_web_search.py` from an installed module, a configured checkout, or `.cache/researchsensei/google-scholar-mcp-server`. |
| arXiv | full-text resolution when URL/arXiv ID is found | source_ready/pdf_ready | Source/e-print is preferred over PDF. Not a default discovery source. |
| OpenAlex | OA metadata already attached to candidates or explicit diagnostics | OA URL/PDF metadata | Not a default discovery source. Its source IDs and OA locations remain useful for resolver tests and explicit diagnostics. |
| Semantic Scholar | OA metadata already attached to candidates or explicit diagnostics | `openAccessPdf` | Not a default discovery source. 429/rate limit must degrade one explicit source, not the whole query. |
| Crossref | DOI/venue metadata in explicit diagnostics | metadata-only | Do not pretend Crossref alone gives full text. |
| DBLP | CS venue metadata in explicit diagnostics | metadata-only | Not a full-text source. |
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

The default acceptance command now searches only through the Google Scholar MCP
adapter, then resolves/downstreams the returned URLs through official/OA
download paths. Legacy source adapters may still be passed explicitly for
diagnostics, but they are not the product default.

The acceptance command prints source metrics, dedup totals, non-arXiv counts, legal full-text
counts, source/PDF/metadata-only counts, and top failure reasons. It writes no
report files.

## Boundaries

- No pirate sources or paywall bypass.
- Google Scholar discovery is routed through
  `JackKuo666/Google-Scholar-MCP-Server`; ResearchSensei only normalizes the MCP
  result rows and feeds returned URLs into official/OA full-text resolvers.
- Direct `pip install git+https://github.com/JackKuo666/Google-Scholar-MCP-Server.git`
  currently fails on upstream flat-layout packaging. Use the adapter's checkout
  loader instead of copying Scholar parsing logic into ResearchSensei.
- No fake PDF, DOI, arXiv ID, OA status, or citation relation.
- Do not hide metadata-only high-value papers.
- Do not treat DEGRADED_SMOKE as broad M1 REAL_E2E.
