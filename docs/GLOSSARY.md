# ResearchSensei Glossary

> **Canonical docs**: See `docs/DESIGN.md`, `docs/STATUS.md`, `docs/DEVELOPMENT.md`.

## Core Terms

- **ResearchSensei**: Paper reading tutor system for graduate students.
- **Paper Skeleton**: Structured extraction of paper components (problem, method, experiments, limitations).
- **Evidence Index**: Mapping of claims to source blocks with confidence scores (compatibility).
- **Paper Card**: Learning card summarizing a paper's core contributions.
- **Formula Card**: Explanation card for formulas with symbol breakdown.
- **Teaching Card**: Five-layer explanation card (human, analogy, formula, example, paper role).
- **Reading Plan**: Prioritized list of papers with scoring breakdown.
- **ParserAdapter**: Interface for document parsers.
- **PassageIndex**: Passage-level text index, grouping blocks into semantic passages.
- **ClaimEvidence**: Evidence binding for a specific claim (block-level).
- **ClaimEvidenceRecord**: Evidence binding with passage_id, claim_type, semantic_support (passage-level).
- **EvidencePack**: Runtime collection of evidence items for LLM input. Not persisted.
- **EvidencePackSummary**: Summary of what the LLM saw, stored in UnderstandingStatus.
- **EvidenceRetriever**: BM25-based passage retrieval for supporting evidence.
- **UnderstandingStatus**: Pipeline status object (SUCCESS / DEGRADED / BASELINE_ONLY / BLOCKED / FAILED).
- **DownstreamGates**: Fine-grained downstream access control (reading_display / phase12_patterns / phase12_drill / advisor_questions).
- **QualityReport**: Audit output with findings list.
- **AuditFinding**: Single audit finding with code / severity / effect.
- **QualityAuditor**: Rule-based auditor that reads candidate artifacts.
- **PatternCard**: Research thinking pattern extraction from paper structure (M4, not yet implemented).
- **DrillCard**: Socratic-style questioning card for deep understanding (M4, not yet implemented).
- **InteractiveAnswer**: On-demand answer to user's specific question about a paper (M4, not yet implemented).
- **ContextPack**: Curated context window for LLM interactive answer (M4, not yet implemented).

## Status Terms

- **SUCCESS**: Full LLM cards generated and audit passed.
- **DEGRADED_STRUCTURAL**: Paper understanding succeeded but teaching layer degraded.
- **BASELINE_ONLY**: No LLM client, rule-based baseline only. Not final understanding.
- **BLOCKED_UNDERSTANDING**: Evidence/LLM/audit failure, understanding not可信.
- **FAILED**: System-level exception (pipeline crash, file system error).

## Artifact Names

- `source_status.json`: Source resolution status
- `parsed_document.json`: Parsed document blocks
- `passage_index.json`: Passage-level text index
- `claim_evidence.json`: Claim evidence record (passage-level)
- `evidence_index.json`: Evidence bindings (compatibility wrapper)
- `paper_skeleton.json`: Paper structure extraction
- `paper_card.json`: Paper learning card
- `formula_cards.json`: Formula explanation cards
- `teaching_cards.json`: Teaching explanation cards
- `understanding_status.json`: Pipeline understanding status
- `quality_report.json`: Audit quality report
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
