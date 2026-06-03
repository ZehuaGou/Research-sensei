from __future__ import annotations

import pytest

from researchsensei.formula_card import build_formula_cards
from researchsensei.grounding import build_evidence_index
from researchsensei.llm.client import MockLLMClient
from researchsensei.paper_card import build_paper_card
from researchsensei.paper_skeleton import build_paper_skeleton
from researchsensei.schemas import (
    BlockType,
    DocumentBlock,
    DocumentIngestion,
    EvidenceType,
)
from researchsensei.teaching_card import build_teaching_cards, build_teaching_cards_with_llm


def _block(
    block_id: str,
    block_type: BlockType,
    section: str,
    text: str,
    paper_id: str = "paper-1",
    raw_latex: str = "",
) -> DocumentBlock:
    return DocumentBlock(
        block_id=block_id,
        type=block_type,
        section=section,
        text=text,
        evidence_ref=f"{paper_id}:{block_id}",
        raw_latex=raw_latex,
    )


def _full_doc() -> DocumentIngestion:
    return DocumentIngestion(
        paper_id="paper-1",
        blocks=[
            _block("t001", BlockType.TITLE, "title", "Tiny TSAD Paper"),
            _block("b001", BlockType.ABSTRACT, "abstract", "We study anomaly detection in time series."),
            _block("b002", BlockType.PARAGRAPH, "introduction", "Current methods miss sensor dependencies."),
            _block("b003", BlockType.PARAGRAPH, "method", "We model dependencies with reconstruction error."),
            _block("eq001", BlockType.FORMULA, "method", "L = L_rec + lambda L_graph", raw_latex="L = L_{rec} + \\lambda L_{graph}"),
            _block("b004", BlockType.PARAGRAPH, "experiments", "Table 1 reports F1 on benchmark datasets."),
        ],
    )


def _build_artifacts(doc: DocumentIngestion):
    """Build all prerequisite artifacts for teaching cards."""
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)
    paper_card = build_paper_card(skeleton, evidence)
    formula_cards = build_formula_cards(doc, evidence, skeleton)
    return paper_card, formula_cards, skeleton, evidence


# ---------------------------------------------------------------------------
# Rule-based builder tests
# ---------------------------------------------------------------------------


def test_rule_based_teaching_cards_from_full_document() -> None:
    doc = _full_doc()
    paper_card, formula_cards, skeleton, evidence = _build_artifacts(doc)

    bundle = build_teaching_cards(paper_card, formula_cards, skeleton, evidence)

    assert bundle.paper_id == "paper-1"
    assert len(bundle.teaching_cards) > 0


def test_rule_based_teaching_cards_have_five_layers() -> None:
    doc = _full_doc()
    paper_card, formula_cards, skeleton, evidence = _build_artifacts(doc)

    bundle = build_teaching_cards(paper_card, formula_cards, skeleton, evidence)

    for card in bundle.teaching_cards:
        # All five layers must exist
        assert card.human_explanation  # Layer 1: 人话版
        assert card.analogy_explanation  # Layer 2: 类比版
        assert card.minimal_formula_explanation  # Layer 3: 最小公式版
        assert card.numeric_example  # Layer 4: 小数字例子
        assert card.paper_role_explanation  # Layer 5: 论文作用版


def test_rule_based_teaching_cards_bind_evidence_refs() -> None:
    doc = _full_doc()
    paper_card, formula_cards, skeleton, evidence = _build_artifacts(doc)

    bundle = build_teaching_cards(paper_card, formula_cards, skeleton, evidence)

    valid_refs = {claim.evidence_ref for claim in evidence.claims}
    for card in bundle.teaching_cards:
        for ref in card.evidence_refs:
            assert ref in valid_refs, f"Invalid ref: {ref}"


def test_rule_based_teaching_cards_degraded_when_no_content() -> None:
    """When paper_card has no usable claims, teaching cards should be empty or degraded."""
    from researchsensei.schemas import PaperCard, FormulaCardBundle

    empty_card = PaperCard(paper_id="p-empty")
    empty_formulas = FormulaCardBundle(paper_id="p-empty")
    empty_skeleton = build_paper_skeleton(
        DocumentIngestion(paper_id="p-empty", blocks=[]),
        build_evidence_index(DocumentIngestion(paper_id="p-empty", blocks=[])),
    )
    empty_evidence = build_evidence_index(DocumentIngestion(paper_id="p-empty", blocks=[]))

    bundle = build_teaching_cards(empty_card, empty_formulas, empty_skeleton, empty_evidence)

    assert len(bundle.teaching_cards) == 0
    assert "NO_TEACHABLE_CONTENT" in bundle.warnings
    assert bundle.evidence_status == EvidenceType.INSUFFICIENT_EVIDENCE


