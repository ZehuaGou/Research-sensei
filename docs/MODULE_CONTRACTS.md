# ResearchSensei Module Contracts

> **Canonical docs**: See `docs/DESIGN.md`, `docs/development/PAPER_UNDERSTANDING.md`, and `docs/development/LITERATURE_SEARCH.md`.

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

## grounding

Input: parsed_document.json
Output: evidence_index.json
Boundary: Does not generate teaching text. Block-level evidence only (v1).

## understanding

Input: parsed_document.json, evidence_index.json
Output: paper_skeleton.json
Boundary: Does not copy abstract as understanding.

## teaching

Input: paper_skeleton.json
Output: teaching_cards.json
Boundary: Does not output empty explanations. Rule-based baseline only (v1).

## formula

Input: formula blocks, paper_skeleton.json
Output: formula_cards.json
Boundary: Does not fabricate symbol meanings. Generic dictionary as REASONABLE_INFERENCE.

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
