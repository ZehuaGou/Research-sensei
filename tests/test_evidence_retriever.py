from __future__ import annotations

from pathlib import Path

from researchsensei.evidence.retriever import EvidenceRetriever, bm25_score, compute_idf, tokenize
from researchsensei.schemas import EvidenceRetrievalResult, Passage, PassageIndex


# ---------------------------------------------------------------------------
# Tokenize tests
# ---------------------------------------------------------------------------


def test_tokenize_lowercases_and_preserves_alnum() -> None:
    tokens = tokenize("We Propose a Graph Neural Network for Anomaly Detection")
    assert tokens == ["we", "propose", "a", "graph", "neural", "network", "for", "anomaly", "detection"]


def test_tokenize_preserves_decimal_numbers() -> None:
    tokens = tokenize("achieves 95.2 accuracy on the benchmark")
    assert "95.2" in tokens
    assert "95" not in tokens


def test_tokenize_preserves_f1() -> None:
    tokens = tokenize("F1 score is 0.89")
    assert "f1" in tokens
    assert "0.89" in tokens


# ---------------------------------------------------------------------------
# IDF tests
# ---------------------------------------------------------------------------


def test_compute_idf_rarer_terms_higher() -> None:
    corpus = [
        ["the", "model", "is", "good"],
        ["the", "model", "is", "bad"],
        ["anomaly", "detection", "method"],
    ]
    idf = compute_idf(corpus)
    assert idf["anomaly"] > idf["the"]
    assert idf["detection"] > idf["model"]


# ---------------------------------------------------------------------------
# Bpaper analysis5 score tests
# ---------------------------------------------------------------------------


def test_bm25_exact_match_scores_positive() -> None:
    tokens = ["graph", "neural", "network"]
    score = bm25_score(tokens, tokens, 3.0, {"graph": 1.0, "neural": 1.0, "network": 1.0})
    assert score > 0


def test_bm25_unrelated_scores_low_or_filtered() -> None:
    query = ["quantum", "physics"]
    doc = ["graph", "neural", "network", "anomaly", "detection"]
    idf = {"quantum": 2.0, "physics": 2.0, "graph": 1.0, "neural": 1.0, "network": 1.0, "anomaly": 1.5, "detection": 1.5}
    score = bm25_score(query, doc, 5.0, idf)
    assert score == 0.0


# ---------------------------------------------------------------------------
# EvidenceRetriever tests
# ---------------------------------------------------------------------------


def _make_passage(passage_id: str, text: str, evidence_ref: str = "") -> Passage:
    return Passage(
        passage_id=passage_id,
        paper_id="test",
        text=text,
        normalized_text=text.lower(),
        token_count=len(text.split()),
        evidence_refs=[evidence_ref] if evidence_ref else [],
    )


def _make_index(passages: list[Passage]) -> PassageIndex:
    return PassageIndex(paper_id="test", passages=passages)


def test_specific_passage_outranks_generic() -> None:
    specific = _make_passage("p001", "We propose a graph neural network for anomaly detection in sensor data.", "test:b001")
    generic = _make_passage("p002", "This is a paper about machine learning and artificial intelligence.", "test:b002")
    index = _make_index([generic, specific])
    retriever = EvidenceRetriever(min_score=0.0)

    results = retriever.retrieve("graph neural network anomaly detection", index)

    assert len(results) >= 2
    assert results[0].passage_id == "p001"


def test_top_k_limits_results() -> None:
    passages = [_make_passage(f"p{i:03d}", f"Passage {i} about anomaly detection method.") for i in range(10)]
    index = _make_index(passages)
    retriever = EvidenceRetriever(top_k=3, min_score=0.0)

    results = retriever.retrieve("anomaly detection", index)

    assert len(results) <= 3


def test_min_score_filters_low_scores() -> None:
    relevant = _make_passage("p001", "We propose a graph neural network for anomaly detection.", "test:b001")
    irrelevant = _make_passage("p002", "The weather is nice today and birds are singing.", "test:b002")
    index = _make_index([relevant, irrelevant])
    retriever = EvidenceRetriever(min_score=100.0)

    results = retriever.retrieve("graph neural network", index)

    passage_ids = {r.passage_id for r in results}
    assert "p002" not in passage_ids


def test_empty_query_returns_empty() -> None:
    index = _make_index([_make_passage("p001", "Some text.")])
    retriever = EvidenceRetriever()

    assert retriever.retrieve("", index) == []
    assert retriever.retrieve("   ", index) == []


def test_empty_passage_index_returns_empty() -> None:
    index = _make_index([])
    retriever = EvidenceRetriever()

    assert retriever.retrieve("anomaly detection", index) == []


def test_matched_terms_recorded() -> None:
    passage = _make_passage("p001", "We propose a graph neural network for anomaly detection.", "test:b001")
    index = _make_index([passage])
    retriever = EvidenceRetriever(min_score=0.0)

    results = retriever.retrieve("graph neural network", index)

    assert len(results) == 1
    assert "graph" in results[0].matched_terms
    assert "neural" in results[0].matched_terms
    assert "network" in results[0].matched_terms


def test_evidence_ref_populated_from_first_passage_ref() -> None:
    passage = _make_passage("p001", "We propose a graph neural network for anomaly detection.", "test:b001")
    index = _make_index([passage])
    retriever = EvidenceRetriever(min_score=0.0)

    results = retriever.retrieve("graph neural network", index)

    assert len(results) == 1
    assert results[0].evidence_ref == "test:b001"


def test_retriever_does_not_write_artifacts(tmp_path: Path) -> None:
    passage = _make_passage("p001", "We propose a graph neural network for anomaly detection.", "test:b001")
    index = _make_index([passage])
    retriever = EvidenceRetriever(min_score=0.0)

    retriever.retrieve("graph neural network", index)

    json_files = list(tmp_path.rglob("*.json"))
    assert json_files == []


def test_claim_evidence_bundle_shape_unchanged() -> None:
    """EvidenceRetrievalResult should be a separate type from ClaimEvidenceRecord."""
    result = EvidenceRetrievalResult(
        passage_id="p001",
        score=1.5,
        matched_terms=["graph", "network"],
        evidence_ref="test:b001",
    )

    assert result.passage_id == "p001"
    assert result.score == 1.5
    assert result.matched_terms == ["graph", "network"]
    assert result.evidence_ref == "test:b001"

    # Should not have claim fields
    assert not hasattr(result, "claim_id")
    assert not hasattr(result, "claim_text")
    assert not hasattr(result, "claim_type")
