from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from researchsensei.acquisition import ArxivAdapter, OpenAlexAdapter
from researchsensei.direction import DirectionRunner
from researchsensei.query import QueryPlanner
from researchsensei.selection import SelectionService
from researchsensei.workspace import WorkspaceStore

# Sample arXiv XML
ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345v1</id>
    <title>Time Series Anomaly Detection</title>
    <summary>We detect anomalies in time series data.</summary>
    <published>2023-01-30T00:00:00Z</published>
    <author><name>John Doe</name></author>
  </entry>
</feed>
"""

OPENALEX_JSON = json.dumps({
    "results": [
        {
            "id": "https://openalex.org/W123",
            "title": "Deep Learning for Anomaly Detection",
            "publication_year": 2023,
            "cited_by_count": 50,
            "primary_location": {"source": {"display_name": "ICML"}},
            "authorships": [{"author": {"display_name": "Alice"}}],
            "abstract_inverted_index": {"anomaly": [0], "detection": [1]},
        }
    ]
})


def _mock_arxiv(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, text=ARXIV_XML)


def _mock_openalex(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, text=OPENALEX_JSON, headers={"content-type": "application/json"})


@pytest.mark.asyncio
async def test_direction_runner_full_pipeline(tmp_path: Path) -> None:
    workspace = WorkspaceStore(tmp_path / "workspace")

    # Create mock adapters
    arxiv_transport = httpx.MockTransport(_mock_arxiv)
    openalex_transport = httpx.MockTransport(_mock_openalex)

    runner = DirectionRunner(
        workspace=workspace,
        query_planner=QueryPlanner(),
        arxiv_adapter=ArxivAdapter(http_client=httpx.Client(transport=arxiv_transport)),
        openalex_adapter=OpenAlexAdapter(http_client=httpx.Client(transport=openalex_transport)),
        sources=["arxiv", "openalex"],
    )

    bundle = await runner.run("time series anomaly detection", direction_id="test-dir")

    # Check query plan
    assert bundle.query_plan.user_query == "time series anomaly detection"
    assert len(bundle.query_plan.core_terms) > 0

    # Check candidate pool
    assert bundle.candidate_pool.retrieved_count == 2
    assert len(bundle.candidate_pool.items) == 2

    # Check reading plan
    assert len(bundle.reading_plan.items) > 0
    assert bundle.reading_plan.topic == "time series anomaly detection"

    # Check artifacts written
    run_dir = tmp_path / "workspace" / "runs" / "test-dir"
    assert (run_dir / "query_plan.json").exists()
    assert (run_dir / "candidate_pool.json").exists()
    assert (run_dir / "reading_plan.json").exists()


@pytest.mark.asyncio
async def test_direction_runner_with_no_candidates(tmp_path: Path) -> None:
    workspace = WorkspaceStore(tmp_path / "workspace")

    def _empty_arxiv(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text='<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>')

    def _empty_openalex(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=json.dumps({"results": []}))

    runner = DirectionRunner(
        workspace=workspace,
        query_planner=QueryPlanner(),
        arxiv_adapter=ArxivAdapter(http_client=httpx.Client(transport=httpx.MockTransport(_empty_arxiv))),
        openalex_adapter=OpenAlexAdapter(http_client=httpx.Client(transport=httpx.MockTransport(_empty_openalex))),
    )

    bundle = await runner.run("nonexistent topic", direction_id="empty-dir")

    assert bundle.candidate_pool.retrieved_count == 0
    assert len(bundle.reading_plan.items) == 0
    assert "NO_CANDIDATES" in bundle.reading_plan.warnings


@pytest.mark.asyncio
async def test_direction_runner_artifacts_are_valid_json(tmp_path: Path) -> None:
    workspace = WorkspaceStore(tmp_path / "workspace")

    arxiv_transport = httpx.MockTransport(_mock_arxiv)
    runner = DirectionRunner(
        workspace=workspace,
        arxiv_adapter=ArxivAdapter(http_client=httpx.Client(transport=arxiv_transport)),
        sources=["arxiv"],
    )

    await runner.run("test query", direction_id="json-test")

    run_dir = tmp_path / "workspace" / "runs" / "json-test"

    # All artifacts should be valid JSON
    for filename in ["query_plan.json", "candidate_pool.json", "filtered_candidates.json", "reading_plan.json"]:
        content = (run_dir / filename).read_text(encoding="utf-8")
        data = json.loads(content)
        assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_direction_runner_writes_filtered_candidates_json(tmp_path: Path) -> None:
    workspace = WorkspaceStore(tmp_path / "workspace")

    runner = DirectionRunner(
        workspace=workspace,
        arxiv_adapter=ArxivAdapter(http_client=httpx.Client(transport=httpx.MockTransport(_mock_arxiv))),
        sources=["arxiv"],
    )

    bundle = await runner.run("test query", direction_id="fc-test")

    run_dir = tmp_path / "workspace" / "runs" / "fc-test"
    assert (run_dir / "filtered_candidates.json").exists()

    # filtered_candidates should be present in the bundle
    assert bundle.filtered_candidates is not None
    assert bundle.filtered_candidates.deduplicated_count <= bundle.candidate_pool.retrieved_count


# Duplicate arXiv XML: same paper from two sources
DUP_ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345v1</id>
    <title>Time Series Anomaly Detection</title>
    <summary>We detect anomalies in time series data.</summary>
    <published>2023-01-30T00:00:00Z</published>
    <author><name>John Doe</name></author>
  </entry>
</feed>
"""

