# ResearchSensei Artifact Contracts

---

## Single Paper Chain

### source_status.json

| Field | Required | Description |
|-------|----------|-------------|
| source_type | yes | upload / local_path / pdf_url / arxiv_id / arxiv_url |
| original_input | yes | original user input |
| resolved_path | yes | resolved file path |
| status | yes | resolved / failed / degraded |
| content_type | yes | MIME type |
| size_bytes | yes | file size |

- **Generator**: source_resolver
- **Consumer**: ingestion
- **v1 status**: complete
- **v2 upgrade**: none needed
- **Failure**: status="failed", warning added

### parsed_document.json

| Field | Required | Description |
|-------|----------|-------------|
| paper_id | yes | unique paper identifier |
| blocks | yes | list of DocumentBlock |
| detected_language | yes | zh / en |
| degraded | yes | true if parsing failed partially |
| warnings | yes | list of WarningItem |

- **Generator**: ingestion/lightweight.py (v1), ParserAdapter (v2)
- **Consumer**: grounding, paper_skeleton, formula_cards
- **v1 status**: complete (PyMuPDF fallback)
- **v2 upgrade**: Phase 11.6 ParserAdapter
- **Blocker for Phase 12**: YES — better parsing needed for quality cards

### evidence_index.json

| Field | Required | Description |
|-------|----------|-------------|
| paper_id | yes | unique paper identifier |
| claims | yes | list of ClaimEvidence |

Each ClaimEvidence:

| Field | Required | Description |
|-------|----------|-------------|
| claim_id | yes | unique claim identifier |
| block_id | yes | source block (v1) |
| evidence_type | yes | EvidenceType enum |
| evidence_ref | yes | reference string |
| quote_or_summary | yes | text from paper |
| confidence | yes | 0.0-1.0 |

- **Generator**: grounding.py (v1), PassageIndex + ClaimExtractor (v2)
- **Consumer**: paper_skeleton, paper_card, formula_cards, teaching_cards
- **v1 status**: complete (block-level)
- **v2 upgrade**: Phase 11.7 passage-level + claim extraction
- **Blocker for Phase 12**: YES — block-level too coarse

### paper_skeleton.json

| Field | Required | Description |
|-------|----------|-------------|
| paper_id | yes | unique paper identifier |
| problem | yes | SkeletonField |
| old_methods | yes | list |
| bottleneck | yes | list |
| mechanism | yes | SkeletonField |
| objective | yes | list |
| experiments | yes | list |
| limitations | yes | list |
| pattern_candidates | yes | list |

- **Generator**: paper_skeleton.py (v1), LLM-enhanced (v2)
- **Consumer**: paper_card, formula_cards, teaching_cards, patterns
- **v1 status**: complete (rule-based, conservative)
- **v2 upgrade**: Phase 11.8 LLM-enhanced extraction
- **Blocker for Phase 12**: YES — patterns need better skeleton

### paper_card.json

| Field | Required | Description |
|-------|----------|-------------|
| paper_id | yes | unique paper identifier |
| core_idea | yes | CardClaim with evidence_ref |
| problem | yes | CardClaim with evidence_ref |
| method_overview | yes | CardClaim with evidence_ref |
| experiments | yes | CardClaim with evidence_ref |
| limitations | yes | CardClaim with evidence_ref |
| evidence_refs | yes | all refs |
| confidence | yes | 0.0-1.0 |
| warnings | yes | list |

- **Generator**: paper_card.py (rule-based + LLM-enhanced)
- **Consumer**: teaching_cards
- **v1 status**: complete (rule-based baseline)
- **v2 upgrade**: Phase 11.8 evidence-constrained LLM
- **Hard-fail**: core_idea must have evidence_ref or degrade

### formula_cards.json

| Field | Required | Description |
|-------|----------|-------------|
| paper_id | yes | unique paper identifier |
| formula_cards | yes | list of FormulaCard |

Each FormulaCard:

| Field | Required | Description |
|-------|----------|-------------|
| formula_id | yes | unique formula identifier |
| formula_raw | yes | raw LaTeX/text |
| purpose | yes | what the formula does |
| symbols | yes | list of FormulaSymbol |
| terms | yes | list of FormulaTerm |
| evidence_ref | yes | reference to source |
| confidence | yes | 0.0-1.0 |

- **Generator**: formula_card.py (rule-based + LLM-enhanced)
- **Consumer**: teaching_cards
- **v1 status**: complete (generic symbol dictionary)
- **v2 upgrade**: Phase 11.8 paper-context symbol grounding
- **Hard-fail**: symbols from generic dictionary must be REASONABLE_INFERENCE

### teaching_cards.json

| Field | Required | Description |
|-------|----------|-------------|
| paper_id | yes | unique paper identifier |
| teaching_cards | yes | list of TeachingCard |

Each TeachingCard (five-layer):

| Field | Required | Description |
|-------|----------|-------------|
| human_explanation | yes | plain language |
| analogy_explanation | yes | analogy |
| minimal_formula_explanation | yes | minimal formula |
| numeric_example | yes | small number example |
| paper_role_explanation | yes | role in paper |
| evidence_refs | yes | references |
| confidence | yes | 0.0-1.0 |

- **Generator**: teaching_card.py (rule-based + LLM-enhanced)
- **Consumer**: user / frontend
- **v1 status**: complete (rule-based baseline)
- **v2 upgrade**: Phase 11.8 evidence-constrained five-layer
- **Hard-fail**: human_explanation must not be formula text

---

## Direction Chain

### query_plan.json

| Field | Required | Description |
|-------|----------|-------------|
| user_query | yes | original query |
| language | yes | zh / en |
| direction_en | yes | English direction |
| core_terms | yes | search terms |
| search_intents | yes | list of SearchIntent |
| warnings | yes | list |

- **Generator**: query/planner.py
- **Consumer**: acquisition adapters
- **v1 status**: complete
- **v2 upgrade**: better Chinese fallback

### candidate_pool.json

| Field | Required | Description |
|-------|----------|-------------|
| query | yes | search query used |
| retrieved_count | yes | total retrieved |
| items | yes | list of CandidatePaper |
| search_log | yes | log of searches |
| warnings | yes | list of failures |

- **Generator**: selection/service.py
- **Consumer**: dedup
- **v1 status**: complete

### filtered_candidates.json

| Field | Required | Description |
|-------|----------|-------------|
| query | yes | search query used |
| retrieved_count | yes | before dedup |
| deduplicated_count | yes | after dedup |
| items | yes | list of CandidatePaper |
| warnings | yes | list |

- **Generator**: selection/service.py (dedup)
- **Consumer**: reading_plan
- **v1 status**: complete

### reading_plan.json

| Field | Required | Description |
|-------|----------|-------------|
| topic | yes | research topic |
| items | yes | list of ReadingPlanItem |
| warnings | yes | list |

Each ReadingPlanItem:

| Field | Required | Description |
|-------|----------|-------------|
| paper | yes | CandidatePaper |
| priority | yes | A_READ / B_SKIM / C_REFERENCE / D_IGNORE |
| scoring_breakdown | yes | explainable scores |
| selection_reason | yes | why selected |
| risk_note | yes | uncertainty note |

- **Generator**: selection/service.py
- **Consumer**: user / source_resolver (for A_READ papers)
- **v1 status**: complete
- **v2 upgrade**: more specific selection_reason
