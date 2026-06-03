from __future__ import annotations

from researchsensei.llm.client import LLMClient, MockLLMClient, parse_llm_json
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


async def build_teaching_cards_v2(
    evidence_pack: EvidencePack,
    paper_card: PaperCard,
    skeleton: PaperSkeleton,
    llm_client: LLMClient | MockLLMClient,
) -> TeachingCardBundle:
    """Build teaching cards using LLM with evidence constraints (fail-closed).

    LLM failure / invalid JSON / schema validation / evidence_ref validation
    all raise directly — no fallback to rule-based.
    """
    prompt_builder = PromptBuilder()
    evidence_text = _format_evidence_for_prompt(evidence_pack)

    concepts = []
    if paper_card.core_idea.text != "UNKNOWN":
        concepts.append(f"核心创新点: {paper_card.core_idea.text[:200]}")
    if paper_card.problem.text != "UNKNOWN":
        concepts.append(f"研究问题: {paper_card.problem.text[:200]}")
    if paper_card.method_overview.text != "UNKNOWN":
        concepts.append(f"方法概述: {paper_card.method_overview.text[:200]}")

    messages = prompt_builder.build_simple(
        system=(
            "你是 ResearchSensei 的教学引擎。\n"
            "根据论文内容生成五层讲解，面向数学基础较弱的用户。\n"
            "只能根据 evidence pack 讲解。不得编造。\n"
            "每个讲解必须绑定 evidence_ref。\n"
            "先直觉，再公式，再数字例子。\n"
            "输出 JSON 格式。"
        ),
        user=f"""论文标题: {skeleton.title}
需要讲解的概念:
{chr(10).join(concepts) if concepts else '无'}

Evidence Pack:
{evidence_text}

要求输出 JSON:
{{
  "teaching_cards": [
    {{
      "target_type": "concept",
      "title": "讲解标题",
      "human_explanation": "用大白话解释",
      "analogy_explanation": "生活中的类比",
      "minimal_formula_explanation": "最简公式形式",
      "numeric_example": "小数字例子",
      "paper_role_explanation": "在论文中的作用",
      "evidence_ref": "对应证据引用"
    }}
  ]
}}""",
    )

    response = await llm_client.chat(messages)
    data = parse_llm_json(response.content)
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
            card_id=llm_card.card_id or f"{paper_id}:teach:v2:{i:03d}",
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
            f"- [{item.claim_type}] {item.evidence_ref}: {item.passage_text[:200]}"
        )
    return "\n".join(lines)