DUP_OPENALEX_JSON = json.dumps({
    "results": [
        {
            "id": "https://openalex.org/W999",
            "title": "Time Series Anomaly Detection",
            "publication_year": 2023,
            "doi": "https://doi.org/10.1234/tsad",
            "cited_by_count": 100,
            "primary_location": {"source": {"display_name": "ICML"}},
            "authorships": [{"author": {"display_name": "John Doe"}}],
            "abstract_inverted_index": {"We": [0], "detect": [1], "anomalies": [2]},
        }
    ]
})


@pytest.mark.asyncio
async def test_direction_runner_deduplicates_across_sources(tmp_path: Path) -> None:
    """Same paper from arXiv and OpenAlex should be deduplicated."""
    workspace = WorkspaceStore(tmp_path / "workspace")

    def _dup_arxiv(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=DUP_ARXIV_XML)

    def _dup_openalex(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=DUP_OPENALEX_JSON, headers={"content-type": "application/json"})

    runner = DirectionRunner(
        workspace=workspace,
        arxiv_adapter=ArxivAdapter(http_client=httpx.Client(transport=httpx.MockTransport(_dup_arxiv))),
        openalex_adapter=OpenAlexAdapter(http_client=httpx.Client(transport=httpx.MockTransport(_dup_openalex))),
        sources=["arxiv", "openalex"],
    )

    bundle = await runner.run("time series anomaly detection", direction_id="dedup-test")

    # Raw pool has 2 papers (one from each source)
    assert bundle.candidate_pool.retrieved_count == 2
    # Filtered candidates should have 1 (deduplicated)
    assert bundle.filtered_candidates.deduplicated_count == 1
    assert len(bundle.filtered_candidates.items) == 1
    # Reading plan should be based on filtered (1 paper)
    assert len(bundle.reading_plan.items) <= 1


@pytest.mark.asyncio
async def test_direction_runner_reading_plan_uses_filtered_candidates(tmp_path: Path) -> None:
    """Reading plan should be built from filtered candidates, not raw pool."""
    workspace = WorkspaceStore(tmp_path / "workspace")

    runner = DirectionRunner(
        workspace=workspace,
        arxiv_adapter=ArxivAdapter(http_client=httpx.Client(transport=httpx.MockTransport(_mock_arxiv))),
        openalex_adapter=OpenAlexAdapter(http_client=httpx.Client(transport=httpx.MockTransport(_mock_openalex))),
        sources=["arxiv", "openalex"],
    )

    bundle = await runner.run("test query", direction_id="rp-test")

    # Reading plan items should not exceed filtered candidate count
    assert len(bundle.reading_plan.items) <= len(bundle.filtered_candidates.items)


@pytest.mark.asyncio
async def test_direction_runner_no_paper_card_artifact(tmp_path: Path) -> None:
    """Direction runner should NOT generate paper_card.json."""
    workspace = WorkspaceStore(tmp_path / "workspace")

    runner = DirectionRunner(
        workspace=workspace,
        arxiv_adapter=ArxivAdapter(http_client=httpx.Client(transport=httpx.MockTransport(_mock_arxiv))),
        sources=["arxiv"],
    )

    await runner.run("test query", direction_id="no-pc-test")

    run_dir = tmp_path / "workspace" / "runs" / "no-pc-test"
    assert not (run_dir / "paper_card.json").exists()
    assert not (run_dir / "formula_cards.json").exists()
    assert not (run_dir / "teaching_cards.json").exists()
