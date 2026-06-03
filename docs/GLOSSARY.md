# ResearchSensei Glossary

> **Canonical docs**: See `docs/DESIGN.md`, `docs/STATUS.md`, `docs/DEVELOPMENT.md`.

## Core Terms

- **ResearchSensei**: Paper reading tutor system for graduate students.
- **Paper Skeleton**: Structured extraction of paper components (problem, method, experiments, limitations).
- **Evidence Index**: Mapping of claims to source blocks with confidence scores.
- **Paper Card**: Learning card summarizing a paper's core contributions.
- **Formula Card**: Explanation card for formulas with symbol breakdown.
- **Teaching Card**: Five-layer explanation card (human, analogy, formula, example, paper role).
- **Reading Plan**: Prioritized list of papers with scoring breakdown.
- **ParserAdapter**: Interface for document parsers (Phase 11.6).
- **PassageIndex**: Passage-level text index (Phase 11.7).
- **ClaimEvidence**: Evidence binding for a specific claim.

## Artifact Names

- `source_status.json`: Source resolution status
- `parsed_document.json`: Parsed document blocks
- `evidence_index.json`: Evidence bindings
- `paper_skeleton.json`: Paper structure extraction
- `paper_card.json`: Paper learning card
- `formula_cards.json`: Formula explanation cards
- `teaching_cards.json`: Teaching explanation cards
- `query_plan.json`: Search plan
- `candidate_pool.json`: Raw candidate papers
- `filtered_candidates.json`: Deduplicated candidates
- `reading_plan.json`: Prioritized reading list

## Evidence Types

- SUPPORTED_BY_TEXT: Direct text evidence
- SUPPORTED_BY_FORMULA: Formula evidence
- SUPPORTED_BY_EXPERIMENT: Experiment evidence
- REASONABLE_INFERENCE: Inferred but not directly stated
- UNVERIFIED: Not yet verified
- NEEDS_HUMAN_CHECK: Requires human verification
- INSUFFICIENT_EVIDENCE: Not enough evidence
