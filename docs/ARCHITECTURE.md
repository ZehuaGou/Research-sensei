# ResearchSensei Current Architecture

This document describes the maintained runtime after the OpenCode paper-agent
convergence. It is intentionally narrower than the historical experiments in
`docs/STATUS.md`.

## End-to-end flow

```text
research direction
  -> literature discovery, relevance ranking, legal full-text resolution
  -> verified local PDF
  -> Paper Analysis OpenCode paper session (page images + page-preserving text)
  -> project-owned passage, claim, card, formula-provenance and quality gates
  -> reader workspace
  -> paper tutor: full-paper dialogue / deterministic source lookup / advisor rehearsal
  -> learning studio: adaptive practice / attempt history / FSRS review scheduling
```

There is one primary PDF path. When the OpenCode paper agent is configured, an
OpenCode failure is reported as a failed job; the runtime does not silently
substitute a different parser and present a lower-quality result as equivalent.
An enabled agent failure is never hidden by parser fallback.
The lightweight importer remains for Markdown, text and explicit non-agent
operation, and PyMuPDF remains the deterministic page-text and rendering layer
inside the paper agent.

## Literature Discovery and Acquisition

Literature Discovery owns search intent, query variants, deterministic relevance, deduplication,
legal open-access resolution, browser-assisted publisher downloads, PDF
verification and library reuse. `paper-search-mcp` is the primary discovery
adapter; OpenAlex, Semantic Scholar, arXiv and publisher resolvers are bounded
fallback or enrichment sources. Candidate count is not a quota: irrelevant
papers are never added merely to reach a number.

OpenCode may help plan multilingual queries, but it does not decide whether a
download is legal or whether bytes are a valid PDF. A candidate is ready for
handoff only when a verified local PDF path exists (`paper_agent_ready`).

## Paper Analysis: one paper agent, two models

Paper Analysis renders PDF pages and preserves page numbers/text with PyMuPDF, then attaches
page batches to one persistent OpenCode session. The vision model extracts
headings, full text, formulas, tables and figures into structured results. The
session id, vision model and tutor model are stored with the run so Paper Tutor can
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

## Reader Workspace

The Vue workspace follows a compact Codex-like shell: persistent research
navigation on the left, a scrollable paper canvas in the center and an
independently scrollable Paper Tutor panel on the right. Large component styles are
co-located in separate CSS files; answer formatting is a standalone utility.
The user-facing modes are:

- **论文问答**: continue the full-paper OpenCode session;
- **原文证据**: deterministic source lookup without a model call;
- **组会演练**: generate a question, accept the learner answer and give feedback.

The interface shows which model produced a full-paper answer and keeps technical
status details collapsible instead of dominating the reading surface.

## Paper Tutor: session-first full-paper tutoring

Paper Tutor uses the persistent paper session first. Selected text is an additional focus,
not a replacement for the paper. Conversation history is bounded and sent for
continuity; local memory is an atomic, size-bounded transcript index and is never
treated as paper evidence. If the session fails, the direct full-text LLM route
is a bounded compatibility fallback. If both fail, Paper Tutor reports degradation rather
than returning canned pseudo-explanations.

Evidence-only mode never calls an LLM. Formula explanations use the paper session
when available and retain the project-owned formula provenance checks.

## Learning Studio: persistent learning loop

Learning Studio is a separate domain rather than another Paper Tutor tab. It
imports reliable paper, teaching, and formula artifacts into durable learning
items. A review session asks one question at a time through the same persistent
paper context, accepts a free-form answer, and asks the model to evaluate
coverage, omissions, misconceptions, and useful next steps. The learner is not
required to reproduce a fixed reference sentence.

ResearchSensei, not the model, owns learning identity and state:

- learning items remain bound to a paper job and evidence refs;
- sessions and prompts are persisted in SQLite;
- every answer creates an immutable attempt record;
- FSRS owns the next due time from the resulting Again/Hard/Good/Easy rating;
- deleting a paper job cascades through its learning data.

OpenCode produces paper-aware questions and qualitative feedback. It does not
choose due dates, overwrite history, or promote unsupported source material
into a learning item. Cross-paper synthesis remains a later layer on top of
this single-paper learning state.

## Provider boundaries

OpenCode Server is the local session and attachment control plane. OpenCode Go is
the upstream model provider. CC Switch remains an optional compatibility adapter,
not a requirement. Provider credentials are read from environment or the guarded
local bridge and never returned by the settings API.

## Deleted legacy paths

The old canonical document pipeline, MinerU/Marker adapters, formula crop repair
scripts, the separate Paper Analysis full pipeline/survey runner and template-heavy Paper Tutor answer
stack are no longer runtime options. Their tests and operational scripts were
removed with them. Historical result notes may remain in `docs/STATUS.md`, but
they do not describe callable code.

## Verification layers

1. Ruff and mypy for static integrity.
2. Backend unit/API contracts, including strict evidence and failure gates.
3. Frontend Vitest, typecheck and production build.
4. A real PDF OpenCode run and a same-session Paper Tutor follow-up.
5. Learning-session persistence and scheduler tests.
6. Playwright inspection of the actual direction, settings, reader, and learning flows.

Offline fixtures, provider probes and live end-to-end acceptance are reported
separately. Passing one layer never implies that a different layer passed.
