# ResearchSensei Module Contracts

`docs/STATUS.md` is the authoritative state file. This document records stable
Input, Output, and Boundary rules for modules so future weaker models can modify
the project without reopening the whole design.

## query

Input: user research direction text and optional limits.
Output: normalized query variants for acquisition.
Boundary: do not invent papers or source identifiers.

## acquisition

Input: query text and the configured PaperSearch MCP discovery source.
Output: `CandidatePaper` objects normalized from PaperSearch MCP result rows,
including title, authors, year, venue/journal, discovery URL, DOI/arXiv ID when
known, plus legal full-text lookup metadata from official/OA resolver inputs.
Boundary: adapters may fail independently; failures must become source metrics
and warnings, not fake success. Direction acquisition should continue across
fallback variants only when the primary PaperSearch query cannot produce usable
candidates; when the primary external search returns results, M1 should preserve
that order rather than injecting venue-targeted variants into the same result
pool.

## selection

Input: raw candidates from acquisition.
Output: deduplicated candidates with relevance, confidence, `discovery_sources`,
source IDs, DOI, arXiv ID, URL, CCF venue rank, FlashRank/download queue fields
(`search_rank`, `rerank_rank`, `rank_score`, `download_selected`,
`download_decision`), and full-text readiness retained.
Boundary: deterministic required-concept coverage and forbidden
intent-mismatch penalties gate Top-1 and deep-read candidates. An optional LLM
judge cannot rescue a deterministic failure. Metadata-only high-value papers
must not be discarded merely because
they cannot immediately enter M2. The default M1 download queue is produced from
the external PaperSearch result pool by the configured reranker, with the
original external result position preserved as `search_rank`. CCF rank is
retained as a quality annotation and reporting signal, not as a hard gate that
blocks unranked but relevant search results from download attempts.

## paper_library

Input: downloaded M1 source-resolution items, candidate metadata, search query,
and the direction folder under `workspace/m1_searches/`.
Output: persistent paper records in `workspace/sensei.sqlite3`, including title,
authors, year, venue/journal, CCF rank, DOI, arXiv ID, URL fields, SHA-256,
local path, search-run membership, and delete state.
Boundary: the library is a reuse and management layer, not a replacement search
engine. M1 must still use PaperSearch MCP for fresh discovery, then use the
library to avoid duplicate download and to reuse already downloaded legal full
text. Soft-deleted papers must not be reused unless explicitly restored later.

## source_resolver

Input: `download_selected` candidate payload, local paper-library match, arXiv
ID/URL, DOI-resolved legal PDF, PDF URL, or uploaded file.
Output: resolved source status, downloaded legal full text when available, and a
preferred M2 input type such as `arxiv_source`, `arxiv_pdf`, `external_pdf`, or
`metadata_only`.
Boundary: arXiv source/e-print is preferred over PDF; DOI-only deep_read may
resolve to a legal OA PDF through Unpaywall, otherwise it fails explicitly with
`NO_LEGAL_OA_FULLTEXT_FOUND`; no paywall bypassing. Direction-search downloads
are grouped by topic under `workspace/m1_searches/<direction>/`, with PDF files
named from paper titles plus a manifest for reuse and duplicate avoidance.
Before any network download, source_resolver must check the paper library; a hit
returns `library_reuse` and records the current search run without redownloading.

## ingestion

Input: canonical bundle, arXiv source, PDF, or resolved source directory.
Output: page-preserving parsed document, optional OpenCode page-vision analysis
and persistent session, passage index, claim evidence, evidence pack,
understanding status, and artifact manifest.
Boundary: malformed input or missing evidence must degrade/block rather than
creating fake evidence. OpenCode visual formula transcriptions use OCR
provenance and cannot impersonate source LaTeX.

## grounding

Input: passage index and extracted claims.
Output: evidence references linked to source text, section, page/block, and
formula context when available.
Boundary: method/result/formula claims require real source support.

## understanding

Input: evidence pack and optional configured LLM.
Output: paper skeleton/card, formula cards, teaching cards, component status,
warnings, and quality report.
Boundary: BASELINE_ONLY is allowed as a status but must not be reported as real
LLM understanding. Paper/formula/teaching card-builder failures fail closed as
`BLOCKED_UNDERSTANDING`; they must not be hidden as user-facing partial cards.

## teaching

