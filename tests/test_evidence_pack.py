from __future__ import annotations

from researchsensei.evidence.evidence_pack import build_evidence_pack
from researchsensei.schemas import EvidenceType
from researchsensei.schemas.evidence import (
    ClaimEvidenceBundle,
    ClaimEvidenceV2,
    Passage,
    PassageIndex,
)


def _claim(idx: int, *, formula_id: str, text: str) -> ClaimEvidenceV2:
    return ClaimEvidenceV2(
        claim_id=f"paper:claim:c{idx:03d}",
        claim_text=text,
        evidence_ref=f"paper:b{idx:04d}",
        block_id=f"b{idx:04d}",
        passage_id=f"p{idx:03d}",
        section="method",
        claim_type="FORMULA_CONTEXT",
        semantic_support=EvidenceType.SUPPORTED_BY_FORMULA.value,
        source_sentence=text,
        quote_or_summary=text,
        confidence=0.6,
        formula_origin="mineru_latex",
        formula_id=formula_id,
        formula_ocr_status="not_required",
    )


def _passage(idx: int, text: str) -> Passage:
    return Passage(
        passage_id=f"p{idx:03d}",
        paper_id="paper",
        block_ids=[f"b{idx:04d}"],
        section="method",
        text=text,
        normalized_text=text.lower(),
        token_count=len(text.split()),
        evidence_refs=[f"paper:b{idx:04d}"],
    )


def test_evidence_pack_selects_core_formula_contexts_not_first_seen() -> None:
    texts = [
        "Shape definition h_i in R^d for EdgeConv input.",
        "Minor where clause defining dimensions.",
        "Another dimensionality helper formula.",
        "Attention(Q,K,V) softmax formula used by the Transformer module.",
        "Loss function L_MSE optimizes reconstruction error.",
        "Final anomaly score A_t aggregates sensor-wise anomaly scores.",
        "Time2Vec t2v embedding formula encodes temporal behavior.",
        r"Formula: w h e r e \quad H_i = Attention(Q_i,K_i,V_i). Context before: Transformer details.",
    ]
    claim_bundle = ClaimEvidenceBundle(
        paper_id="paper",
        claims=[
            _claim(i + 1, formula_id=f"formula_{i + 1:03d}", text=text)
            for i, text in enumerate(texts)
        ],
    )
    passage_index = PassageIndex(
        paper_id="paper",
        passages=[_passage(i + 1, text) for i, text in enumerate(texts)],
    )

    pack = build_evidence_pack(claim_bundle, passage_index)
    formula_ids = [
        item.formula_id for item in pack.items
        if item.claim_type == "FORMULA_CONTEXT"
    ]

    assert len(formula_ids) == 5
    assert "formula_004" in formula_ids
    assert "formula_005" in formula_ids
    assert "formula_006" in formula_ids
    assert "formula_007" in formula_ids
    assert "formula_002" not in formula_ids
    assert "formula_003" not in formula_ids
    assert "formula_008" not in formula_ids
