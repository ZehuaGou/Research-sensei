# Paper Tutor Interactive Learning Contract

Paper Tutor v1 is an evidence-bound tutor inside PaperWorkspace. It is not a raw-PDF
chatbot and it is not a general assistant. Current verification evidence lives
in `docs/STATUS.md`.

## Implemented Surface

- Backend service: `src/researchsensei/tutor/service.py`
- Schemas: `src/researchsensei/schemas/tutor.py`
- Router: `src/researchsensei/web/routers/tutor.py`
- API routes:
  - `POST /api/v1/jobs/{job_id}/selection/explain`
  - `POST /api/v1/jobs/{job_id}/formula/explain`
  - `POST /api/v1/jobs/{job_id}/ask`
  - `POST /api/v1/jobs/{job_id}/advisor/question`
  - `POST /api/v1/jobs/{job_id}/advisor/evaluate`
  - `GET /api/v1/jobs/{job_id}/memory`
  - `DELETE /api/v1/jobs/{job_id}/memory`
- Frontend tutor, selected-text actions, formula actions, and advisor flow
- Memory artifact: `tutor_memory.json`, schema `tutor_memory.v1`

## Input Boundary

Paper Tutor reads only user-facing artifacts for the current job: paper cards, formula
cards, teaching cards, passage index, claim evidence, evidence index, and
previous valid Paper Tutor memory. Paper Tutor controls mount only when `/cards` is allowed.

Non-paper prompts such as weather, jokes, travel booking, creative writing, or
unrelated code generation return a clear refusal/degraded result without
calling the LLM or writing memory.

## Claim-Level Grounding

The LLM first produces an internal structure containing claims. Every claim has:

- natural-language content;
- its own `evidence_refs`;
- supporting text/quotation;
- uncertainty.

The backend then validates:

1. every ref exists in the current allowed set;
2. the evidence text supports that specific claim;
3. formulae, thresholds, numeric values, datasets, metrics, comparisons, and
   experiment results satisfy stricter matching;
4. unsupported claims are removed or explicitly degraded.

It is not valid to attach all allowed refs to a fluent answer. A correct ref
does not make an unsupported conclusion correct. If no material claim survives,
Paper Tutor returns `DEGRADED` rather than disguising the result as `SUCCESS`.

## Deterministic Fallback Boundary

Deterministic fallback may summarize existing paper/formula/teaching cards and
their evidence. It must not infer spectral residual, Fourier processing,
threshold rules, datasets, metrics, or any named method merely from broad words
such as “time series” or “anomaly”. Such details are allowed only when the
current paper artifacts contain the corresponding method/formula/step and a
supporting evidence ref.

A teaching toy example may use clearly fictional numbers, but its calculation
rule must come directly from the current paper context. Missing support produces
an explicit limitation, not a general-domain answer.

## Memory Reliability

- Schema version is `tutor_memory.v1`; legacy records are migrated explicitly.
- A per-job/path lock protects concurrent read-modify-write operations.
- Writes use a sibling temporary file, flush, `fsync`, and atomic replace.
- Record count and file size are bounded.
- Blank, duplicate, and low-quality records are removed.
- Damaged JSON is renamed to a timestamped `tutor_memory.corrupt-*.json` artifact
  and surfaced as a warning. It is never silently overwritten with an empty
  history.
- A write interruption leaves the previously committed file readable.

## Provider and Failure Handling

The configured live path defaults to OpenCode Go. CC Switch remains an optional
compatibility route. Interactive requests are bounded by route-specific
token/timeout settings. Missing, empty, invalid, timed-out, or unsupported LLM
output goes through evidence-safe fallback/degradation. Provider readiness or a
listening port is not a live acceptance result.

User-facing Paper Tutor text remains Chinese. Evidence refs and memory counts may appear
as compact technical details.

## Frontend Interaction

- Selected text exposes Chinese follow-up/simplify/example actions.
- The toolbar is positioned from the selection rectangle and clamped to the
  viewport.
- The Paper Tutor panel is bounded by the actual viewport and uses overlay/drawer behavior
  on small screens.
- Open, close, and resize flows support Escape/focus/keyboard semantics.
- Formula dock and Paper Tutor panel coordinate structurally and do not obscure one
  another through arbitrary z-index escalation.

## Not Implemented

- Direction-level interactive chat
- Seed-expansion interactive chat
- Broad cross-paper vector memory

Full learning sessions no longer belong inside the Paper Tutor panel. They are
implemented by the separate Learning Studio; see `LEARNING_STUDIO.md`.

## Validation

Backend regressions cover gating, claim/ref support, legal-ref-but-unsupported
content, numeric/formula strictness, broad-keyword fallback refusal, advisor
flows, concurrent memory writes, interrupted writes, corruption quarantine,
migration, and bounds. Frontend tests cover the tutor interaction; default
browser E2E uses local fixtures/mocks. Exact current commands and counts live in
`docs/STATUS.md`.
