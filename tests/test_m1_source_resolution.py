from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from researchsensei.acquisition import ArxivAdapter
from researchsensei.direction import DirectionRunner
from researchsensei.query import QueryPlanner
from researchsensei.schemas import (
    CandidatePaper,
    PaperSourceStatus,
    PaperSourceType,
    ResolvedPaperSource,
    SourceResolutionResult,
    WarningItem,
)
from researchsensei.source_resolver import PaperSourceResolver
from researchsensei.workspace import WorkspaceStore


def _paper(**updates: object) -> CandidatePaper:
    data: dict[str, object] = {
        "paper_id": "p1",
        "title": "A Paper",
        "source": "arxiv",
        "abstract": "metadata only",
    }
    data.update(updates)
    return CandidatePaper(**data)


def test_source_resolution_schema_round_trip_with_structured_warnings() -> None:
    result = SourceResolutionResult(
        query="time series anomaly detection",
        items=[
            ResolvedPaperSource(
                paper_id="p1",
                title="A Paper",
                status=PaperSourceStatus.NOT_FOUND,
                source_type=PaperSourceType.METADATA_ONLY,
                warnings=[WarningItem(code="NO_SOURCE_URL", message="No source URL found.")],
            )
        ],
        warnings=[WarningItem(code="PARTIAL_SOURCE_RESOLUTION", message="Some papers are metadata-only.")],
    )

    restored = SourceResolutionResult.model_validate_json(result.model_dump_json())

    assert restored.items[0].warnings[0].code == "NO_SOURCE_URL"
    assert restored.warnings[0].message


def test_paper_source_resolver_resolves_existing_pdf_url() -> None:
    resolver = PaperSourceResolver(network_enabled=False)
    resolved = resolver.resolve_one(
        _paper(
            pdf_url="https://example.org/paper.pdf",
            url="https://example.org/landing",
            doi="10.1234/example",
        )
    )

    assert resolved.status == PaperSourceStatus.RESOLVED
    assert resolved.source_type == PaperSourceType.PDF
    assert resolved.pdf_url == "https://example.org/paper.pdf"
    assert resolved.landing_url == "https://example.org/landing"
    assert resolved.warnings == []


def test_paper_source_resolver_prefers_arxiv_source_before_pdf() -> None:
    resolver = PaperSourceResolver(network_enabled=False)
    resolved = resolver.resolve_one(_paper(arxiv_id="2301.12345v2", pdf_url="https://example.org/fallback.pdf"))

    assert resolved.status == PaperSourceStatus.RESOLVED
    assert resolved.source_type == PaperSourceType.ARXIV_SOURCE
    assert resolved.source_url == "https://arxiv.org/e-print/2301.12345v2"
    assert resolved.pdf_url == "https://arxiv.org/pdf/2301.12345v2.pdf"
    assert resolved.metadata["fallback_pdf_url"] == "https://example.org/fallback.pdf"


def test_paper_source_resolver_marks_landing_only_as_partial() -> None:
    resolver = PaperSourceResolver(network_enabled=False)
    resolved = resolver.resolve_one(_paper(source="openalex", url="https://openalex.org/W123"))

    assert resolved.status == PaperSourceStatus.PARTIAL
    assert resolved.source_type == PaperSourceType.LANDING_PAGE
    assert resolved.landing_url == "https://openalex.org/W123"
    assert resolved.warnings[0].code == "PDF_URL_MISSING"


def test_paper_source_resolver_marks_no_source_as_not_found() -> None:
    resolver = PaperSourceResolver(network_enabled=False)
    resolved = resolver.resolve_one(_paper(source="", url="", doi="", arxiv_id="", pdf_url=""))

    assert resolved.status == PaperSourceStatus.NOT_FOUND
    assert resolved.source_type == PaperSourceType.METADATA_ONLY
    assert {warning.code for warning in resolved.warnings} == {"NO_SOURCE_URL", "PDF_URL_MISSING"}


def test_paper_source_resolver_records_resolver_exception_as_failed() -> None:
    def fail(_: CandidatePaper) -> ResolvedPaperSource | None:
        raise RuntimeError("resolver down")

    resolver = PaperSourceResolver(network_enabled=True, external_resolver=fail)
    resolved = resolver.resolve_one(_paper(doi="10.1234/example"))

    assert resolved.status == PaperSourceStatus.FAILED
    assert resolved.warnings[0].code == "RESOLVER_FAILED"
    assert "resolver down" in resolved.error


def test_paper_source_resolver_network_disabled_does_not_call_external_resolver() -> None:
    called = False

    def external(_: CandidatePaper) -> ResolvedPaperSource | None:
        nonlocal called
        called = True
        return None

    resolver = PaperSourceResolver(network_enabled=False, external_resolver=external)
    resolved = resolver.resolve_one(_paper(doi="10.1234/example"))

    assert called is False
    assert resolved.status == PaperSourceStatus.PARTIAL
    assert resolved.landing_url == "https://doi.org/10.1234/example"
    assert resolved.warnings[0].code == "NETWORK_DISABLED"


@pytest.mark.asyncio
async def test_m1_direction_runner_writes_source_resolution_artifact(tmp_path: Path) -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345v1</id>
    <title>Time Series Anomaly Detection</title>
    <summary>We detect anomalies in time series data.</summary>
    <published>2023-01-30T00:00:00Z</published>
    <link title="pdf" href="https://arxiv.org/pdf/2301.12345v1"/>
  </entry>
</feed>
"""

    runner = DirectionRunner(
        workspace=WorkspaceStore(tmp_path / "workspace"),
        query_planner=QueryPlanner(),
        arxiv_adapter=ArxivAdapter(http_client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, text=xml)))),
        sources=["arxiv"],
        source_resolver=PaperSourceResolver(network_enabled=False),
    )

    bundle = await runner.run("time series anomaly detection", direction_id="m1-source")
    run_dir = tmp_path / "workspace" / "runs" / "m1-source"
    source_resolution_path = run_dir / "source_resolution.json"

    assert source_resolution_path.exists()
    content = json.loads(source_resolution_path.read_text(encoding="utf-8"))
    assert content["query"] == "time series anomaly detection"
    assert content["items"][0]["status"] == "RESOLVED"
    assert content["items"][0]["source_type"] == "ARXIV_SOURCE"
    assert content["items"][0]["warnings"] == []
    assert bundle.source_resolution.items[0].paper_id == "2301.12345v1"
    assert len(bundle.reading_plan.items) > 0
