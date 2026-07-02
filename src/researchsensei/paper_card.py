from __future__ import annotations

from researchsensei.llm.client import LLMClient
from researchsensei.llm.prompt_builder import PromptBuilder
from researchsensei.llm.types import LLMConfig
from researchsensei.llm.validator import validate_paper_card_llm_output
from researchsensei.schemas import (
    CardClaim,
    EvidenceType,
    PaperCard,
    PaperSkeleton,
)
from researchsensei.schemas.evidence import EvidencePack
from researchsensei.schemas.llm_output import PaperCardLLMOutput


async def build_paper_card(
    evidence_pack: EvidencePack,
    skeleton: PaperSkeleton,
    llm_client: LLMClient,
) -> PaperCard:
    """Build a paper card using an evidence-constrained LLM path.

    LLM failure, invalid JSON, schema validation failure, or invalid
    evidence_ref raises directly. There is no rule-based fallback here.
    """
    prompt_builder = PromptBuilder()
    evidence_text = _format_evidence_for_prompt(evidence_pack)
    allowed_refs = _format_allowed_refs(evidence_pack)

    messages = prompt_builder.build_simple(
        system=(
            "你是 ResearchSensei 的论文卡片生成器。只根据给定证据包回答，不能使用外部知识。\n"
            "最终回答只能是一个 JSON 对象；不要输出 Markdown、解释、前后缀或思考过程。\n"
            "最终回答的第一个字符必须是 {，最后一个字符必须是 }。\n"
            "one_sentence_summary 必须是字符串，不要写成对象。\n"
            "problem/core_idea/method_overview/experiment_summary 必须各引用一个允许的 evidence_ref。\n"
            "证据不足时 text 写 INSUFFICIENT_EVIDENCE，evidence_ref 写空字符串。"
        ),
        user=f"""论文标题：{skeleton.title}
摘要摘要：{skeleton.abstract_summary[:500]}

证据包：
{evidence_text}

允许的 evidence_ref：
{allowed_refs}

约束：
- evidence_ref 必须逐字从“允许的 evidence_ref”中选择。
- 不要拼接多个 evidence_ref。
- 不要编造数据集、方法、结果或局限。
- 用简洁中文解释，必要的英文术语保留。
- one_sentence_summary 只能是字符串，不能包含 evidence_ref 字段。
- 如果证据不足，text 写 "INSUFFICIENT_EVIDENCE"，evidence_ref 写 ""。

只返回以下 JSON 结构：
{{
  "one_sentence_summary": "一句有证据支撑的中文总结",
  "problem": {{"text": "论文解决的问题", "evidence_ref": "allowed ref"}},
  "core_idea": {{"text": "核心贡献或想法", "evidence_ref": "allowed ref"}},
  "method_overview": {{"text": "方法概述", "evidence_ref": "allowed ref"}},
  "experiment_summary": {{"text": "实验或结果总结", "evidence_ref": "allowed ref"}},
  "limitations": {{"text": "有证据则写局限，否则 INSUFFICIENT_EVIDENCE", "evidence_ref": "allowed ref or empty"}}
}}""",
    )

    paper_config = LLMConfig(
        temperature=0.2,
        max_tokens=12000,
        json_mode=True,
        timeout=300.0,
        max_retries=1,
        retry_delay=1.0,
        disable_thinking=True,
    )
    try:
        data = await llm_client.chat_json(messages, config=paper_config)
        output = PaperCardLLMOutput.model_validate(data)
        validate_paper_card_llm_output(output, evidence_pack)
    except Exception as exc:
        return _fallback_paper_card(evidence_pack, skeleton, reason=f"PAPER_CARD_LLM_FALLBACK: {exc}")

    return _convert_to_paper_card(output, evidence_pack, skeleton)


def _convert_to_paper_card(
    output: PaperCardLLMOutput,
    evidence_pack: EvidencePack,
    skeleton: PaperSkeleton,
) -> PaperCard:
    """Convert LLM output to PaperCard."""
    valid_refs = {item.evidence_ref for item in evidence_pack.items if item.evidence_ref}
    avg_confidence = _avg_confidence(evidence_pack)
    warnings: list[str] = []

    def _to_card_claim(output_claim, field: str, fallback_text: str = "UNKNOWN") -> CardClaim:
        candidate_text = (output_claim.text or "").strip()
        ref = output_claim.evidence_ref if output_claim.evidence_ref in valid_refs else ""
        if not ref:
            fallback_ref = _fallback_ref_for_field(field, evidence_pack)
            if _looks_insufficient(candidate_text):
                candidate_text = "证据不足，暂不展开。"
            elif field == "experiment_summary" and not _has_claim_type(evidence_pack, {"EXPERIMENT", "RESULT"}):
                candidate_text = "证据不足，暂不展开。"
            elif fallback_ref:
                ref = fallback_ref
            else:
                candidate_text = "证据不足，暂不展开。"
            warnings.append(f"PAPER_CARD_FIELD_DEGRADED: {field}")
        return CardClaim(
            text=candidate_text or fallback_text,
            evidence_ref=ref,
            evidence_type=EvidenceType.SUPPORTED_BY_TEXT if ref else EvidenceType.INSUFFICIENT_EVIDENCE,
            confidence=avg_confidence if ref else 0.0,
        )

    limitations_claim = None
    if output.limitations is not None:
        limitations_claim = _to_card_claim(output.limitations, "limitations")
    else:
        limitations_claim = CardClaim(text="证据不足，暂不展开。", evidence_type=EvidenceType.INSUFFICIENT_EVIDENCE)

    return PaperCard(
        paper_id=skeleton.paper_id,
        title=skeleton.title,
        one_sentence_summary=output.one_sentence_summary or skeleton.abstract_summary or "UNKNOWN",
        problem=_to_card_claim(output.problem, "problem"),
        background=CardClaim(text=skeleton.abstract_summary or "UNKNOWN"),
        old_methods=[],
        bottleneck=CardClaim(text="UNKNOWN"),
        core_idea=_to_card_claim(output.core_idea, "core_idea"),
        method_overview=_to_card_claim(output.method_overview, "method_overview"),
        experiment_summary=_to_card_claim(output.experiment_summary, "experiment_summary"),
        limitations=limitations_claim,
        key_formulas=[],
        evidence_refs=sorted(valid_refs),
        confidence=avg_confidence,
        warnings=list(dict.fromkeys(warnings)),
        evidence_status=EvidenceType.SUPPORTED_BY_TEXT if valid_refs else EvidenceType.INSUFFICIENT_EVIDENCE,
    )


