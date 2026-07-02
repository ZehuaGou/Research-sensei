from __future__ import annotations

import asyncio
from types import SimpleNamespace

from researchsensei.ingestion.pipeline import _summarize_raw_copy_paper_card_fields
from researchsensei.paper_card import build_paper_card
from researchsensei.schemas import PaperSkeleton
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


def test_paper_card_summarizes_llm_raw_copy_fields() -> None:
    pack, skeleton, passage = _raw_copy_fixture()

    card = asyncio.run(build_paper_card(pack, skeleton, RawCopyPaperCardLLM(passage)))

    assert card.method_overview.evidence_ref == "paper:b001"
    assert card.method_overview.text != passage
    assert "PAPER_CARD_FIELD_SUMMARIZED_FROM_RAW_COPY: method_overview" in card.warnings
    assert "F-SE-LSTM" in card.method_overview.text


def test_paper_card_summarizes_raw_copy_after_fallback_ref() -> None:
    pack, skeleton, passage = _raw_copy_fixture()

    card = asyncio.run(build_paper_card(pack, skeleton, RawCopyPaperCardLLM(passage, evidence_ref="")))

    assert card.method_overview.evidence_ref == "paper:b001"
    assert card.method_overview.text != passage
    assert "PAPER_CARD_FIELD_DEGRADED: method_overview" in card.warnings
    assert "PAPER_CARD_FIELD_SUMMARIZED_FROM_RAW_COPY: method_overview" in card.warnings


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
