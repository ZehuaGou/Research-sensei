# ResearchSensei Product Requirements

> **Canonical docs**: See `docs/DESIGN.md`, `docs/STATUS.md`, `docs/DEVELOPMENT.md`.

ResearchSensei is a paper reading tutor system for graduate students and junior researchers. It helps users truly understand papers, not just skim them.

## Core Requirements

1. **Paper Understanding**: Parse PDF/Markdown/text into structured blocks with evidence binding.
2. **Formula Explanation**: Break formulas into symbols, terms, roles, and numeric examples.
3. **Teaching Cards**: Five-layer explanation (human, analogy, formula, example, paper role).
4. **Evidence Constraint**: Every explanation must be backed by evidence from the paper.
5. **Direction Learning**: Search, deduplicate, score, and rank papers for reading plans.
6. **Uncertainty Handling**: Degrade honestly when evidence is insufficient.

## Quality Standards

- No fabrication of results, datasets, or conclusions.
- No formula text as human-readable explanation.
- No template-based generic output.
- All claims must have evidence_ref or degrade to INSUFFICIENT_EVIDENCE.

## Current Status

Phase 1-11 baseline infrastructure complete. Phase 12 frozen pending quality upgrades.

## Non-Goals

- Not a paper summarizer.
- Not an auto-paper-writing system.
- Not an auto-research system.
- Not a RAG chatbot.

## Detailed Specification

See `docs/DESIGN.md` for architecture, artifact contracts, and external project decisions.
See `docs/DEVELOPMENT.md` for development rules and phase specifications.
