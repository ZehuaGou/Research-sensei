from __future__ import annotations

import asyncio
import re

from researchsensei.llm.client import LLMClient
from researchsensei.llm.prompt_builder import PromptBuilder
from researchsensei.llm.runtime_config import (
    card_max_retries,
    card_retry_delay_seconds,
    card_timeout_seconds,
    formula_card_concurrency,
    formula_card_batch_size,
)
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


DEFAULT_FORMULA_CARD_BATCH_SIZE = 10
DERIVATION_BLOCKED_ORIGINS = {"raw_formula_text", "unknown", "unresolved"}


class FormulaLLMNoCardsError(ValueError):
    """Raised when the LLM returns a valid JSON envelope with no formula cards."""


class FormulaCardGenerationError(ValueError):
    """Raised when derivable formula evidence does not receive an LLM card."""


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
    warnings: list[str] = []
    batch_size = formula_card_batch_size(_default_formula_card_batch_size(llm_client))
    batches = [
        derivable_items[start:start + batch_size]
        for start in range(0, len(derivable_items), batch_size)
    ]
    formula_config = LLMConfig(
        temperature=0.15,
        max_tokens=4500,
        json_mode=True,
        timeout=card_timeout_seconds(90.0),
        max_retries=card_max_retries(0),
        retry_delay=card_retry_delay_seconds(0.5),
        disable_thinking=True,
    )
    concurrency = min(
        max(1, formula_card_concurrency(_default_formula_card_concurrency(llm_client))),
        max(1, len(batches)),
    )
    semaphore = asyncio.Semaphore(concurrency)

    async def run_batch(batch: list[EvidencePackItem]) -> tuple[list[FormulaCardLLMOutput], list[str]]:
        async with semaphore:
            return await _build_formula_cards_batch(
                llm_client,
                prompt_builder,
                skeleton,
                evidence_pack.paper_id,
                batch,
                formula_config,
            )

    results = await asyncio.gather(*(run_batch(batch) for batch in batches))
    llm_cards: list[FormulaCardLLMOutput] = []
    for cards_for_batch, warnings_for_batch in results:
        llm_cards.extend(cards_for_batch)
        warnings.extend(warnings_for_batch)

    return _convert_to_bundle(llm_cards, evidence_pack, skeleton, warnings)


async def _build_formula_cards_batch(
    llm_client: LLMClient,
    prompt_builder: PromptBuilder,
    skeleton: PaperSkeleton,
    paper_id: str,
    batch: list[EvidencePackItem],
    formula_config: LLMConfig,
) -> tuple[list[FormulaCardLLMOutput], list[str]]:
    refs = _refs_label(batch)
    try:
        output = await _request_formula_cards_batch(
            llm_client,
            prompt_builder,
            skeleton,
            paper_id,
            batch,
            formula_config,
        )
        return output.formula_cards, []
    except FormulaLLMNoCardsError:
        if len(batch) == 1:
            return [], [f"LLM_RETURNED_NO_FORMULA_CARDS_FOR_BATCH: {refs}"]
        split_cards, split_warnings = await _split_retry_formula_batch(
            llm_client,
            prompt_builder,
            skeleton,
            paper_id,
            batch,
            formula_config,
        )
        return split_cards, [
            f"FORMULA_LLM_BATCH_SPLIT_RETRY: {refs}: LLM returned no formula_cards",
            *split_warnings,
        ]
    except Exception as exc:
        if len(batch) == 1:
            retry_cards, retry_warning = await _compact_retry_formula_batch(
                llm_client,
                prompt_builder,
                skeleton,
                paper_id,
                batch,
            )
            if retry_cards:
                return retry_cards, [
                    f"FORMULA_LLM_COMPACT_RETRY: {refs}: recovered after {exc}",
                    *retry_warning,
                ]
            return [], [
                f"FORMULA_LLM_BATCH_FALLBACK: {refs}: {exc}",
                *retry_warning,
            ]
        split_cards, split_warnings = await _split_retry_formula_batch(
            llm_client,
            prompt_builder,
            skeleton,
            paper_id,
            batch,
            formula_config,
        )
        return split_cards, [
            f"FORMULA_LLM_BATCH_SPLIT_RETRY: {refs}: {exc}",
            *split_warnings,
        ]


async def _split_retry_formula_batch(
    llm_client: LLMClient,
    prompt_builder: PromptBuilder,
    skeleton: PaperSkeleton,
    paper_id: str,
    batch: list[EvidencePackItem],
    formula_config: LLMConfig,
) -> tuple[list[FormulaCardLLMOutput], list[str]]:
    cards: list[FormulaCardLLMOutput] = []
    warnings: list[str] = []
    for item in batch:
        item_cards, item_warnings = await _build_formula_cards_batch(
            llm_client,
            prompt_builder,
            skeleton,
            paper_id,
            [item],
            formula_config,
        )
        cards.extend(item_cards)
        warnings.extend(item_warnings)
    return cards, warnings


async def _request_formula_cards_batch(
    llm_client: LLMClient,
    prompt_builder: PromptBuilder,
    skeleton: PaperSkeleton,
    paper_id: str,
    batch: list[EvidencePackItem],
    formula_config: LLMConfig,
) -> FormulaCardsLLMOutput:
    batch_pack = EvidencePack(
        paper_id=paper_id,
        items=batch,
        total_tokens=sum(item.token_count for item in batch),
    )
    messages = _build_batch_messages(prompt_builder, skeleton, batch)
    data = await llm_client.chat_json(messages, config=formula_config)
    output = FormulaCardsLLMOutput.model_validate(data)
    if not output.formula_cards:
        raise FormulaLLMNoCardsError("LLM returned no formula_cards")
    validate_formula_cards_llm_output(output, batch_pack)
    return output


