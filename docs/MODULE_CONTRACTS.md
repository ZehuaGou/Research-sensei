# ResearchSensei Module Contracts

`docs/STATUS.md` is the authoritative state file. This document records stable
Input, Output, and Boundary rules for modules so future weaker models can modify
the project without reopening the whole design.

## query

Input: user research direction text and optional limits.
Output: normalized query variants for acquisition.
Boundary: do not invent papers or source identifiers.

## acquisition

Input: query variants and enabled source names.
Output: `CandidatePaper` objects from arXiv, OpenAlex, Semantic Scholar,
Crossref, DBLP, and legal full-text lookup metadata.
Boundary: adapters may fail independently; failures must become source metrics
and warnings, not fake success.

## selection

Input: raw candidates from acquisition.
Output: deduplicated candidates with relevance, confidence, `discovery_sources`,
source IDs, DOI, arXiv ID, URL, and full-text readiness retained.
Boundary: metadata-only high-value papers must not be discarded merely because
they cannot immediately enter M2.

## source_resolver

Input: candidate payload, arXiv ID/URL, DOI, PDF URL, or uploaded file.
Output: resolved source status, downloaded legal full text when available, and a
preferred M2 input type such as `arxiv_source`, `arxiv_pdf`, `external_pdf`, or
`metadata_only`.
Boundary: arXiv source/e-print is preferred over PDF; DOI-only deep_read may
resolve to a legal OA PDF through Unpaywall, otherwise it fails explicitly with
`NO_LEGAL_OA_FULLTEXT_FOUND`; no paywall bypassing.

## ingestion

Input: canonical bundle, arXiv source, PDF, or resolved source directory.
Output: parsed document, passage index, claim evidence, evidence pack,
understanding status, and artifact manifest.
Boundary: malformed input or missing evidence must degrade/block rather than
creating fake evidence.

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
Boundary: citation graph claims must be real or clearly marked as weak
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
Output: selected-text explanations, formula/symbol explanations,
evidence-bound answers, advisor questions/evaluations, and `m4_memory.json`.
Boundary: answers must be grounded in paper cards, formula cards, passage index,
claim evidence, or stored M4 memory. No raw PDF access, no free-form answer
without evidence/degraded status, and no direction-level chat yet.

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
allowed and the backend M4 gate accepts the job.

## Canonical Parser Boundary

- MinerU2.5-Pro via mineru-vl-utils is the primary M1 parser.
- Marker is fallback/audit baseline.
- Ollama is an optional structured refiner.
- Ollama must not modify latex, bbox, page, or source identity.
- M1 gate blocks all-formulas-in-Abstract.
- M1 gate blocks section contradiction.
- M1 gate blocks missing latex/crop/overlay.
