from __future__ import annotations

from researchsensei.llm.client import LLMClient
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
            "You are the ResearchSensei paper-understanding builder.\n"
            "Use only the supplied evidence pack. Do not use outside knowledge.\n"
            "Every core claim must cite exactly one allowed evidence_ref.\n"
            "If evidence is insufficient, write INSUFFICIENT_EVIDENCE and leave evidence_ref empty.\n"
            "Return only valid JSON."
        ),
        user=f"""Paper title: {skeleton.title}
Abstract summary: {skeleton.abstract_summary[:500]}

Evidence Pack:
{evidence_text}

Allowed evidence_ref values:
{allowed_refs}

Constraints:
- Choose evidence_ref exactly from Allowed evidence_ref values.
- Do not concatenate multiple evidence refs.
- Do not invent datasets, methods, results, or limitations.
- Use concise Chinese explanations with necessary English terms preserved.
- If evidence is insufficient, set text to "INSUFFICIENT_EVIDENCE" and evidence_ref to "".

Return JSON with this schema:
{{
  "one_sentence_summary": "one evidence-grounded sentence",
  "problem": {{"text": "problem addressed by the paper", "evidence_ref": "allowed ref"}},
  "core_idea": {{"text": "core contribution or idea", "evidence_ref": "allowed ref"}},
  "method_overview": {{"text": "method overview", "evidence_ref": "allowed ref"}},
  "experiment_summary": {{"text": "experiment or result summary", "evidence_ref": "allowed ref"}},
  "limitations": {{"text": "limitations if supported, otherwise INSUFFICIENT_EVIDENCE", "evidence_ref": "allowed ref or empty"}}
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
            f"- [{item.claim_type}] {item.evidence_ref}: {item.passage_text[:300]}"
        )
    return "\n".join(lines)


def _format_allowed_refs(evidence_pack: EvidencePack) -> str:
    refs = [item.evidence_ref for item in evidence_pack.items[:20] if item.evidence_ref]
    return "\n".join(f"- {ref}" for ref in refs) or "- NONE"
