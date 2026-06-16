# M1 Literature Search, Direction Exploration, And Seed Expansion

This is the M1 contract document. Current status and evidence live in
`docs/STATUS.md`.

## Scope

M1 is responsible for:

- direction query normalization;
- multi-source paper discovery;
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
| Legal full-text discovery | DEGRADED_SMOKE | arXiv, OpenAlex, Semantic Scholar, Crossref, DBLP, and Unpaywall participate; metadata-only papers stay visible with `needs_user_upload=true`. |
| deep_read handoff | DEGRADED_SMOKE / partial real | Source-backed candidates can create PaperWorkspace jobs. DOI-only handoff remains explicit `DOI_NOT_IMPLEMENTED`. |

## Source And Full-Text Priority

For each candidate, FullTextResolver should evaluate legal full-text options in
this order:

1. arXiv source/e-print
2. arXiv PDF
3. Unpaywall / OpenAlex best OA PDF
4. Semantic Scholar `openAccessPdf`
5. publisher OA PDF
6. repository PDF
7. legal HTML such as ar5iv when implemented
8. user upload
9. metadata-only

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
| arXiv | search + source/PDF | source_ready/pdf_ready | Source/e-print is preferred over PDF. |
| OpenAlex | search + OA metadata | OA URL/PDF metadata | DOI and best OA location should survive dedup. |
| Semantic Scholar | search + citation metadata | `openAccessPdf` | 429/rate limit must degrade one source, not the whole query. |
| Crossref | DOI/venue metadata | metadata-only | Do not pretend Crossref alone gives full text. |
| DBLP | CS venue metadata | metadata-only | Useful for discovery/venue; not a full-text source. |
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

## Smoke Command

```powershell
.venv\Scripts\python.exe scripts\run_literature_acquisition_smoke.py --query "time series anomaly detection" --max-results 80 --download-top-n 10
```

The smoke prints source metrics, dedup totals, non-arXiv counts, legal full-text
counts, source/PDF/metadata-only counts, and top failure reasons. It writes no
report files.

## Boundaries

- No pirate sources or paywall bypass.
- No fake PDF, DOI, arXiv ID, OA status, or citation relation.
- Do not hide metadata-only high-value papers.
- Do not treat DEGRADED_SMOKE as broad M1 REAL_E2E.
