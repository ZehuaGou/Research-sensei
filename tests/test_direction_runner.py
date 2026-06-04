from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from researchsensei.direction import DirectionRunner
from researchsensei.llm.client import MockLLMClient
from researchsensei.query import QueryPlanner
from researchsensei.schemas import CandidatePaper
from researchsensei.source_resolver import PaperSourceResolver
from researchsensei.workspace import WorkspaceStore


def _query_planner() -> QueryPlanner:
    return QueryPlanner(
        MockLLMClient(
            response=json.dumps(
                {
                    "direction_zh": "时间序列异常检测",
                    "direction_en": "Time Series Anomaly Detection",
                    "english_query": "time series anomaly detection",
                    "query_variants": ["multivariate time series anomaly detection"],
                    "core_terms": ["time series", "anomaly detection"],
                    "related_terms": ["outlier detection"],
                    "exclude_terms": ["forecasting only"],
                    "search_intents": ["SURVEY", "SOTA"],
                    "sub_directions": [],
                    "is_cross_domain": False,
                    "domain_components": [],
                }
            )
        )
    )


def _paper(
    paper_id: str,
    title: str,
    *,
    source: str = "arxiv",
    doi: str = "",
    arxiv_id: str = "",
    pdf_url: str = "https://example.org/paper.pdf",
    citation_count: int | None = 20,
) -> CandidatePaper:
    return CandidatePaper(
        paper_id=paper_id,
        title=title,
        year=2023,
        venue="arXiv" if source == "arxiv" else "ICML 2023",
        source=source,
        sources=[source],
        source_ids={source: paper_id},
        doi=doi,
        arxiv_id=arxiv_id,
        abstract="We study anomaly detection in time series data.",
        citation_count=citation_count,
        pdf_url=pdf_url,
        pdf_available=bool(pdf_url),
        source_confidence="medium",
        metadata_confidence="medium",
    )


class _FakeAdapter:
    def __init__(self, results: list[CandidatePaper], *, fail: bool = False) -> None:
        self.results = results
        self.fail = fail

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        if self.fail:
            raise RuntimeError("adapter failed")
        return self.results[:max_results]


def _pdf_resolver(tmp_path: Path) -> PaperSourceResolver:
    def _mock_download(request: httpx.Request) -> httpx.Response:
        content = b"%PDF-1.4\nfake\n"
        return httpx.Response(
            200,
            content=content,
            headers={"content-type": "application/pdf", "content-length": str(len(content))},
            request=request,
        )

    return PaperSourceResolver(
        network_enabled=True,
        http_client=httpx.Client(transport=httpx.MockTransport(_mock_download)),
        download_dir=tmp_path / "downloads",
    )


@pytest.mark.asyncio
async def test_direction_runner_full_pipeline(tmp_path: Path) -> None:
    workspace = WorkspaceStore(tmp_path / "workspace")
    runner = DirectionRunner(
        workspace=workspace,
        query_planner=_query_planner(),
        arxiv_adapter=_FakeAdapter([_paper("2301.12345v1", "Time Series Anomaly Detection", arxiv_id="2301.12345v1")]),
        openalex_adapter=_FakeAdapter([_paper("W123", "Deep Learning for Anomaly Detection", source="openalex")]),
        sources=["arxiv", "openalex"],
        source_resolver=_pdf_resolver(tmp_path),
    )

    bundle = await runner.run("时间序列异常检测", direction_id="test-dir")

    assert bundle.query_plan.english_query == "time series anomaly detection"
    assert bundle.candidate_pool.retrieved_count == 2
    assert bundle.filtered_candidates.deduplicated_count == 2
    assert bundle.reading_plan.status == "OK"
    assert any(item.priority == "A_READ" and item.can_enter_m2 for item in bundle.reading_plan.items)

    run_dir = tmp_path / "workspace" / "runs" / "test-dir"
    assert (run_dir / "query_plan.json").exists()
    assert (run_dir / "candidate_pool.json").exists()
    assert (run_dir / "source_resolution.json").exists()
    assert (run_dir / "filtered_candidates.json").exists()
    assert (run_dir / "reading_plan.json").exists()


