"""P0 Quality Tests: Anti-hallucination.

Checks that the system does not fabricate results, datasets,
or formulas when the input paper lacks them.
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

FABRICATED_RESULT_WORDS = {"accuracy", "f1-score", "f1 score", "sota", "state-of-the-art"}
FABRICATED_DATASETS = {"imagenet", "cifar-10", "cifar-100", "coco", "mnist"}


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


def _card_text_lower(paper_card, teaching_cards) -> str:
    """Collect all text from paper_card and teaching_cards."""
    parts = []
    # PaperCard has individual CardClaim fields
    for claim in [paper_card.problem, paper_card.core_idea, paper_card.method_overview,
                  paper_card.bottleneck, paper_card.experiment_summary, paper_card.limitations]:
        parts.append(claim.text.lower())
    for claim in paper_card.old_methods:
        parts.append(claim.text.lower())
    for tc in teaching_cards.teaching_cards:
        parts.append(tc.human_explanation.lower())
        parts.append(tc.analogy_explanation.lower())
        parts.append(tc.minimal_formula_explanation.lower())
    return " ".join(parts)


def test_minimal_paper_does_not_fabricate_results() -> None:
    """Minimal paper must not contain fabricated accuracy/SOTA claims."""
    data = _build_from_fixture("fixture_minimal.md")
    text = _card_text_lower(data["paper_card"], data["teaching_cards"])
    for word in FABRICATED_RESULT_WORDS:
        assert word not in text, (
            f"Minimal paper contains '{word}' which is likely fabricated"
        )


def test_minimal_paper_does_not_fabricate_datasets() -> None:
    """Minimal paper must not mention datasets not in the input."""
    data = _build_from_fixture("fixture_minimal.md")
    text = _card_text_lower(data["paper_card"], data["teaching_cards"])
    for ds in FABRICATED_DATASETS:
        assert ds not in text, (
            f"Minimal paper contains dataset '{ds}' which is not in input"
        )


def test_minimal_paper_no_formula_cards() -> None:
    """Minimal paper (no formulas) should not generate formula cards."""
    data = _build_from_fixture("fixture_minimal.md")
    formula_cards = data["formula_cards"]
    assert len(formula_cards.formula_cards) == 0 or all(
        fc.formula_raw == "" or fc.formula_raw == "UNKNOWN"
        for fc in formula_cards.formula_cards
    ), "Minimal paper should not have real formula cards"


def test_formula_heavy_paper_does_not_copy_formula_as_explanation() -> None:
    """Formula-heavy paper: human_explanation must not be raw formula text."""
    data = _build_from_fixture("fixture_formula_heavy.md")
    teaching_cards = data["teaching_cards"]
    for tc in teaching_cards.teaching_cards:
        explanation = tc.human_explanation
        if not explanation or explanation in ("UNKNOWN", "NEEDS_HUMAN_CHECK"):
            continue
        # Check that explanation is not dominated by formula characters
        formula_chars = sum(1 for c in explanation if c in "=+−*/^_{}[]()\\")
        if len(explanation) > 10:
            formula_ratio = formula_chars / len(explanation)
            assert formula_ratio < 0.3, (
                f"human_explanation is likely formula text (ratio={formula_ratio:.2f}): "
                f"{explanation[:80]}..."
            )


def test_minimal_paper_has_warnings() -> None:
    """Minimal paper should have degradation warnings."""
    data = _build_from_fixture("fixture_minimal.md")
    all_warnings = []
    all_warnings.extend(data["paper_card"].warnings)
    all_warnings.extend(data["formula_cards"].warnings)
    all_warnings.extend(data["teaching_cards"].warnings)
    assert len(all_warnings) > 0, "Minimal paper should have warnings"
