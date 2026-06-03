# ResearchSensei Review Checklist

Use this checklist before accepting any implementation change.

## Architecture

- [ ] Module does one job only.
- [ ] JSON/Pydantic input and output are explicit.
- [ ] Search, parsing, teaching, interaction, and render remain separate.
- [ ] External tools are behind replaceable adapters.

## Evidence

- [ ] Every factual claim has evidence status.
- [ ] AI inference is labeled as inference.
- [ ] Evidence refs point to block IDs.
- [ ] Missing full text triggers degraded mode.

## Teaching Quality

- [ ] Output is Chinese-first.
- [ ] Formula explanations include symbols, terms, numeric example, remove effect, weight effect.
- [ ] Paper card covers Problem, Old Methods, Bottleneck, Assumption, Representation, Mechanism, Objective, Evidence, Limitation, Transfer.
- [ ] Drill cards include advisor questions and error attribution.

## Interaction

- [ ] Follow-up question includes current card, selected text, evidence chunks, recent history summary.
- [ ] Prompt builder isolates user question.
- [ ] System does not send full paper every time.
- [ ] Feedback can update memory later.

## Safety and Privacy

- [ ] API keys never appear in logs.
- [ ] LaTeX commands are not executed.
- [ ] PDF scripts are not executed.
- [ ] HTML source is sanitized before render.

## UI

- [ ] Cards are not squeezed horizontally.
- [ ] Font is readable.
- [ ] Ask buttons exist for major learning units.
- [ ] Evidence state is visible.
