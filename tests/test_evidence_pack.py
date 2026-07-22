from __future__ import annotations

from researchsensei.evidence.evidence_pack import build_evidence_pack
from researchsensei.schemas import EvidenceType
from researchsensei.schemas.evidence import (
    ClaimEvidenceBundle,
    ClaimEvidenceRecord,
    Passage,
    PassageIndex,
)


def _claim(idx: int, *, formula_id: str, text: str) -> ClaimEvidenceRecord:
    return ClaimEvidenceRecord(
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


def _method_claim(idx: int, text: str) -> ClaimEvidenceRecord:
    return ClaimEvidenceRecord(
        claim_id=f"paper:claim:m{idx:03d}",
        claim_text=text,
        evidence_ref=f"paper:m{idx:04d}",
        block_id=f"m{idx:04d}",
        passage_id=f"pm{idx:03d}",
        section="method",
        claim_type="METHOD",
        semantic_support=EvidenceType.SUPPORTED_BY_TEXT.value,
        source_sentence=text,
        quote_or_summary=text,
        confidence=0.7,
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


def _method_passage(idx: int, text: str) -> Passage:
    return Passage(
        passage_id=f"pm{idx:03d}",
        paper_id="paper",
        block_ids=[f"m{idx:04d}"],
        section="method",
        text=text,
        normalized_text=text.lower(),
        token_count=len(text.split()),
        evidence_refs=[f"paper:m{idx:04d}"],
    )


def test_formula_evidence_pack_includes_neighboring_formula_context() -> None:
    formula_text = r"h_q(f) = \frac{1}{q^2}\begin{bmatrix}1&1\\1&1\end{bmatrix}"
    claim_bundle = ClaimEvidenceBundle(
        paper_id="paper",
        claims=[
            ClaimEvidenceRecord(
                claim_id="paper:claim:c001",
                claim_text=formula_text,
                evidence_ref="paper:eq001",
                block_id="eq001",
                passage_id="p002",
                section="sr",
                claim_type="FORMULA_CONTEXT",
                semantic_support=EvidenceType.SUPPORTED_BY_FORMULA.value,
                source_sentence=formula_text,
                quote_or_summary=formula_text,
                confidence=0.7,
                formula_origin="source_latex",
                formula_id="source_latex_formula_002",
                formula_ocr_status="not_required",
            )
        ],
    )
    passage_index = PassageIndex(
        paper_id="paper",
        passages=[
            Passage(
                passage_id="p001",
                paper_id="paper",
                block_ids=["b001"],
                section="sr",
                text="AL(f) is the average spectrum of L(f), approximated by convoluting L(f) with h_q(f).",
                source_block_types=["paragraph"],
                evidence_refs=["paper:b001"],
            ),
            Passage(
                passage_id="p002",
                paper_id="paper",
                block_ids=["eq001"],
                section="sr",
                text=formula_text,
                source_block_types=["formula"],
                evidence_refs=["paper:eq001"],
                formula_ids=["source_latex_formula_002"],
                formula_origins=["source_latex"],
            ),
            Passage(
                passage_id="p003",
                paper_id="paper",
                block_ids=["b002"],
                section="sr",
                text="R(f) subtracts the averaged log spectrum AL(f), making the innovation part more significant.",
                source_block_types=["paragraph"],
                evidence_refs=["paper:b002"],
            ),
        ],
    )

    pack = build_evidence_pack(
        claim_bundle,
        passage_index,
        None,
        max_items_per_type=0,
        max_formula_items=1,
        max_passage_chars=1200,
    )

    item = pack.items[0]
    assert item.passage_text.startswith("Formula source_latex_formula_002. Origin: source_latex.")
    assert "Formula:" in item.passage_text
    assert "Context before:" in item.passage_text
    assert "average spectrum of L(f)" in item.passage_text
    assert "Context after:" in item.passage_text
    assert "innovation part" in item.passage_text


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


def test_evidence_pack_retains_method_claim_before_formula_budget() -> None:
    method_text = "Our method introduces a neural architecture for anomaly detection."
    formula_texts = [
        f"Formula: L_{idx} = x_{idx} + y_{idx}. Context before: method details."
        for idx in range(1, 8)
    ]
    claim_bundle = ClaimEvidenceBundle(
        paper_id="paper",
        claims=[
            _method_claim(1, method_text),
            *[
                _claim(idx + 1, formula_id=f"formula_{idx + 1:03d}", text=text)
                for idx, text in enumerate(formula_texts)
            ],
        ],
    )
    passage_index = PassageIndex(
        paper_id="paper",
        passages=[
            _method_passage(1, method_text),
            *[_passage(idx + 1, text) for idx, text in enumerate(formula_texts)],
        ],
    )

    pack = build_evidence_pack(claim_bundle, passage_index)

    assert pack.items[0].claim_type == "METHOD"
    assert any(item.claim_type == "METHOD" for item in pack.items)


def test_evidence_pack_keeps_enough_prose_for_card_generation_by_default() -> None:
    passage_text = "We present a semiautomated root analysis toolbox. " + ("Detailed method context. " * 45)
    claim_bundle = ClaimEvidenceBundle(
        paper_id="paper",
        claims=[_method_claim(1, "We present a semiautomated root analysis toolbox.")],
    )
    passage_index = PassageIndex(
        paper_id="paper",
        passages=[_method_passage(1, passage_text)],
    )

    pack = build_evidence_pack(claim_bundle, passage_index)

    assert len(pack.items[0].passage_text) > 500
    assert len(pack.items[0].passage_text) <= 1200
