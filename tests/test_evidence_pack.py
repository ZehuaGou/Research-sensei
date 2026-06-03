from __future__ import annotations

from pathlib import Path

from researchsensei.evidence.evidence_pack import build_evidence_pack
from researchsensei.evidence.retriever import EvidenceRetriever
from researchsensei.schemas import (
    ClaimEvidenceBundle,
    ClaimEvidenceV2,
    EvidencePack,
    EvidencePackItem,
    EvidenceRetrievalResult,
    Passage,
    PassageIndex,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_claim(
    claim_id: str,
    claim_type: str,
    passage_id: str,
    claim_text: str = "test claim",
    semantic_support: str = "DIRECT_QUOTE",
    confidence: float = 0.7,
    evidence_ref: str = "test:b001",
) -> ClaimEvidenceV2:
    return ClaimEvidenceV2(
        claim_id=claim_id,
        claim_text=claim_text,
        evidence_ref=evidence_ref,
        block_id="b001",
        passage_id=passage_id,
        claim_type=claim_type,
        semantic_support=semantic_support,
        source_sentence=claim_text,
        quote_or_summary=claim_text[:240],
        confidence=confidence,
    )


def _make_passage(passage_id: str, text: str, evidence_ref: str = "test:b001") -> Passage:
    return Passage(
        passage_id=passage_id,
        paper_id="test",
        text=text,
        normalized_text=text.lower(),
        token_count=len(text.split()),
        evidence_refs=[evidence_ref] if evidence_ref else [],
    )


def _make_bundle(claims: list[ClaimEvidenceV2]) -> ClaimEvidenceBundle:
    return ClaimEvidenceBundle(paper_id="test", claims=claims)


def _make_index(passages: list[Passage]) -> PassageIndex:
    return PassageIndex(paper_id="test", passages=passages)


class FakeRetriever:
    """Fake retriever that returns preset results."""
    def __init__(self, results: list[EvidenceRetrievalResult]) -> None:
        self._results = results

    def retrieve(self, query: str, passage_index: PassageIndex) -> list[EvidenceRetrievalResult]:
        return self._results


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_evidence_pack_item_round_trip() -> None:
    item = EvidencePackItem(
        claim_id="c001",
        claim_type="METHOD",
        evidence_ref="test:b001",
        passage_id="p001",
        quote_or_summary="We propose a model.",
        passage_text="We propose a graph neural network for anomaly detection.",
        confidence=0.7,
        retrieval_score=1.5,
        token_count=9,
    )

    json_str = item.model_dump_json()
    restored = EvidencePackItem.model_validate_json(json_str)

    assert restored.claim_id == "c001"
    assert restored.claim_type == "METHOD"
    assert restored.retrieval_score == 1.5
    assert restored.token_count == 9


def test_evidence_pack_round_trip() -> None:
    item = EvidencePackItem(
        claim_id="c001", claim_type="METHOD", evidence_ref="test:b001",
        passage_text="Test.", confidence=0.5,
    )
    pack = EvidencePack(paper_id="test", items=[item], total_tokens=1)

    json_str = pack.model_dump_json()
    restored = EvidencePack.model_validate_json(json_str)

    assert restored.paper_id == "test"
    assert len(restored.items) == 1
    assert restored.total_tokens == 1


# ---------------------------------------------------------------------------
# Filtering tests
# ---------------------------------------------------------------------------


def test_filters_insufficient_evidence() -> None:
    claim = _make_claim("c001", "METHOD", "p001", semantic_support="INSUFFICIENT_EVIDENCE")
    bundle = _make_bundle([claim])
    index = _make_index([_make_passage("p001", "We propose a model.")])

    pack = build_evidence_pack(bundle, index)

    assert len(pack.items) == 0


def test_filters_low_confidence() -> None:
    claim = _make_claim("c001", "METHOD", "p001", confidence=0.2)
    bundle = _make_bundle([claim])
    index = _make_index([_make_passage("p001", "We propose a model.")])

    pack = build_evidence_pack(bundle, index)

    assert len(pack.items) == 0


def test_filters_empty_claim_type() -> None:
    claim = _make_claim("c001", "", "p001")
    bundle = _make_bundle([claim])
    index = _make_index([_make_passage("p001", "We propose a model.")])

    pack = build_evidence_pack(bundle, index)

    assert len(pack.items) == 0


# ---------------------------------------------------------------------------
# Grouping / ordering tests
# ---------------------------------------------------------------------------


def test_limits_items_per_type() -> None:
    claims = [
        _make_claim(f"c{i}", "METHOD", f"p{i}", claim_text=f"Method claim {i}.")
        for i in range(5)
    ]
    passages = [
        _make_passage(f"p{i}", f"We propose model {i} for anomaly detection.")
        for i in range(5)
    ]
    bundle = _make_bundle(claims)
    index = _make_index(passages)

    pack = build_evidence_pack(bundle, index, max_items_per_type=2)

    method_items = [i for i in pack.items if i.claim_type == "METHOD"]
    assert len(method_items) <= 2


def test_prioritizes_method_before_result() -> None:
    result_claim = _make_claim("c001", "RESULT", "p001", claim_text="We achieve 95 F1.")
    method_claim = _make_claim("c002", "METHOD", "p002", claim_text="We propose a model.")
    bundle = _make_bundle([result_claim, method_claim])
    index = _make_index([
        _make_passage("p001", "We achieve 95 F1 score on the benchmark."),
        _make_passage("p002", "We propose a graph neural network for anomaly detection."),
    ])

    pack = build_evidence_pack(bundle, index)

    assert len(pack.items) == 2
    assert pack.items[0].claim_type == "METHOD"
    assert pack.items[1].claim_type == "RESULT"


# ---------------------------------------------------------------------------
# Retriever tests
# ---------------------------------------------------------------------------


def test_uses_retriever_top_result() -> None:
    claim = _make_claim("c001", "METHOD", "p001", claim_text="We propose a model.")
    bundle = _make_bundle([claim])
    index = _make_index([_make_passage("p001", "Original passage.")])

    fake_retriever = FakeRetriever([
        EvidenceRetrievalResult(passage_id="p001", score=2.5, matched_terms=["propose"], evidence_ref="test:b999"),
    ])

    pack = build_evidence_pack(bundle, index, retriever=fake_retriever)

    assert len(pack.items) == 1
    assert pack.items[0].retrieval_score == 2.5
    assert pack.items[0].evidence_ref == "test:b999"


def test_falls_back_to_claim_passage_id_when_retriever_no_hit() -> None:
    claim = _make_claim("c001", "METHOD", "p001", claim_text="We propose a model.")
    bundle = _make_bundle([claim])
    index = _make_index([_make_passage("p001", "We propose a graph neural network.")])

    fake_retriever = FakeRetriever([])

    pack = build_evidence_pack(bundle, index, retriever=fake_retriever)

    assert len(pack.items) == 1
    assert pack.items[0].retrieval_score == 0.0
    assert "graph neural network" in pack.items[0].passage_text


def test_falls_back_when_retriever_is_none() -> None:
    claim = _make_claim("c001", "METHOD", "p001", claim_text="We propose a model.")
    bundle = _make_bundle([claim])
    index = _make_index([_make_passage("p001", "We propose a graph neural network.")])

    pack = build_evidence_pack(bundle, index, retriever=None)

    assert len(pack.items) == 1
    assert pack.items[0].retrieval_score == 0.0
    assert "graph neural network" in pack.items[0].passage_text


# ---------------------------------------------------------------------------
# Budget / truncation tests
# ---------------------------------------------------------------------------


def test_truncates_long_passage_text() -> None:
    long_text = "word " * 1000  # 5000 chars
    claim = _make_claim("c001", "METHOD", "p001")
    bundle = _make_bundle([claim])
    index = _make_index([_make_passage("p001", long_text)])

    pack = build_evidence_pack(bundle, index, max_passage_chars=200)

    assert len(pack.items) == 1
    assert len(pack.items[0].passage_text) <= 200


def test_records_total_tokens() -> None:
    claim = _make_claim("c001", "METHOD", "p001")
    bundle = _make_bundle([claim])
    index = _make_index([_make_passage("p001", "We propose a graph neural network for anomaly detection.")])

    pack = build_evidence_pack(bundle, index)

    assert pack.total_tokens > 0
    assert pack.total_tokens == pack.items[0].token_count


def test_token_budget_exceeded_warning() -> None:
    claims = [_make_claim(f"c{i}", "METHOD", f"p{i}") for i in range(10)]
    passages = [_make_passage(f"p{i}", f"We propose model {i} for anomaly detection in sensor data.") for i in range(10)]
    bundle = _make_bundle(claims)
    index = _make_index(passages)

    pack = build_evidence_pack(bundle, index, max_total_tokens=5, max_items_per_type=10)

    assert any(w.code == "TOKEN_BUDGET_EXCEEDED" for w in pack.warnings)


# ---------------------------------------------------------------------------
# Warning tests
# ---------------------------------------------------------------------------


def test_missing_passage_warning() -> None:
    claim = _make_claim("c001", "METHOD", "nonexistent")
    bundle = _make_bundle([claim])
    index = _make_index([])

    pack = build_evidence_pack(bundle, index)

    assert any(w.code == "MISSING_PASSAGE" for w in pack.warnings)


def test_empty_pack_warning() -> None:
    bundle = _make_bundle([])
    index = _make_index([])

    pack = build_evidence_pack(bundle, index)

    assert any(w.code == "EMPTY_EVIDENCE_PACK" for w in pack.warnings)


# ---------------------------------------------------------------------------
# Safety tests
# ---------------------------------------------------------------------------


def test_does_not_write_artifact(tmp_path: Path) -> None:
    claim = _make_claim("c001", "METHOD", "p001")
    bundle = _make_bundle([claim])
    index = _make_index([_make_passage("p001", "We propose a model.")])

    build_evidence_pack(bundle, index)

    json_files = list(tmp_path.rglob("*.json"))
    assert json_files == []


def test_does_not_modify_claim_bundle() -> None:
    claim = _make_claim("c001", "METHOD", "p001")
    bundle = _make_bundle([claim])
    index = _make_index([_make_passage("p001", "We propose a model.")])

    original_count = len(bundle.claims)
    build_evidence_pack(bundle, index)

    assert len(bundle.claims) == original_count


def test_does_not_modify_passage_index() -> None:
    claim = _make_claim("c001", "METHOD", "p001")
    bundle = _make_bundle([claim])
    passage = _make_passage("p001", "We propose a model.")
    index = _make_index([passage])

    original_count = len(index.passages)
    build_evidence_pack(bundle, index)

    assert len(index.passages) == original_count
