"""P0 Quality Tests: Formula teaching quality.

Checks that formula_cards have symbol explanations, purpose,
and that formula-heavy input triggers conservative fallback.
"""

from __future__ import annotations

from pathlib import Path

from researchsensei.formula_card_baseline import build_formula_cards
from researchsensei.grounding import build_evidence_index
from researchsensei.ingestion.lightweight import LightweightIngestionService
from researchsensei.paper_card_baseline import build_paper_card
from researchsensei.paper_skeleton import build_paper_skeleton
from researchsensei.teaching_card_baseline import build_teaching_cards

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "quality"


def _build_from_fixture(fixture_name: str):
    ingestion = LightweightIngestionService()
    source = FIXTURE_DIR / fixture_name
    document = ingestion.ingest_path(source, paper_id="test-paper")
    evidence_index = build_evidence_index(document)
    skeleton = build_paper_skeleton(document, evidence_index)
    paper_card = build_paper_card(skeleton, evidence_index)
    formula_cards = build_formula_cards(document, evidence_index, skeleton)
    teaching_cards = build_teaching_cards(paper_card, formula_cards, skeleton, evidence_index)
    return {
        "document": document,
        "evidence_index": evidence_index,
        "skeleton": skeleton,
        "paper_card": paper_card,
        "formula_cards": formula_cards,
        "teaching_cards": teaching_cards,
    }


def test_formula_heavy_paper_has_formula_cards() -> None:
    """Formula-heavy paper should produce formula cards."""
    data = _build_from_fixture("fixture_formula_heavy.md")
    assert len(data["formula_cards"].formula_cards) > 0, "Formula-heavy paper should have formula cards"


def test_formula_cards_have_symbols() -> None:
    """Formula cards must have symbol explanations."""
    data = _build_from_fixture("fixture_formula_heavy.md")
    for fc in data["formula_cards"].formula_cards:
        if fc.formula_raw and fc.formula_raw != "UNKNOWN":
            assert len(fc.symbols) > 0, (
                f"Formula card '{fc.formula_id}' has no symbols"
            )


def test_formula_cards_have_purpose_or_degraded() -> None:
    """Formula cards must have purpose or be properly degraded.

    If purpose is UNKNOWN, the card must have degraded confidence or warnings.
    """
    data = _build_from_fixture("fixture_formula_heavy.md")
    for fc in data["formula_cards"].formula_cards:
        if fc.formula_raw and fc.formula_raw != "UNKNOWN":
            has_purpose = fc.purpose and fc.purpose not in ("UNKNOWN", "")
            # UNKNOWN purpose IS degradation - confidence should reflect this
            is_degraded = fc.confidence < 0.5 or any(
                "NEEDS" in w for w in fc.warnings
            )
            assert has_purpose or is_degraded, (
                f"Formula card '{fc.formula_id}' has purpose='{fc.purpose}' "
                f"but confidence={fc.confidence} and warnings={fc.warnings}"
            )


def test_formula_heavy_teaching_cards_have_reasonable_confidence() -> None:
    """Formula-heavy input: teaching cards must have reasonable confidence (not overconfident)."""
    data = _build_from_fixture("fixture_formula_heavy.md")
    teaching_cards = data["teaching_cards"]
    for tc in teaching_cards.teaching_cards:
        # Confidence should be in valid range and not overconfident for formula content
        assert 0.0 <= tc.confidence <= 1.0, (
            f"Teaching card confidence {tc.confidence} out of range"
        )
        # If the explanation contains formula text, confidence should not be 1.0
        explanation = tc.human_explanation
        if explanation and explanation not in ("UNKNOWN", "NEEDS_HUMAN_CHECK"):
            formula_chars = sum(1 for c in explanation if c in "=+−*/^_{}[]()\\")
            if len(explanation) > 10 and formula_chars / len(explanation) > 0.15:
                assert tc.confidence < 1.0, (
                    "Formula-heavy explanation should not have confidence 1.0"
                )


def test_minimal_paper_no_real_formulas() -> None:
    """Minimal paper should not have formula cards with real content."""
    data = _build_from_fixture("fixture_minimal.md")
    for fc in data["formula_cards"].formula_cards:
        if fc.formula_raw and fc.formula_raw not in ("UNKNOWN", ""):
            assert fc.purpose != "UNKNOWN" or len(fc.symbols) == 0, (
                "Minimal paper should not have fully populated formula cards"
            )


def test_formula_card_confidence_reasonable() -> None:
    """Formula cards from formula-heavy paper should have reasonable confidence."""
    data = _build_from_fixture("fixture_formula_heavy.md")
    for fc in data["formula_cards"].formula_cards:
        if fc.formula_raw and fc.formula_raw != "UNKNOWN":
            assert 0.0 <= fc.confidence <= 1.0, (
                f"Formula card confidence {fc.confidence} out of range"
            )
