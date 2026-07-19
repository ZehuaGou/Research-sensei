from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from researchsensei.browser_downloader import BrowserDownloadResult
from researchsensei.library import PaperLibraryStore
from researchsensei.schemas import CandidatePaper, PaperSourceStatus, SourcePriority
from researchsensei.schemas import PaperSourceType, ResolvedPaperSource
from researchsensei.source_resolver import PaperSourceResolver


class FakeBrowserDownloader:
    available = True

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def download(self, **kwargs: object) -> BrowserDownloadResult:
        self.calls.append(kwargs)
        target = Path(str(kwargs["target_path"]))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"%PDF-1.4\nbrowser session\n%%EOF")
        pdf_urls = kwargs.get("pdf_urls")
        final_url = str(kwargs.get("landing_url") or "")
        if isinstance(pdf_urls, list) and pdf_urls:
            final_url = str(pdf_urls[0])
        return BrowserDownloadResult(
            attempted=True,
            success=True,
            local_path=str(target),
            final_url=final_url,
            content_type="application/pdf",
            browser_mode="native_chrome_cdp",
        )


class FailingBrowserDownloader:
    available = True

    def download(self, **kwargs: object) -> BrowserDownloadResult:
        return BrowserDownloadResult(
            attempted=True,
            success=False,
            browser_mode="native_chrome_cdp",
            error_code="BROWSER_PDF_NOT_FOUND",
            error="No validated PDF was exposed by the publisher page.",
        )


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


def test_direct_open_pdf_does_not_launch_native_chrome(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf"},
            content=b"%PDF-1.4\ndirect open paper\n%%EOF",
            request=request,
        )

    browser = FakeBrowserDownloader()
    resolver = PaperSourceResolver(
        network_enabled=True,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        browser_downloader=browser,  # type: ignore[arg-type]
    )
    result = resolver.resolve_one(
        CandidatePaper(
            paper_id="direct-open-paper",
            title="Direct Open Paper",
            pdf_url="https://repository.example.org/direct-open-paper.pdf",
        ),
        download_dir=tmp_path,
    )

    assert result.status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED
    assert result.metadata["resolution_strategy"] == "downloaded_validated_pdf"
    assert browser.calls == []


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