def test_rule_based_formula_teaching_card() -> None:
    doc = _full_doc()
    paper_card, formula_cards, skeleton, evidence = _build_artifacts(doc)

    bundle = build_teaching_cards(paper_card, formula_cards, skeleton, evidence)

    formula_cards_list = [c for c in bundle.teaching_cards if c.target_type == "formula"]
    assert len(formula_cards_list) >= 1

    fc = formula_cards_list[0]
    assert fc.minimal_formula_explanation != "UNKNOWN"
    assert fc.paper_role_explanation != "UNKNOWN"


def test_rule_based_teaching_cards_evidence_status() -> None:
    doc = _full_doc()
    paper_card, formula_cards, skeleton, evidence = _build_artifacts(doc)

    bundle = build_teaching_cards(paper_card, formula_cards, skeleton, evidence)

    # Should have at least SUPPORTED_BY_TEXT or SUPPORTED_BY_FORMULA
    assert bundle.evidence_status in {
        EvidenceType.SUPPORTED_BY_TEXT,
        EvidenceType.SUPPORTED_BY_FORMULA,
        EvidenceType.SUPPORTED_BY_EXPERIMENT,
    }


# ---------------------------------------------------------------------------
# LLM-enhanced builder tests (mock)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_enhanced_teaching_cards_use_mock_llm() -> None:
    doc = _full_doc()
    paper_card, formula_cards, skeleton, evidence = _build_artifacts(doc)

    mock_response = '{"human_explanation": "用重构误差检测异常", "analogy_explanation": "像自动纠错系统", "minimal_formula_explanation": "L = L_rec", "numeric_example": "输入5输出4.8误差0.2", "paper_role_explanation": "核心方法", "evidence_ref": "paper-1:b003"}'
    mock = MockLLMClient(response=mock_response)

    bundle = await build_teaching_cards_with_llm(paper_card, formula_cards, skeleton, evidence, llm_client=mock)

    assert len(bundle.teaching_cards) > 0
    # At least one card should have LLM-enhanced content
    enhanced = [c for c in bundle.teaching_cards if "重构误差" in c.human_explanation or "自动纠错" in c.analogy_explanation]
    assert len(enhanced) > 0


@pytest.mark.asyncio
async def test_llm_enhanced_teaching_cards_reject_hallucinated_refs() -> None:
    doc = _full_doc()
    paper_card, formula_cards, skeleton, evidence = _build_artifacts(doc)

    mock_response = '{"human_explanation": "test", "analogy_explanation": "test", "minimal_formula_explanation": "test", "numeric_example": "test", "paper_role_explanation": "test", "evidence_ref": "FAKE:ref"}'
    mock = MockLLMClient(response=mock_response)

    bundle = await build_teaching_cards_with_llm(paper_card, formula_cards, skeleton, evidence, llm_client=mock)

    # Hallucinated refs should be stripped
    for card in bundle.teaching_cards:
        for ref in card.evidence_refs:
            assert ref != "FAKE:ref"


@pytest.mark.asyncio
async def test_llm_enhanced_teaching_cards_fall_back_on_failure() -> None:
    doc = _full_doc()
    paper_card, formula_cards, skeleton, evidence = _build_artifacts(doc)

    mock = MockLLMClient(response="not valid json")

    bundle = await build_teaching_cards_with_llm(paper_card, formula_cards, skeleton, evidence, llm_client=mock)

    # Should fall back to rule-based
    assert len(bundle.teaching_cards) > 0
    # Rule-based fallback should have NEEDS_HUMAN_CHECK for analogy
    for card in bundle.teaching_cards:
        if card.target_type == "concept":
            assert card.analogy_explanation == "NEEDS_HUMAN_CHECK"


# ---------------------------------------------------------------------------
# Content quality tests (Phase 10 review fixes)
# ---------------------------------------------------------------------------


def test_concept_card_human_explanation_not_pure_formula() -> None:
    """When claim text is formula-heavy, human_explanation should not be the raw formula."""
    doc = _full_doc()
    paper_card, formula_cards, skeleton, evidence = _build_artifacts(doc)

    bundle = build_teaching_cards(paper_card, formula_cards, skeleton, evidence)

    concept_cards = [c for c in bundle.teaching_cards if c.target_type == "concept"]
    for card in concept_cards:
        # human_explanation should not be a pure formula like "L = L_rec + lambda L_graph"
        if "L =" in card.human_explanation or "\\lambda" in card.human_explanation:
            # If it contains formula, it should also have disclaimer text
            assert "需要进一步解释" in card.human_explanation or "NEEDS_HUMAN_CHECK" in card.human_explanation


