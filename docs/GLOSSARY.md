# ResearchSensei Glossary

## Core Terms

- **ResearchSensei**: Evidence-bound paper reading tutor for graduate-level
  research learning.
- **ccswitch / cc_switch**: Default live LLM provider. ResearchSensei calls
  the local ccswitch endpoint and sends the model selected in the settings page.
- **Paper Skeleton**: Structured extraction of paper components: problem,
  method, experiments, and limitations.
- **PassageIndex**: Passage-level text index.
- **ClaimEvidence**: Evidence binding for a claim with passage identity and
  support metadata.
- **EvidencePack**: Curated evidence items sent to card builders or M4 context.
- **Paper Card**: Evidence-backed summary of the paper's problem, idea, method,
  experiments, and limitations.
- **Formula Card**: Evidence-backed formula explanation with provenance,
  symbols/terms, intuition, examples, and removal/weight effects.
- **Teaching Card**: Teaching explanation card for concepts, methods, or
  formula roles.
- **UnderstandingStatus**: Gate object controlling whether cards and downstream
  interactions are allowed.
- **DownstreamGates**: Fine-grained access control for reading display, pattern
  views, drill paths, and advisor questions.
- **QualityAuditor**: Rule-based auditor for card/evidence/status consistency.
- **M4MemoryBundle**: JSON memory artifact stored as `m4_memory.json`.
- **InteractiveAnswer**: M4 answer to a user's question, grounded in M2
  artifacts or memory.

## Status Terms

- **SUCCESS**: Paper, formula, and teaching cards were generated and passed
  validation/audit.
- **BASELINE_ONLY**: No real LLM client was used. Diagnostic only; not
  user-facing understanding.
- **BLOCKED_UNDERSTANDING**: Evidence, LLM output, card validation, or audit
  failure. User-facing cards must stay hidden.
- **DEGRADED_STRUCTURAL**: Non-LLM structural limitation after otherwise
  successful understanding, for example formula derivation blocked by unreliable
  provenance. It must not be used to hide paper/formula/teaching card-builder
  failures.
- **FAILED**: System-level exception such as file system or pipeline crash.

## Artifact Names

- `source_status.json`: Source resolution status.
- `parsed_document.json`: Parsed document blocks.
- `passage_index.json`: Passage-level text index.
- `claim_evidence.json`: Passage-level claim evidence.
- `evidence_index.json`: Compatibility evidence wrapper.
- `paper_skeleton.json`: Paper structure extraction.
- `paper_card.json`: Paper learning card.
- `formula_cards.json`: Formula explanation cards.
- `teaching_cards.json`: Teaching explanation cards.
- `understanding_status.json`: Status and gates.
- `quality_report.json`: Audit report.
- `m4_memory.json`: M4 interaction memory.
