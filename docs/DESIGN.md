# ResearchSensei Design Overview

This file is a compact design overview. `docs/STATUS.md` remains the
authoritative implementation/status source.

## Product Shape

ResearchSensei is a research-reading system with four active surfaces:

1. Literature Discovery discovers papers, resolves legal full text, and hands source-backed
   candidates to PaperWorkspace.
2. Paper Analysis converts paper material into evidence-backed understanding artifacts:
   paper cards, formula cards, teaching cards, formula provenance, and quality
   audit reports.
3. Reader Workspace renders a Chinese workflow for direction search, seed expansion, upload,
   settings, and the PaperWorkspace card reader.
4. Paper Tutor v1 provides claim-level evidence-bound interaction inside PaperWorkspace: selected
   text explanation, formula explanation, paper Q&A, advisor questions,
   advisor evaluation, and atomic bounded JSON memory.

Live LLM execution defaults to OpenCode Go (`opencode_go` config key). The
general, PDF-vision, and paper-tutor models remain independently selectable.
CC Switch is an optional compatibility provider.

## Runtime Flow

```text
direction query / uploaded source / arXiv / DOI
  -> deterministic task/concept relevance gate
  -> legal source resolver
  -> Literature Discovery canonical candidate or source file
  -> Paper Analysis parse, evidence, cards, audit
  -> understanding_status
  -> gated /cards
  -> Chinese PaperWorkspace
  -> Paper Tutor evidence-bound tutoring
```

Pipeline completion, candidate relevance, source readiness, and understanding
quality are independent status dimensions. No single `SUCCESS` value is allowed
to imply all four.

## Runtime Composition

`researchsensei.web.app:create_app` is a compatibility entry point. The real
composition lives in `web/app_factory.py`; it loads one complete configuration,
builds dependencies, and mounts focused settings, jobs, library, directions,
and Paper Tutor routers. Bounded Pydantic request models define API input. Upload and job
logic live in focused services instead of route functions.

Long direction search and deep-read operations use a small local executor with
SQLite-backed task state. A task records stage, progress, result, typed failure,
cancellation, and restart interruption. This is intentionally local and
maintainable; ResearchSensei does not require a distributed queue.

SQLite stores use a busy timeout, WAL, explicit transactions, and schema
versions. Cleanup is permitted only under workspace-managed roots.

## Literature Discovery Relevance Boundary

Deterministic required-concept coverage and forbidden intent-mismatch penalties
gate Top-1 and deep-read candidates. Survey, forecasting, imputation, anomaly,
clustering, graph, GNN, diffusion, and RCA intent are not interchangeable. An
optional LLM judge can veto or annotate but cannot rescue a deterministic
failure. Insufficient relevance returns `DEGRADED` or `BLOCKED`.

## Paper Analysis Fail-Closed Rules

- `paper_card`, `formula_cards`, and `teaching_cards` are core card-builder
  outputs. If any LLM card builder fails or returns invalid/empty output, the
  run becomes `BLOCKED_UNDERSTANDING` and `/cards` is not user-facing.
- `BASELINE_ONLY` is diagnostic only. It means no real LLM client was used and
  must not be counted as live understanding.
- `DEGRADED_STRUCTURAL` is reserved for structural safety cases where a
  successful understanding has an explicitly unavailable component, such as
  unsafe formula derivation provenance. It is not used to hide LLM card-builder
  failures.
- Weak or unknown formula provenance must not produce detailed derivations.
- QualityAuditor and evidence-ref validation remain hard gates.

## Reader Workspace/Paper Tutor UI Design

- The first screen of PaperWorkspace is a working reader, not a marketing page.
- The reader uses a left navigation rail, central card reading pane, and right
  paper tutor panel.
- User-facing text is Chinese by default.
- Status details are available but compact; they should not dominate the
  reading surface.
- Text selection opens a small Paper Tutor action toolbar positioned from the selection
  rectangle and clamped to the viewport to avoid browser-native selection UI.
- Paper Tutor controls mount only when the job is allowed to show cards.
- Workspace API access is centralized in a typed client. Formula dock, tab and
  scroll memory, chat resizing, and workspace data are separate typed units.
- Floating controls are viewport-clamped after drag, resize, zoom/layout
  change, and persisted-coordinate migration; keyboard operation is required.

## Paper Tutor Evidence Design

Paper Tutor produces internal claims, each with its own evidence refs, supporting text,
and uncertainty. The backend validates both ref membership and semantic support
before rendering Chinese prose. Formulae, thresholds, numbers, datasets,
metrics, and experimental results use stricter matching. Unsupported claims are
removed or cause `DEGRADED`; all allowed refs are never attached wholesale.

Memory schema `tutor_memory.v1` uses per-job locking and temp-file plus atomic
replace. Corruption is quarantined and surfaced as a warning rather than
silently overwritten.

## External Tool Position

External projects and services are adapters or strategy references only.
ResearchSensei keeps its own schemas, provenance gates, status gates, and UI
contracts. Do not replace the project with PaperQA, DeepXiv, ARIS, MinerU,
Marker, or any search tool clone.
