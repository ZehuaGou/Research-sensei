from __future__ import annotations

from researchsensei.llm.client import LLMClient, MockLLMClient
from researchsensei.llm.prompt_builder import PromptBuilder
from researchsensei.llm.validator import validate_paper_card_llm_output
from researchsensei.schemas import (
    CardClaim,
    EvidenceType,
    PaperCard,
    PaperSkeleton,
)
from researchsensei.schemas.evidence import EvidencePack
from researchsensei.schemas.llm_output import PaperCardLLMOutput


async def build_paper_card_v2(
    evidence_pack: EvidencePack,
    skeleton: PaperSkeleton,
    llm_client: LLMClient | MockLLMClient,
) -> PaperCard:
    """Build a paper card using LLM with evidence constraints (fail-closed).

    LLM failure / invalid JSON / schema validation / evidence_ref validation
    all raise directly — no fallback to rule-based.
    """
    prompt_builder = PromptBuilder()
    evidence_text = _format_evidence_for_prompt(evidence_pack)

    messages = prompt_builder.build_simple(
        system=(
            "你是 ResearchSensei 的论文研读导师。\n"
            "只能根据 evidence pack 解释论文。不得使用 evidence pack 外的信息。\n"
            "不确定就返回 INSUFFICIENT_EVIDENCE。\n"
            "每个核心 claim 必须给出 evidence_ref。\n"
            "输出 JSON 格式。"
        ),
        user=f"""论文标题: {skeleton.title}
摘要: {skeleton.abstract_summary[:500]}

Evidence Pack:
{evidence_text}

要求输出 JSON:
{{
  "one_sentence_summary": "一句话说清论文在做什么",
  "problem": {{"text": "论文要解决什么问题", "evidence_ref": "对应证据引用"}},
  "core_idea": {{"text": "核心创新点", "evidence_ref": "对应证据引用"}},
  "method_overview": {{"text": "方法概述", "evidence_ref": "对应证据引用"}},
  "experiment_summary": {{"text": "实验结果概述", "evidence_ref": "对应证据引用"}},
  "limitations": {{"text": "局限性", "evidence_ref": "对应证据引用或空字符串"}}
}}""",
    )

    data = await llm_client.chat_json(messages)
    output = PaperCardLLMOutput.model_validate(data)
    validate_paper_card_llm_output(output, evidence_pack)

    return _convert_to_paper_card(output, evidence_pack, skeleton)


def _convert_to_paper_card(
    output: PaperCardLLMOutput,
    evidence_pack: EvidencePack,
    skeleton: PaperSkeleton,
) -> PaperCard:
    """Convert LLM output to PaperCard."""
    valid_refs = {item.evidence_ref for item in evidence_pack.items if item.evidence_ref}
    avg_confidence = _avg_confidence(evidence_pack)

    def _to_card_claim(output_claim, fallback_text: str = "UNKNOWN") -> CardClaim:
        ref = output_claim.evidence_ref if output_claim.evidence_ref in valid_refs else ""
        return CardClaim(
            text=output_claim.text or fallback_text,
            evidence_ref=ref,
            evidence_type=EvidenceType.SUPPORTED_BY_TEXT if ref else EvidenceType.UNVERIFIED,
            confidence=avg_confidence if ref else 0.0,
        )

    limitations_claim = None
    if output.limitations is not None:
        limitations_claim = _to_card_claim(output.limitations)
    else:
        limitations_claim = CardClaim(text="UNKNOWN")

    return PaperCard(
        paper_id=skeleton.paper_id,
        title=skeleton.title,
        one_sentence_summary=output.one_sentence_summary,
        problem=_to_card_claim(output.problem),
        background=CardClaim(text=skeleton.abstract_summary),
        old_methods=[],
        bottleneck=CardClaim(text="UNKNOWN"),
        core_idea=_to_card_claim(output.core_idea),
        method_overview=_to_card_claim(output.method_overview),
        experiment_summary=_to_card_claim(output.experiment_summary),
        limitations=limitations_claim,
        key_formulas=[],
        evidence_refs=sorted(valid_refs),
        confidence=avg_confidence,
        warnings=[],
        evidence_status=EvidenceType.SUPPORTED_BY_TEXT,
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