Input: supported paper understanding and teaching evidence.
Output: teaching cards for successful components.
Boundary: teaching cards cannot explain blocked components as if they passed.

## formula

Input: formula evidence, formula origin, OCR/source status, and surrounding
method context.
Output: formula cards, skipped/limited formula explanations, or blocked formula
status.
Boundary: unknown formula origin cannot produce detailed derivation; FSA-5 stays
strict.

## direction

Input: direction query or seed paper payload.
Output: DirectionBundle, SeedExpansionBundle, source metrics, grouped papers,
reading order, and deep_read handoff payloads.
Boundary: `pipeline_status`, `relevance_status`, `source_status`, and
`understanding_status` are independent; one `SUCCESS` cannot stand for all of
them. Citation graph claims must be real or clearly marked as weak
query/title-similarity relations. DOI/landing URLs must not be smuggled through
`arxiv_url`; only actual arXiv URLs belong there.

## patterns

Input: method-family and sub-direction signals.
Output: lightweight grouping labels used by Direction Exploration and Seed
Expansion.
Boundary: labels are navigation hints, not proof of scientific relation.

## drill

Input: M4 learning state and paper-grounded teaching/advisor context.
Output: future full drill sessions. Current v1 only exposes advisor-style
questions and answer evaluation.
Boundary: do not present v1 advisor checks as a complete drill engine.

## interactive

Input: current job id, selected text, formula id/symbol, user question, advisor
mode, and existing user-facing M2 artifacts.
Output: selected-text explanations, formula/symbol explanations, claim-level
evidence-bound answers, advisor questions/evaluations, and schema-versioned
`m4_memory.json`.
Boundary: strict evidence mode still requires each material claim to bind to
allowed refs whose text supports that claim. A legal ref does not legalize
unrelated prose, and all allowed refs must not be attached wholesale. Formulae,
thresholds, numbers, datasets, metrics, and results use stricter support checks.
Full-paper mode may continue the paper-scoped OpenCode session created during
M2, which contains rendered pages and page-preserving text; it must remain
inside that paper and report unavailable details instead of inventing them.
Memory writes are locked, atomic, and bounded; corruption is quarantined with a
warning. There is no direction-level chat yet.

## context

Input: current job artifacts and UI route context.
Output: safe status and component metadata for frontend display.
Boundary: raw artifacts stay debug/admin oriented.

## llm

Input: schema-specific prompt, provider config, and API key environment.
Output: parsed JSON or explicit LLM/validation failure.
Boundary: bad JSON, missing keys, or provider errors fail closed/degrade; they
must not silently become accepted evidence. Use `DEGRADED_STRUCTURAL` only for
explicit structural limitations, not for core LLM card-builder failure.

## render

Input: API status payloads and gated cards.
Output: DirectionSearchView, SeedExpansionPanel, SettingsView, HomeView, and
PaperWorkspace UI.
Boundary: render status before cards; BLOCKED, BASELINE_ONLY, and FAILED never
show explanatory card content. Mount M4 chat/QA controls only when cards are
allowed and the backend M4 gate accepts the job. API calls use the typed client;
floating controls remain viewport-clamped and keyboard-operable.

## configuration

Input: explicit app overrides, environment, local TOML, example TOML, and code
defaults in that precedence order.
Output: one validated runtime configuration injected into all services.
Boundary: no adapter-owned shadow defaults, ineffective options, invalid search
sources, negative timeouts, unsafe limits, or secret-bearing settings output.

## upload

Input: supported user document stream plus declared extension/MIME.
Output: a generated workspace-managed file or a typed validation failure.
Boundary: read fixed chunks, enforce maximum bytes during write, verify basic
signature, never use the user filename as the final path, and clean temporary
files after failure or cancellation.

## jobs

Input: bounded direction search or deep-read request.
Output: persistent local job id, stage, progress, result, typed failure, and
cancellation state.
Boundary: restart marks stale running work explicitly; duplicate active source
identity is rejected unless force semantics create a distinct identity; cleanup
is restricted to workspace-managed roots.

## Canonical Parser Boundary

- MinerU2.5-Pro via mineru-vl-utils is the primary M1 parser.
- Marker is fallback/audit baseline.
- Ollama is an optional structured refiner.
- Ollama must not modify latex, bbox, page, or source identity.
- M1 gate blocks all-formulas-in-Abstract.
- M1 gate blocks section contradiction.
- M1 gate blocks missing latex/crop/overlay.