@pytest.mark.asyncio
async def test_direction_runner_with_no_candidates(tmp_path: Path) -> None:
    runner = DirectionRunner(
        workspace=WorkspaceStore(tmp_path / "workspace"),
        query_planner=_query_planner(),
        arxiv_adapter=_FakeAdapter([]),
        openalex_adapter=_FakeAdapter([]),
        sources=["arxiv", "openalex"],
        source_resolver=PaperSourceResolver(network_enabled=False),
    )

    bundle = await runner.run("nonexistent topic", direction_id="empty-dir")

    assert bundle.candidate_pool.retrieved_count == 0
    assert bundle.reading_plan.status == "FAILED"
    assert "NO_CANDIDATES" in bundle.reading_plan.warnings


@pytest.mark.asyncio
async def test_direction_runner_artifacts_are_valid_json(tmp_path: Path) -> None:
    runner = DirectionRunner(
        workspace=WorkspaceStore(tmp_path / "workspace"),
        query_planner=_query_planner(),
        arxiv_adapter=_FakeAdapter([_paper("p1", "Time Series Anomaly Detection")]),
        sources=["arxiv"],
        source_resolver=PaperSourceResolver(network_enabled=False),
    )

    await runner.run("test query", direction_id="json-test")

    run_dir = tmp_path / "workspace" / "runs" / "json-test"
    for filename in [
        "query_plan.json",
        "candidate_pool.json",
        "source_resolution.json",
        "filtered_candidates.json",
        "reading_plan.json",
    ]:
        data = json.loads((run_dir / filename).read_text(encoding="utf-8"))
        assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_direction_runner_deduplicates_across_sources(tmp_path: Path) -> None:
    runner = DirectionRunner(
        workspace=WorkspaceStore(tmp_path / "workspace"),
        query_planner=_query_planner(),
        arxiv_adapter=_FakeAdapter([_paper("a1", "Time Series Anomaly Detection", doi="10.1234/tsad")]),
        openalex_adapter=_FakeAdapter([_paper("oa1", "Time Series Anomaly Detection", source="openalex", doi="10.1234/TSAD")]),
        sources=["arxiv", "openalex"],
        source_resolver=PaperSourceResolver(network_enabled=False),
    )

    bundle = await runner.run("time series anomaly detection", direction_id="dedup-test")

    assert bundle.candidate_pool.retrieved_count == 2
    assert bundle.filtered_candidates.deduplicated_count == 1
    assert len(bundle.filtered_candidates.items) == 1
    assert bundle.filtered_candidates.items[0].sources == ["arxiv", "openalex"]


@pytest.mark.asyncio
async def test_direction_runner_records_adapter_failure_in_source_metrics(tmp_path: Path) -> None:
    runner = DirectionRunner(
        workspace=WorkspaceStore(tmp_path / "workspace"),
        query_planner=_query_planner(),
        arxiv_adapter=_FakeAdapter([], fail=True),
        sources=["arxiv"],
        source_resolver=PaperSourceResolver(network_enabled=False),
    )

    bundle = await runner.run("time series anomaly detection", direction_id="failure-test")

    assert bundle.candidate_pool.source_metrics[0]["success"] is False
    assert any("ACQUISITION_FAILED:arxiv" in warning for warning in bundle.warnings)


@pytest.mark.asyncio
async def test_direction_runner_no_paper_card_artifact(tmp_path: Path) -> None:
    runner = DirectionRunner(
        workspace=WorkspaceStore(tmp_path / "workspace"),
        query_planner=_query_planner(),
        arxiv_adapter=_FakeAdapter([_paper("p1", "Time Series Anomaly Detection")]),
        sources=["arxiv"],
        source_resolver=PaperSourceResolver(network_enabled=False),
    )

    await runner.run("test query", direction_id="no-pc-test")

    run_dir = tmp_path / "workspace" / "runs" / "no-pc-test"
    assert not (run_dir / "paper_card.json").exists()
    assert not (run_dir / "formula_cards.json").exists()
    assert not (run_dir / "teaching_cards.json").exists()
