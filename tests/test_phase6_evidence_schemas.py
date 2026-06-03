from __future__ import annotations

import pytest
from pydantic import ValidationError

from researchsensei.schemas import (
    ClaimEvidence,
    EvidenceIndex,
    EvidenceType,
    PaperSkeleton,
)


def test_claim_evidence_serializes_and_validates_confidence() -> None:
    claim = ClaimEvidence(
        claim_id="c-abstract-001",
        claim_text="This claim is grounded in the abstract block.",
        evidence_type=EvidenceType.SUPPORTED_BY_TEXT,
        evidence_ref="paper-1:b001",
        block_id="b001",
        section="abstract",
        quote_or_summary="We study anomaly detection.",
        confidence=0.7,
    )

    restored = ClaimEvidence.model_validate_json(claim.model_dump_json())

    assert restored.evidence_ref == "paper-1:b001"
    assert restored.confidence == 0.7


def test_claim_evidence_rejects_confidence_outside_zero_to_one() -> None:
    with pytest.raises(ValidationError):
        ClaimEvidence(
            claim_id="c-bad",
            claim_text="Bad confidence.",
            evidence_type=EvidenceType.UNVERIFIED,
            evidence_ref="paper-1:b001",
            block_id="b001",
            section="abstract",
            quote_or_summary="Bad confidence.",
            confidence=1.2,
        )


def test_evidence_index_round_trips_with_supported_experiment_type() -> None:
    index = EvidenceIndex(
        paper_id="paper-1",
        claims=[
            ClaimEvidence(
                claim_id="c-exp-001",
                claim_text="This block belongs to an experiments section.",
                evidence_type=EvidenceType.SUPPORTED_BY_EXPERIMENT,
                evidence_ref="paper-1:b003",
                block_id="b003",
                section="experiments",
                quote_or_summary="Table 1 reports F1.",
                confidence=0.65,
            )
        ],
    )

    restored = EvidenceIndex.model_validate_json(index.model_dump_json())

    assert restored.claims[0].evidence_type == EvidenceType.SUPPORTED_BY_EXPERIMENT


def test_paper_skeleton_allows_conservative_unknown_fields() -> None:
    skeleton = PaperSkeleton(
        paper_id="paper-1",
        title="Tiny Paper",
        abstract_summary="UNKNOWN",
        problem="INSUFFICIENT_EVIDENCE",
        method_overview="UNKNOWN",
        experiment_overview="UNKNOWN",
        formulas=[],
        limitations="NEEDS_HUMAN_CHECK",
        evidence_refs=[],
        confidence=0.2,
        warnings=["METHOD_SECTION_MISSING"],
    )

    restored = PaperSkeleton.model_validate_json(skeleton.model_dump_json())

    assert restored.problem == "INSUFFICIENT_EVIDENCE"
    assert restored.confidence == 0.2


def test_paper_skeleton_rejects_high_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        PaperSkeleton(
            paper_id="paper-1",
            title="Tiny Paper",
            abstract_summary="UNKNOWN",
            problem="UNKNOWN",
            method_overview="UNKNOWN",
            experiment_overview="UNKNOWN",
            formulas=[],
            limitations="UNKNOWN",
            evidence_refs=[],
            confidence=2.0,
            warnings=[],
        )
