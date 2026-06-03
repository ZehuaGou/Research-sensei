from __future__ import annotations

import logging
import re

from researchsensei.llm.client import LLMClient, LLMResponseError, MockLLMClient, parse_llm_json
from researchsensei.llm.prompt_builder import PromptBuilder
from researchsensei.llm.types import ChatMessage
from researchsensei.schemas import (
    BlockType,
    DocumentIngestion,
    EvidenceIndex,
    EvidenceType,
    FormulaCard,
    FormulaCardBundle,
    FormulaSymbol,
    FormulaTerm,
    PaperSkeleton,
)

logger = logging.getLogger(__name__)


def build_formula_cards(
    document: DocumentIngestion,
    evidence_index: EvidenceIndex,
    skeleton: PaperSkeleton,
) -> FormulaCardBundle:
    """Build formula cards from parsed document and evidence index (rule-based only)."""
    formula_blocks = [b for b in document.blocks if b.type == BlockType.FORMULA]

    if not formula_blocks:
        return FormulaCardBundle(
            paper_id=document.paper_id,
            formula_cards=[],
            warnings=["FORMULA_UNAVAILABLE"],
            evidence_status=EvidenceType.INSUFFICIENT_EVIDENCE,
        )

    cards = [_build_single_rule(document, evidence_index, block) for block in formula_blocks]
    return _build_bundle(document.paper_id, cards)


async def build_formula_cards_with_llm(
    document: DocumentIngestion,
    evidence_index: EvidenceIndex,
    skeleton: PaperSkeleton,
    llm_client: LLMClient | MockLLMClient,
) -> FormulaCardBundle:
    """Build formula cards with LLM enhancement. Falls back to rule-based on failure."""
    formula_blocks = [b for b in document.blocks if b.type == BlockType.FORMULA]

    if not formula_blocks:
        return FormulaCardBundle(
            paper_id=document.paper_id,
            formula_cards=[],
            warnings=["FORMULA_UNAVAILABLE"],
            evidence_status=EvidenceType.INSUFFICIENT_EVIDENCE,
        )

    cards: list[FormulaCard] = []
    for block in formula_blocks:
        try:
            card = await _build_single_llm(document, evidence_index, skeleton, block, llm_client)
        except Exception as exc:
            logger.warning("LLM formula card failed for %s, falling back: %s", block.block_id, exc)
            card = _build_single_rule(document, evidence_index, block)
        cards.append(card)

    return _build_bundle(document.paper_id, cards)


def _build_bundle(paper_id: str, cards: list[FormulaCard]) -> FormulaCardBundle:
    """Build a FormulaCardBundle from a list of cards."""
    return FormulaCardBundle(
        paper_id=paper_id,
        formula_cards=cards,
        evidence_refs=_collect_evidence_refs(cards),
        confidence=_bundle_confidence(cards),
        warnings=_collect_warnings(cards),
        evidence_status=_overall_status(cards),
    )


def _build_single_rule(
    document: DocumentIngestion,
    evidence_index: EvidenceIndex,
    block,
) -> FormulaCard:
    """Rule-based formula card: conservative extraction, no LLM."""
    formula_raw = block.raw_latex or block.text
    evidence_ref = block.evidence_ref
    section = block.section
    nearby = block.text if block.raw_latex else ""

    # Find matching evidence claim
    matching_claim = None
    for claim in evidence_index.claims:
        if claim.block_id == block.block_id:
            matching_claim = claim
            break

    evidence_status = matching_claim.evidence_type if matching_claim else EvidenceType.NEEDS_HUMAN_CHECK
    confidence = matching_claim.confidence if matching_claim else 0.2

    # Extract symbols via regex
    symbols = _extract_symbols(formula_raw)

    # Extract terms (heuristic: split on +, -, =)
    terms = _extract_terms(formula_raw)

    # Determine purpose from section context
    purpose = _infer_purpose(section, nearby)

    warnings: list[str] = []
    if not nearby:
        warnings.append("NO_NEARBY_TEXT")

    return FormulaCard(
        formula_id=f"{document.paper_id}:eq:{block.block_id}",
        paper_id=document.paper_id,
        formula_raw=formula_raw,
        location=section,
        purpose=purpose,
        symbols=symbols,
        terms=terms,
        intuition="NEEDS_HUMAN_CHECK",
        numeric_example="NEEDS_HUMAN_CHECK",
        what_if_removed="NEEDS_HUMAN_CHECK",
        weight_sensitivity="NEEDS_HUMAN_CHECK",
        plain_summary="NEEDS_HUMAN_CHECK",
        evidence_ref=evidence_ref,
        evidence_status=evidence_status,
        confidence=confidence,
        warnings=warnings,
    )


