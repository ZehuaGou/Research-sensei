from __future__ import annotations

from researchsensei.llm.client import LLMClient
from researchsensei.llm.prompt_builder import PromptBuilder
from researchsensei.llm.validator import validate_formula_cards_llm_output
from researchsensei.schemas import (
    EvidenceType,
    FormulaCard,
    FormulaCardBundle,
    PaperSkeleton,
)
from researchsensei.schemas.evidence import EvidencePack, EvidencePackItem
from researchsensei.schemas.llm_output import FormulaCardsLLMOutput


async def build_formula_cards_v2(
    evidence_pack: EvidencePack,
    skeleton: PaperSkeleton,
    llm_client: LLMClient,
) -> FormulaCardBundle:
    """Build formula cards using an evidence-constrained LLM path.

    LLM failure, invalid JSON, schema validation failure, or invalid
    evidence_ref raises directly. There is no rule-based fallback here.
    """
    prompt_builder = PromptBuilder()
    formula_items = _formula_items(evidence_pack)
    if not formula_items:
        return FormulaCardBundle(
            paper_id=skeleton.paper_id,
            formula_cards=[],
            confidence=0.0,
            warnings=["NO_FORMULA_EVIDENCE_IN_PACK"],
            evidence_status=EvidenceType.INSUFFICIENT_EVIDENCE,
        )

    evidence_text = _format_evidence_for_prompt(formula_items)
    allowed_refs = "\n".join(f"- {item.evidence_ref}" for item in formula_items if item.evidence_ref) or "- NONE"

    messages = prompt_builder.build_simple(
        system=(
            "You are the ResearchSensei formula-understanding builder.\n"
            "Use only the supplied formula evidence. Do not infer from outside knowledge.\n"
            "Each formula_card must cite exactly one allowed evidence_ref.\n"
            "Preserve formula_id, formula_raw, formula_origin, and formula_ocr_status from evidence.\n"
            "Never claim parser/OCR/raw formulas are source-level LaTeX.\n"
            "Return only valid JSON."
        ),
        user=f"""Paper title: {skeleton.title}

Formula evidence:
{evidence_text}

Allowed evidence_ref values:
{allowed_refs}

Constraints:
- Generate at most {min(5, len(formula_items))} formula_cards.
- Choose evidence_ref exactly from the allowed list.
- Use formula_id/formula_raw/formula_origin/formula_ocr_status exactly as shown in evidence.
- For parser_latex or mineru_latex, say the explanation is parser-derived.
- For raw_formula_text, unknown, or unresolved origins, do not provide detailed derivation.
- Use concise Chinese explanations with necessary English/math terms preserved.

Return JSON with this schema:
{{
  "formula_cards": [
    {{
      "formula_id": "formula id from evidence",
      "formula_raw": "formula text from evidence",
      "formula_origin": "origin from evidence",
      "formula_ocr_status": "ocr status from evidence",
      "formula_explanation_status": "parser_derived | source_exact | degraded",
      "purpose": "what this formula does in the paper",
      "intuition": "plain-language intuition",
      "numeric_example": "small example if evidence supports it, otherwise INSUFFICIENT_EVIDENCE",
      "plain_summary": "one sentence summary",
      "evidence_ref": "allowed ref"
    }}
  ]
}}""",
    )

    data = await llm_client.chat_json(messages)
    output = FormulaCardsLLMOutput.model_validate(data)
    validate_formula_cards_llm_output(output, evidence_pack)

    return _convert_to_bundle(output, evidence_pack, skeleton)


def _convert_to_bundle(
    output: FormulaCardsLLMOutput,
    evidence_pack: EvidencePack,
    skeleton: PaperSkeleton,
) -> FormulaCardBundle:
    """Convert LLM output to FormulaCardBundle."""
    evidence_by_ref = {item.evidence_ref: item for item in evidence_pack.items if item.evidence_ref}
    valid_refs = set(evidence_by_ref)
    avg_confidence = _avg_confidence(evidence_pack)
    paper_id = skeleton.paper_id

    cards: list[FormulaCard] = []
    for i, llm_card in enumerate(output.formula_cards):
        ref = llm_card.evidence_ref if llm_card.evidence_ref in valid_refs else ""
        evidence = evidence_by_ref.get(ref)
        formula_raw = llm_card.formula_raw or _formula_raw_from_evidence(evidence)
        formula_origin = llm_card.formula_origin or (evidence.formula_origin if evidence else "")
        formula_ocr_status = llm_card.formula_ocr_status or (evidence.formula_ocr_status if evidence else "")
        formula_id = llm_card.formula_id or (evidence.formula_id if evidence else f"{paper_id}:eq:v2:{i:03d}")
        explanation_status = llm_card.formula_explanation_status or _explanation_status(formula_origin)
        cards.append(FormulaCard(
            formula_id=formula_id,
            paper_id=paper_id,
            formula_raw=formula_raw,
            original_latex=formula_raw if formula_origin == "source_latex" else "",
            formula_origin=formula_origin,
            formula_ocr_status=formula_ocr_status,
            formula_explanation_status=explanation_status,
            purpose=llm_card.purpose or "UNKNOWN",
            intuition=llm_card.intuition or "UNKNOWN",
            numeric_example=llm_card.numeric_example or "UNKNOWN",
            plain_summary=llm_card.plain_summary or "UNKNOWN",
            evidence_ref=ref,
            evidence_status=EvidenceType.SUPPORTED_BY_FORMULA if ref else EvidenceType.UNVERIFIED,
            confidence=avg_confidence if ref else 0.0,
            warnings=list(evidence.risk_flags) if evidence else [],
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


def _formula_items(evidence_pack: EvidencePack) -> list[EvidencePackItem]:
    return [
        item for item in evidence_pack.items
        if item.claim_type == "FORMULA_CONTEXT" and item.evidence_ref
    ]


def _formula_raw_from_evidence(evidence: EvidencePackItem | None) -> str:
    if evidence is None:
        return ""
    text = evidence.passage_text
    marker = "Formula:"
    if marker in text:
        return text.split(marker, 1)[1].split("Context before:", 1)[0].strip()
    return text[:300].strip()


def _explanation_status(formula_origin: str) -> str:
    if formula_origin == "source_latex":
        return "source_exact"
    if formula_origin in {"raw_formula_text", "unknown", "unresolved"}:
        return "degraded"
    return "parser_derived"


def _avg_confidence(evidence_pack: EvidencePack) -> float:
    if not evidence_pack.items:
        return 0.0
    return round(sum(i.confidence for i in evidence_pack.items) / len(evidence_pack.items), 2)


def _format_evidence_for_prompt(items: list[EvidencePackItem]) -> str:
    lines: list[str] = []
    for item in items[:8]:
        lines.append(
            "\n".join(
                [
                    f"- evidence_ref: {item.evidence_ref}",
                    f"  formula_id: {item.formula_id}",
                    f"  formula_origin: {item.formula_origin or 'unknown'}",
                    f"  formula_ocr_status: {item.formula_ocr_status or 'not_required'}",
                    f"  page: {item.formula_page if item.formula_page is not None else 'unknown'}",
                    f"  text: {item.passage_text[:500]}",
                ]
            )
        )
    return "\n".join(lines)
