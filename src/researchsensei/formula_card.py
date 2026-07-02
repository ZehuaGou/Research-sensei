from __future__ import annotations

from researchsensei.llm.client import LLMClient
from researchsensei.llm.prompt_builder import PromptBuilder
from researchsensei.llm.runtime_config import card_timeout_seconds
from researchsensei.llm.types import LLMConfig
from researchsensei.llm.validator import validate_formula_cards_llm_output
from researchsensei.schemas import (
    EvidenceType,
    FormulaCard,
    FormulaCardBundle,
    FormulaSymbol,
    FormulaTerm,
    PaperSkeleton,
)
from researchsensei.schemas.evidence import EvidencePack, EvidencePackItem
from researchsensei.schemas.llm_output import FormulaCardLLMOutput, FormulaCardsLLMOutput


FORMULA_CARD_BATCH_SIZE = 3
DERIVATION_BLOCKED_ORIGINS = {"raw_formula_text", "unknown", "unresolved"}


async def build_formula_cards(
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

    derivable_items = [
        item for item in formula_items
        if not _is_derivation_blocked_formula(item)
    ]
    llm_cards: list[FormulaCardLLMOutput] = []
    warnings: list[str] = []
    for start in range(0, len(derivable_items), FORMULA_CARD_BATCH_SIZE):
        batch = derivable_items[start:start + FORMULA_CARD_BATCH_SIZE]
        batch_pack = EvidencePack(
            paper_id=evidence_pack.paper_id,
            items=batch,
            total_tokens=sum(item.token_count for item in batch),
        )
        messages = _build_batch_messages(prompt_builder, skeleton, batch)
        # Formula cards need enough budget for Cici Switch reasoning-model proxies.
        formula_config = LLMConfig(
            temperature=0.2,
            max_tokens=12000,
            json_mode=True,
            timeout=card_timeout_seconds(300.0),
            max_retries=1,
            retry_delay=1.0,
            disable_thinking=True,
        )
        refs = ", ".join(item.evidence_ref for item in batch if item.evidence_ref)
        try:
            data = await llm_client.chat_json(messages, config=formula_config)
            output = FormulaCardsLLMOutput.model_validate(data)
            if not output.formula_cards:
                warnings.append(f"LLM_RETURNED_NO_FORMULA_CARDS_FOR_BATCH: {refs}")
                continue
            validate_formula_cards_llm_output(output, batch_pack)
            llm_cards.extend(output.formula_cards)
        except Exception as exc:
            warnings.append(f"FORMULA_LLM_BATCH_FALLBACK: {refs}: {exc}")
            continue

    return _convert_to_bundle(llm_cards, evidence_pack, skeleton, warnings)


def _build_batch_messages(
    prompt_builder: PromptBuilder,
    skeleton: PaperSkeleton,
    formula_items: list[EvidencePackItem],
):
    evidence_text = _format_evidence_for_prompt(formula_items)
    allowed_refs = "\n".join(f"- {item.evidence_ref}" for item in formula_items if item.evidence_ref) or "- NONE"
    return prompt_builder.build_simple(
        system=(
            "你是 ResearchSensei 的公式卡片生成器。只根据给定公式证据回答。\n"
            "最终回答只能是一个 JSON 对象；不要输出 Markdown、解释、前后缀或思考过程。\n"
            "最终回答的第一个字符必须是 {，最后一个字符必须是 }。\n"
            "每个 formula_card 必须引用一个允许的 evidence_ref。\n"
            "必须保留证据中的 formula_id、formula_origin、formula_ocr_status。\n"
            "不要输出 formula_raw。"
        ),
        user=f"""论文：{skeleton.title}

公式证据：
{evidence_text}

允许的 evidence_ref：
{allowed_refs}

规则：
- 每条公式证据输出一张 formula_card。evidence_ref 只能来自允许列表。
- formula_id/formula_origin/formula_ocr_status 必须照抄证据值。
- 不要输出 formula_raw。用简洁中文解释，必要的英文数学术语保留。
- symbols[].symbol 和 terms[].term 可以保留必要数学符号；meaning/encourages/penalizes/if_removed 必须是完整中文短句，不能以逗号、顿号、冒号结尾。
- 不要把 LaTeX 源码当作解释；例如 symbol="\\mathbf{{V}}" 时 meaning 应写“值矩阵。”，而不是复述 "\\mathbf{{V}}"。
- source_latex 对应 source_exact；parser_latex/mineru_latex/marker_latex 对应 parser_derived；ocr_latex 对应 ocr_derived；raw/unknown 对应 degraded。

只返回以下 JSON 结构：
{{"formula_cards": [{{"formula_id":"","formula_origin":"","formula_ocr_status":"","formula_explanation_status":"","purpose":"","symbols":[{{"symbol":"","meaning":""}}],"terms":[{{"term":"","meaning":"","encourages":"","penalizes":"","if_removed":""}}],"intuition":"","numeric_example":"","what_if_removed":"","weight_sensitivity":"","plain_summary":"","evidence_ref":""}}]}}""",
    )


def _convert_to_bundle(
    output_cards: list[FormulaCardLLMOutput],
    evidence_pack: EvidencePack,
    skeleton: PaperSkeleton,
    warnings: list[str],
) -> FormulaCardBundle:
    """Convert LLM output to FormulaCardBundle."""
    evidence_by_ref = {item.evidence_ref: item for item in evidence_pack.items if item.evidence_ref}
    avg_confidence = _avg_confidence(evidence_pack)
    paper_id = skeleton.paper_id

    cards: list[FormulaCard] = []
    used_refs: set[str] = set()
    for i, llm_card in enumerate(output_cards):
        ref = llm_card.evidence_ref if llm_card.evidence_ref in evidence_by_ref else ""
        evidence = evidence_by_ref.get(ref)
        if evidence is None:
            continue
        if ref in used_refs:
            warnings.append(f"DUPLICATE_FORMULA_CARD_REF: {ref}")
            continue
        used_refs.add(ref)
        formula_raw = _formula_raw_from_evidence(evidence)
        formula_origin = _formula_origin_from_evidence(evidence)
        formula_ocr_status = _formula_ocr_status_from_evidence(evidence, formula_origin)
        formula_id = evidence.formula_id or f"{paper_id}:formula:{i:03d}"
        explanation_status = _normalized_explanation_status(
            llm_card.formula_explanation_status,
            formula_origin,
        )
        confidence = _card_confidence(formula_origin, avg_confidence, explanation_status)
        if _is_derivation_blocked_origin(formula_origin):
            cards.append(_fallback_card(evidence, paper_id))
            warnings.append(f"FORMULA_DERIVATION_BLOCKED_FOR_UNRELIABLE_PROVENANCE: {ref}")
            continue
        cards.append(FormulaCard(
            formula_id=formula_id,
            paper_id=paper_id,
            formula_raw=formula_raw,
            original_latex=formula_raw if formula_origin == "source_latex" else "",
            formula_origin=formula_origin,
            formula_ocr_status=formula_ocr_status,
            formula_explanation_status=explanation_status,
            formula_page=evidence.formula_page,
            equation_number=evidence.equation_number,
            equation_group_id=evidence.equation_group_id,
            group_order=evidence.group_order,
            group_crop_path=evidence.group_crop_path,
            coverage_status="LLM_EXPLAINED",
            is_core_formula=True,
            derivation_status=_derivation_status(formula_origin, explanation_status),
            location=_location(evidence),
            purpose=llm_card.purpose or "UNKNOWN",
            symbols=_symbols(llm_card.symbols, confidence),
            terms=_terms(llm_card.terms, confidence),
            intuition=llm_card.intuition or "UNKNOWN",
            numeric_example=llm_card.numeric_example or "UNKNOWN",
            what_if_removed=llm_card.what_if_removed or "UNKNOWN",
            weight_sensitivity=llm_card.weight_sensitivity or "UNKNOWN",
            plain_summary=llm_card.plain_summary or "UNKNOWN",
            evidence_ref=ref,
            evidence_status=EvidenceType.SUPPORTED_BY_FORMULA if ref else EvidenceType.UNVERIFIED,
            confidence=confidence if ref else 0.0,
            warnings=list(evidence.risk_flags) if evidence else [],
        ))

    for item in evidence_pack.items:
        if item.claim_type != "FORMULA_CONTEXT" or not item.evidence_ref:
            continue
        if item.evidence_ref not in used_refs:
            cards.append(_fallback_card(item, paper_id))
            if _is_derivation_blocked_formula(item):
                warnings.append(
                    f"FORMULA_DERIVATION_BLOCKED_FOR_UNRELIABLE_PROVENANCE: {item.formula_id or item.evidence_ref}"
                )
            else:
                warnings.append(f"LLM_CARD_MISSING_FOR_FORMULA: {item.formula_id or item.evidence_ref}")

    evidence_refs = sorted({c.evidence_ref for c in cards if c.evidence_ref})
    if _has_derivable_formula_items(evidence_pack) and not output_cards:
        warnings.append("NO_FORMULA_CARDS_FROM_LLM")

    return FormulaCardBundle(
        paper_id=paper_id,
        formula_cards=cards,
        evidence_refs=evidence_refs,
        confidence=_bundle_confidence(cards),
        warnings=warnings,
        evidence_status=_bundle_evidence_status(cards),
    )


def _formula_items(evidence_pack: EvidencePack) -> list[EvidencePackItem]:
    return [
        item for item in evidence_pack.items
        if item.claim_type == "FORMULA_CONTEXT" and item.evidence_ref
    ]


def _formula_origin_from_evidence(evidence: EvidencePackItem) -> str:
    return (evidence.formula_origin or "").strip() or "unknown"


def _formula_ocr_status_from_evidence(evidence: EvidencePackItem, formula_origin: str) -> str:
    status = (evidence.formula_ocr_status or "").strip()
    if status:
        return status
    if formula_origin == "ocr_latex":
        return "ocr_status_unknown"
    if _is_derivation_blocked_origin(formula_origin):
        return "not_available"
    return "not_required"


def _is_derivation_blocked_formula(item: EvidencePackItem) -> bool:
    return _is_derivation_blocked_origin(_formula_origin_from_evidence(item))


def _is_derivation_blocked_origin(formula_origin: str) -> bool:
    return formula_origin in DERIVATION_BLOCKED_ORIGINS


def _has_derivable_formula_items(evidence_pack: EvidencePack) -> bool:
    return any(
        item.claim_type == "FORMULA_CONTEXT"
        and item.evidence_ref
        and not _is_derivation_blocked_formula(item)
        for item in evidence_pack.items
    )


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


def _normalized_explanation_status(candidate: str, formula_origin: str) -> str:
    candidate = (candidate or "").strip().lower()
    if formula_origin == "source_latex":
        return "source_exact"
    if formula_origin in {"parser_latex", "mineru_latex", "marker_latex"}:
        return "parser_derived"
    if formula_origin == "ocr_latex":
        return "ocr_derived"
    if _is_derivation_blocked_origin(formula_origin):
        return "degraded"
    allowed = {"source_exact", "parser_derived", "ocr_derived", "degraded"}
    if candidate in allowed:
        return candidate
    return _explanation_status(formula_origin)


def _derivation_status(formula_origin: str, explanation_status: str) -> str:
    if formula_origin in {"raw_formula_text", "unknown", "unresolved"} or explanation_status == "degraded":
        return "blocked"
    if explanation_status == "source_exact":
        return "source_grounded"
    if explanation_status == "ocr_derived":
        return "ocr_cautious"
    return "parser_derived"


def _card_confidence(formula_origin: str, avg_confidence: float, explanation_status: str) -> float:
    base = avg_confidence or 0.6
    if formula_origin == "source_latex":
        return min(max(base, 0.7), 0.9)
    if formula_origin in {"parser_latex", "mineru_latex", "marker_latex"}:
        return min(base, 0.74)
    if formula_origin == "ocr_latex":
        return min(base, 0.65)
    if formula_origin in {"raw_formula_text", "unknown", "unresolved"} or explanation_status == "degraded":
        return min(base, 0.35)
    return min(base, 0.5)


def _fallback_card(item: EvidencePackItem, paper_id: str) -> FormulaCard:
    formula_raw = _formula_raw_from_evidence(item)
    origin = _formula_origin_from_evidence(item)
    raw_or_unknown = _is_derivation_blocked_origin(origin)
    warning = "RAW_OR_UNRESOLVED_FORMULA_DERIVATION_BLOCKED" if raw_or_unknown else "LLM_CARD_MISSING"
    return FormulaCard(
        formula_id=item.formula_id or item.evidence_ref,
        paper_id=paper_id,
        formula_raw=formula_raw,
        original_latex=formula_raw if origin == "source_latex" else "",
        formula_origin=origin,
        formula_ocr_status=_formula_ocr_status_from_evidence(item, origin),
        formula_explanation_status="degraded" if raw_or_unknown else _explanation_status(origin),
        formula_page=item.formula_page,
        equation_number=item.equation_number,
        equation_group_id=item.equation_group_id,
        group_order=item.group_order,
        group_crop_path=item.group_crop_path,
        coverage_status="SUMMARY_ONLY" if not raw_or_unknown else "BLOCKED_RAW_ONLY",
        is_core_formula=False,
        derivation_status="blocked" if raw_or_unknown else "summary_only",
        location=_location(item),
        purpose=_fallback_purpose(item, raw_or_unknown),
        intuition="INSUFFICIENT_EVIDENCE" if raw_or_unknown else "M2 preserved the formula evidence, but the LLM did not return a dedicated explanation for this formula.",
        numeric_example="INSUFFICIENT_EVIDENCE",
        what_if_removed="INSUFFICIENT_EVIDENCE",
        weight_sensitivity="INSUFFICIENT_EVIDENCE",
        plain_summary=_fallback_summary(item, raw_or_unknown),
        evidence_ref=item.evidence_ref,
        evidence_status=EvidenceType.NEEDS_HUMAN_CHECK if raw_or_unknown else EvidenceType.SUPPORTED_BY_FORMULA,
        confidence=0.0 if raw_or_unknown else 0.45,
        warnings=list(dict.fromkeys([*item.risk_flags, warning])),
    )


def _fallback_purpose(item: EvidencePackItem, raw_or_unknown: bool) -> str:
    if raw_or_unknown:
        return "INSUFFICIENT_EVIDENCE: M1 did not provide reliable LaTeX for downstream derivation."
    context = item.quote_or_summary or item.passage_text
    return f"Formula evidence preserved from M1 context: {context[:180].strip() or 'UNKNOWN'}"


def _fallback_summary(item: EvidencePackItem, raw_or_unknown: bool) -> str:
    if raw_or_unknown:
        return "M2 preserved this formula slot but blocked detailed derivation because only raw/unknown formula text was available."
    return "M2 preserved this formula slot and provided a summary-only card because the LLM omitted a dedicated card."


def _location(item: EvidencePackItem) -> str:
    parts: list[str] = []
    if item.formula_page is not None:
        parts.append(f"page {item.formula_page}")
    if item.equation_number:
        parts.append(f"equation {item.equation_number}")
    if item.equation_group_id:
        parts.append(f"group {item.equation_group_id}")
    return ", ".join(parts)


def _symbols(values: list[dict], confidence: float) -> list[FormulaSymbol]:
    symbols: list[FormulaSymbol] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        symbol = str(value.get("symbol") or "").strip()
        if not symbol:
            continue
        symbols.append(FormulaSymbol(
            symbol=symbol,
            meaning=_complete_sentence(value.get("meaning"), fallback="UNKNOWN"),
            evidence_status=EvidenceType.SUPPORTED_BY_FORMULA,
            confidence=confidence,
        ))
    return symbols


def _terms(values: list[dict], confidence: float) -> list[FormulaTerm]:
    terms: list[FormulaTerm] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        term = str(value.get("term") or "").strip()
        if not term:
            continue
        terms.append(FormulaTerm(
            term=term,
            meaning=_complete_sentence(value.get("meaning"), fallback="UNKNOWN"),
            encourages=_complete_sentence(value.get("encourages"), fallback="UNKNOWN"),
            penalizes=_complete_sentence(value.get("penalizes"), fallback="UNKNOWN"),
            if_removed=_complete_sentence(value.get("if_removed"), fallback="UNKNOWN"),
            evidence_status=EvidenceType.SUPPORTED_BY_FORMULA,
            confidence=confidence,
        ))
    return terms


def _complete_sentence(value: object, *, fallback: str) -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    text = text.rstrip("，,、；;：:")
    if text in {"UNKNOWN", "INSUFFICIENT_EVIDENCE"}:
        return text
    if text.endswith(("。", ".", "！", "!", "？", "?", "）", ")")):
        return text
    return f"{text}。"


def _bundle_confidence(cards: list[FormulaCard]) -> float:
    if not cards:
        return 0.0
    return round(sum(card.confidence for card in cards) / len(cards), 2)


def _bundle_evidence_status(cards: list[FormulaCard]) -> EvidenceType:
    if not cards:
        return EvidenceType.INSUFFICIENT_EVIDENCE
    if any(card.evidence_status == EvidenceType.SUPPORTED_BY_FORMULA for card in cards):
        return EvidenceType.SUPPORTED_BY_FORMULA
    return EvidenceType.INSUFFICIENT_EVIDENCE


def _avg_confidence(evidence_pack: EvidencePack) -> float:
    if not evidence_pack.items:
        return 0.0
    return round(sum(i.confidence for i in evidence_pack.items) / len(evidence_pack.items), 2)


def _format_evidence_for_prompt(items: list[EvidencePackItem]) -> str:
    lines: list[str] = []
    for item in items:
        lines.append(
            "\n".join(
                [
                    f"- evidence_ref: {item.evidence_ref}",
                    f"  formula_id: {item.formula_id}",
                    f"  formula_origin: {item.formula_origin or 'unknown'}",
                    f"  formula_ocr_status: {item.formula_ocr_status or 'not_required'}",
                    f"  page: {item.formula_page if item.formula_page is not None else 'unknown'}",
                    f"  equation_number: {item.equation_number or 'unknown'}",
                    f"  equation_group_id: {item.equation_group_id or 'unknown'}",
                    f"  group_order: {item.group_order}",
                    f"  text: {item.passage_text[:300]}",
                ]
            )
        )
    return "\n".join(lines)
