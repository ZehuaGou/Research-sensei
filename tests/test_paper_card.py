from __future__ import annotations

import asyncio
from types import SimpleNamespace

from researchsensei.audit.quality_auditor import QualityAuditor
from researchsensei.ingestion.pipeline import _summarize_raw_copy_paper_card_fields
from researchsensei.paper_card import build_paper_card, summarize_paper_card_field
from researchsensei.schemas import ArtifactBundle, PaperSkeleton
from researchsensei.schemas.evidence import EvidencePack, EvidencePackItem


class RawCopyPaperCardLLM:
    def __init__(self, passage: str, *, evidence_ref: str = "paper:b001") -> None:
        self.passage = passage
        self.evidence_ref = evidence_ref

    async def chat_json(self, messages, *, config=None):
        return {
            "one_sentence_summary": "The paper studies F-SE-LSTM for time series anomaly detection.",
            "problem": {"text": self.passage, "evidence_ref": self.evidence_ref},
            "core_idea": {"text": self.passage, "evidence_ref": self.evidence_ref},
            "method_overview": {"text": self.passage, "evidence_ref": self.evidence_ref},
            "experiment_summary": {"text": self.passage, "evidence_ref": self.evidence_ref},
            "limitations": {"text": "INSUFFICIENT_EVIDENCE", "evidence_ref": ""},
        }


class FailingPaperCardLLM:
    async def chat_json(self, messages, *, config=None):
        raise TimeoutError("provider timed out")


def test_paper_card_summarizes_llm_raw_copy_fields() -> None:
    pack, skeleton, passage = _raw_copy_fixture()

    card = asyncio.run(build_paper_card(pack, skeleton, RawCopyPaperCardLLM(passage)))

    assert card.method_overview.evidence_ref == "paper:b001"
    assert card.method_overview.text != passage
    assert "PAPER_CARD_FIELD_SUMMARIZED_FROM_RAW_COPY: method_overview" in card.warnings
    assert "F-SE-LSTM" in card.method_overview.text
    report = QualityAuditor().audit(_audit_bundle(card, skeleton, passage))
    assert not [finding for finding in report.findings if finding.code == "F-8" and finding.effect == "BLOCK"]


def test_paper_card_summarizes_raw_copy_after_fallback_ref() -> None:
    pack, skeleton, passage = _raw_copy_fixture()

    card = asyncio.run(build_paper_card(pack, skeleton, RawCopyPaperCardLLM(passage, evidence_ref="")))

    assert card.method_overview.evidence_ref == "paper:b001"
    assert card.method_overview.text != passage
    assert "PAPER_CARD_FIELD_DEGRADED: method_overview" in card.warnings
    assert "PAPER_CARD_FIELD_SUMMARIZED_FROM_RAW_COPY: method_overview" in card.warnings


def test_paper_card_summarizes_supported_limitations_without_error() -> None:
    _pack, skeleton, passage = _raw_copy_fixture()
    summary = summarize_paper_card_field("limitations", passage, skeleton)

    assert "F-SE-LSTM" in summary
    assert summary.startswith("证据指向")


def test_pipeline_summarizes_raw_copy_before_quality_audit() -> None:
    pack, skeleton, passage = _raw_copy_fixture()
    card = asyncio.run(build_paper_card(pack, skeleton, RawCopyPaperCardLLM(passage)))
    raw_card = card.model_copy(update={
        "method_overview": card.method_overview.model_copy(update={"text": passage}),
    })
    claim_evidence = SimpleNamespace(
        claims=[
            SimpleNamespace(
                evidence_ref="paper:b001",
                quote_or_summary=passage,
                source_sentence=passage,
                claim_text=passage,
            )
        ]
    )

    updated = _summarize_raw_copy_paper_card_fields(
        {"paper_card": raw_card},
        claim_evidence,
        SimpleNamespace(claims=[]),
        skeleton,
    )

    assert updated["paper_card"].method_overview.text != passage
    assert "PAPER_CARD_FIELD_SUMMARIZED_FROM_RAW_COPY: method_overview" in updated["paper_card"].warnings
    report = QualityAuditor().audit(_audit_bundle(updated["paper_card"], skeleton, passage))
    assert not [finding for finding in report.findings if finding.code == "F-8" and finding.effect == "BLOCK"]


def test_fallback_does_not_attach_valid_ref_to_insufficient_placeholder() -> None:
    pack, skeleton, _passage = _raw_copy_fixture()
    skeleton = skeleton.model_copy(update={"problem": "INSUFFICIENT_EVIDENCE"})

    card = asyncio.run(build_paper_card(pack, skeleton, FailingPaperCardLLM()))

    assert card.problem.text == "证据不足，暂不展开。"
    assert card.problem.evidence_ref == ""
    assert card.problem.evidence_type.value == "INSUFFICIENT_EVIDENCE"


def _raw_copy_fixture() -> tuple[EvidencePack, PaperSkeleton, str]:
    passage = (
        "In order to detect hidden abnormal data more accurately, and improve the anomaly detection "
        "ability of time series, a time series anomaly detection method F-SE-LSTM based on frequency "
        "domain is proposed, which constructs frequency matrix data by FFT and extracts features by "
        "using SENet and LSTM."
    )
    pack = EvidencePack(
        paper_id="paper",
        items=[
            EvidencePackItem(
                claim_id="paper:claim:c001",
                claim_type="METHOD",
                evidence_ref="paper:b001",
                passage_id="paper:b001",
                quote_or_summary=passage,
                passage_text=passage,
                confidence=0.8,
                token_count=80,
            )
        ],
        total_tokens=80,
    )
    skeleton = PaperSkeleton(
        paper_id="paper",
        title="F-SE-LSTM: A Time Series Anomaly Detection Method with Frequency Domain Information",
        abstract_summary="A paper about time series anomaly detection.",
        method_overview=passage,
        experiment_overview=passage,
    )
    return pack, skeleton, passage


def _audit_bundle(card, skeleton: PaperSkeleton, passage: str) -> ArtifactBundle:
    return ArtifactBundle(
        paper_card=card.model_dump(mode="json"),
        claim_evidence={
            "claims": [
                {
                    "claim_id": "paper:claim:c001",
                    "claim_type": "METHOD",
                    "evidence_ref": "paper:b001",
                    "passage_id": "paper:b001",
                    "quote_or_summary": passage,
                    "source_sentence": passage,
                    "claim_text": passage,
                }
            ]
        },
        evidence_index={"paper_id": "paper", "claims": []},
        paper_skeleton=skeleton.model_dump(mode="json"),
    )
