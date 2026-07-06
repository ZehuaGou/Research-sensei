from __future__ import annotations

import logging

from researchsensei.schemas import (
    EvidenceIndex,
    EvidenceType,
    FormulaCardBundle,
    PaperCard,
    PaperSkeleton,
    TeachingCard,
    TeachingCardBundle,
)

logger = logging.getLogger(__name__)


def build_teaching_cards(
    paper_card: PaperCard,
    formula_bundle: FormulaCardBundle,
    skeleton: PaperSkeleton,
    evidence_index: EvidenceIndex,
) -> TeachingCardBundle:
    """Build teaching cards from existing artifacts (rule-based only)."""
    cards: list[TeachingCard] = []

    # Generate teaching card for paper-level concepts
    for claim_attr, target_type, title in [
        ("core_idea", "concept", "核心创新点"),
        ("problem", "concept", "研究问题"),
        ("method_overview", "method", "方法概述"),
    ]:
        claim = getattr(paper_card, claim_attr, None)
        if claim and claim.text not in ("UNKNOWN", "INSUFFICIENT_EVIDENCE"):
            card = _build_concept_card(
                paper_card.paper_id,
                f"{paper_card.paper_id}:teach:{claim_attr}",
                target_type,
                title,
                claim.text,
                claim.evidence_ref,
                claim.evidence_type,
                claim.confidence,
                evidence_index,
            )
            cards.append(card)

    # Generate teaching cards for formulas
    for fc in formula_bundle.formula_cards[:3]:  # Limit to 3 formulas
        card = _build_formula_teaching_card(paper_card, fc, evidence_index)
        cards.append(card)

    if not cards:
        return TeachingCardBundle(
            paper_id=paper_card.paper_id,
            teaching_cards=[],
            warnings=["NO_TEACHABLE_CONTENT"],
            evidence_status=EvidenceType.INSUFFICIENT_EVIDENCE,
        )

    evidence_refs = _collect_evidence_refs(cards)
    overall_status = _overall_status(cards)
    warnings = _collect_warnings(cards)

    return TeachingCardBundle(
        paper_id=paper_card.paper_id,
        teaching_cards=cards,
        evidence_refs=evidence_refs,
        confidence=_bundle_confidence(cards),
        warnings=warnings,
        evidence_status=overall_status,
    )


# ---------------------------------------------------------------------------
# Rule-based builders
# ---------------------------------------------------------------------------


def _build_concept_card(
    paper_id: str,
    card_id: str,
    target_type: str,
    title: str,
    text: str,
    evidence_ref: str,
    evidence_type: EvidenceType,
    confidence: float,
    evidence_index: EvidenceIndex,
) -> TeachingCard:
    """Build a rule-based teaching card for a concept."""
    # Layer 1: 人话版 - if text is formula-heavy, use conservative fallback
    if _is_formula_heavy(text):
        human = _human_fallback_for_formula_text(target_type)
        effective_confidence = min(confidence, 0.3)
    else:
        human = text
        effective_confidence = confidence

    # Layer 2: 类比版 - cannot generate without LLM
    analogy = "NEEDS_HUMAN_CHECK"

    # Layer 3: 最小公式版 - extract from text if contains formula-like content
    minimal_formula = _extract_minimal_formula(text)

    # Layer 4: 小数字例子 - cannot generate without LLM
    numeric = "NEEDS_HUMAN_CHECK"

    # Layer 5: 论文作用版 - infer from target_type
    paper_role = _infer_paper_role(target_type)

    warnings: list[str] = []
    if not evidence_ref:
        warnings.append("NO_EVIDENCE_REF")
    if _is_formula_heavy(text):
        warnings.append("FORMULA_HEAVY_TEXT_NEEDS_HUMAN_EXPLANATION")

    return TeachingCard(
        card_id=card_id,
        paper_id=paper_id,
        target_type=target_type,
        target_id=evidence_ref,
        title=title,
        human_explanation=human,
        analogy_explanation=analogy,
        minimal_formula_explanation=minimal_formula,
        numeric_example=numeric,
        paper_role_explanation=paper_role,
        evidence_refs=[evidence_ref] if evidence_ref else [],
        evidence_status=evidence_type if evidence_ref else EvidenceType.INSUFFICIENT_EVIDENCE,
        confidence=effective_confidence,
        warnings=warnings,
    )


