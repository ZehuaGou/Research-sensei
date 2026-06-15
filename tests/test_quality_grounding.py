"""P0 Quality Tests: Evidence grounding.

Checks that all card evidence_refs exist in evidence_index,
core claims have evidence_ref, and missing evidence triggers degradation.
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
    """Build all artifacts from a fixture markdown file."""
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


def _collect_valid_block_ids(evidence_index) -> set[str]:
    """Collect all block_ids referenced in evidence_index."""
    ids: set[str] = set()
    for ev in evidence_index.claims:
        if ev.evidence_ref:
            parts = ev.evidence_ref.split(":", 1)
            if len(parts) == 2:
                ids.add(parts[1])
    return ids


def _collect_card_evidence_refs(paper_card, formula_cards, teaching_cards) -> list[str]:
    """Collect all evidence_refs from all cards."""
    refs: list[str] = []
    # PaperCard has individual CardClaim fields
    for claim in [paper_card.problem, paper_card.core_idea, paper_card.method_overview,
                  paper_card.bottleneck, paper_card.experiment_summary, paper_card.limitations]:
        if claim.evidence_ref:
            refs.append(claim.evidence_ref)
    for claim in paper_card.old_methods:
        if claim.evidence_ref:
            refs.append(claim.evidence_ref)
    for claim in paper_card.key_formulas:
        if claim.evidence_ref:
            refs.append(claim.evidence_ref)
    # FormulaCardBundle uses formula_cards field
    for fc in formula_cards.formula_cards:
        if fc.evidence_ref:
            refs.append(fc.evidence_ref)
    # TeachingCardBundle
    for tc in teaching_cards.teaching_cards:
        for ref in tc.evidence_refs:
            if ref:
                refs.append(ref)
    return refs


def test_all_evidence_refs_exist_in_index() -> None:
    """Every evidence_ref in cards must reference a block that exists."""
    data = _build_from_fixture("fixture_method_paper.md")
    valid_block_ids = _collect_valid_block_ids(data["evidence_index"])
    card_refs = _collect_card_evidence_refs(
        data["paper_card"], data["formula_cards"], data["teaching_cards"]
    )
    for ref in card_refs:
        parts = ref.split(":", 1)
        if len(parts) == 2:
            block_id = parts[1]
            assert block_id in valid_block_ids, (
                f"evidence_ref '{ref}' references non-existent block '{block_id}'"
            )


def test_core_claims_have_evidence_ref() -> None:
    """paper_card core_idea and problem must have evidence_ref or be degraded."""
    data = _build_from_fixture("fixture_method_paper.md")
    pc = data["paper_card"]
    for claim in [pc.core_idea, pc.problem]:
        has_ref = bool(claim.evidence_ref)
        is_degraded = claim.evidence_type.value in (
            "INSUFFICIENT_EVIDENCE",
            "UNVERIFIED",
            "NEEDS_HUMAN_CHECK",
        )
        assert has_ref or is_degraded, (
            f"Claim has no evidence_ref and is not degraded: "
            f"evidence_type={claim.evidence_type}"
        )


def test_minimal_paper_has_degraded_claims() -> None:
    """Minimal paper (abstract only) must degrade claims."""
    data = _build_from_fixture("fixture_minimal.md")
    pc = data["paper_card"]
    all_claims = [pc.problem, pc.core_idea, pc.method_overview, pc.experiment_summary, pc.limitations]
    all_claims.extend(pc.old_methods)
    degraded_count = sum(
        1 for c in all_claims
        if c.evidence_type.value in ("INSUFFICIENT_EVIDENCE", "UNVERIFIED", "NEEDS_HUMAN_CHECK")
    )
    assert degraded_count > 0, "Minimal paper should have degraded claims"


def test_evidence_ref_format_stable() -> None:
    """Evidence refs must follow paper_id:block_id format."""
    data = _build_from_fixture("fixture_method_paper.md")
    card_refs = _collect_card_evidence_refs(
        data["paper_card"], data["formula_cards"], data["teaching_cards"]
    )
    for ref in card_refs:
        if ref:
            assert ":" in ref, f"evidence_ref '{ref}' missing colon separator"
