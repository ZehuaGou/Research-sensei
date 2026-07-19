from __future__ import annotations

from pathlib import Path

import httpx

from researchsensei.library import PaperLibraryStore
from researchsensei.schemas import CandidatePaper, PaperSourceStatus, SourcePriority
from researchsensei.schemas import PaperSourceType, ResolvedPaperSource
from researchsensei.source_resolver import PaperSourceResolver


def test_downloaded_pdf_sets_source_aware_fields(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf"},
            content=b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF",
            request=request,
        )

    resolver = PaperSourceResolver(
        network_enabled=True,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    paper = CandidatePaper(
        paper_id="p1",
        title="Downloaded PDF",
        pdf_url="https://example.test/paper.pdf",
    )

    result = resolver.resolve_one(paper, download_dir=tmp_path)

    assert result.status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED
    assert result.source_priority == SourcePriority.PDF
    assert result.preferred_m2_input == "pdf"
    assert result.has_valid_deep_reading_source is True
    assert result.local_path
    assert Path(result.local_path).exists()
    assert Path(result.local_path).name == "Downloaded PDF.pdf"


def test_resolve_many_writes_direction_manifest(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf"},
            content=b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF",
            request=request,
        )

    resolver = PaperSourceResolver(
        network_enabled=True,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    paper = CandidatePaper(
        paper_id="p1",
        title="Manifest Paper",
        venue="AAAI",
        pdf_url="https://example.test/paper.pdf",
    )

    resolver.resolve_many("time series anomaly detection", [paper], download_dir=tmp_path)

    assert (tmp_path / "Manifest Paper.pdf").exists()
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "README.md").exists()


def test_resolver_reuses_named_pdf_from_sibling_direction(tmp_path: Path) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf"},
            content=b"%PDF-1.4\ncached\n%%EOF",
            request=request,
        )

    resolver = PaperSourceResolver(
        network_enabled=True,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    paper = CandidatePaper(
        paper_id="p1",
        title="Reusable Paper",
        pdf_url="https://example.test/paper.pdf",
    )

    first = resolver.resolve_one(paper, download_dir=tmp_path / "time series anomaly detection")
    second = resolver.resolve_one(paper, download_dir=tmp_path / "graph anomaly detection")

    assert calls == 1
    assert Path(first.local_path).name == "Reusable Paper.pdf"
    assert Path(second.local_path).name == "Reusable Paper.pdf"
    assert Path(second.local_path).exists()
    assert second.metadata["resolution_strategy"] == "reused_named_pdf"


def test_resolver_reuses_local_library_before_network(tmp_path: Path) -> None:
    db = PaperLibraryStore(tmp_path / "sensei.sqlite3")
    pdf = tmp_path / "library-paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\ncached\n%%EOF")
    paper = CandidatePaper(
        paper_id="p1",
        title="Cached Library Paper",
        doi="10.5555/cached",
        pdf_url="https://example.test/library.pdf",
    )
    db.upsert_download(
        paper,
        ResolvedPaperSource(
            paper_id=paper.paper_id,
            title=paper.title,
            doi=paper.doi,
            pdf_url=paper.pdf_url,
            source_type=PaperSourceType.PDF,
            status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,
            download_status="downloaded",
            local_path=str(pdf),
            sha256="b" * 64,
            file_size=pdf.stat().st_size,
            has_valid_deep_reading_source=True,
            metadata={"resolution_strategy": "downloaded_validated_pdf"},
        ),
    )
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500, request=request)

    resolver = PaperSourceResolver(
        network_enabled=True,
        paper_library=db,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = resolver.resolve_one(
        CandidatePaper(
            paper_id="p2",
            title="Cached Library Paper",
            doi="https://doi.org/10.5555/cached",
            pdf_url="https://example.test/other.pdf",
        ),
        download_dir=tmp_path / "downloads",
    )

    assert calls == 0
    assert result.status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED
    assert result.metadata["resolution_strategy"] == "library_reuse"
    assert result.local_path == str(pdf.resolve())


def test_resolver_retries_alternative_pdf_urls_until_valid_pdf(tmp_path: Path) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "blocked" in str(request.url):
            return httpx.Response(403, request=request)
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf"},
            content=b"%PDF-1.4\nvalid fallback\n%%EOF",
            request=request,
        )

    resolver = PaperSourceResolver(
        network_enabled=True,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = resolver.resolve_one(
        CandidatePaper(
            paper_id="fallback-paper",
            title="Fallback Paper",
            pdf_url="https://publisher.test/blocked.pdf",
            candidate_pdf_urls=[
                "https://publisher.test/blocked.pdf",
                "https://mirror.test/working.pdf",
            ],
        ),
        download_dir=tmp_path,
    )

    assert result.status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED
    assert result.pdf_url == "https://mirror.test/working.pdf"
    assert calls == [
        "https://publisher.test/blocked.pdf",
        "https://mirror.test/working.pdf",
    ]
    assert result.metadata["fallback_count"] == 1