def test_concept_card_formula_heavy_text_gets_degraded_confidence() -> None:
    """When claim text is formula-heavy, confidence should be reduced."""
    doc = _full_doc()
    paper_card, formula_cards, skeleton, evidence = _build_artifacts(doc)

    bundle = build_teaching_cards(paper_card, formula_cards, skeleton, evidence)

    concept_cards = [c for c in bundle.teaching_cards if c.target_type == "concept"]
    for card in concept_cards:
        if "FORMULA_HEAVY_TEXT_NEEDS_HUMAN_EXPLANATION" in card.warnings:
            assert card.confidence <= 0.3


def test_concept_card_formula_heavy_text_has_warning() -> None:
    """When claim text is formula-heavy, a warning should be added."""
    doc = _full_doc()
    paper_card, formula_cards, skeleton, evidence = _build_artifacts(doc)

    bundle = build_teaching_cards(paper_card, formula_cards, skeleton, evidence)

    concept_cards = [c for c in bundle.teaching_cards if c.target_type == "concept"]
    formula_heavy_cards = [c for c in concept_cards if "FORMULA_HEAVY_TEXT_NEEDS_HUMAN_EXPLANATION" in c.warnings]
    # At least one concept card should be detected as formula-heavy (core_idea/method_overview from method section)
    assert len(formula_heavy_cards) > 0


def test_formula_teaching_card_human_explanation_preserves_formula_text() -> None:
    """Formula teaching card should preserve formula text when plain_summary is UNKNOWN."""
    doc = _full_doc()
    paper_card, formula_cards, skeleton, evidence = _build_artifacts(doc)

    bundle = build_teaching_cards(paper_card, formula_cards, skeleton, evidence)

    formula_cards_list = [c for c in bundle.teaching_cards if c.target_type == "formula"]
    for card in formula_cards_list:
        # Should not be just "NEEDS_HUMAN_CHECK" - should have formula text or disclaimer
        if card.human_explanation == "NEEDS_HUMAN_CHECK":
            # This is only acceptable if there's no formula_raw at all
            assert "UNKNOWN" in card.minimal_formula_explanation


def test_paper_role_explanation_not_generic_template() -> None:
    """paper_role_explanation should not use the old generic template."""
    doc = _full_doc()
    paper_card, formula_cards, skeleton, evidence = _build_artifacts(doc)

    bundle = build_teaching_cards(paper_card, formula_cards, skeleton, evidence)

    generic_phrases = [
        "理解论文核心思想的关键",
        "论文提出的核心技术方案",
        "实验证明了方法的有效性",
        "公式定义了模型的数学形式",
    ]
    for card in bundle.teaching_cards:
        for phrase in generic_phrases:
            assert card.paper_role_explanation != phrase, f"Generic template found: {phrase}"


def test_paper_role_explanation_uses_specific_language() -> None:
    """paper_role_explanation should use specific language based on target_type."""
    doc = _full_doc()
    paper_card, formula_cards, skeleton, evidence = _build_artifacts(doc)

    bundle = build_teaching_cards(paper_card, formula_cards, skeleton, evidence)

    for card in bundle.teaching_cards:
        if card.paper_role_explanation != "NEEDS_HUMAN_CHECK":
            # Should contain type-specific language
            if card.target_type == "concept":
                assert "问题" in card.paper_role_explanation or "思路" in card.paper_role_explanation
            elif card.target_type == "method":
                assert "技术方案" in card.paper_role_explanation or "方法" in card.paper_role_explanation
            elif card.target_type == "formula":
                assert "公式" in card.paper_role_explanation or "数学" in card.paper_role_explanation or "位于" in card.paper_role_explanation


def test_all_teaching_cards_have_valid_evidence_refs() -> None:
    """All teaching cards must have valid evidence_refs after fixes."""
    doc = _full_doc()
    paper_card, formula_cards, skeleton, evidence = _build_artifacts(doc)

    bundle = build_teaching_cards(paper_card, formula_cards, skeleton, evidence)

    valid_refs = {claim.evidence_ref for claim in evidence.claims}
    for card in bundle.teaching_cards:
        for ref in card.evidence_refs:
            assert ref in valid_refs, f"Invalid ref: {ref}"


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


def test_teaching_cards_serializes_to_json() -> None:
    doc = _full_doc()
    paper_card, formula_cards, skeleton, evidence = _build_artifacts(doc)

    bundle = build_teaching_cards(paper_card, formula_cards, skeleton, evidence)
    json_str = bundle.model_dump_json()

    assert "paper-1" in json_str
    assert "teaching_cards" in json_str
    assert len(json_str) > 100