async def _compact_retry_formula_batch(
    llm_client: LLMClient,
    prompt_builder: PromptBuilder,
    skeleton: PaperSkeleton,
    paper_id: str,
    batch: list[EvidencePackItem],
) -> tuple[list[FormulaCardLLMOutput], list[str]]:
    if len(batch) != 1:
        return [], []
    refs = _refs_label(batch)
    retry_config = LLMConfig(
        temperature=0.0,
        max_tokens=2600,
        json_mode=True,
        timeout=card_timeout_seconds(90.0),
        max_retries=0,
        retry_delay=card_retry_delay_seconds(0.5),
        disable_thinking=True,
    )
    try:
        batch_pack = EvidencePack(
            paper_id=paper_id,
            items=batch,
            total_tokens=sum(item.token_count for item in batch),
        )
        messages = _build_compact_retry_messages(prompt_builder, skeleton, batch)
        data = await llm_client.chat_json(messages, config=retry_config)
        output = FormulaCardsLLMOutput.model_validate(data)
        if not output.formula_cards:
            raise FormulaLLMNoCardsError("compact retry returned no formula_cards")
        validate_formula_cards_llm_output(output, batch_pack)
        return output.formula_cards, []
    except Exception as retry_exc:
        return [], [f"FORMULA_LLM_COMPACT_RETRY_FAILED: {refs}: {retry_exc}"]


def _default_formula_card_batch_size(llm_client: LLMClient) -> int:
    provider = getattr(llm_client, "provider", None)
    if getattr(provider, "kind", "") == "anthropic_compatible":
        return 1
    return DEFAULT_FORMULA_CARD_BATCH_SIZE


def _default_formula_card_concurrency(llm_client: LLMClient) -> int:
    provider = getattr(llm_client, "provider", None)
    if getattr(provider, "kind", "") == "anthropic_compatible":
        return 3
    return 2


def _refs_label(items: list[EvidencePackItem]) -> str:
    return ", ".join(item.evidence_ref for item in items if item.evidence_ref)


def _build_batch_messages(
    prompt_builder: PromptBuilder,
    skeleton: PaperSkeleton,
    formula_items: list[EvidencePackItem],
):
    evidence_text = _format_evidence_for_prompt(formula_items)
    paper_context = _paper_context_for_prompt(skeleton)
    allowed_refs = "\n".join(f"- {item.evidence_ref}" for item in formula_items if item.evidence_ref) or "- NONE"
    return prompt_builder.build_simple(
        system=(
            "你是 ResearchSensei 的公式卡片生成器。只根据给定公式证据回答。\n"
            "最终回答只能是一个 JSON 对象；不要输出 Markdown、解释、前后缀或思考过程。\n"
            "最终回答的第一个字符必须是 {，最后一个字符必须是 }。\n"
            "每个 formula_card 必须引用一个允许的 evidence_ref。\n"
            "必须保留证据中的 formula_id、formula_origin、formula_ocr_status。\n"
            "不要输出 formula_raw。\n"
            "必须优先使用公式前后文解释符号和作用，不能只根据变量名或常识猜。\n"
            "如果上下文确实没有说明某个字段，写 INSUFFICIENT_EVIDENCE，不要生成看似合理但无证据的解释。\n"
            "不要长篇推理，直接生成最终 JSON；terms 可以为空数组。\n"
            "每个字段只写短句，优先保证 JSON 完整闭合。"
        ),
        user=f"""论文：{skeleton.title}

论文上下文：
{paper_context}

公式证据：
{evidence_text}

允许的 evidence_ref：
{allowed_refs}

规则：
- 每条公式证据输出一张 formula_card。evidence_ref 只能来自允许列表。
- formula_id/formula_origin/formula_ocr_status 必须照抄证据值。
- 不要输出 formula_raw。用简洁中文解释，必要的英文数学术语保留。
- purpose 不超过 70 个汉字；intuition/numeric_example/what_if_removed/weight_sensitivity/plain_summary 各不超过 100 个汉字。
- symbols 最多 5 个；terms 不是必填，只有公式里有非常关键的整体项时最多写 1 个，否则返回 []。
- symbols[].symbol 和 terms[].term 可以保留必要数学符号；meaning/encourages/penalizes/if_removed 必须是完整中文短句，不能以逗号、顿号、冒号结尾。
- 不要把 LaTeX 源码当作解释；例如 symbol="\\mathbf{{V}}" 时 meaning 应写“值矩阵。”，而不是复述 "\\mathbf{{V}}"。
- 遇到 h_q(f)、\\overline{{S(x_i)}}、g(x_i,x_j) 这类符号时，必须从 Context before/after 里找定义；上下文有定义时不能泛化成别的领域解释。
- source_latex 对应 source_exact；parser_latex/mineru_latex/marker_latex 对应 parser_derived；ocr_latex 对应 ocr_derived；raw/unknown 对应 degraded。

只返回以下 JSON 结构：
{{"formula_cards": [{{"formula_id":"","formula_origin":"","formula_ocr_status":"","formula_explanation_status":"","purpose":"","symbols":[{{"symbol":"","meaning":""}}],"terms":[],"intuition":"","numeric_example":"","what_if_removed":"","weight_sensitivity":"","plain_summary":"","evidence_ref":""}}]}}""",
    )


