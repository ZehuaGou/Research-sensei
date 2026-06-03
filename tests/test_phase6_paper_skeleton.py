from __future__ import annotations

from researchsensei.grounding import build_evidence_index
from researchsensei.paper_skeleton import build_paper_skeleton
from researchsensei.schemas import BlockType, DocumentBlock, DocumentIngestion


def _block(
    block_id: str,
    block_type: BlockType,
    section: str,
    text: str,
    paper_id: str = "paper-1",
) -> DocumentBlock:
    return DocumentBlock(
        block_id=block_id,
        type=block_type,
        section=section,
        text=text,
        evidence_ref=f"{paper_id}:{block_id}",
    )


def test_build_paper_skeleton_uses_only_grounded_blocks() -> None:
    doc = DocumentIngestion(
        paper_id="paper-1",
        blocks=[
            _block("t001", BlockType.TITLE, "title", "Tiny TSAD Paper"),
            _block("b001", BlockType.ABSTRACT, "abstract", "We study anomaly detection in time series."),
            _block("b002", BlockType.PARAGRAPH, "introduction", "Current methods miss sensor dependencies."),
            _block("b003", BlockType.PARAGRAPH, "method", "We model dependencies with reconstruction error."),
            _block("eq001", BlockType.FORMULA, "method", "L = L_rec + lambda L_graph"),
            _block("b004", BlockType.PARAGRAPH, "experiments", "Table 1 reports F1 on benchmark datasets."),
        ],
    )
    evidence = build_evidence_index(doc)

    skeleton = build_paper_skeleton(doc, evidence)

    assert skeleton.title == "Tiny TSAD Paper"
    assert skeleton.abstract_summary == "We study anomaly detection in time series."
    assert skeleton.problem == "Current methods miss sensor dependencies."
    assert skeleton.method_overview == "We model dependencies with reconstruction error."
    assert skeleton.experiment_overview == "Table 1 reports F1 on benchmark datasets."
    assert skeleton.formulas == ["L = L_rec + lambda L_graph"]
    assert skeleton.limitations == "NEEDS_HUMAN_CHECK"
    assert "LIMITATIONS_SECTION_MISSING" in skeleton.warnings
    assert skeleton.confidence <= 0.7
    assert all(ref.startswith("paper-1:") for ref in skeleton.evidence_refs)


def test_abstract_only_skeleton_stays_degraded_and_low_confidence() -> None:
    doc = DocumentIngestion(
        paper_id="paper-abstract",
        blocks=[
            _block(
                "b001",
                BlockType.ABSTRACT,
                "abstract",
                "We propose a method, but this parsed fixture has no method or experiments section.",
                paper_id="paper-abstract",
            )
        ],
    )
    evidence = build_evidence_index(doc)

    skeleton = build_paper_skeleton(doc, evidence)

    assert skeleton.abstract_summary.startswith("We propose a method")
    assert skeleton.problem == "INSUFFICIENT_EVIDENCE"
    assert skeleton.method_overview == "INSUFFICIENT_EVIDENCE"
    assert skeleton.experiment_overview == "INSUFFICIENT_EVIDENCE"
    assert skeleton.formulas == []
    assert skeleton.confidence <= 0.3
    assert "METHOD_SECTION_MISSING" in skeleton.warnings
    assert "EXPERIMENT_SECTION_MISSING" in skeleton.warnings
    assert "FORMULA_UNAVAILABLE" in skeleton.warnings