def test_resolver_uses_official_pmc_cloud_pdf_instead_of_html_download_screen(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        calls.append(url)
        if request.url.path == "/" and request.url.params.get("prefix") == "metadata/PMC10490803.":
            return httpx.Response(
                200,
                content=(
                    b'<?xml version="1.0" encoding="UTF-8"?>'
                    b'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
                    b"<Contents><Key>metadata/PMC10490803.1.json</Key></Contents>"
                    b"</ListBucketResult>"
                ),
                request=request,
            )
        if request.url.path == "/metadata/PMC10490803.1.json":
            return httpx.Response(
                200,
                json={
                    "pmcid": "PMC10490803",
                    "version": 1,
                    "is_pmc_openaccess": True,
                    "is_manuscript": False,
                    "pdf_url": (
                        "s3://pmc-oa-opendata/PMC10490803.1/"
                        "PMC10490803.1.pdf?md5=0123456789abcdef"
                    ),
                },
                request=request,
            )
        if request.url.path == "/PMC10490803.1/PMC10490803.1.pdf":
            return httpx.Response(
                200,
                headers={"content-type": "binary/octet-stream"},
                content=b"%PDF-1.4\nopen PMC cloud paper\n%%EOF",
                request=request,
            )
        return httpx.Response(404, request=request)

    resolver = PaperSourceResolver(
        network_enabled=True,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    paper = CandidatePaper(
        paper_id="pmc-paper",
        title="Masked Graph Neural Networks",
        landing_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC10490803/",
        pdf_url=(
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC10490803/pdf/"
            "sensors-23-07552.pdf"
        ),
    )

    result = resolver.resolve_one(paper, download_dir=tmp_path)

    assert result.status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED
    assert result.metadata["resolution_strategy"] == "pmc_cloud_pdf"
    assert result.metadata["pmcid"] == "PMC10490803"
    assert result.pdf_url.startswith(
        "https://pmc-oa-opendata.s3.amazonaws.com/PMC10490803.1/"
    )
    assert Path(result.local_path).read_bytes().startswith(b"%PDF")
    assert not any("pmc.ncbi.nlm.nih.gov/articles" in call for call in calls)


def test_resolver_recovers_pmc_copy_by_doi_after_publisher_pdf_is_blocked(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        calls.append(url)
        if request.url.host == "www.mdpi.com":
            return httpx.Response(403, request=request)
        if request.url.path == "/tools/idconv/api/v1/articles/":
            assert request.url.params.get("ids") == "10.3390/s23177552"
            assert request.url.params.get("idtype") == "doi"
            return httpx.Response(
                200,
                json={
                    "status": "ok",
                    "records": [
                        {
                            "doi": "10.3390/s23177552",
                            "pmcid": "PMC10490803",
                        }
                    ],
                },
                request=request,
            )
        if request.url.path == "/" and request.url.params.get("prefix") == "metadata/PMC10490803.":
            return httpx.Response(
                200,
                content=(
                    b'<?xml version="1.0" encoding="UTF-8"?>'
                    b'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
                    b"<Contents><Key>metadata/PMC10490803.1.json</Key></Contents>"
                    b"</ListBucketResult>"
                ),
                request=request,
            )
        if request.url.path == "/metadata/PMC10490803.1.json":
            return httpx.Response(
                200,
                json={
                    "pmcid": "PMC10490803",
                    "version": 1,
                    "is_pmc_openaccess": True,
                    "is_manuscript": False,
                    "pdf_url": "s3://pmc-oa-opendata/PMC10490803.1/PMC10490803.1.pdf",
                },
                request=request,
            )
        if request.url.path == "/PMC10490803.1/PMC10490803.1.pdf":
            return httpx.Response(
                200,
                headers={"content-type": "application/pdf"},
                content=b"%PDF-1.4\nopen PMC DOI fallback\n%%EOF",
                request=request,
            )
        return httpx.Response(404, request=request)

    browser = FakeBrowserDownloader()
    resolver = PaperSourceResolver(
        network_enabled=True,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        browser_downloader=browser,  # type: ignore[arg-type]
    )
    result = resolver.resolve_one(
        CandidatePaper(
            paper_id="masked-gnn",
            title="Masked Graph Neural Networks for Multivariate Time Series",
            doi="https://doi.org/10.3390/S23177552",
            landing_url="https://doi.org/10.3390/s23177552",
            pdf_url="https://www.mdpi.com/1424-8220/23/17/7552/pdf",
        ),
        download_dir=tmp_path,
    )

    assert result.status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED
    assert result.metadata["resolution_strategy"] == "pmc_cloud_pdf"
    assert result.metadata["pmcid"] == "PMC10490803"
    assert result.metadata["fallback_count"] == 1
    assert result.metadata["attempted_pdf_urls"] == [
        "https://www.mdpi.com/1424-8220/23/17/7552/pdf"
    ]
    assert calls[0] == "https://www.mdpi.com/1424-8220/23/17/7552/pdf"
    assert not browser.calls


def test_resolver_uses_native_chrome_session_for_any_publisher_after_http_failure(
    tmp_path: Path,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, request=request)

    browser = FakeBrowserDownloader()
    resolver = PaperSourceResolver(
        network_enabled=True,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        browser_downloader=browser,  # type: ignore[arg-type]
    )
    paper = CandidatePaper(
        paper_id="publisher-paper",
        title="Relevant Publisher Paper",
        landing_url="https://journals.example.org/article/relevant-paper",
        pdf_url="https://journals.example.org/article/relevant-paper.pdf",
    )

    result = resolver.resolve_one(paper, download_dir=tmp_path)

    assert result.status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED
    assert result.metadata["resolution_strategy"] == "authorized_browser_session"
    assert result.metadata["browser_mode"] == "native_chrome_cdp"
    assert result.pdf_url == "https://journals.example.org/article/relevant-paper.pdf"
    assert Path(result.local_path).read_bytes().startswith(b"%PDF")
    assert len(browser.calls) == 1


def test_resolver_can_discover_pdf_from_landing_with_authorized_browser_session(
    tmp_path: Path,
) -> None:
    browser = FakeBrowserDownloader()
    resolver = PaperSourceResolver(
        network_enabled=True,
        browser_downloader=browser,  # type: ignore[arg-type]
    )
    paper = CandidatePaper(
        paper_id="landing-only",
        title="Landing Only Relevant Paper",
        landing_url="https://dl.acm.org/doi/10.1145/landing-only",
    )

    result = resolver.resolve_one(paper, download_dir=tmp_path)

    assert result.status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED
    assert result.metadata["resolution_strategy"] == "authorized_browser_session"
    assert browser.calls[0]["pdf_urls"] == []


@pytest.mark.parametrize(
    "landing_url",
    [
        "https://www.semanticscholar.org/paper/metadata-id",
        "https://doi.org/10.5555/metadata-only",
        "https://openalex.org/W123456789",
    ],
)
def test_resolver_does_not_open_chrome_for_metadata_only_landing_pages(
    tmp_path: Path,
    landing_url: str,
) -> None:
    browser = FakeBrowserDownloader()
    resolver = PaperSourceResolver(
        network_enabled=True,
        browser_downloader=browser,  # type: ignore[arg-type]
    )

    result = resolver.resolve_one(
        CandidatePaper(
            paper_id="metadata-only",
            title="Relevant Metadata Only Paper",
            landing_url=landing_url,
        ),
        download_dir=tmp_path,
    )

    assert result.status == PaperSourceStatus.RESOLVED_LANDING_ONLY
    assert result.download_status == "not_available"
    assert browser.calls == []


def test_resolver_preserves_native_chrome_failure_reason(tmp_path: Path) -> None:
    resolver = PaperSourceResolver(
        network_enabled=True,
        browser_downloader=FailingBrowserDownloader(),  # type: ignore[arg-type]
    )
    paper = CandidatePaper(
        paper_id="publisher-no-pdf",
        title="Relevant Publisher Paper Without PDF",
        landing_url="https://publisher.example.org/article/no-pdf",
    )

    result = resolver.resolve_one(paper, download_dir=tmp_path)

    assert result.status == PaperSourceStatus.FAILED_DOWNLOAD
    assert result.error_code == "BROWSER_PDF_NOT_FOUND"
    assert result.metadata["resolution_strategy"] == "authorized_browser_session_failed"
    assert result.metadata["browser_mode"] == "native_chrome_cdp"
