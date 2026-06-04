# ResearchSensei Module Contracts

> **Canonical docs**: See `docs/DEVELOPMENT.md` and `docs/development/`.

## query

Input: user_query
Output: query_plan.json
Boundary: Does not search papers. Does not generate reading plans.

## acquisition

Input: query_plan.json
Output: candidate_pool.json
Boundary: Does not filter A_READ. Does not do paper reading.

## selection

Input: candidate_pool.json
Output: filtered_candidates.json, reading_plan.json
Boundary: Does not download full text. Does not generate paper cards.

## source_resolver

Input: paper metadata, input_path/url
Output: source_status.json, source file
Boundary: Does not parse content. Does not generate understanding.

## ingestion

Input: source file
Output: parsed_document.json
Boundary: Does not explain papers. Does not generate paper_skeleton.

## passage_index

Input: parsed_document.json
Output: passage_index.json
Boundary: Only builds passages. Does not judge claims.

## claim_evidence

Input: passage_index.json
Output: claim_evidence.json
Boundary: Only extracts claim evidence. Does not generate final explanations.

## grounding

Input: parsed_document.json
Output: evidence_index.json
Boundary: Block-level evidence (v1 compatibility). Does not generate teaching text.

## evidence_retriever

Input: claim_evidence.json + passage_index.json
Output: EvidenceRetrievalResult (runtime, not persisted)
Boundary: BM25 retrieval only. Does not generate cards.

## evidence_pack

Input: claim_evidence.json + passage_index.json + optional retriever
Output: EvidencePack + EvidencePackSummary (runtime, not persisted)
Boundary: Filters and prioritizes evidence for LLM. Not persisted.

## understanding

Input: EvidencePack + paper_skeleton.json
Output: paper_card.json / formula_cards.json / teaching_cards.json / understanding_status.json
Boundary: Fail-closed. Unreliable → BLOCKED_UNDERSTANDING.

## teaching

Input: paper_skeleton.json, paper_card, formula_cards
Output: teaching_cards.json
Boundary: Does not output empty explanations. Rule-based baseline (v1) or LLM v2 (fail-closed).

## formula

Input: formula blocks, paper_skeleton.json
Output: formula_cards.json
Boundary: Does not fabricate symbol meanings. Generic dictionary as REASONABLE_INFERENCE.

## audit

Input: candidate artifacts (in-memory dicts)
Output: quality_report.json
Boundary: Reads candidate artifacts, does not regenerate cards. Does not write artifacts. Pure logic.

## api

Input: job_id
Output: /understanding_status, /cards
Boundary: /artifacts debug-only. Normal frontend must not use /artifacts.

## frontend

Input: /understanding_status + /cards
Output: User page display
Boundary: Does not read /artifacts directly. Does not display BASELINE/BLOCKED cards.

## direction

Input: reading_plan.json, paper_skeleton.json
Output: direction_map.json (future)
Boundary: Must be problem-driven, not just paper list.

## patterns

Input: paper_skeleton.json
Output: pattern_cards.json (Phase 12, frozen)
Boundary: Not all papers are "method innovation."

## drill

Input: paper_card.json, formula_cards.json, pattern_cards.json
Output: drill_cards.json (Phase 12, frozen)
Boundary: Must not only ask "what method did the paper propose?"

## interactive

Input: user_question, card_id, selected_text, session_id
Output: interactive_answer.json (Phase 15, roadmap)
Boundary: Must not send entire paper to prompt.

## context

Input: session state, user question, cards, blocks
Output: context_pack.json (Phase 15, roadmap)
Boundary: Must not grow prompt without limit.

## llm

Input: messages
Output: response
Boundary: All LLM calls through llm/client.py. No direct API calls in business modules.

## render

Input: cards JSON
Output: HTML/Markdown (Phase 14, roadmap)
Boundary: Must not call LLM in render.
