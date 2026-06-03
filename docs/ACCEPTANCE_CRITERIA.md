# ResearchSensei Acceptance Criteria

ResearchSensei passes v0.5 acceptance only when it behaves as a learning system, not a summary toy.

## Direction Learning

- Produces a reading plan, not a raw paper table.
- Selects few core papers and labels A_READ/B_SKIM/C_REFERENCE/D_IGNORE.
- Gives explainable scoring breakdown and filtering reasons.
- Survey is not treated as baseline.
- Recent arXiv is not promoted without quality evidence.

## Single Paper Learning

- Ingests full text when available; missing full text is explicitly degraded.
- Produces block-level parsed document with evidence refs.
- Builds paper skeleton with core ten-part framework.
- Produces paper, formula, pattern, and drill cards.
- Formula cards explain each term, numeric example, remove effect, weight effect, and uncertainty.

## Interaction

- User can ask about current card, formula, concept, or selected text.
- Follow-up includes context package and evidence chunks.
- Prompt isolates user question to reduce injection risk.
- Session memory tracks confusion and weak concepts.

## Reliability

- Pipeline writes artifacts per step and supports restart from successful steps.
- Logs record duration, model, token/cost where available, cache hit, errors, degraded reason, output paths.
- API keys are never written to logs.

## UI

- Learning workspace has left navigation, center reading area, right ask panel.
- Text is readable; cards are vertical and not squeezed.
- Evidence state and ask buttons are visible.
