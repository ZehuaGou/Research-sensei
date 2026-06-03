from __future__ import annotations

from researchsensei.grounding import build_evidence_index
from researchsensei.schemas import BlockType, DocumentBlock, DocumentIngestion, EvidenceType


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


def test_build_evidence_index_extracts_safe_block_level_claims() -> None:
    doc = DocumentIngestion(
        paper_id="paper-1",
        blocks=[
            _block("t001", BlockType.TITLE, "title", "Tiny TSAD Paper"),
            _block("b001", BlockType.ABSTRACT, "abstract", "We study anomaly detection in time series."),
            _block("b002", BlockType.PARAGRAPH, "method", "We model dependencies with reconstruction error."),
            _block("eq001", BlockType.FORMULA, "method", "L = L_rec + lambda L_graph"),
            _block("b003", BlockType.PARAGRAPH, "experiments", "Table 1 reports F1 on benchmark datasets."),
            _block("tbl001", BlockType.TABLE, "experiments", "Dataset F1"),
            _block("fig001", BlockType.FIGURE, "method", "Model architecture overview."),
        ],
    )

    index = build_evidence_index(doc)
    claims_by_id = {claim.claim_id: claim for claim in index.claims}
    block_ids = {block.block_id for block in doc.blocks}

    assert claims_by_id["paper-1-abstract-b001"].evidence_type == EvidenceType.SUPPORTED_BY_TEXT
    assert claims_by_id["paper-1-formula-eq001"].evidence_type == EvidenceType.SUPPORTED_BY_FORMULA
    assert claims_by_id["paper-1-experiment-b003"].evidence_type == EvidenceType.SUPPORTED_BY_EXPERIMENT
    assert claims_by_id["paper-1-table-tbl001"].evidence_type == EvidenceType.NEEDS_HUMAN_CHECK
    assert claims_by_id["paper-1-figure-fig001"].evidence_type == EvidenceType.NEEDS_HUMAN_CHECK
    assert all(claim.block_id in block_ids for claim in index.claims)
    assert all(claim.evidence_ref.endswith(f":{claim.block_id}") for claim in index.claims)


def test_abstract_only_input_marks_missing_sections_as_low_confidence() -> None:
    doc = DocumentIngestion(
        paper_id="paper-abstract",
        blocks=[
            _block(
                "b001",
                BlockType.ABSTRACT,
                "abstract",
                "We introduce a method, but this fixture has no full method or experiments section.",
                paper_id="paper-abstract",
            )
        ],
    )

    index = build_evidence_index(doc)
    missing_claims = [
        claim
        for claim in index.claims
        if claim.evidence_type
        in {
            EvidenceType.INSUFFICIENT_EVIDENCE,
            EvidenceType.NEEDS_HUMAN_CHECK,
            EvidenceType.UNVERIFIED,
        }
    ]

    assert any(claim.claim_id == "paper-abstract-missing-method" for claim in missing_claims)
    assert any(claim.claim_id == "paper-abstract-missing-experiments" for claim in missing_claims)
    assert any(claim.claim_id == "paper-abstract-missing-formulas" for claim in missing_claims)
    assert all(claim.confidence <= 0.5 for claim in missing_claims)
    assert all(claim.block_id == "b001" for claim in missing_claims)
