# Learning Studio Contract

Learning Studio closes the gap between reading a paper once and retaining its
ideas over time. The code and API use the semantic `learning` name; the old
numbered stage name is not part of the maintained architecture.

## Inputs and gate

A paper job can enter Learning Studio only when
`allowed_downstream.learning_drills=true`. Import reads user-facing paper,
teaching, and formula cards. A candidate learning item must have useful source
text and at least one evidence ref. Raw parser fragments and unsupported model
claims are not promoted into the review queue.

## Learning items

The importer creates stable items for:

- research problem;
- core idea and method mechanism;
- experiment conclusion and limitations;
- teaching-card concepts;
- reliable formula cards.

The stable id is derived from the job, item type, concept, and source text.
Re-import updates source material without resetting existing FSRS state.

## Session flow

1. `POST /api/v1/jobs/{job_id}/learning/import` prepares reliable items.
2. `POST /api/v1/jobs/{job_id}/learning/sessions` selects due items.
3. Paper Tutor/OpenCode generates one contextual question for the current item.
4. The learner answers naturally; no exact reference sentence is required.
5. OpenCode evaluates covered points, missing points, misconceptions, and next steps.
6. ResearchSensei converts the score into an FSRS rating and persists the attempt.
7. The next item is prepared until the session is complete.

`include_not_due=true` explicitly starts free practice when nothing is due.

## Scheduling

The runtime uses the official `fsrs` Python package. The serialized FSRS card is
stored with each learning item. ResearchSensei uses deterministic, non-fuzzed
scheduling so tests and user-visible due times remain reproducible.

Score conversion is intentionally simple in the first release:

- below `0.40`: Again;
- below `0.65`: Hard;
- below `0.90`: Good;
- otherwise: Easy.

This conversion can later be personalized without changing stored attempts.

## Persistence

SQLite owns four tables:

- `learning_items`;
- `learning_sessions`;
- `learning_session_prompts`;
- `learning_attempts`.

Paper deletion cascades through its learning data. Tutor memory and learning
attempts are separate: tutor memory supports conversation continuity, while
attempts are the durable learning ledger.

## Frontend

`/study` is the global review dashboard. `/study/{job_id}` imports and opens one
paper. The page is full-width inside the Codex-like shell and provides:

- today due, completed, mastered, and total counts;
- a paper learning list;
- one-question-at-a-time practice;
- answer feedback and next due time;
- recent attempt history;
- automatic restoration of the latest unfinished session;
- a return path to the reader workspace.

The reader workspace exposes `加入学习`. The learning page must never be
compressed into the Paper Tutor side panel.

## Current boundary

This release is single-paper learning plus a global review queue. Cross-paper
comparison, concept graphs, and research-gap synthesis remain future work. They
must be built on the persisted learning state and retain per-paper evidence
links.
