# ResearchSensei Current Architecture

This document describes the maintained runtime after the OpenCode paper-agent
convergence. It is intentionally narrower than the historical experiments in
`docs/STATUS.md`.

## End-to-end flow

```text
research direction
  -> M1 discovery, relevance ranking, legal full-text resolution
  -> verified local PDF
  -> M2 OpenCode paper session (page images + page-preserving text)
  -> project-owned passage, claim, card, formula-provenance and quality gates
  -> M3 reader workspace
  -> M4 full-paper dialogue / deterministic source lookup / advisor rehearsal
```

There is one primary PDF path. When the OpenCode paper agent is configured, an
OpenCode failure is reported as a failed job; the runtime does not silently
substitute a different parser and present a lower-quality result as equivalent.
An enabled agent failure is never hidden by parser fallback.
The lightweight importer remains for Markdown, text and explicit non-agent
operation, and PyMuPDF remains the deterministic page-text and rendering layer
inside the paper agent.

## M1: discovery and acquisition

M1 owns search intent, query variants, deterministic relevance, deduplication,
legal open-access resolution, browser-assisted publisher downloads, PDF
verification and library reuse. `paper-search-mcp` is the primary discovery
adapter; OpenAlex, Semantic Scholar, arXiv and publisher resolvers are bounded
fallback or enrichment sources. Candidate count is not a quota: irrelevant
papers are never added merely to reach a number.

OpenCode may help plan multilingual queries, but it does not decide whether a
download is legal or whether bytes are a valid PDF. A candidate is ready for
handoff only when a verified local PDF path exists (`paper_agent_ready`).

## M2: one paper agent, two models

M2 renders PDF pages and preserves page numbers/text with PyMuPDF, then attaches
page batches to one persistent OpenCode session. The vision model extracts
headings, full text, formulas, tables and figures into structured results. The
session id, vision model and tutor model are stored with the run so M4 can
continue the same paper context.

The models are deliberately independent:

- `model`: page-vision/OCR model; it must support image attachments. The current
  default is `qwen3.7-plus` because the checked formula-page comparison was more
  faithful than MiMo V2.5.
- `tutor_model`: full-paper explanation and follow-up model. The current default
  is `mimo-v2.5`; it is selected separately in Settings.

OpenCode is the semantic reader, not the provenance authority. ResearchSensei
still owns stable block ids, page references, evidence refs, formula origins,
QualityAuditor and the fail-closed `/cards` contract. A model cannot promote an
unsupported formula derivation merely by sounding confident.

## M3: reader workspace

The Vue workspace follows a compact Codex-like shell: persistent research
navigation on the left, a scrollable paper canvas in the center and an
independently scrollable M4 panel on the right. Large component styles are
co-located in separate CSS files; answer formatting is a standalone utility.
The user-facing modes are:

- **论文问答**: continue the full-paper OpenCode session;
- **原文证据**: deterministic source lookup without a model call;
- **组会演练**: generate a question, accept the learner answer and give feedback.

The interface shows which model produced a full-paper answer and keeps technical
status details collapsible instead of dominating the reading surface.

## M4: session-first full-paper tutoring

M4 uses the persistent paper session first. Selected text is an additional focus,
not a replacement for the paper. Conversation history is bounded and sent for
continuity; local memory is an atomic, size-bounded transcript index and is never
treated as paper evidence. If the session fails, the direct full-text LLM route
is a bounded compatibility fallback. If both fail, M4 reports degradation rather
than returning canned pseudo-explanations.

Evidence-only mode never calls an LLM. Formula explanations use the paper session
when available and retain the project-owned formula provenance checks.

## Provider boundaries

OpenCode Server is the local session and attachment control plane. OpenCode Go is
the upstream model provider. CC Switch remains an optional compatibility adapter,
not a requirement. Provider credentials are read from environment or the guarded
local bridge and never returned by the settings API.

## Deleted legacy paths

The old canonical document pipeline, MinerU/Marker adapters, formula crop repair
scripts, the separate M2 full pipeline/survey runner and template-heavy M4 answer
stack are no longer runtime options. Their tests and operational scripts were
removed with them. Historical result notes may remain in `docs/STATUS.md`, but
they do not describe callable code.

## Verification layers

1. Ruff and mypy for static integrity.
2. Backend unit/API contracts, including strict evidence and failure gates.
3. Frontend Vitest, typecheck and production build.
4. A real PDF OpenCode run and a same-session M4 follow-up.
5. Playwright inspection of the actual direction, settings and reader flows.

Offline fixtures, provider probes and live end-to-end acceptance are reported
separately. Passing one layer never implies that a different layer passed.