def _build_formula_teaching_card(
    paper_card: PaperCard,
    formula_card,
    evidence_index: EvidenceIndex,
) -> TeachingCard:
    """Build a rule-based teaching card for a formula."""
    # Layer 1: 人话版 - fallback: plain_summary → purpose → formula text + disclaimer
    if formula_card.plain_summary not in ("UNKNOWN", "NEEDS_HUMAN_CHECK"):
        human = formula_card.plain_summary
    elif formula_card.purpose not in ("UNKNOWN", "NEEDS_HUMAN_CHECK"):
        human = formula_card.purpose
    elif formula_card.formula_raw:
        human = f"该公式为：{formula_card.formula_raw[:100]}。当前系统尚不能可靠解释每一项，需要进一步讲解。"
    else:
        human = "NEEDS_HUMAN_CHECK"

    # Layer 2: 类比版
    analogy = formula_card.intuition if formula_card.intuition not in ("UNKNOWN", "NEEDS_HUMAN_CHECK") else "NEEDS_HUMAN_CHECK"

    # Layer 3: 最小公式版
    minimal_formula = formula_card.formula_raw[:200] if formula_card.formula_raw else "UNKNOWN"

    # Layer 4: 小数字例子
    numeric = formula_card.numeric_example if formula_card.numeric_example not in ("UNKNOWN", "NEEDS_HUMAN_CHECK") else "NEEDS_HUMAN_CHECK"

    # Layer 5: 论文作用版 - use location and purpose for specificity
    if formula_card.purpose not in ("UNKNOWN", "NEEDS_HUMAN_CHECK") and formula_card.location:
        paper_role = f"此公式位于{formula_card.location}部分，用于{formula_card.purpose}"
    elif formula_card.purpose not in ("UNKNOWN", "NEEDS_HUMAN_CHECK"):
        paper_role = f"此公式用于{formula_card.purpose}"
    elif formula_card.location:
        paper_role = f"此公式位于{formula_card.location}部分，具体作用需要进一步分析"
    else:
        paper_role = "NEEDS_HUMAN_CHECK"

    evidence_ref = formula_card.evidence_ref
    warnings: list[str] = []
    if not evidence_ref:
        warnings.append("NO_EVIDENCE_REF")

    return TeachingCard(
        card_id=f"{paper_card.paper_id}:teach:formula:{formula_card.formula_id}",
        paper_id=paper_card.paper_id,
        target_type="formula",
        target_id=formula_card.formula_id,
        title=f"公式讲解: {formula_card.formula_raw[:50]}",
        human_explanation=human,
        analogy_explanation=analogy,
        minimal_formula_explanation=minimal_formula,
        numeric_example=numeric,
        paper_role_explanation=paper_role,
        evidence_refs=[evidence_ref] if evidence_ref else [],
        evidence_status=formula_card.evidence_status,
        confidence=formula_card.confidence,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_formula_heavy(text: str) -> bool:
    """Check if text is primarily formula content rather than human-readable explanation."""
    formula_indicators = [
        "L =", "L=", "\\lambda", "\\alpha", "\\beta", "\\gamma", "\\theta",
        "\\sum", "\\prod", "\\int", "\\frac", "\\sqrt", "\\min", "\\max",
        "argmin", "argmax", "lambda L", "+ lambda", "= min", "= max",
    ]
    text_lower = text.lower()
    # Count formula-like patterns
    formula_count = sum(1 for indicator in formula_indicators if indicator.lower() in text_lower)
    # If text has multiple formula indicators or is very short with formula content
    if formula_count >= 2:
        return True
    # If text is short and contains formula operators
    if len(text) < 100 and formula_count >= 1 and any(op in text for op in ["=", "+", "-", "*", "\\"]):
        return True
    return False


def _human_fallback_for_formula_text(target_type: str) -> str:
    """Return a conservative human-readable fallback when claim text is formula-heavy."""
    fallbacks = {
        "concept": "该部分涉及论文的核心机制，但当前证据主要为公式形式，需要进一步解释才能转化为人话。",
        "method": "该部分涉及论文提出的方法，但当前证据主要为公式形式，需要进一步解释。",
        "experiment": "该部分涉及论文的实验评估，但当前证据不足以自动生成可靠的人话解释。",
    }
    return fallbacks.get(target_type, "该内容主要为公式形式，需要进一步解释。")


def _extract_minimal_formula(text: str) -> str:
    """Extract formula-like content from text."""
    # Look for common formula patterns
    for pattern in ["L =", "L=", "loss", "min", "max", "argmin", "argmax"]:
        if pattern.lower() in text.lower():
            # Return the sentence containing the formula
            for sentence in text.split("."):
                if pattern.lower() in sentence.lower():
                    return sentence.strip()[:200]
    return "UNKNOWN"


def _infer_paper_role(target_type: str) -> str:
    """Infer the role of a concept in the paper.

    Returns conservative, specific descriptions that don't make performance claims.
    """
    roles = {
        "concept": "此内容用于理解论文要解决的问题或核心思路",
        "method": "此内容用于理解作者提出的技术方案",
        "experiment": "此内容用于理解实验设计和评估方式",
        "formula": "此内容用于理解论文中的数学目标或计算机制",
    }
    return roles.get(target_type, "UNKNOWN")


def _collect_evidence_refs(cards: list[TeachingCard]) -> list[str]:
    """Collect unique evidence refs from teaching cards."""
    refs: list[str] = []
    for card in cards:
        for ref in card.evidence_refs:
            if ref not in refs:
                refs.append(ref)
    return refs


def _overall_status(cards: list[TeachingCard]) -> EvidenceType:
    """Determine overall evidence status."""
    if not cards:
        return EvidenceType.INSUFFICIENT_EVIDENCE
    types = {card.evidence_status for card in cards}
    if EvidenceType.SUPPORTED_BY_EXPERIMENT in types:
        return EvidenceType.SUPPORTED_BY_EXPERIMENT
    if EvidenceType.SUPPORTED_BY_FORMULA in types:
        return EvidenceType.SUPPORTED_BY_FORMULA
    if EvidenceType.SUPPORTED_BY_TEXT in types:
        return EvidenceType.SUPPORTED_BY_TEXT
    if EvidenceType.NEEDS_HUMAN_CHECK in types:
        return EvidenceType.NEEDS_HUMAN_CHECK
    return EvidenceType.INSUFFICIENT_EVIDENCE


def _collect_warnings(cards: list[TeachingCard]) -> list[str]:
    """Collect warnings from all teaching cards."""
    warnings: set[str] = set()
    for card in cards:
        warnings.update(card.warnings)
    return sorted(warnings)


def _bundle_confidence(cards: list[TeachingCard]) -> float:
    """Calculate bundle confidence."""
    if not cards:
        return 0.0
    return round(sum(c.confidence for c in cards) / len(cards), 2)


def _build_bundle(paper_id: str, cards: list[TeachingCard]) -> TeachingCardBundle:
    """Build a TeachingCardBundle from a list of cards."""
    return TeachingCardBundle(
        paper_id=paper_id,
        teaching_cards=cards,
        evidence_refs=_collect_evidence_refs(cards),
        confidence=_bundle_confidence(cards),
        warnings=_collect_warnings(cards),
        evidence_status=_overall_status(cards),
    )
