from __future__ import annotations

import logging

from researchsensei.llm.client import LLMClient, LLMResponseError, MockLLMClient, parse_llm_json
from researchsensei.llm.prompt_builder import PromptBuilder
from researchsensei.llm.types import ChatMessage
from researchsensei.schemas import (
    CardClaim,
    ClaimEvidence,
    EvidenceIndex,
    EvidenceType,
    PaperCard,
    PaperSkeleton,
)

logger = logging.getLogger(__name__)

LOW_CONFIDENCE_TYPES = {
    EvidenceType.UNVERIFIED,
    EvidenceType.NEEDS_HUMAN_CHECK,
    EvidenceType.INSUFFICIENT_EVIDENCE,
}


def build_paper_card(
    skeleton: PaperSkeleton,
    evidence_index: EvidenceIndex,
) -> PaperCard:
    """Build a paper card from skeleton and evidence index (rule-based only)."""
    claims_by_section = _index_claims(evidence_index)
    return _build_rule_based(skeleton, evidence_index, claims_by_section)


async def build_paper_card_with_llm(
    skeleton: PaperSkeleton,
    evidence_index: EvidenceIndex,
    llm_client: LLMClient | MockLLMClient,
) -> PaperCard:
    """Build a paper card with optional LLM enhancement.

    Falls back to rule-based on LLM failure.
    """
    claims_by_section = _index_claims(evidence_index)

    try:
        return await _build_llm_enhanced(skeleton, evidence_index, claims_by_section, llm_client)
    except Exception as exc:
        logger.warning("LLM-enhanced card failed, falling back to rule-based: %s", exc)

    return _build_rule_based(skeleton, evidence_index, claims_by_section)


def _build_rule_based(
    skeleton: PaperSkeleton,
    evidence_index: EvidenceIndex,
    claims_by_section: dict[str, list[ClaimEvidence]],
) -> PaperCard:
    """Rule-based card builder: conservative extraction, no LLM."""
    title_claim = _find_claim(claims_by_section, "title", skeleton.title)
    abstract_claim = _find_claim(claims_by_section, "abstract", skeleton.abstract_summary)
    problem_claim = _find_or_degraded(claims_by_section, "introduction", skeleton.problem, "PROBLEM_SECTION_MISSING")
    method_claim = _find_or_degraded(claims_by_section, "method", skeleton.method_overview, "METHOD_SECTION_MISSING")
    experiment_claim = _find_or_degraded(claims_by_section, "experiment", skeleton.experiment_overview, "EXPERIMENT_SECTION_MISSING")
    limitation_claim = _find_or_degraded(claims_by_section, "limitations", skeleton.limitations, "LIMITATIONS_SECTION_MISSING")

    formula_claims = _formula_claims(skeleton, claims_by_section)
    old_method_claims = _old_method_claims(claims_by_section)

    one_sentence = _build_one_sentence(skeleton, abstract_claim)
    evidence_refs = _collect_evidence_refs(evidence_index)
    overall_status = _overall_evidence_status(evidence_index)
    warnings = list(skeleton.warnings)

    return PaperCard(
        paper_id=skeleton.paper_id,
        title=title_claim.text if title_claim else skeleton.title,
        one_sentence_summary=one_sentence,
        problem=problem_claim,
        background=abstract_claim,
        old_methods=old_method_claims,
        bottleneck=CardClaim(
            text="UNKNOWN",
            evidence_type=EvidenceType.INSUFFICIENT_EVIDENCE,
        ),
        core_idea=method_claim,
        method_overview=method_claim,
        experiment_summary=experiment_claim,
        limitations=limitation_claim,
        key_formulas=formula_claims,
        evidence_refs=evidence_refs,
        confidence=skeleton.confidence,
        warnings=warnings,
        evidence_status=overall_status,
    )


