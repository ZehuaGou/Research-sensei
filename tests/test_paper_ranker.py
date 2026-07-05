from __future__ import annotations

from typing import Any

from researchsensei.ranking import PaperRanker, select_downloads
from researchsensei.schemas import CandidatePaper


class FakeRanker:
    def rerank(self, request: Any) -> list[dict[str, float | int]]:
        passages = getattr(request, "passages", None)
        if passages is None and isinstance(request, dict):
            passages = request.get("passages", [])
        results: list[dict[str, float | int]] = []
        for fallback_index, passage in enumerate(passages or []):
            if isinstance(passage, dict):
                idx = int(passage.get("id", fallback_index))
                text = str(passage.get("text", ""))
            else:
                idx = int(getattr(passage, "id", fallback_index))
                text = str(getattr(passage, "text", ""))
            score = 0.95 if "root cause" in text.lower() else 0.10
            results.append({"id": idx, "score": score})
        return sorted(results, key=lambda item: float(item["score"]), reverse=True)


def _paper(**overrides: object) -> CandidatePaper:
    base = {
        "paper_id": "paper-1",
        "title": "Generic Time Series Anomaly Detection",
        "abstract": "A broad anomaly detection paper.",
        "source": "paper_search",
        "year": 2024,
        "venue": "OpenReview",
        "raw_source_metadata": {"search_rank": 1},
    }
    base.update(overrides)
    return CandidatePaper(**base)


def test_paper_ranker_uses_external_scores_and_records_rank_fields() -> None:
    ranker = PaperRanker(ranker=FakeRanker(), model_name="fake")
    broad = _paper(paper_id="broad", title="Generic anomaly detection", raw_source_metadata={"search_rank": 1})
    rca = _paper(
        paper_id="rca",
        title="Root Cause Analysis for Time Series Anomaly Detection",
        abstract="This paper studies root cause localization for anomalies.",
        raw_source_metadata={"search_rank": 2},
    )

    ranked = ranker.rank("time series anomaly detection root cause analysis", [broad, rca])

    assert [paper.paper_id for paper in ranked] == ["rca", "broad"]
    assert ranked[0].search_rank == 2
    assert ranked[0].rerank_rank == 1
    assert ranked[0].rerank_score is not None
    assert ranked[0].rank_score is not None
    assert "flashrank model relevance" in ranked[0].rank_reason
    assert ranker.last_status == "flashrank"


def test_select_downloads_marks_primary_download_fields() -> None:
    ranked = [
        _paper(paper_id="p1", title="Paper 1", search_rank=1, rerank_rank=1),
        _paper(paper_id="p2", title="Paper 2", search_rank=2, rerank_rank=2),
        _paper(paper_id="p3", title="Paper 3", search_rank=3, rerank_rank=3),
    ]

    selected = select_downloads(ranked, max_download_candidates=2)

    assert [paper.download_selected for paper in selected] == [True, True, False]
    assert selected[0].download_decision == "SELECTED_BY_RERANKER"
    assert selected[2].download_decision == "SKIPPED_OVER_DOWNLOAD_LIMIT"


def test_paper_ranker_disabled_preserves_external_search_order() -> None:
    ranker = PaperRanker(enabled=False)
    papers = [
        _paper(paper_id="p1", raw_source_metadata={"search_rank": 1}),
        _paper(paper_id="p2", raw_source_metadata={"search_rank": 2}),
    ]

    ranked = ranker.rank("graph anomaly detection", papers)

    assert [paper.paper_id for paper in ranked] == ["p1", "p2"]
    assert [paper.rerank_rank for paper in ranked] == [1, 2]
    assert all(paper.rank_reason == "reranker disabled" for paper in ranked)