def _build_compact_retry_messages(
    prompt_builder: PromptBuilder,
    skeleton: PaperSkeleton,
    formula_items: list[EvidencePackItem],
):
    evidence_text = _format_evidence_for_prompt(formula_items, max_chars=1100)
    allowed_refs = "\n".join(f"- {item.evidence_ref}" for item in formula_items if item.evidence_ref) or "- NONE"
    return prompt_builder.build_simple(
        system=(
            "你是 ResearchSensei 的公式卡片生成器。上一次请求没有给出最终 JSON。\n"
            "现在只做补救：不要解释过程，不要 Markdown，不要思考文本，只输出一个 JSON 对象。\n"
            "terms 必须返回 []。每个中文字段控制在 80 个汉字内。"
        ),
        user=f"""论文：{skeleton.title}

公式证据：
{evidence_text}

允许的 evidence_ref：
{allowed_refs}

只返回：
{{"formula_cards":[{{"formula_id":"","formula_origin":"","formula_ocr_status":"","formula_explanation_status":"","purpose":"","symbols":[{{"symbol":"","meaning":""}}],"terms":[],"intuition":"","numeric_example":"","what_if_removed":"","weight_sensitivity":"","plain_summary":"","evidence_ref":""}}]}}""",
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
            if _is_derivation_blocked_formula(item):
                cards.append(_fallback_card(item, paper_id))
                warnings.append(
                    f"FORMULA_DERIVATION_BLOCKED_FOR_UNRELIABLE_PROVENANCE: {item.formula_id or item.evidence_ref}"
                )
            else:
                reason = _missing_formula_reason(item.evidence_ref, warnings)
                cards.append(_llm_failed_card(item, paper_id, reason=reason))
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
    if not raw_or_unknown:
        raise FormulaCardGenerationError(
            "Refusing to create a structure-derived fallback for derivable formula evidence: "
            f"{item.evidence_ref}"
        )
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


def _llm_failed_card(item: EvidencePackItem, paper_id: str, *, reason: str) -> FormulaCard:
    formula_raw = _formula_raw_from_evidence(item)
    origin = _formula_origin_from_evidence(item)
    failure = _compact_prompt_text(reason or "LLM did not return a valid formula card.", max_chars=260)
    return FormulaCard(
        formula_id=item.formula_id or item.evidence_ref,
        paper_id=paper_id,
        formula_raw=formula_raw,
        original_latex=formula_raw if origin == "source_latex" else "",
        formula_origin=origin,
        formula_ocr_status=_formula_ocr_status_from_evidence(item, origin),
        formula_explanation_status=_explanation_status(origin),
        formula_page=item.formula_page,
        equation_number=item.equation_number,
        equation_group_id=item.equation_group_id,
        group_order=item.group_order,
        group_crop_path=item.group_crop_path,
        coverage_status="LLM_FAILED",
        is_core_formula=False,
        derivation_status="llm_failed",
        location=_location(item),
        purpose=f"LLM 没有返回这条公式的有效解释：{failure}",
        symbols=[],
        terms=[],
        intuition="LLM_FAILED",
        numeric_example="LLM_FAILED",
        what_if_removed="LLM_FAILED",
        weight_sensitivity="LLM_FAILED",
        plain_summary="这不是兜底解释；该公式保留为失败状态，需重新解析或更换模型后再生成。",
        evidence_ref=item.evidence_ref,
        evidence_status=EvidenceType.NEEDS_HUMAN_CHECK,
        confidence=0.0,
        warnings=list(dict.fromkeys([*item.risk_flags, "LLM_FORMULA_CARD_FAILED", failure])),
    )


def _missing_formula_reason(evidence_ref: str, warnings: list[str]) -> str:
    for warning in reversed(warnings):
        if evidence_ref and evidence_ref in warning:
            return warning
    return "LLM did not return a valid formula card for this evidence_ref."


def _fallback_purpose(item: EvidencePackItem, raw_or_unknown: bool) -> str:
    if raw_or_unknown:
        return "INSUFFICIENT_EVIDENCE: M1 did not provide reliable LaTeX for downstream derivation."
    context = item.quote_or_summary or item.passage_text
    return f"Formula evidence preserved from M1 context: {context[:180].strip() or 'UNKNOWN'}"


def _fallback_summary(item: EvidencePackItem, raw_or_unknown: bool) -> str:
    if raw_or_unknown:
        return "M2 preserved this formula slot but blocked detailed derivation because only raw/unknown formula text was available."
    return "M2 preserved this formula slot and provided a summary-only card because the LLM omitted a dedicated card."


def _structure_derived_confidence(origin: str) -> float:
    if origin == "source_latex":
        return 0.62
    if origin in {"parser_latex", "mineru_latex", "marker_latex"}:
        return 0.54
    if origin == "ocr_latex":
        return 0.45
    return 0.4


def _structure_derived_formula_explanation(formula_raw: str) -> dict[str, object]:
    raw = re.sub(r"\s+", " ", formula_raw).strip()
    confidence = 0.62
    known_explanation = _known_structure_derived_formula_explanation(raw, confidence)
    if known_explanation is not None:
        return known_explanation
    if _looks_like_spectral_residual_formula(raw):
        return {
            "purpose": "把时间序列转换到频域，去掉平均谱成分，保留更突出的谱残差，再还原成时间点显著性得分。",
            "symbols": [
                _derived_symbol("A(f)", "频率 f 上的幅度谱，表示该频率成分有多强。", confidence),
                _derived_symbol("P(f)", "频率 f 上的相位谱，保留信号在时间位置上的结构。", confidence),
                _derived_symbol("L(f)", "幅度谱取对数后的结果，用来压缩尺度差异。", confidence),
                _derived_symbol("h_q(f)", "局部平均滤波器，用来估计普通背景谱。", confidence),
                _derived_symbol("R(f)", "谱残差，表示当前频率相对背景谱突出的部分。", confidence),
                _derived_symbol("S(x)", "逆变换后得到的显著性得分，得分高的时间点更可能异常。", confidence),
            ],
            "terms": [
                _derived_term(
                    "L(f) - h_q(f) \\cdot L(f)",
                    "用原始对数幅度减去局部平均幅度，留下不寻常的频率成分。",
                    "突出和周围频率不一样的成分。",
                    "把平滑背景也当成异常信号。",
                    "显著性得分会更像普通频谱，异常点更难凸显。",
                    confidence,
                ),
                _derived_term(
                    "\\mathfrak{F}^{-1}(exp(R(f)+iP(f)))",
                    "把谱残差和相位重新合成，再逆变换回时间域。",
                    "把频域里的突出成分定位回原始时间点。",
                    "缺少相位或逆变换时无法知道异常发生在序列哪里。",
                    "只能知道频域异常，不能得到逐点异常分数。",
                    confidence,
                ),
            ],
            "intuition": "直觉上，它先估计“正常频谱背景”，再看哪些频率突然突出；突出部分还原到时间轴后，就形成异常显著性曲线。",
            "numeric_example": "可以把一个序列想成大多数点都平稳，某个点突然尖起来。傅里叶变换后，这个尖峰会让部分频率幅度偏高；减掉局部平均谱后，偏高部分留下来，逆变换后尖峰附近的 S(x) 会更大。",
            "what_if_removed": "如果不减去平均谱，普通周期成分和真正突出的异常成分会混在一起，显著性分数更容易被背景模式淹没。",
            "weight_sensitivity": "滤波窗口 q 越大，背景谱越平滑，可能更容易突出大尺度异常；q 越小，背景估计更贴近局部变化，可能更保守。",
            "plain_summary": "这组公式是在做谱残差异常检测：先找频谱里不寻常的部分，再把它转回时间轴得到异常分数。",
        }
    if _looks_like_threshold_formula(raw):
        return {
            "purpose": "把显著性得分转成二值异常标签：相对平均显著性超过阈值就判为异常，否则判为正常。",
            "symbols": [
                _derived_symbol("O(x_i)", "第 i 个时间点的输出标签，1 表示异常，0 表示正常。", confidence),
                _derived_symbol("S(x_i)", "第 i 个时间点的显著性得分。", confidence),
                _derived_symbol("\\overline{S(x_i)}", "显著性得分的局部或平均基准。", confidence),
                _derived_symbol("\\tau", "判定异常所需超过的阈值。", confidence),
            ],
            "terms": [
                _derived_term(
                    "\\frac{S(x_i)-\\overline{S(x_i)}}{\\overline{S(x_i)}}",
                    "衡量当前点比平均显著性高出多少比例。",
                    "让判定关注相对突增，而不是只看绝对大小。",
                    "平均基准太低时可能放大噪声，阈值需要配合调节。",
                    "只能看原始得分，跨序列或跨区间比较会更不稳定。",
                    confidence,
                ),
            ],
            "intuition": "不是看到分数高就直接判异常，而是先问它相对附近平均水平高了多少；只有高出足够多才给异常标签。",
            "numeric_example": "假设某点 S(x_i)=15，平均显著性为 10，阈值 τ=0.3，则相对增幅是 (15-10)/10=0.5，大于 0.3，所以 O(x_i)=1；如果 S(x_i)=11，则增幅 0.1，不超过阈值，输出 0。",
            "what_if_removed": "如果没有这个阈值规则，模型只能给连续显著性分数，无法直接得到每个时间点是否异常的最终标签。",
            "weight_sensitivity": "τ 越大，判异常越严格，误报可能下降但漏报可能上升；τ 越小，召回可能上升但误报也会变多。",
            "plain_summary": "这条公式负责最后一步决策：把连续异常分数变成 0/1 异常标签。",
        }
    if _looks_like_average_filter_formula(raw):
        return {
            "purpose": "定义一个 q×q 的平均滤波器，用来估计局部平均背景。",
            "symbols": [
                _derived_symbol("h_q(f)", "大小为 q 的平均滤波器。", confidence),
                _derived_symbol("q", "滤波窗口大小。", confidence),
            ],
            "terms": [
                _derived_term(
                    "\\frac{1}{q^2}",
                    "让 q×q 个位置的权重总和为 1。",
                    "得到真正的平均值，而不是把总和放大。",
                    "窗口过大可能抹掉局部细节。",
                    "滤波结果会随窗口大小改变尺度，不再是平均背景。",
                    confidence,
                ),
            ],
            "intuition": "它就是一个局部平均器：用周围一块区域的平均值代表普通背景，再拿原始值和背景比较。",
            "numeric_example": "当 q=3 时，矩阵有 9 个位置，每个权重都是 1/9；如果 9 个位置的值相加为 18，滤波后的平均值就是 2。",
            "what_if_removed": "没有平均滤波器，就缺少背景谱估计，后面的残差计算无法判断哪些频率是普通背景、哪些是突出成分。",
            "weight_sensitivity": "q 越大，背景估计越平滑；q 越小，背景更贴近局部变化，但也更容易受噪声影响。",
            "plain_summary": "这条公式定义了谱残差方法里的背景估计器。",
        }
    if _looks_like_trend_forecast_formula(raw):
        return {
            "purpose": "用最近 m 个历史差分的平均变化量，外推下一个时间点。",
            "symbols": [
                _derived_symbol("\\overline{g}", "最近 m 个变化量的平均值。", confidence),
                _derived_symbol("m", "用于估计趋势的历史步数。", confidence),
                _derived_symbol("x_{n+1}", "预测得到的下一个时间点。", confidence),
            ],
            "terms": [
                _derived_term(
                    "x_{n-m+1}+\\overline{g}\\cdot m",
                    "从 m 步前的值出发，加上 m 步平均变化量来预测下一点。",
                    "把最近趋势延续到未来。",
                    "如果趋势突然变化，平均差分会滞后。",
                    "缺少趋势外推，只能依赖当前点或静态基准。",
                    confidence,
                ),
            ],
            "intuition": "它把最近一段时间的平均变化速度当作趋势，然后顺着这个趋势往前推一步。",
            "numeric_example": "如果 m=3，三段变化的平均值是 2，三步前的值是 10，那么预测 x_{n+1}=10+2×3=16。",
            "what_if_removed": "没有这一步，系统更难区分正常趋势上升和真正异常突增。",
            "weight_sensitivity": "m 越大，趋势估计越平滑但反应更慢；m 越小，反应更快但更容易受短期噪声影响。",
            "plain_summary": "这条公式用平均差分做简单趋势预测。",
        }
    if _looks_like_augmentation_formula(raw):
        return {
            "purpose": "通过均值平移、方差缩放和随机系数生成扰动后的样本，用来扩展或模拟序列变化。",
            "symbols": [
                _derived_symbol("\\overline{x}", "原始或标准化后的输入值。", confidence),
                _derived_symbol("mean", "用于平移的均值项。", confidence),
                _derived_symbol("var", "用于缩放波动幅度的方差项。", confidence),
                _derived_symbol("r", "随机缩放因子。", confidence),
            ],
            "terms": [
                _derived_term(
                    "(\\overline{x}+mean)(1+var)\\cdot r",
                    "先平移，再按方差缩放，最后乘随机因子。",
                    "生成不同幅度和位置的样本变化。",
                    "随机或方差设置过大时可能产生不真实样本。",
                    "样本变化会更单一，鲁棒性提升有限。",
                    confidence,
                ),
            ],
            "intuition": "它是在原始序列附近做受控扰动，让模型或算法见到更多可能的幅度变化。",
            "numeric_example": "若 \\overline{x}=2，mean=1，var=0.1，r=0.5，再加回偏移 x=3，则新值约为 (2+1)×1.1×0.5+3=4.65。",
            "what_if_removed": "没有扰动生成，模型看到的变化更少，对尺度或均值变化的适应性会弱一些。",
            "weight_sensitivity": "var 和 r 越大，生成样本变化越强；过大时可能偏离真实数据分布。",
            "plain_summary": "这条公式描述了一种基于均值、方差和随机缩放的数据扰动方式。",
        }
    return {
        "purpose": "根据公式结构，把输入量组合成一个可计算的输出，用于论文方法中的某个中间步骤。",
        "symbols": _generic_symbols_from_formula(raw, confidence),
        "terms": [
            _derived_term(
                "公式右侧整体",
                "把若干输入量通过加减乘除、求和或变换组合起来。",
                "让抽象关系变成可执行计算。",
                "如果某个输入量噪声较大，输出也可能受影响。",
                "方法会失去这一层可计算关系，只能依赖更粗的描述。",
                confidence,
            )
        ],
        "intuition": "这类公式的读法是先找等号左边的输出，再看右边哪些变量共同决定它。",
        "numeric_example": "可以先给每个变量代一个小数字，沿着等号右边一步步计算，观察哪个变量变化会让输出变大或变小。",
        "what_if_removed": "没有这条公式，对应的中间量或决策量就缺少明确计算方式。",
        "weight_sensitivity": "右侧变量的尺度越大、或乘法系数越大，对输出的影响通常越明显。",
        "plain_summary": "这条公式提供了一个可执行的计算关系；由于上下文较少，解释主要来自公式结构本身。",
    }


def _known_structure_derived_formula_explanation(raw: str, confidence: float) -> dict[str, object] | None:
    if _looks_like_branchwise_attention_formula(raw):
        return _derived_explanation(
            purpose="把输入表示沿特征维度拆成两条注意力分支：一条用 MultiHead 学习 token 之间的交互，另一条用 Global 学习全局注意力模式，最后把两条分支拼接成总的 Attention 输出。",
            symbols=[
                ("Attention", "两条分支拼接后的最终注意力表示."),
                ("A^(1)", "MultiHead 分支的输出，主要保留输入相关的 token 交互信息."),
                ("A^(2)", "Global 分支的输出，主要保留全局学习到的注意力模式."),
                ("X^(1)", "送入 MultiHead 分支的输入子空间."),
                ("X^(2)", "送入 Global 分支的输入子空间."),
            ],
            terms=[
                ("Concat(A^(1), A^(2))", "沿特征或通道维度合并两条分支输出.", "让局部/token 交互信息和全局模式同时进入后续层.", "如果某个分支质量差，拼接后的表示会带入对应噪声.", "模型只能依赖单一注意力形态，难以同时兼顾表达力和效率."),
                ("MultiHead(X^(1))", "对第一部分输入做多头注意力，学习不同子空间里的 token 关系.", "捕捉长距离依赖和输入相关的 pairwise 交互.", "计算量通常比固定或全局学习模式更高.", "会削弱模型对输入内容动态调整注意力的能力."),
                ("Global(X^(2))", "对第二部分输入使用全局学习的注意力模式.", "用更低成本补充全局上下文结构.", "如果全局模板不适合当前样本，可能不如输入相关注意力灵活.", "模型会少掉论文中用于降低计算成本的全局分支."),
            ],
            intuition="这条公式不是在定义一个普通输出，而是在说明分工：一部分维度交给 MultiHead 负责细粒度交互，另一部分维度交给 Global 负责更便宜的全局模式，最后再合并。",
            numeric_example="假设隐藏维度 d=128，可以把 X 拆成 X^(1) 和 X^(2) 两个 64 维子空间。MultiHead 分支输出 64 维的 A^(1)，Global 分支输出 64 维的 A^(2)，Concat 后重新得到 128 维的 Attention 表示。",
            what_if_removed="如果去掉 MultiHead 分支，模型会失去输入相关的 token 交互；如果去掉 Global 分支，就少了论文想要的低成本全局注意力补充。",
            weight_sensitivity="d1 和 d2 的分配会影响速度和表达力：给 MultiHead 更多维度通常更强但更慢，给 Global 更多维度通常更省但可能更依赖全局模板质量。",
            plain_summary="这条公式描述的是 branch-wise mixing attention：把表示拆成 MultiHead 和 Global 两条路，再拼接回一个注意力输出。",
            confidence=confidence,
        )
    if _looks_like_scaled_dot_product_attention(raw):
        return _derived_explanation(
            purpose="计算标准 scaled dot-product attention：用 Q 和 K 的相似度得到注意力权重，再用这些权重对 V 做加权求和。",
            symbols=[
                ("Q", "query 表示，用来提出当前 token 想找什么信息."),
                ("K", "key 表示，用来和 query 匹配."),
                ("V", "value 表示，被注意力权重加权汇总的内容."),
                ("d_k", "key/query 子空间维度，用于缩放点积."),
            ],
            terms=[
                ("QK^T", "计算每个 query 和每个 key 的相似度.", "让相关 token 得到更高注意力分数.", "序列长时会带来 O(n^2) 的 pairwise 计算.", "模型就无法根据 token 间相似度分配注意力."),
                ("Softmax(QK^T / sqrt(d_k))V", "先把相似度归一化成权重，再对 value 做加权求和.", "输出聚合与当前 token 最相关的信息.", "相似度过尖或过平都会影响聚合质量.", "attention 会退化成没有归一化权重的线性组合."),
            ],
            intuition="先问当前位置和其他位置有多相关，再把相关位置的信息按权重拿过来。",
            numeric_example="如果一个 token 对三个位置的缩放分数是 [2, 1, 0]，Softmax 后第一个位置权重最大，输出就更接近第一个 value，同时仍保留其他 value 的少量信息。",
            what_if_removed="没有这条公式，就没有 vanilla self-attention 的核心计算，后面的 MultiHead 也没有可调用的基本 attention 单元。",
            weight_sensitivity="d_k 越大，点积幅度越容易变大；除以 sqrt(d_k) 可以避免 Softmax 过早变得极端。",
            plain_summary="这条公式是 Transformer 里最基本的 attention：用 QK 相似度选信息，再汇总 V。",
            confidence=confidence,
        )
    if _looks_like_global_learned_attention(raw):
        return _derived_explanation(
            purpose="用一个可学习的全局矩阵 S 直接产生注意力权重，再对 V 做加权汇总，从而替代依赖 QK 点积的输入相关注意力。",
            symbols=[
                ("S", "跨样本学习到的全局 compatibility 矩阵."),
                ("V", "value 表示，是最终被加权汇总的信息."),
                ("Softmax(S)", "由全局矩阵归一化得到的注意力权重."),
            ],
            terms=[
                ("Softmax(S)", "把可学习矩阵 S 转成每个位置的注意力分布.", "用固定学习到的全局模式减少 Q/K 投影和点积开销.", "如果样本差异很大，固定全局模式可能不够灵活.", "模型就回不到论文提出的 global-learned attention 分支."),
                ("Softmax(S)V", "用全局注意力权重聚合 value.", "保留一种更省计算的上下文混合方式.", "权重模板学偏时会把不相关位置也混进输出.", "只能依赖输入相关注意力，计算成本会更高."),
            ],
            intuition="它把“每次都重新算 QK 相似度”换成“训练一个全局注意力模板”，所以更像一个可学习的全局混合器。",
            numeric_example="如果 S 的某一行 Softmax 后主要关注当前位置和前一个位置，那么对应输出就是这两个位置的 value 加权和，而不需要再计算 QK^T。",
            what_if_removed="去掉它后，论文里的低成本全局分支不存在，模型只能使用更贵的 pairwise token interaction。",
            weight_sensitivity="S 的初始化和训练质量很关键；S 学得越集中，输出越偏向少数位置，学得越平，输出越像平均混合。",
            plain_summary="这条公式解释 global-learned attention：用可学习矩阵 S 直接生成注意力模式。",
            confidence=confidence,
        )
    if _looks_like_attention_head_formula(raw):
        return _derived_explanation(
            purpose="定义第 i 个 attention head：先把 Q、K、V 投影到该 head 的子空间，再调用 attention 计算这个子空间里的上下文表示。",
            symbols=[
                ("head_i", "第 i 个注意力头的输出."),
                ("W_i^Q", "第 i 个 head 的 query 投影矩阵."),
                ("W_i^K", "第 i 个 head 的 key 投影矩阵."),
                ("W_i^V", "第 i 个 head 的 value 投影矩阵."),
            ],
            terms=[
                ("QW_i^Q, KW_i^K, VW_i^V", "把同一组输入映射到第 i 个 head 专属的 Q/K/V 子空间.", "让不同 head 观察不同表示子空间.", "投影矩阵学得差时，该 head 可能只学到重复或噪声关系.", "多个 head 会失去分工，只能共享同一种表示视角."),
                ("Attention(QW_i^Q, KW_i^K, VW_i^V)", "在该子空间内执行一次 scaled attention.", "让 head_i 聚合它负责的上下文关系.", "如果该 head 关注错误位置，最终 MultiHead 输出也会受影响.", "MultiHead 公式里就没有可拼接的单头结果."),
            ],
            intuition="一个 head 就像一个观察角度：它先把输入换到自己的坐标系，再在这个坐标系里做 attention。",
            numeric_example="如果有 8 个 head，每个 head 都有自己的 W_i^Q、W_i^K、W_i^V，那么第 3 个 head 可能专门学周期关系，第 5 个 head 可能更关注局部突变。",
            what_if_removed="没有单个 head 的定义，MultiHead 只能停留在名字上，无法说明每个 head 是如何产生的。",
            weight_sensitivity="W_i^Q/W_i^K 控制匹配方式，W_i^V 控制被汇总的信息内容；这些矩阵变化会直接改变该 head 关注什么。",
            plain_summary="这条公式说明每个注意力头怎样由 Q/K/V 的独立投影和 attention 计算得到。",
            confidence=confidence,
        )
    if _looks_like_multihead_concat_formula(raw):
        return _derived_explanation(
            purpose="把多个 attention head 的结果拼接起来，再乘输出矩阵 W^O 投影回模型需要的表示维度。",
            symbols=[
                ("MultiHead(Q,K,V)", "多头注意力模块的总输出."),
                ("head_1 ... head_h", "不同注意力头产生的子空间上下文表示."),
                ("h", "注意力头数量."),
                ("W^O", "拼接后用于混合各 head 信息的输出投影矩阵."),
            ],
            terms=[
                ("Concat(head_1, ..., head_h)", "把所有 head 的输出沿特征维度拼接.", "保留多个子空间、多个位置关系的并行观察结果.", "如果 head 之间高度重复，拼接会浪费维度.", "模型只能使用单一 attention 视角."),
                ("Concat(...) W^O", "把拼接后的高维表示重新混合并投影到目标维度.", "让不同 head 的信息发生交互.", "W^O 学得差会导致有用 head 被压制.", "拼接结果无法回到后续层期望的维度."),
            ],
            intuition="多个 head 先各看各的，再由 W^O 把这些视角重新调和成一个统一表示。",
            numeric_example="如果 h=4，每个 head 输出 16 维，Concat 后得到 64 维；再乘 W^O，可以把这 64 维混合成后续层需要的模型维度。",
            what_if_removed="去掉 Concat 就无法合并多头信息；去掉 W^O 则无法把多头结果投影成统一输出。",
            weight_sensitivity="head 数越多，模型可观察的子空间越多，但每个 head 分到的维度可能变小；W^O 决定哪些 head 的信息被放大。",
            plain_summary="这条公式是多头注意力的合并步骤：拼接所有 head，再用 W^O 统一输出。",
            confidence=confidence,
        )
    if "\\mathrm{F1}" in raw and "Precision" in raw and "Recall" in raw:
        return _simple_known_formula_explanation(
            "用 Precision 和 Recall 的调和平均衡量检测结果，避免只看准确率或只看召回率。",
            [("F1", "Precision 和 Recall 的综合分数."), ("Precision", "预测为异常的样本里真正异常的比例."), ("Recall", "真实异常样本中被找出来的比例.")],
            "2 * Precision * Recall / (Precision + Recall)",
            "只有 Precision 和 Recall 都高时 F1 才会高。",
            "如果 Precision=0.8、Recall=0.5，则 F1=2*0.8*0.5/(0.8+0.5)=0.615。",
            "没有 F1，异常检测结果很容易只展示 Precision 或 Recall，无法看出二者的折中。",
            confidence,
        )
    if "\\mathrm{Precision}" in raw and "TP" in raw and "FP" in raw:
        return _simple_known_formula_explanation(
            "计算精确率：模型报出的异常里，有多少是真的异常。",
            [("TP", "被正确检测出的异常."), ("FP", "被误报为异常的正常样本."), ("Precision", "异常报警的可信度.")],
            "TP / (TP + FP)",
            "它关心报警是否可信，FP 越多 Precision 越低。",
            "如果 TP=80、FP=20，则 Precision=80/(80+20)=0.8。",
            "没有 Precision，就看不出模型是不是靠大量误报换来了高召回。",
            confidence,
        )
    if "\\mathrm{Recall}" in raw and "TP" in raw and "FN" in raw:
        return _simple_known_formula_explanation(
            "计算召回率：真实异常里，有多少被模型找了出来。",
            [("TP", "被正确检测出的异常."), ("FN", "被漏掉的真实异常."), ("Recall", "模型覆盖真实异常的能力.")],
            "TP / (TP + FN)",
            "它关心真实异常有没有被抓住，FN 越多 Recall 越低。",
            "如果 TP=70、FN=30，则 Recall=70/(70+30)=0.7。",
            "没有 Recall，就可能漏掉大量异常却看不出来。",
            confidence,
        )
    if "\\mathcal{L}_{mse}" in raw:
        return _simple_known_formula_explanation(
            "用均方误差训练预测模型，让预测序列尽量接近真实观测序列。",
            [("L_mse", "预测误差损失."), ("Y^(t)", "第 t 个时间点的真实观测."), ("hat(Y)^(t)", "第 t 个时间点的预测输出."), ("M", "归一化项.")],
            "sum ||Y^(t) - hat(Y)^(t)||_2^2 / M",
            "预测错得越多，平方误差越大；大误差会被更重地惩罚。",
            "如果真实值是 10、预测是 7，平方误差是 9；预测变成 9 时误差降到 1。",
            "没有 MSE 损失，预测分支就缺少清晰的优化目标。",
            confidence,
        )
    if "\\hat{\\mathbf{y}}" in raw and "\\mathcal{Y}_{i}^{(t)}" in raw:
        return _simple_known_formula_explanation(
            "把每个变量在时间 t 的预测误差累加成异常分数，误差越大表示越可能异常。",
            [("hat(y)^(t)", "时间 t 的异常分数."), ("Y_i^(t)", "第 i 个变量的真实值."), ("hat(Y)_i^(t)", "第 i 个变量的预测值."), ("M", "变量数量.")],
            "sum_i ||Y_i^(t) - hat(Y)_i^(t)||_2^2",
            "如果模型能预测正常模式，预测误差突然变大时该时间点就更可疑。",
            "两个变量误差分别为 1 和 3，则分数是 1^2+3^2=10。",
            "没有这条公式，就难以把预测结果转成可排序的异常强度。",
            confidence,
        )
    if "argmax" in raw and "\\log \\pi" in raw and "g^" in raw:
        return _simple_known_formula_explanation(
            "用 Gumbel-Max 技巧从二元边或结构变量中采样一个离散选择。",
            [("z^(i,j)", "节点或变量对 (i,j) 的离散选择结果."), ("pi_c^(i,j)", "类别 c 的概率参数."), ("g_c^(i,j)", "Gumbel 噪声."), ("c", "二分类选择.")],
            "argmax_c(log pi_c + g_c)",
            "它在概率基础上加随机扰动，让结构采样既受概率控制又能探索。",
            "类别 1 概率更高时更常被选中，但 Gumbel 噪声可能让单次采样选到类别 0。",
            "没有这一步，模型很难从概率化边权生成明确的 0/1 结构选择。",
            confidence,
        )
    if "\\exp" in raw and "\\tau" in raw and "\\log \\pi" in raw:
        return _simple_known_formula_explanation(
            "用 Gumbel-Softmax 把离散采样近似成可微的软选择，方便神经网络反向传播。",
            [("z_c^(i,j)", "类别 c 的软采样权重."), ("pi_c^(i,j)", "类别 c 的概率参数."), ("g_c^(i,j)", "Gumbel 噪声."), ("tau", "温度系数.")],
            "softmax((log pi + g) / tau)",
            "tau 小时选择接近 one-hot，tau 大时选择更平滑。",
            "tau 很小时输出可能接近 [0.02, 0.98]；tau 较大时可能是 [0.45, 0.55]。",
            "没有 Gumbel-Softmax，学习离散图结构时反向传播会更困难。",
            confidence,
        )
    if "\\mathcal{L}_{s}" in raw and "\\log \\pi" in raw:
        return _simple_known_formula_explanation(
            "通过累加边存在概率的对数项来约束结构选择，使学习到的图结构更符合预设偏好。",
            [("L_s", "结构相关损失项."), ("pi_1^(i,j)", "节点或变量对 (i,j) 选择类别 1 的概率."), ("M", "变量或节点数量.")],
            "sum log pi_1^(i,j)",
            "它给图结构学习增加一个显式正则信号。",
            "pi_1=0.9 时 log(pi_1) 接近 0；pi_1=0.1 时 log(pi_1) 很负。",
            "没有结构损失，学到的边可能更散或更不稳定。",
            confidence,
        )
    if "\\tilde{x}" in raw and "\\min X_{train}" in raw and "\\max X_{train}" in raw:
        return _simple_known_formula_explanation(
            "把原始变量按训练集最小值和最大值缩放到统一范围，减少不同量纲对模型的影响。",
            [("tilde(x)", "归一化后的输入值."), ("x", "原始输入值."), ("min X_train", "训练集中的最小值."), ("max X_train", "训练集中的最大值.")],
            "(x - min X_train) / (max X_train - min X_train)",
            "它把每个变量放到自己的训练集坐标尺上读数。",
            "如果训练集最小值是 10、最大值是 30，当前 x=20，则 tilde(x)=0.5。",
            "没有归一化，数值范围大的变量会更容易影响模型训练和异常分数。",
            confidence,
        )
    if "\\mathbf{x}^{\\prime}_{i}" in raw and "\\mathcal{N}(i)" in raw:
        return _simple_known_formula_explanation(
            "对节点 i 的邻居信息做聚合，更新节点 i 的表示，用于图卷积或动态图结构建模。",
            [("x'_i", "更新后的节点 i 表示."), ("N(i)", "节点 i 的邻居集合."), ("h_Theta", "带参数的邻居变换函数."), ("x_i, x_j", "中心节点和邻居节点特征.")],
            "sum_{j in N(i)} h_Theta(...)",
            "节点 i 的新表示会吸收邻居节点的信息。",
            "如果节点 i 有 3 个邻居，就分别计算 3 个 h_Theta 输出再相加。",
            "没有这条图聚合，变量之间的连接关系就难以进入表示学习。",
            confidence,
        )
    return None


def _simple_known_formula_explanation(
    purpose: str,
    symbols: list[tuple[str, str]],
    term: str,
    intuition: str,
    numeric_example: str,
    what_if_removed: str,
    confidence: float,
) -> dict[str, object]:
    return _derived_explanation(
        purpose=purpose,
        symbols=symbols,
        terms=[(
            term,
            "这是公式中的核心计算项.",
            "让公式对应的量可以被明确计算或优化.",
            "输入统计、噪声或超参数变化会改变这一项的数值.",
            what_if_removed,
        )],
        intuition=intuition,
        numeric_example=numeric_example,
        what_if_removed=what_if_removed,
        weight_sensitivity="相关变量增大时输出通常会随之变化；归一化、温度或分母项会控制变化幅度。",
        plain_summary=purpose,
        confidence=confidence,
    )


def _derived_explanation(
    *,
    purpose: str,
    symbols: list[tuple[str, str]],
    terms: list[tuple[str, str, str, str, str]],
    intuition: str,
    numeric_example: str,
    what_if_removed: str,
    weight_sensitivity: str,
    plain_summary: str,
    confidence: float,
) -> dict[str, object]:
    return {
        "purpose": purpose,
        "symbols": [_derived_symbol(symbol, meaning, confidence) for symbol, meaning in symbols],
        "terms": [
            _derived_term(term, meaning, encourages, penalizes, if_removed, confidence)
            for term, meaning, encourages, penalizes, if_removed in terms
        ],
        "intuition": intuition,
        "numeric_example": numeric_example,
        "what_if_removed": what_if_removed,
        "weight_sensitivity": weight_sensitivity,
        "plain_summary": plain_summary,
    }


def _looks_like_branchwise_attention_formula(raw: str) -> bool:
    return all(marker in raw for marker in ["Attention", "Concat", "MultiHead", "Global"])


def _looks_like_scaled_dot_product_attention(raw: str) -> bool:
    return all(marker in raw for marker in ["Attention", "Softmax", "\\mathbf{Q}", "\\mathbf{K}", "\\sqrt{d"])


def _looks_like_global_learned_attention(raw: str) -> bool:
    return "Attention" in raw and "Softmax" in raw and "\\mathbf{S}" in raw and "\\mathbf{Q}" not in raw


def _looks_like_attention_head_formula(raw: str) -> bool:
    return "\\textit{head}" in raw and "Attention" in raw and "W_{i}^{Q}" in raw


def _looks_like_multihead_concat_formula(raw: str) -> bool:
    return "MultiHead" in raw and "Concat" in raw and "W^{O}" in raw


def _looks_like_spectral_residual_formula(raw: str) -> bool:
    return all(marker in raw for marker in ["Amplitude", "Phrase", "R(f)", "S("])


def _looks_like_threshold_formula(raw: str) -> bool:
    return "\\begin{cases}" in raw and ("\\tau" in raw or "tau" in raw) and ("O(x" in raw or "O(" in raw)


def _looks_like_average_filter_formula(raw: str) -> bool:
    return "h_q" in raw and "\\frac{1}{q" in raw and "\\begin{bmatrix}" in raw


def _looks_like_trend_forecast_formula(raw: str) -> bool:
    return "\\overline{g}" in raw and "x_{n+1}" in raw


def _looks_like_augmentation_formula(raw: str) -> bool:
    compact = raw.replace(" ", "")
    return "(\\overline{x}+mean)(1+var)" in compact and "\\cdot r" in raw


def _generic_symbols_from_formula(raw: str, confidence: float) -> list[FormulaSymbol]:
    candidates = re.findall(r"\\?[A-Za-z](?:_\{?[A-Za-z0-9]+\}?|\([^)]+\))?", raw)
    seen: set[str] = set()
    symbols: list[FormulaSymbol] = []
    skip = {"begin", "end", "frac", "text", "label", "left", "right", "overline", "sum", "cdot"}
    for candidate in candidates:
        token = candidate.strip("\\")
        if token in skip or not token or token in seen:
            continue
        seen.add(token)
        symbols.append(_derived_symbol(candidate, "公式中的一个输入、中间量或输出量，需要结合正文语境进一步命名。", confidence))
        if len(symbols) >= 6:
            break
    return symbols


def _derived_symbol(symbol: str, meaning: str, confidence: float) -> FormulaSymbol:
    return FormulaSymbol(
        symbol=symbol,
        meaning=_complete_sentence(meaning, fallback="UNKNOWN"),
        evidence_status=EvidenceType.SUPPORTED_BY_FORMULA,
        confidence=confidence,
    )


def _derived_term(
    term: str,
    meaning: str,
    encourages: str,
    penalizes: str,
    if_removed: str,
    confidence: float,
) -> FormulaTerm:
    return FormulaTerm(
        term=term,
        meaning=_complete_sentence(meaning, fallback="UNKNOWN"),
        encourages=_complete_sentence(encourages, fallback="UNKNOWN"),
        penalizes=_complete_sentence(penalizes, fallback="UNKNOWN"),
        if_removed=_complete_sentence(if_removed, fallback="UNKNOWN"),
        evidence_status=EvidenceType.SUPPORTED_BY_FORMULA,
        confidence=confidence,
    )


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


def _format_evidence_for_prompt(items: list[EvidencePackItem], *, max_chars: int = 1600) -> str:
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
                    f"  text: {_compact_prompt_text(item.passage_text, max_chars=max_chars)}",
                ]
            )
        )
    return "\n".join(lines)


def _paper_context_for_prompt(skeleton: PaperSkeleton) -> str:
    rows = [
        ("摘要", skeleton.abstract_summary),
        ("研究问题", skeleton.problem),
        ("方法概览", skeleton.method_overview),
        ("实验概览", skeleton.experiment_overview),
    ]
    rendered = [
        f"- {label}: {_compact_prompt_text(text, max_chars=420)}"
        for label, text in rows
        if text and text not in {"UNKNOWN", "INSUFFICIENT_EVIDENCE"}
    ]
    return "\n".join(rendered) if rendered else "- UNKNOWN"


def _compact_prompt_text(text: str, *, max_chars: int) -> str:
    compact = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."