async def _build_single_llm(
    document: DocumentIngestion,
    evidence_index: EvidenceIndex,
    skeleton: PaperSkeleton,
    block,
    llm_client: LLMClient | MockLLMClient,
) -> FormulaCard:
    """LLM-enhanced formula card: uses LLM for explanations within evidence constraints."""
    rule_card = _build_single_rule(document, evidence_index, block)

    formula_raw = block.raw_latex or block.text
    nearby = block.text if block.raw_latex else ""
    evidence_text = _format_evidence_for_prompt(evidence_index, block.block_id)

    prompt_builder = PromptBuilder()
    messages = prompt_builder.build_simple(
        system=(
            "你是 ResearchSensei 的公式讲解引擎。\n"
            "把 LaTeX 公式讲清楚，面向数学基础较弱的用户。\n"
            "严格约束：\n"
            "1. 不得生成证据之外的内容\n"
            "2. 不知道就写 UNKNOWN 或 NEEDS_HUMAN_CHECK\n"
            "3. 每个解释必须绑定 evidence_ref\n"
            "4. 不得把数学猜测写成论文事实\n"
            "输出 JSON 格式。"
        ),
        user=f"""公式: {formula_raw[:1000]}
附近文本: {nearby[:1000]}
证据: {evidence_text[:2000]}

要求输出 JSON:
{{
  "purpose": "这个公式在论文中起什么作用",
  "intuition": "用直觉解释这个公式",
  "numeric_example": "一个小数字例子",
  "what_if_removed": "去掉这个公式会怎样",
  "weight_sensitivity": "关键参数变大变小会怎样",
  "plain_summary": "一句话人话总结",
  "symbols": [{{"symbol": "x", "meaning": "输入数据"}}],
  "terms": [{{"term": "L_rec", "meaning": "重构损失", "encourages": "准确重构", "penalizes": "重构误差", "if_removed": "模型不学习重构"}}],
  "evidence_ref": "对应的证据引用"
}}""",
    )

    response = await llm_client.chat(messages)
    try:
        data = parse_llm_json(response.content)
    except LLMResponseError:
        raise

    return _merge_llm_into_card(rule_card, data, evidence_index)


