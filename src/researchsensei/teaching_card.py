from __future__ import annotations

from researchsensei.llm.client import LLMClient
from researchsensei.llm.prompt_builder import PromptBuilder
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
            "You are the ResearchSensei teaching-card builder.\n"
            "Teach from intuition to minimal formula to small example.\n"
            "Use only the supplied evidence pack and paper card.\n"
            "Every teaching card must cite exactly one allowed evidence_ref.\n"
            "Return only valid compact JSON with no markdown and no literal newlines inside string values."
        ),
        user=f"""Paper title: {skeleton.title}

Concepts to teach:
{chr(10).join(concepts) if concepts else 'None'}

Evidence Pack:
{evidence_text}

Allowed evidence_ref values:
{allowed_refs}

Constraints:
- Choose evidence_ref exactly from Allowed evidence_ref values.
- Generate at most 2 teaching_cards.
- Keep each text field concise: title <= 30 Chinese characters, each explanation <= 90 Chinese characters.
- Do not concatenate multiple evidence refs.
- Do not invent background not present in evidence.
- Use concise Chinese explanations with necessary English/math terms preserved.
- If evidence is insufficient, do not generate that teaching_card.

Return JSON with this schema:
{{
  "teaching_cards": [
    {{
      "target_type": "concept",
      "title": "teaching title",
      "human_explanation": "plain-language explanation",
      "analogy_explanation": "simple analogy grounded in the evidence",
      "minimal_formula_explanation": "minimal math explanation if supported, otherwise INSUFFICIENT_EVIDENCE",
      "numeric_example": "small numeric example if supported, otherwise INSUFFICIENT_EVIDENCE",
      "paper_role_explanation": "why this concept matters in the paper",
      "evidence_ref": "allowed ref"
    }}
  ]
}}""",
    )

    data = await llm_client.chat_json(messages)
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
    for item in evidence_pack.items[:20]:
        lines.append(
            f"- [{item.claim_type}] {item.evidence_ref}: {item.passage_text[:300]}"
        )
    return "\n".join(lines)


def _format_allowed_refs(evidence_pack: EvidencePack) -> str:
    refs = [item.evidence_ref for item in evidence_pack.items[:20] if item.evidence_ref]
    return "\n".join(f"- {ref}" for ref in refs) or "- NONE"