async def _build_llm_enhanced(
    skeleton: PaperSkeleton,
    evidence_index: EvidenceIndex,
    claims_by_section: dict[str, list[ClaimEvidence]],
    llm_client: LLMClient | MockLLMClient,
) -> PaperCard:
    """LLM-enhanced card builder: uses LLM for summaries within evidence constraints."""
    rule_card = _build_rule_based(skeleton, evidence_index, claims_by_section)

    evidence_text = _format_evidence_for_prompt(evidence_index)
    skeleton_text = skeleton.model_dump_json()

    prompt_builder = PromptBuilder()
    messages = prompt_builder.build_simple(
        system=(
            "你是 ResearchSensei 的论文卡片生成引擎。\n"
            "根据论文骨架和证据，生成一句话总结和核心要点。\n"
            "严格约束：\n"
            "1. 不得生成证据之外的内容\n"
            "2. 证据不足时必须标注 INSUFFICIENT_EVIDENCE\n"
            "3. 每个核心 claim 必须给出 evidence_ref\n"
            "4. 不要自由发挥，只基于提供的材料改写和总结\n"
            "输出 JSON 格式。"
        ),
        user=f"""论文骨架:
{skeleton_text[:4000]}

证据索引:
{evidence_text[:3000]}

要求输出 JSON:
{{
  "one_sentence_summary": "一句话说清论文在做什么，为什么重要",
  "problem": {{"text": "论文要解决什么问题", "evidence_ref": "对应证据引用"}},
  "core_idea": {{"text": "核心创新点是什么", "evidence_ref": "对应证据引用"}},
  "method_overview": {{"text": "方法概述", "evidence_ref": "对应证据引用"}},
  "experiment_summary": {{"text": "实验结果概述", "evidence_ref": "对应证据引用"}},
  "limitations": {{"text": "局限性", "evidence_ref": "对应证据引用或空字符串"}}
}}""",
    )

    response = await llm_client.chat(messages)
    try:
        data = parse_llm_json(response.content)
    except LLMResponseError:
        raise  # Let outer handler catch this
    except Exception as exc:
        raise LLMResponseError(f"Failed to parse LLM output: {exc}") from exc

    # Merge LLM output with rule-based card, enforcing evidence constraints
    return _merge_llm_into_card(rule_card, data, evidence_index)