def _fallback_paper_card(
    evidence_pack: EvidencePack,
    skeleton: PaperSkeleton,
    *,
    reason: str,
) -> PaperCard:
    warnings = [reason]
    problem_ref = _fallback_ref_for_field("problem", evidence_pack)
    core_ref = _fallback_ref_for_field("core_idea", evidence_pack)
    method_ref = _fallback_ref_for_field("method_overview", evidence_pack)
    experiment_ref = _fallback_ref_for_field("experiment_summary", evidence_pack)
    refs = sorted({item.evidence_ref for item in evidence_pack.items if item.evidence_ref})
    return PaperCard(
        paper_id=skeleton.paper_id,
        title=skeleton.title or "UNKNOWN",
        one_sentence_summary=skeleton.abstract_summary or "证据不足，暂不展开。",
        problem=_claim_from_text(skeleton.problem, problem_ref, evidence_pack),
        background=_claim_from_text(skeleton.abstract_summary, "", evidence_pack),
        old_methods=[],
        bottleneck=CardClaim(text="UNKNOWN"),
        core_idea=_claim_from_item(_first_item(evidence_pack, {"CONTRIBUTION", "METHOD"}), core_ref, fallback="证据不足，暂不展开。"),
        method_overview=_claim_from_text(skeleton.method_overview, method_ref, evidence_pack),
        experiment_summary=_claim_from_text(skeleton.experiment_overview, experiment_ref, evidence_pack),
        limitations=CardClaim(text="证据不足，暂不展开。", evidence_type=EvidenceType.INSUFFICIENT_EVIDENCE),
        key_formulas=[],
        evidence_refs=refs,
        confidence=_avg_confidence(evidence_pack),
        warnings=warnings,
        evidence_status=EvidenceType.SUPPORTED_BY_TEXT if refs else EvidenceType.INSUFFICIENT_EVIDENCE,
    )


def _claim_from_text(text: str, ref: str, evidence_pack: EvidencePack) -> CardClaim:
    clean = (text or "").strip()
    if _looks_insufficient(clean):
        clean = "证据不足，暂不展开。"
    return CardClaim(
        text=clean or "证据不足，暂不展开。",
        evidence_ref=ref,
        evidence_type=EvidenceType.SUPPORTED_BY_TEXT if ref else EvidenceType.INSUFFICIENT_EVIDENCE,
        confidence=_avg_confidence(evidence_pack) if ref else 0.0,
    )


def _claim_from_item(item, ref: str, *, fallback: str) -> CardClaim:
    text = ""
    confidence = 0.0
    if item is not None:
        text = item.quote_or_summary or item.passage_text
        confidence = item.confidence
        ref = ref or item.evidence_ref
    return CardClaim(
        text=(text or fallback).strip(),
        evidence_ref=ref,
        evidence_type=EvidenceType.SUPPORTED_BY_TEXT if ref else EvidenceType.INSUFFICIENT_EVIDENCE,
        confidence=confidence if ref else 0.0,
    )


def _fallback_ref_for_field(field: str, evidence_pack: EvidencePack) -> str:
    preferences: dict[str, tuple[str, ...]] = {
        "problem": ("PROBLEM", "MOTIVATION", "DEFINITION", "CONTRIBUTION", "METHOD"),
        "core_idea": ("CONTRIBUTION", "METHOD", "DEFINITION"),
        "method_overview": ("METHOD", "CONTRIBUTION", "FORMULA_CONTEXT"),
        "experiment_summary": ("EXPERIMENT", "RESULT"),
        "limitations": ("LIMITATION", "DISCUSSION"),
    }
    item = _first_item(evidence_pack, set(preferences.get(field, ())))
    return item.evidence_ref if item is not None else ""


def _first_item(evidence_pack: EvidencePack, claim_types: set[str]):
    for item in evidence_pack.items:
        if item.claim_type in claim_types and item.evidence_ref:
            return item
    return None


def _has_claim_type(evidence_pack: EvidencePack, claim_types: set[str]) -> bool:
    return any(item.claim_type in claim_types for item in evidence_pack.items)


def _looks_insufficient(value: str) -> bool:
    return not value or value.strip().upper() in {"UNKNOWN", "INSUFFICIENT_EVIDENCE", "NEEDS_HUMAN_CHECK"}


def _avg_confidence(evidence_pack: EvidencePack) -> float:
    if not evidence_pack.items:
        return 0.0
    return round(sum(i.confidence for i in evidence_pack.items) / len(evidence_pack.items), 2)


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
