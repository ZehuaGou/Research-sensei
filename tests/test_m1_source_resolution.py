from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from researchsensei.direction import DirectionRunner
from researchsensei.llm.client import MockLLMClient
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
        "sources": ["arxiv"],
        "abstract": "metadata only",
        "metadata_confidence": "medium",
    }
    data.update(updates)
    return CandidatePaper(**data)


def _query_planner() -> QueryPlanner:
    return QueryPlanner(
        MockLLMClient(
            response=json.dumps(
                {
                    "direction_en": "time series anomaly detection",
                    "english_query": "time series anomaly detection",
                    "core_terms": ["time series", "anomaly detection"],
                    "related_terms": [],
                    "exclude_terms": [],
                    "search_intents": ["SOTA"],
                }
            )
        )
    )


def test_source_resolution_schema_round_trip_with_structured_warnings() -> None:
    result = SourceResolutionResult(
        query="time series anomaly detection",
        items=[
            ResolvedPaperSource(
                paper_id="p1",
                title="A Paper",
                status=PaperSourceStatus.NO_SOURCE_FOUND,
                source_type=PaperSourceType.METADATA_ONLY,
                warnings=[WarningItem(code="NO_SOURCE_URL", message="No source URL found.")],
            )
        ],
        warnings=[WarningItem(code="PARTIAL_SOURCE_RESOLUTION", message="Some papers are metadata-only.")],
    )

    restored = SourceResolutionResult.model_validate_json(result.model_dump_json())

    assert restored.items[0].warnings[0].code == "NO_SOURCE_URL"
    assert restored.warnings[0].message


def test_paper_source_resolver_records_pdf_url_without_download() -> None:
    resolver = PaperSourceResolver(network_enabled=False)
    resolved = resolver.resolve_one(
        _paper(
            pdf_url="https://example.org/paper.pdf",
            url="https://example.org/landing",
            doi="10.1234/example",
        )
    )

    assert resolved.status == PaperSourceStatus.RESOLVED_PDF_URL_ONLY
    assert resolved.source_type == PaperSourceType.PDF
    assert resolved.pdf_url == "https://example.org/paper.pdf"
    assert resolved.local_path == ""
    assert resolved.download_status == "not_downloaded"


def test_paper_source_resolver_prefers_arxiv_pdf_url() -> None:
    resolver = PaperSourceResolver(network_enabled=False)
    resolved = resolver.resolve_one(_paper(arxiv_id="2301.12345v2", pdf_url="https://example.org/fallback.pdf"))

    assert resolved.status == PaperSourceStatus.RESOLVED_PDF_URL_ONLY
    assert resolved.source_type == PaperSourceType.ARXIV_SOURCE
    assert resolved.source_url == "https://arxiv.org/e-print/2301.12345v2"
    assert resolved.pdf_url == "https://example.org/fallback.pdf"


def test_paper_source_resolver_marks_landing_only() -> None:
    resolver = PaperSourceResolver(network_enabled=False)
    resolved = resolver.resolve_one(_paper(source="openalex", sources=["openalex"], url="https://openalex.org/W123"))

    assert resolved.status == PaperSourceStatus.RESOLVED_LANDING_ONLY
    assert resolved.source_type == PaperSourceType.LANDING_PAGE
    assert resolved.landing_url == "https://openalex.org/W123"
    assert resolved.warnings[0].code == "PDF_URL_MISSING"


def test_paper_source_resolver_marks_no_source() -> None:
    resolver = PaperSourceResolver(network_enabled=False)
    resolved = resolver.resolve_one(_paper(source="", sources=[], url="", doi="", arxiv_id="", pdf_url=""))

    assert resolved.status == PaperSourceStatus.NO_SOURCE_FOUND
    assert resolved.source_type == PaperSourceType.METADATA_ONLY
    assert {warning.code for warning in resolved.warnings} == {"NO_SOURCE_URL", "PDF_URL_MISSING"}


def test_paper_source_resolver_records_resolver_exception_as_failed() -> None:
    def fail(_: CandidatePaper) -> ResolvedPaperSource | None:
        raise RuntimeError("resolver down")

    resolver = PaperSourceResolver(network_enabled=True, external_resolver=fail)
    resolved = resolver.resolve_one(_paper(doi="10.1234/example"))

    assert resolved.status == PaperSourceStatus.FAILED_DOWNLOAD
    assert resolved.error_code == "RESOLVER_FAILED"
    assert "resolver down" in resolved.error


def test_paper_source_resolver_downloads_and_hashes_pdf(tmp_path: Path) -> None:
    pdf_bytes = b"%PDF-1.4\nfake pdf\n"

    def _mock_download(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=pdf_bytes,
            headers={"content-type": "application/pdf", "content-length": str(len(pdf_bytes))},
            request=request,
        )

    resolver = PaperSourceResolver(
        network_enabled=True,
        http_client=httpx.Client(transport=httpx.MockTransport(_mock_download)),
        download_dir=tmp_path,
    )
    resolved = resolver.resolve_one(_paper(pdf_url="https://example.org/paper.pdf"))

    assert resolved.status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED
    assert resolved.download_status == "downloaded"
    assert resolved.sha256
    assert Path(resolved.local_path).read_bytes() == pdf_bytes


def test_paper_source_resolver_rejects_non_pdf_download(tmp_path: Path) -> None:
    def _mock_download(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html></html>", headers={"content-type": "text/html"}, request=request)

    resolver = PaperSourceResolver(
        network_enabled=True,
        http_client=httpx.Client(transport=httpx.MockTransport(_mock_download)),
        download_dir=tmp_path,
    )
    resolved = resolver.resolve_one(_paper(pdf_url="https://example.org/paper.pdf"))

    assert resolved.status == PaperSourceStatus.FAILED_DOWNLOAD
    assert resolved.error_code == "UNSUPPORTED_SOURCE"
    assert resolved.local_path == ""


class _FakeAdapter:
    def __init__(self, results: list[CandidatePaper]) -> None:
        self.results = results

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        return self.results[:max_results]


@pytest.mark.asyncio
async def test_m1_direction_runner_writes_source_resolution_artifact(tmp_path: Path) -> None:
    runner = DirectionRunner(
        workspace=WorkspaceStore(tmp_path / "workspace"),
        query_planner=_query_planner(),
        arxiv_adapter=_FakeAdapter(
            [
                _paper(
                    paper_id="2301.12345v1",
                    title="Time Series Anomaly Detection",
                    abstract="We detect anomalies in time series data.",
                    arxiv_id="2301.12345v1",
                    pdf_url="https://arxiv.org/pdf/2301.12345v1.pdf",
                    pdf_available=True,
                    source_confidence="medium",
                )
            ]
        ),
        sources=["arxiv"],
        source_resolver=PaperSourceResolver(network_enabled=False),
    )

    bundle = await runner.run("time series anomaly detection", direction_id="m1-source")
    run_dir = tmp_path / "workspace" / "runs" / "m1-source"
    source_resolution_path = run_dir / "source_resolution.json"

    assert source_resolution_path.exists()
    content = json.loads(source_resolution_path.read_text(encoding="utf-8"))
    assert content["query"] == "time series anomaly detection"
    assert content["items"][0]["status"] == "RESOLVED_PDF_URL_ONLY"
    assert content["items"][0]["source_type"] == "ARXIV_SOURCE"
    assert bundle.source_resolution.items[0].paper_id == "2301.12345v1"
    assert bundle.reading_plan.status == "DEGRADED"