def _merge_llm_into_card(
    rule_card: FormulaCard,
    llm_data: dict,
    evidence_index: EvidenceIndex,
) -> FormulaCard:
    """Merge LLM output into rule-based card, enforcing evidence constraints."""
    valid_refs = {claim.evidence_ref for claim in evidence_index.claims}

    # Validate evidence_ref
    ref = llm_data.get("evidence_ref", "")
    if ref and ref not in valid_refs:
        ref = ""  # LLM hallucinated a ref

    evidence_status = rule_card.evidence_status
    confidence = rule_card.confidence
    if ref:
        matching = next((c for c in evidence_index.claims if c.evidence_ref == ref), None)
        if matching:
            evidence_status = matching.evidence_type
            confidence = matching.confidence

    # Parse symbols from LLM
    llm_symbols = []
    for s in llm_data.get("symbols", []):
        llm_symbols.append(FormulaSymbol(
            symbol=s.get("symbol", "?"),
            meaning=s.get("meaning", "UNKNOWN"),
            evidence_status=evidence_status,
            confidence=confidence,
        ))

    # Parse terms from LLM
    llm_terms = []
    for t in llm_data.get("terms", []):
        llm_terms.append(FormulaTerm(
            term=t.get("term", "?"),
            meaning=t.get("meaning", "UNKNOWN"),
            encourages=t.get("encourages", "UNKNOWN"),
            penalizes=t.get("penalizes", "UNKNOWN"),
            if_removed=t.get("if_removed", "UNKNOWN"),
            evidence_status=evidence_status,
            confidence=confidence,
        ))

    def _safe_str(val: str, fallback: str) -> str:
        return val if val and val != "UNKNOWN" else fallback

    return rule_card.model_copy(
        update={
            "purpose": _safe_str(llm_data.get("purpose", ""), rule_card.purpose),
            "intuition": _safe_str(llm_data.get("intuition", ""), rule_card.intuition),
            "numeric_example": _safe_str(llm_data.get("numeric_example", ""), rule_card.numeric_example),
            "what_if_removed": _safe_str(llm_data.get("what_if_removed", ""), rule_card.what_if_removed),
            "weight_sensitivity": _safe_str(llm_data.get("weight_sensitivity", ""), rule_card.weight_sensitivity),
            "plain_summary": _safe_str(llm_data.get("plain_summary", ""), rule_card.plain_summary),
            "symbols": llm_symbols if llm_symbols else rule_card.symbols,
            "terms": llm_terms if llm_terms else rule_card.terms,
            "evidence_ref": ref or rule_card.evidence_ref,
            "evidence_status": evidence_status,
            "confidence": confidence,
        }
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Common LaTeX symbols and their typical meanings
_SYMBOL_KNOWN: dict[str, str] = {
    "L": "损失函数或优化目标",
    "lambda": "正则项权重",
    "alpha": "学习率或权重参数",
    "beta": "动量或权重参数",
    "gamma": "衰减系数",
    "theta": "模型参数",
    "omega": "权重矩阵或参数",
    "x": "输入数据",
    "y": "输出或标签",
    "z": "隐变量或中间表示",
    "h": "隐藏层表示",
    "W": "权重矩阵",
    "b": "偏置项",
    "mu": "均值",
    "sigma": "标准差",
    "epsilon": "小常数或噪声",
    "delta": "差值或变化量",
    "n": "样本数量",
    "N": "样本总数",
    "t": "时间步",
    "T": "总时间步",
    "d": "维度",
    "K": "类别数或聚类数",
    "p": "概率",
    "q": "概率",
    "H": "熵",
    "D": "距离或散度",
    "E": "期望",
    "P": "概率分布",
    "Q": "近似分布",
    "R": "正则项或奖励",
    "f": "函数",
    "g": "函数",
    "r": "比率或奖励",
    "v": "值函数",
    "s": "状态",
    "a": "动作",
}


def _extract_symbols(formula_raw: str) -> list[FormulaSymbol]:
    """Extract symbols from LaTeX formula via regex."""
    # Match single-letter variables and common LaTeX commands
    candidates = set()

    # Single-letter variables (not in common LaTeX commands)
    for match in re.finditer(r"(?<![a-zA-Z\\])([a-zA-Z])(?![a-zA-Z])", formula_raw):
        sym = match.group(1)
        if sym not in {"d", "e"}:  # Skip common non-symbol letters
            candidates.add(sym)

    # Greek letters via LaTeX commands
    for match in re.finditer(r"\\([a-zA-Z]+)", formula_raw):
        cmd = match.group(1)
        if cmd in _SYMBOL_KNOWN:
            candidates.add(cmd)

    symbols: list[FormulaSymbol] = []
    for sym in sorted(candidates):
        meaning = _SYMBOL_KNOWN.get(sym, "UNKNOWN")
        symbols.append(FormulaSymbol(
            symbol=sym,
            meaning=meaning,
            evidence_status=EvidenceType.NEEDS_HUMAN_CHECK if meaning == "UNKNOWN" else EvidenceType.REASONABLE_INFERENCE,
            confidence=0.3 if meaning == "UNKNOWN" else 0.5,
        ))

    return symbols[:10]  # Limit to 10 symbols


def _extract_terms(formula_raw: str) -> list[FormulaTerm]:
    """Extract terms from formula by splitting on +, -, =."""
    # Simple heuristic: split on top-level operators
    parts = re.split(r"[+=]", formula_raw)
    terms: list[FormulaTerm] = []
    for part in parts:
        term = part.strip()
        if term and len(term) > 1:
            terms.append(FormulaTerm(
                term=term[:100],
                meaning="UNKNOWN",
                encourages="UNKNOWN",
                penalizes="UNKNOWN",
                if_removed="UNKNOWN",
                evidence_status=EvidenceType.NEEDS_HUMAN_CHECK,
                confidence=0.1,
            ))
    return terms[:6]  # Limit to 6 terms


def _infer_purpose(section: str, nearby: str) -> str:
    """Infer formula purpose from section context."""
    section_lower = section.lower()
    if "method" in section_lower or "approach" in section_lower:
        return "定义模型的核心优化目标或计算过程"
    if "experiment" in section_lower or "result" in section_lower:
        return "用于实验评估或指标计算"
    if "loss" in nearby.lower() or "objective" in nearby.lower():
        return "定义损失函数或优化目标"
    if "attention" in nearby.lower():
        return "定义注意力计算机制"
    return "UNKNOWN"


def _format_evidence_for_prompt(evidence_index: EvidenceIndex, block_id: str) -> str:
    """Format relevant evidence for formula prompt."""
    lines: list[str] = []
    for claim in evidence_index.claims:
        if claim.block_id == block_id or claim.evidence_type == EvidenceType.SUPPORTED_BY_FORMULA:
            lines.append(
                f"- [{claim.evidence_type.value}] {claim.evidence_ref}: "
                f"{claim.quote_or_summary[:200]}"
            )
    return "\n".join(lines[:10])


def _collect_evidence_refs(cards: list[FormulaCard]) -> list[str]:
    """Collect unique evidence refs from formula cards."""
    refs: list[str] = []
    for card in cards:
        if card.evidence_ref and card.evidence_ref not in refs:
            refs.append(card.evidence_ref)
    return refs


def _overall_status(cards: list[FormulaCard]) -> EvidenceType:
    """Determine overall evidence status from all formula cards."""
    if not cards:
        return EvidenceType.INSUFFICIENT_EVIDENCE
    types = {card.evidence_status for card in cards}
    if EvidenceType.SUPPORTED_BY_FORMULA in types:
        return EvidenceType.SUPPORTED_BY_FORMULA
    if EvidenceType.SUPPORTED_BY_TEXT in types:
        return EvidenceType.SUPPORTED_BY_TEXT
    if EvidenceType.NEEDS_HUMAN_CHECK in types:
        return EvidenceType.NEEDS_HUMAN_CHECK
    return EvidenceType.INSUFFICIENT_EVIDENCE


def _collect_warnings(cards: list[FormulaCard]) -> list[str]:
    """Collect warnings from all formula cards."""
    warnings: set[str] = set()
    for card in cards:
        warnings.update(card.warnings)
    return sorted(warnings)


def _bundle_confidence(cards: list[FormulaCard]) -> float:
    """Calculate bundle confidence from individual card confidences."""
    if not cards:
        return 0.0
    return round(sum(c.confidence for c in cards) / len(cards), 2)
