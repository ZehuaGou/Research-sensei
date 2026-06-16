from __future__ import annotations

from researchsensei.llm.client import LLMClient
from researchsensei.llm.prompt_builder import PromptBuilder
from researchsensei.llm.types import LLMConfig
from researchsensei.llm.validator import validate_teaching_cards_llm_output
from researchsensei.schemas import (
    EvidenceType,
    PaperCard,
    PaperSkeleton,
    TeachingCard,
    TeachingCardBundle,
)
from researchsensei.schemas.evidence import EvidencePack
from researchsensei.schemas.llm_output import TeachingCardsLLMOutput


async def build_teaching_cards(
    evidence_pack: EvidencePack,
    paper_card: PaperCard,
    skeleton: PaperSkeleton,
    llm_client: LLMClient,
) -> TeachingCardBundle:
    """Build teaching cards using an evidence-constrained LLM path.

    LLM failure, invalid JSON, schema validation failure, or invalid
    evidence_ref raises directly. There is no rule-based fallback here.
    """
    prompt_builder = PromptBuilder()
    evidence_text = _format_evidence_for_prompt(evidence_pack)
    allowed_refs = _format_allowed_refs(evidence_pack)

    concepts = []
    if paper_card.core_idea.text != "UNKNOWN":
        concepts.append(f"Core idea: {paper_card.core_idea.text[:200]}")
    if paper_card.problem.text != "UNKNOWN":
        concepts.append(f"Research problem: {paper_card.problem.text[:200]}")
    if paper_card.method_overview.text != "UNKNOWN":
        concepts.append(f"Method overview: {paper_card.method_overview.text[:200]}")

    messages = prompt_builder.build_simple(
        system=(
            "You are a teaching card builder. Use only the supplied evidence.\n"
            "Every teaching card must cite exactly one allowed evidence_ref.\n"
            "Return only valid compact JSON. No markdown fences."
        ),
        user=f"""Paper: {skeleton.title}

Concepts:
{chr(10).join(concepts) if concepts else 'None'}

Evidence:
{evidence_text}

Allowed refs:
{allowed_refs}

Rules:
- evidence_ref from allowed list only. Max 2 teaching_cards.
- Title <= 30 chars, explanations <= 90 chars. Chinese with English math terms.
- INSUFFICIENT_EVIDENCE for unsupported fields.

JSON: {{"teaching_cards": [{{"target_type":"concept","title":"","human_explanation":"","analogy_explanation":"","minimal_formula_explanation":"","numeric_example":"","paper_role_explanation":"","evidence_ref":""}}]}}""",
    )

    teaching_config = LLMConfig(
        temperature=0.2,
        max_tokens=4096,
        json_mode=True,
        timeout=180.0,
        max_retries=1,
    )
    data = await llm_client.chat_json(messages, config=teaching_config)
    output = TeachingCardsLLMOutput.model_validate(data)
    validate_teaching_cards_llm_output(output, evidence_pack)

    return _convert_to_bundle(output, evidence_pack, paper_card)


def _convert_to_bundle(
    output: TeachingCardsLLMOutput,
    evidence_pack: EvidencePack,
    paper_card: PaperCard,
) -> TeachingCardBundle:
    """Convert LLM output to TeachingCardBundle."""
    valid_refs = {item.evidence_ref for item in evidence_pack.items if item.evidence_ref}
    avg_confidence = _avg_confidence(evidence_pack)
    paper_id = paper_card.paper_id

    cards: list[TeachingCard] = []
    for i, llm_card in enumerate(output.teaching_cards):
        ref = llm_card.evidence_ref if llm_card.evidence_ref in valid_refs else ""
        cards.append(TeachingCard(
            card_id=llm_card.card_id or f"{paper_id}:teaching:{i:03d}",
            paper_id=paper_id,
            target_type=llm_card.target_type or "concept",
            target_id=llm_card.target_id or "",
            title=llm_card.title or "UNKNOWN",
            human_explanation=llm_card.human_explanation or "UNKNOWN",
            analogy_explanation=llm_card.analogy_explanation or "UNKNOWN",
            minimal_formula_explanation=llm_card.minimal_formula_explanation or "UNKNOWN",
            numeric_example=llm_card.numeric_example or "UNKNOWN",
            paper_role_explanation=llm_card.paper_role_explanation or "UNKNOWN",
            evidence_refs=[ref] if ref else [],
            evidence_status=EvidenceType.SUPPORTED_BY_TEXT if ref else EvidenceType.UNVERIFIED,
            confidence=avg_confidence if ref else 0.0,
            warnings=[],
        ))

    evidence_refs = []
    for card in cards:
        for ref in card.evidence_refs:
            if ref not in evidence_refs:
                evidence_refs.append(ref)

    return TeachingCardBundle(
        paper_id=paper_id,
        teaching_cards=cards,
        evidence_refs=evidence_refs,
        confidence=_bundle_confidence(cards),
        warnings=[],
        evidence_status=_overall_status(cards),
    )


def _avg_confidence(evidence_pack: EvidencePack) -> float:
    if not evidence_pack.items:
        return 0.0
    return round(sum(i.confidence for i in evidence_pack.items) / len(evidence_pack.items), 2)


def _bundle_confidence(cards: list[TeachingCard]) -> float:
    if not cards:
        return 0.0
    return round(sum(c.confidence for c in cards) / len(cards), 2)


def _overall_status(cards: list[TeachingCard]) -> EvidenceType:
    if not cards:
        return EvidenceType.INSUFFICIENT_EVIDENCE
    types = {card.evidence_status for card in cards}
    if EvidenceType.SUPPORTED_BY_TEXT in types:
        return EvidenceType.SUPPORTED_BY_TEXT
    if EvidenceType.SUPPORTED_BY_FORMULA in types:
        return EvidenceType.SUPPORTED_BY_FORMULA
    return EvidenceType.INSUFFICIENT_EVIDENCE


def _format_evidence_for_prompt(evidence_pack: EvidencePack) -> str:
    lines: list[str] = []
    for item in evidence_pack.items[:15]:
        lines.append(
            f"- [{item.claim_type}] {item.evidence_ref}: {item.passage_text[:200]}"
        )
    return "\n".join(lines)


def _format_allowed_refs(evidence_pack: EvidencePack) -> str:
    refs = [item.evidence_ref for item in evidence_pack.items[:20] if item.evidence_ref]
    return "\n".join(f"- {ref}" for ref in refs) or "- NONE"
