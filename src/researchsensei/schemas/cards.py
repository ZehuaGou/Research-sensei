from __future__ import annotations

from pydantic import Field

from researchsensei.schemas.base import SenseiModel
from researchsensei.schemas.enums import EvidenceType


class CardClaim(SenseiModel):
    """A single claim in a paper card, with evidence binding."""

    text: str
    evidence_ref: str = ""
    evidence_type: EvidenceType = EvidenceType.UNVERIFIED
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class PaperCard(SenseiModel):
    """Evidence-constrained paper card for learning.

    Every key claim must bind to an evidence_ref from the evidence index.
    Unsupported claims must be marked with low-confidence evidence types.
    """

    paper_id: str
    title: str = "UNKNOWN"
    one_sentence_summary: str = "UNKNOWN"
    problem: CardClaim = Field(default_factory=lambda: CardClaim(text="UNKNOWN"))
    background: CardClaim = Field(default_factory=lambda: CardClaim(text="UNKNOWN"))
    old_methods: list[CardClaim] = Field(default_factory=list)
    bottleneck: CardClaim = Field(default_factory=lambda: CardClaim(text="UNKNOWN"))
    core_idea: CardClaim = Field(default_factory=lambda: CardClaim(text="UNKNOWN"))
    method_overview: CardClaim = Field(default_factory=lambda: CardClaim(text="UNKNOWN"))
    experiment_summary: CardClaim = Field(default_factory=lambda: CardClaim(text="UNKNOWN"))
    limitations: CardClaim = Field(default_factory=lambda: CardClaim(text="UNKNOWN"))
    key_formulas: list[CardClaim] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    evidence_status: EvidenceType = EvidenceType.UNVERIFIED


class FormulaSymbol(SenseiModel):
    """Explanation of a single symbol in a formula."""

    symbol: str
    meaning: str = "UNKNOWN"
    evidence_status: EvidenceType = EvidenceType.UNVERIFIED
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class FormulaTerm(SenseiModel):
    """Explanation of a single term in a formula."""

    term: str
    meaning: str = "UNKNOWN"
    encourages: str = "UNKNOWN"
    penalizes: str = "UNKNOWN"
    if_removed: str = "UNKNOWN"
    evidence_status: EvidenceType = EvidenceType.UNVERIFIED
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class FormulaCard(SenseiModel):
    """Evidence-constrained formula explanation card.

    Every explanation must bind to an evidence_ref from the evidence index.
    If formula blocks are absent or nearby text is insufficient, mark as degraded.
    """

    formula_id: str
    paper_id: str
    formula_raw: str = ""
    location: str = ""
    purpose: str = "UNKNOWN"
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    symbols: list[FormulaSymbol] = Field(default_factory=list)
    terms: list[FormulaTerm] = Field(default_factory=list)
    intuition: str = "UNKNOWN"
    numeric_example: str = "UNKNOWN"
    what_if_removed: str = "UNKNOWN"
    weight_sensitivity: str = "UNKNOWN"
    plain_summary: str = "UNKNOWN"
    evidence_ref: str = ""
    evidence_status: EvidenceType = EvidenceType.UNVERIFIED
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class FormulaCardBundle(SenseiModel):
    """Collection of formula cards for a single paper."""

    paper_id: str
    formula_cards: list[FormulaCard] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    evidence_status: EvidenceType = EvidenceType.UNVERIFIED


class TeachingCard(SenseiModel):
    """Five-layer teaching card for a single concept or formula.

    Implements the 五层讲解法:
    1. human_explanation: 人话版
    2. analogy_explanation: 类比版
    3. minimal_formula_explanation: 最小公式版
    4. numeric_example: 小数字例子版
    5. paper_role_explanation: 论文作用版
    """

    card_id: str
    paper_id: str
    target_type: str = "concept"  # paper / formula / concept / method / experiment
    target_id: str = ""
    title: str = "UNKNOWN"
    human_explanation: str = "UNKNOWN"
    analogy_explanation: str = "UNKNOWN"
    minimal_formula_explanation: str = "UNKNOWN"
    numeric_example: str = "UNKNOWN"
    paper_role_explanation: str = "UNKNOWN"
    evidence_refs: list[str] = Field(default_factory=list)
    evidence_status: EvidenceType = EvidenceType.UNVERIFIED
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class TeachingCardBundle(SenseiModel):
    """Collection of teaching cards for a single paper."""

    paper_id: str
    teaching_cards: list[TeachingCard] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    evidence_status: EvidenceType = EvidenceType.UNVERIFIED