def _merge_llm_into_card(
    rule_card: PaperCard,
    llm_data: dict,
    evidence_index: EvidenceIndex,
) -> PaperCard:
    """Merge LLM output into rule-based card, enforcing evidence constraints."""
    valid_refs = {claim.evidence_ref for claim in evidence_index.claims}

    def _safe_claim(data: dict, fallback: CardClaim) -> CardClaim:
        text = data.get("text", fallback.text)
        ref = data.get("evidence_ref", "")
        if ref and ref not in valid_refs:
            ref = ""  # LLM hallucinated a ref
        if not ref:
            return CardClaim(
                text=text,
                evidence_type=EvidenceType.INSUFFICIENT_EVIDENCE,
                confidence=0.2,
            )
        # Find the matching claim for evidence type
        matching = next((c for c in evidence_index.claims if c.evidence_ref == ref), None)
        return CardClaim(
            text=text,
            evidence_ref=ref,
            evidence_type=matching.evidence_type if matching else EvidenceType.UNVERIFIED,
            confidence=matching.confidence if matching else 0.3,
        )

    one_sentence = llm_data.get("one_sentence_summary", rule_card.one_sentence_summary)
    if not one_sentence or one_sentence == "UNKNOWN":
        one_sentence = rule_card.one_sentence_summary

    return rule_card.model_copy(
        update={
            "one_sentence_summary": one_sentence,
            "problem": _safe_claim(llm_data.get("problem", {}), rule_card.problem),
            "core_idea": _safe_claim(llm_data.get("core_idea", {}), rule_card.core_idea),
            "method_overview": _safe_claim(llm_data.get("method_overview", {}), rule_card.method_overview),
            "experiment_summary": _safe_claim(llm_data.get("experiment_summary", {}), rule_card.experiment_summary),
            "limitations": _safe_claim(llm_data.get("limitations", {}), rule_card.limitations),
        }
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _index_claims(evidence_index: EvidenceIndex) -> dict[str, list[ClaimEvidence]]:
    """Index claims by section for fast lookup."""
    by_section: dict[str, list[ClaimEvidence]] = {}
    for claim in evidence_index.claims:
        section = claim.section.strip().lower().replace(" ", "_")
        by_section.setdefault(section, []).append(claim)
    return by_section


def _find_claim(
    claims_by_section: dict[str, list[ClaimEvidence]],
    section: str,
    fallback_text: str,
) -> CardClaim:
    """Find the best claim for a section, or create a degraded one."""
    section_claims = claims_by_section.get(section, [])
    if section_claims:
        best = max(section_claims, key=lambda c: c.confidence)
        return CardClaim(
            text=best.quote_or_summary or best.claim_text,
            evidence_ref=best.evidence_ref,
            evidence_type=best.evidence_type,
            confidence=best.confidence,
        )
    if fallback_text and fallback_text not in ("UNKNOWN", "INSUFFICIENT_EVIDENCE", "NEEDS_HUMAN_CHECK"):
        return CardClaim(
            text=fallback_text,
            evidence_type=EvidenceType.INSUFFICIENT_EVIDENCE,
            confidence=0.2,
        )
    return CardClaim(text="UNKNOWN", evidence_type=EvidenceType.INSUFFICIENT_EVIDENCE, confidence=0.0)


def _find_or_degraded(
    claims_by_section: dict[str, list[ClaimEvidence]],
    section: str,
    skeleton_text: str,
    warning_code: str,
) -> CardClaim:
    """Find claim or return degraded status with warning."""
    return _find_claim(claims_by_section, section, skeleton_text)


def _formula_claims(
    skeleton: PaperSkeleton,
    claims_by_section: dict[str, list[ClaimEvidence]],
) -> list[CardClaim]:
    """Build formula claims from skeleton formulas and evidence."""
    formula_claims_list = claims_by_section.get("formula", [])
    result: list[CardClaim] = []
    for i, formula_text in enumerate(skeleton.formulas[:3]):  # max 3 formulas
        matching = formula_claims_list[i] if i < len(formula_claims_list) else None
        if matching:
            result.append(CardClaim(
                text=formula_text,
                evidence_ref=matching.evidence_ref,
                evidence_type=matching.evidence_type,
                confidence=matching.confidence,
            ))
        else:
            result.append(CardClaim(
                text=formula_text,
                evidence_type=EvidenceType.NEEDS_HUMAN_CHECK,
                confidence=0.3,
            ))
    return result


def _old_method_claims(claims_by_section: dict[str, list[ClaimEvidence]]) -> list[CardClaim]:
    """Extract old method claims from introduction/background sections."""
    intro_claims = claims_by_section.get("introduction", [])
    background_claims = claims_by_section.get("background", [])
    all_relevant = intro_claims + background_claims
    result: list[CardClaim] = []
    for claim in all_relevant[:2]:  # max 2 old method claims
        result.append(CardClaim(
            text=claim.quote_or_summary or claim.claim_text,
            evidence_ref=claim.evidence_ref,
            evidence_type=claim.evidence_type,
            confidence=claim.confidence,
        ))
    return result


def _build_one_sentence(skeleton: PaperSkeleton, abstract_claim: CardClaim) -> str:
    """Build one-sentence summary from available evidence."""
    if abstract_claim.text and abstract_claim.text not in ("UNKNOWN", "INSUFFICIENT_EVIDENCE"):
        compact = " ".join(abstract_claim.text.split())
        if len(compact) > 150:
            return f"{compact[:147]}..."
        return compact
    if skeleton.abstract_summary and skeleton.abstract_summary not in ("UNKNOWN",):
        compact = " ".join(skeleton.abstract_summary.split())
        if len(compact) > 150:
            return f"{compact[:147]}..."
        return compact
    return "UNKNOWN"


def _collect_evidence_refs(evidence_index: EvidenceIndex) -> list[str]:
    """Collect unique evidence refs from the evidence index."""
    refs: list[str] = []
    for claim in evidence_index.claims:
        if claim.evidence_ref and claim.evidence_ref not in refs:
            refs.append(claim.evidence_ref)
    return refs


def _overall_evidence_status(evidence_index: EvidenceIndex) -> EvidenceType:
    """Determine overall evidence status from all claims."""
    types = {claim.evidence_type for claim in evidence_index.claims}
    if EvidenceType.SUPPORTED_BY_EXPERIMENT in types:
        return EvidenceType.SUPPORTED_BY_EXPERIMENT
    if EvidenceType.SUPPORTED_BY_FORMULA in types:
        return EvidenceType.SUPPORTED_BY_FORMULA
    if EvidenceType.SUPPORTED_BY_TEXT in types:
        return EvidenceType.SUPPORTED_BY_TEXT
    if EvidenceType.NEEDS_HUMAN_CHECK in types:
        return EvidenceType.NEEDS_HUMAN_CHECK
    if types:
        return EvidenceType.INSUFFICIENT_EVIDENCE
    return EvidenceType.UNVERIFIED


def _format_evidence_for_prompt(evidence_index: EvidenceIndex) -> str:
    """Format evidence claims for inclusion in LLM prompt."""
    lines: list[str] = []
    for claim in evidence_index.claims[:20]:  # limit to avoid token overflow
        lines.append(
            f"- [{claim.evidence_type.value}] {claim.evidence_ref}: "
            f"{claim.quote_or_summary[:200]}"
        )
    return "\n".join(lines)
