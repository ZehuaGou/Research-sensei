from __future__ import annotations

from researchsensei.llm.client import LLMClient, MockLLMClient, parse_llm_json
from researchsensei.llm.prompt_builder import PromptBuilder
from researchsensei.llm.validator import validate_formula_cards_llm_output
from researchsensei.schemas import (
    EvidenceType,
    FormulaCard,
    FormulaCardBundle,
    PaperSkeleton,
)
from researchsensei.schemas.evidence import EvidencePack
from researchsensei.schemas.llm_output import FormulaCardsLLMOutput


async def build_formula_cards_v2(
    evidence_pack: EvidencePack,
    skeleton: PaperSkeleton,
    llm_client: LLMClient | MockLLMClient,
) -> FormulaCardBundle:
    """Build formula cards using LLM with evidence constraints (fail-closed).

    LLM failure / invalid JSON / schema validation / evidence_ref validation
    all raise directly — no fallback to rule-based.
    """
    prompt_builder = PromptBuilder()
    evidence_text = _format_evidence_for_prompt(evidence_pack)

    messages = prompt_builder.build_simple(
        system=(
            "你是 ResearchSensei 的公式讲解引擎。\n"
            "只能根据 evidence pack 解释公式。不得编造。\n"
            "每个公式必须给出 evidence_ref。\n"
            "输出 JSON 格式。"
        ),
        user=f"""论文标题: {skeleton.title}
公式列表: {', '.join(skeleton.formulas[:5])}

Evidence Pack:
{evidence_text}

要求输出 JSON:
{{
  "formula_cards": [
    {{
      "purpose": "公式在论文中的作用",
      "intuition": "直觉解释",
      "numeric_example": "小数字例子",
      "plain_summary": "一句话人话总结",
      "evidence_ref": "对应证据引用"
    }}
  ]
}}""",
    )

    response = await llm_client.chat(messages)
    data = parse_llm_json(response.content)
    output = FormulaCardsLLMOutput.model_validate(data)
    validate_formula_cards_llm_output(output, evidence_pack)

    return _convert_to_bundle(output, evidence_pack, skeleton)


def _convert_to_bundle(
    output: FormulaCardsLLMOutput,
    evidence_pack: EvidencePack,
    skeleton: PaperSkeleton,
) -> FormulaCardBundle:
    """Convert LLM output to FormulaCardBundle."""
    valid_refs = {item.evidence_ref for item in evidence_pack.items if item.evidence_ref}
    avg_confidence = _avg_confidence(evidence_pack)
    paper_id = skeleton.paper_id

    cards: list[FormulaCard] = []
    for i, llm_card in enumerate(output.formula_cards):
        ref = llm_card.evidence_ref if llm_card.evidence_ref in valid_refs else ""
        cards.append(FormulaCard(
            formula_id=llm_card.formula_id or f"{paper_id}:eq:v2:{i:03d}",
            paper_id=paper_id,
            formula_raw=llm_card.formula_raw,
            purpose=llm_card.purpose or "UNKNOWN",
            intuition=llm_card.intuition or "UNKNOWN",
            numeric_example=llm_card.numeric_example or "UNKNOWN",
            plain_summary=llm_card.plain_summary or "UNKNOWN",
            evidence_ref=ref,
            evidence_status=EvidenceType.SUPPORTED_BY_FORMULA if ref else EvidenceType.UNVERIFIED,
            confidence=avg_confidence if ref else 0.0,
            warnings=[],
        ))

    evidence_refs = sorted({c.evidence_ref for c in cards if c.evidence_ref})
    warnings: list[str] = []
    if not cards:
        warnings.append("NO_FORMULA_CARDS_FROM_LLM")

    return FormulaCardBundle(
        paper_id=paper_id,
        formula_cards=cards,
        evidence_refs=evidence_refs,
        confidence=avg_confidence,
        warnings=warnings,
        evidence_status=EvidenceType.SUPPORTED_BY_FORMULA if cards else EvidenceType.INSUFFICIENT_EVIDENCE,
    )


def _avg_confidence(evidence_pack: EvidencePack) -> float:
    if not evidence_pack.items:
        return 0.0
    return round(sum(i.confidence for i in evidence_pack.items) / len(evidence_pack.items), 2)


def _format_evidence_for_prompt(evidence_pack: EvidencePack) -> str:
    lines: list[str] = []
    for item in evidence_pack.items[:20]:
        lines.append(
            f"- [{item.claim_type}] {item.evidence_ref}: {item.passage_text[:200]}"
        )
    return "\n".join(lines)
