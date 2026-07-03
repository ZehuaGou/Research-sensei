from __future__ import annotations

from pathlib import Path

import pytest

from researchsensei.acquisition.arxiv_adapter import ArxivAdapter
from researchsensei.acquisition import FullTextResolver
from researchsensei.acquisition.google_scholar_adapter import GoogleScholarAdapter
from researchsensei.acquisition.openalex_adapter import OpenAlexAdapter
from researchsensei.acquisition.venue_registry import lookup_venue
from researchsensei.acquisition.semantic_scholar_adapter import SemanticScholarAdapter
from researchsensei.schemas import CandidatePaper
from researchsensei.selection import SelectionService

from scripts.run_literature_acquisition_acceptance import run_literature_acquisition_fixture, run_literature_acquisition_acceptance


class StubResponse:
    def __init__(self, payload: dict[str, object], *, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, object]:
        return self.payload


class HtmlResponse:
    def __init__(self, text: str, *, url: str, status_code: int = 200) -> None:
        self.text = text
        self.content = text.encode("utf-8")
        self.headers: dict[str, str] = {"content-type": "text/html"}
        self.url = url
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class LandingClient:
    def __init__(self, html: str) -> None:
        self.html = html
        self.calls: list[dict[str, object]] = []

    def get(self, url: str, **kwargs: object) -> HtmlResponse:
        self.calls.append({"url": url, **kwargs})
        return HtmlResponse(self.html, url=url)


class BinaryResponse:
    def __init__(self, content: bytes, *, url: str, content_type: str = "application/pdf", status_code: int = 200) -> None:
        self.content = content
        self.text = content.decode("latin1", errors="ignore")
        self.headers = {"content-type": content_type, "content-length": str(len(content))}
        self.url = url
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class LandingAndPdfClient:
    def __init__(self, html: str, pdf_url: str, pdf_content: bytes = b"%PDF-1.4\n% test\n") -> None:
        self.html = html
        self.pdf_url = pdf_url
        self.pdf_content = pdf_content
        self.calls: list[dict[str, object]] = []

    def get(self, url: str, **kwargs: object) -> HtmlResponse | BinaryResponse:
        self.calls.append({"url": url, **kwargs})
        if url == self.pdf_url:
            return BinaryResponse(self.pdf_content, url=url)
        return HtmlResponse(self.html, url=url)


class NoNetworkClient:
    def get(self, url: str, **kwargs: object) -> HtmlResponse:
        raise AssertionError(f"unexpected network call: {url}")


class OpenAlexWorksStub:
    def __init__(self, rows: list[dict[str, object]], *, fail: bool = False) -> None:
        self.rows = rows
        self.fail = fail
        self.search_queries: list[str] = []
        self.per_pages: list[int] = []

    def search(self, query: str) -> OpenAlexWorksStub:
        self.search_queries.append(query)
        if self.fail:
            raise RuntimeError("openalex generic search failed")
        return self

    def get(self, *, per_page: int) -> list[dict[str, object]]:
        self.per_pages.append(per_page)
        return self.rows[:per_page]


class OpenAlexHttpClient:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.calls: list[dict[str, object]] = []

    def get(self, url: str, **kwargs: object) -> StubResponse:
        self.calls.append({"url": url, **kwargs})
        return StubResponse({"results": self.rows})


class FakeGoogleScholarMcpSearch:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, int]] = []

    def __call__(self, query: str, num_results: int = 5) -> list[dict[str, object]]:
        self.calls.append((query, num_results))
        return self.rows[:num_results]


class SemanticScholarClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def get(self, url: str, **kwargs: object) -> StubResponse:
        self.calls.append({"url": url, **kwargs})
        query = str((kwargs.get("params") or {}).get("query") or "paper")
        return StubResponse({
            "data": [
                {
                    "paperId": f"s2-{len(self.calls)}",
                    "title": f"{query} Result",
                    "authors": [{"name": "A. Researcher"}],
                    "year": 2024,
                    "venue": "Conference",
                    "abstract": "A source-backed method paper.",
                    "citationCount": 12,
                    "externalIds": {"DOI": "10.1234/example"},
                    "openAccessPdf": {"url": "https://example.test/paper.pdf"},
                    "url": "https://semanticscholar.org/paper/test",
                }
            ]
        })


class RateLimitedSemanticScholarClient:
    def __init__(self) -> None:
        self.calls = 0

    def get(self, url: str, **kwargs: object) -> StubResponse:
        self.calls += 1
        return StubResponse({"message": "Too Many Requests"}, status_code=429)


class UnpaywallClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.urls: list[str] = []

    def get(self, url: str, **kwargs: object) -> StubResponse:
        self.urls.append(url)
        return StubResponse(self.payload)


class StaticAdapter:
    def __init__(self, papers: list[CandidatePaper]) -> None:
        self.papers = papers

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        return self.papers[:max_results]


class FailingAdapter:
    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        raise RuntimeError("429 Too Many Requests")


class RetryExhaustedArxivAdapter(ArxivAdapter):
    def __init__(self) -> None:
        super().__init__(timeout=1.0)
        self.calls = 0

    def _fetch_atom(self, query: str, *, max_results: int, id_list: list[str] | None = None) -> list[CandidatePaper]:
        self.calls += 1
        raise RuntimeError("arXiv API exhausted 3 retries after rate limited (429) for query")


def paper(**overrides: object) -> CandidatePaper:
    base = {
        "paper_id": "p1",
        "title": "Time Series Anomaly Detection with Legal Full Text",
        "authors": ["A. Researcher"],
        "year": 2024,
        "source": "openalex",
        "sources": ["openalex"],
        "source_ids": {"openalex": "p1"},
        "landing_url": "https://example.test/paper",
        "abstract": "A method paper for time series anomaly detection.",
        "source_confidence": "high",
        "metadata_confidence": "high",
    }
    base.update(overrides)
    return CandidatePaper(**base)


def openalex_row(
    *,
    work_id: str,
    title: str,
    venue: str,
    source_id: str,
    doi: str = "",
    pdf_url: str = "",
) -> dict[str, object]:
    location = {
        "pdf_url": pdf_url,
        "landing_page_url": f"https://example.test/{work_id}",
        "source": {
            "id": f"https://openalex.org/{source_id}",
            "display_name": venue,
        },
    }
    return {
        "id": f"https://openalex.org/{work_id}",
        "title": title,
        "doi": doi,
        "publication_year": 2024,
        "primary_location": location,
        "best_oa_location": location,
        "locations": [location],
        "open_access": {"is_oa": bool(pdf_url), "oa_status": "gold" if pdf_url else None, "oa_url": pdf_url},
        "cited_by_count": 12,
    }


def test_openalex_search_adds_ccf_venue_boost() -> None:
    generic = openalex_row(
        work_id="W-GENERIC",
        title="Generic Time Series Search Result",
        venue="arXiv.org",
        source_id="S4210160352",
    )
    venue = openalex_row(
        work_id="W-AAAI",
        title="AAAI Time Series Anomaly Detection",
        venue="Proceedings of the AAAI Conference on Artificial Intelligence",
        source_id="S4210191458",
    )
    works = OpenAlexWorksStub([generic])
    http_client = OpenAlexHttpClient([venue])
    adapter = OpenAlexAdapter(
        works=works,
        http_client=http_client,
        ccf_venue_source_ids=["S4210191458"],
        ccf_venue_boost_extra_results=4,
    )

    results = adapter.search("time series anomaly detection", max_results=1)

    assert [paper.title for paper in results] == [
        "AAAI Time Series Anomaly Detection",
        "Generic Time Series Search Result",
    ]
    assert http_client.calls
    params = http_client.calls[0]["params"]
    assert params["filter"] == "primary_location.source.id:S4210191458"
    assert params["search"] == "time series anomaly detection"


def test_openalex_ccf_venue_boost_can_cover_generic_search_failure() -> None:
    venue = openalex_row(
        work_id="W-AAAI",
        title="AAAI Time Series Anomaly Detection",
        venue="Proceedings of the AAAI Conference on Artificial Intelligence",
        source_id="S4210191458",
    )
    adapter = OpenAlexAdapter(
        works=OpenAlexWorksStub([], fail=True),
        http_client=OpenAlexHttpClient([venue]),
        ccf_venue_source_ids=["S4210191458"],
    )

    results = adapter.search("time series anomaly detection", max_results=3)

    assert len(results) == 1
    assert results[0].title == "AAAI Time Series Anomaly Detection"
    assert results[0].venue == "Proceedings of the AAAI Conference on Artificial Intelligence"


def test_google_scholar_adapter_maps_mcp_results_to_candidates() -> None:
    GoogleScholarAdapter.clear_cache()
    search = FakeGoogleScholarMcpSearch([
        {
            "Title": "Graph Neural Network-Based Anomaly Detection in Multivariate Time Series",
            "Authors": "A Deng, B Hooi - Proceedings of the AAAI Conference on Artificial Intelligence, 2021 - ojs.aaai.org",
            "Abstract": "We study graph neural network anomaly detection.",
            "URL": "https://arxiv.org/pdf/2106.06947.pdf",
        }
    ])
    adapter = GoogleScholarAdapter(
        search_function=search,
        min_request_interval_seconds=0,
        cache_ttl_seconds=0,
    )

    results = adapter.search("graph neural network anomaly detection", max_results=5)

    assert search.calls == [("graph neural network anomaly detection", 5)]
    assert len(results) == 1
    paper = results[0]
    assert paper.source == "google_scholar"
    assert paper.source_ids["google_scholar"] == "graph_neural_network_based_anomaly_detection_in_multivariate_time_series"
    assert paper.title == "Graph Neural Network-Based Anomaly Detection in Multivariate Time Series"
    assert paper.authors == ["A Deng", "B Hooi"]
    assert paper.year == 2021
    assert paper.venue == "Proceedings of the AAAI Conference on Artificial Intelligence"
    assert paper.abstract == "We study graph neural network anomaly detection."
    assert paper.arxiv_id == "2106.06947"
    assert paper.pdf_url == "https://arxiv.org/pdf/2106.06947.pdf"
    assert paper.can_deep_read is False
    assert "https://arxiv.org/pdf/2106.06947.pdf" in paper.candidate_pdf_urls
    assert paper.raw_source_metadata["mcp_project"] == "JackKuo666/Google-Scholar-MCP-Server"


def test_google_scholar_mcp_aaai_url_feeds_fulltext_resolver() -> None:
    GoogleScholarAdapter.clear_cache()
    aaai_url = "https://ojs.aaai.org/index.php/AAAI/article/download/16523/16330"
    adapter = GoogleScholarAdapter(
        search_function=FakeGoogleScholarMcpSearch([
            {
                "Title": "Graph Neural Network-Based Anomaly Detection in Multivariate Time Series",
                "Authors": "A Deng, B Hooi - Proceedings of the AAAI Conference on Artificial Intelligence, 2021 - ojs.aaai.org",
                "Abstract": "We study graph neural network anomaly detection.",
                "URL": aaai_url,
            }
        ]),
        min_request_interval_seconds=0,
        cache_ttl_seconds=0,
    )

    paper = adapter.search("graph neural network anomaly detection", max_results=5)[0]
    resolved, metrics = FullTextResolver(unpaywall_email="").resolve(paper)

    assert paper.pdf_url == aaai_url
    assert aaai_url in paper.candidate_pdf_urls
    assert resolved.fulltext_status == "pdf_ready"
    assert resolved.selected_fulltext_source == "publisher_oa_pdf"
    assert resolved.selected_fulltext_url == aaai_url
    assert resolved.can_deep_read is True
    assert metrics == []


def test_google_scholar_adapter_infers_venue_from_landing_url() -> None:
    GoogleScholarAdapter.clear_cache()
    adapter = GoogleScholarAdapter(
        search_function=FakeGoogleScholarMcpSearch([
            {
                "Title": "Graph Neural Network-Based Anomaly Detection in Multivariate Time Series",
                "Authors": "A Deng, B Hooi - 2021 - ojs.aaai.org",
                "Abstract": "We study graph neural network anomaly detection.",
                "URL": "https://ojs.aaai.org/index.php/AAAI/article/view/16523",
            }
        ]),
        min_request_interval_seconds=0,
        cache_ttl_seconds=0,
    )

    paper = adapter.search("graph neural network anomaly detection", max_results=5)[0]

    assert paper.year == 2021
    assert paper.venue == "AAAI"
    assert paper.raw_source_metadata["venue_inferred_from_url"] is True


def test_openalex_oa_pdf_is_recognized_as_fulltext_candidate() -> None:
    resolver = FullTextResolver(unpaywall_email="")
    candidate = paper(
        raw_source_metadata={
            "best_oa_location": {
                "pdf_url": "https://publisher.example/paper.pdf",
                "landing_page_url": "https://publisher.example/paper",
            }
        }
    )

    resolved, metrics = resolver.resolve(candidate)

    assert resolved.fulltext_status == "pdf_ready"
    assert resolved.can_deep_read is True
    assert resolved.needs_user_upload is False
    assert resolved.selected_fulltext_url == "https://publisher.example/paper.pdf"
    assert metrics == []


def test_openalex_oa_pdf_with_doi_does_not_require_unpaywall_email() -> None:
    resolver = FullTextResolver(unpaywall_email="")
    candidate = paper(
        doi="10.1234/example",
        raw_source_metadata={
            "best_oa_location": {
                "pdf_url": "https://publisher.example/paper.pdf",
                "landing_page_url": "https://publisher.example/paper",
            }
        },
    )

    resolved, metrics = resolver.resolve(candidate)

    assert resolved.fulltext_status == "pdf_ready"
    assert resolved.selected_fulltext_url == "https://publisher.example/paper.pdf"
    assert metrics == []


def test_known_oa_venue_landing_is_extracted_to_pdf() -> None:
    html = Path("tests/fixtures/oa_landing_pages/aaai_sample.html").read_text(encoding="utf-8")
    client = LandingClient(html)
    resolver = FullTextResolver(http_client=client, unpaywall_email="")
    candidate = paper(
        landing_url="https://ojs.aaai.org/index.php/AAAI/article/view/12345",
        raw_source_metadata={
            "best_oa_location": {
                "pdf_url": "",
                "landing_page_url": "https://ojs.aaai.org/index.php/AAAI/article/view/12345",
                "source": {
                    "id": "https://openalex.org/S4210191458",
                    "display_name": "AAAI Conference on Artificial Intelligence",
                },
            }
        },
    )

    resolved, metrics = resolver.resolve(candidate)

    assert resolved.fulltext_status == "pdf_ready"
    assert resolved.can_deep_read is True
    assert resolved.selected_fulltext_url == "https://ojs.aaai.org/index.php/AAAI/article/view/12345/15000"
    assert resolved.candidate_pdf_urls == ["https://ojs.aaai.org/index.php/AAAI/article/view/12345/15000"]
    assert metrics[0]["source"] == "landing_extractor:aaai"
    assert metrics[0]["success"] is True
    assert client.calls[0]["url"] == "https://ojs.aaai.org/index.php/AAAI/article/view/12345"


def test_official_landing_without_public_pdf_is_not_treated_as_fulltext() -> None:
    resolver = FullTextResolver(http_client=NoNetworkClient(), unpaywall_email="")

    resolved, metrics = resolver.resolve(
        paper(
            landing_url="https://dl.acm.org/doi/10.1145/1234567",
            raw_source_metadata={
                "best_oa_location": {
                    "pdf_url": "",
                    "landing_page_url": "https://dl.acm.org/doi/10.1145/1234567",
                    "source": {
                        "id": "https://openalex.org/S4306419648",
                        "display_name": "SIGMOD",
                    },
                }
            },
        )
    )

    assert resolved.fulltext_status == "metadata_only"
    assert resolved.can_deep_read is False
    assert resolved.needs_user_upload is True
    assert metrics[0]["source"] == "landing_extractor:acm_dl"
    assert metrics[0]["success"] is False


def test_acm_landing_pdf_url_requires_download_verification() -> None:
    html = """
    <html><head>
      <meta name="citation_pdf_url" content="https://dl.acm.org/doi/pdf/10.1145/1234567">
    </head><body><a href="/doi/pdf/10.1145/1234567">PDF</a></body></html>
    """
    client = LandingClient(html)
    resolver = FullTextResolver(http_client=client, unpaywall_email="")

    resolved, metrics = resolver.resolve(
        paper(
            landing_url="https://dl.acm.org/doi/10.1145/1234567",
            raw_source_metadata={
                "best_oa_location": {
                    "pdf_url": "",
                    "landing_page_url": "https://dl.acm.org/doi/10.1145/1234567",
                    "source": {"display_name": "ACM CHI"},
                }
            },
        )
    )

    assert resolved.fulltext_status == "metadata_only"
    assert resolved.can_deep_read is False
    assert resolved.fulltext_failure_reason == "PDF_URL_REQUIRES_DOWNLOAD_VERIFICATION"
    assert resolved.selected_fulltext_source == "official_pdf_url_unverified"
    assert resolved.selected_fulltext_url == "https://dl.acm.org/doi/pdf/10.1145/1234567"
    assert resolved.pdf_url == "https://dl.acm.org/doi/pdf/10.1145/1234567"
    assert metrics[0]["source"] == "landing_extractor:acm_dl"
    assert metrics[0]["success"] is True


def test_acm_landing_pdf_download_promotes_to_ready(tmp_path: Path) -> None:
    pdf_url = "https://dl.acm.org/doi/pdf/10.1145/1234567"
    html = f"""
    <html><head>
      <meta name="citation_pdf_url" content="{pdf_url}">
    </head><body><a href="/doi/pdf/10.1145/1234567">PDF</a></body></html>
    """
    client = LandingAndPdfClient(html, pdf_url)
    resolver = FullTextResolver(http_client=client, unpaywall_email="")

    resolved, metrics = resolver.resolve(
        paper(
            landing_url="https://dl.acm.org/doi/10.1145/1234567",
            raw_source_metadata={
                "best_oa_location": {
                    "pdf_url": "",
                    "landing_page_url": "https://dl.acm.org/doi/10.1145/1234567",
                    "source": {"display_name": "ACM CHI"},
                }
            },
        ),
        download=True,
        run_dir=tmp_path,
    )

    assert resolved.fulltext_status == "pdf_ready"
    assert resolved.can_deep_read is True
    assert resolved.selected_fulltext_source == "publisher_oa_pdf"
    assert resolved.selected_fulltext_url == pdf_url
    assert (tmp_path / "source.pdf").exists()
    assert [call["url"] for call in client.calls] == [
        "https://dl.acm.org/doi/10.1145/1234567",
        pdf_url,
    ]
    assert metrics[0]["source"] == "landing_extractor:acm_dl"


def test_venue_registry_covers_2026_ccf_a_conferences_and_journals() -> None:
    ccf_a_venues = [
        "PPoPP", "FAST", "DAC", "HPCA", "MICRO", "SC", "ASPLOS", "ISCA", "ACM SIGOPS ATC", "EuroSys", "HPDC",
        "SIGCOMM", "MobiCom", "INFOCOM", "NSDI",
        "CCS", "EUROCRYPT", "IEEE Symposium on Security and Privacy", "CRYPTO", "USENIX Security", "NDSS",
        "PLDI", "POPL", "FSE", "SOSP", "OOPSLA", "ASE", "ICSE", "ISSTA", "OSDI", "Formal Methods",
        "SIGMOD", "SIGKDD", "ICDE", "SIGIR", "VLDB",
        "STOC", "SODA", "CAV", "FOCS", "LICS",
        "ACM MM", "SIGGRAPH", "IEEE VR", "IEEE VIS",
        "AAAI", "NeurIPS", "ACL", "CVPR", "ICCV", "ICML", "ICLR",
        "CSCW", "CHI", "UbiComp", "UIST", "WWW", "RTSS",
        "ACM Transactions on Computer Systems", "ACM Transactions on Storage",
        "IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems",
        "IEEE Transactions on Computers", "IEEE Transactions on Parallel and Distributed Systems",
        "ACM Transactions on Architecture and Code Optimization",
        "IEEE Journal on Selected Areas in Communications", "IEEE Transactions on Mobile Computing",
        "IEEE Transactions on Networking", "IEEE Transactions on Dependable and Secure Computing",
        "IEEE Transactions on Information Forensics and Security", "Journal of Cryptology",
        "ACM Transactions on Programming Languages and Systems",
        "ACM Transactions on Software Engineering and Methodology", "IEEE Transactions on Software Engineering",
        "IEEE Transactions on Services Computing", "ACM Transactions on Database Systems",
        "ACM Transactions on Information Systems", "IEEE Transactions on Knowledge and Data Engineering",
        "The VLDB Journal", "IEEE Transactions on Information Theory", "Information and Computation",
        "SIAM Journal on Computing", "ACM Transactions on Graphics",
        "IEEE Transactions on Image Processing", "IEEE Transactions on Visualization and Computer Graphics",
        "IEEE Transactions on Multimedia", "Artificial Intelligence",
        "IEEE Transactions on Pattern Analysis and Machine Intelligence",
        "International Journal of Computer Vision", "Journal of Machine Learning Research",
        "ACM Transactions on Computer-Human Interaction", "International Journal of Human-Computer Studies",
        "Journal of the ACM", "Proceedings of the IEEE", "Science China Information Sciences", "Bioinformatics",
    ]

    missing = [venue for venue in ccf_a_venues if lookup_venue(venue) is None]

    assert missing == []


def test_openalex_preserves_locations_for_arxiv_crosslink() -> None:
    candidate = OpenAlexAdapter()._to_candidate(
        {
            "id": "https://openalex.org/W123",
            "title": "Venue Paper With Hidden Arxiv Copy",
            "publication_year": 2024,
            "primary_location": {
                "landing_page_url": "https://ojs.aaai.org/index.php/AAAI/article/view/12345",
                "source": {
                    "id": "https://openalex.org/S4210191458",
                    "display_name": "AAAI Conference on Artificial Intelligence",
                },
            },
            "best_oa_location": {
                "landing_page_url": "https://ojs.aaai.org/index.php/AAAI/article/view/12345",
                "source": {
                    "id": "https://openalex.org/S4210191458",
                    "display_name": "AAAI Conference on Artificial Intelligence",
                },
            },
            "locations": [
                {
                    "pdf_url": "https://arxiv.org/pdf/2401.12345",
                    "landing_page_url": "https://arxiv.org/abs/2401.12345",
                    "source": {
                        "id": "https://openalex.org/S4210160352",
                        "display_name": "arXiv.org",
                    },
                }
            ],
            "open_access": {"is_oa": True, "oa_status": "green", "oa_url": "https://arxiv.org/abs/2401.12345"},
        }
    )

    assert candidate.raw_source_metadata["locations"][0]["source"]["id"] == "https://openalex.org/S4210160352"

    resolved, _ = FullTextResolver(unpaywall_email="").resolve(candidate)

    assert resolved.arxiv_id == "2401.12345"
    assert resolved.selected_fulltext_source == "arxiv_source"
    assert resolved.fulltext_status == "source_ready"


def test_arxiv_search_propagates_retry_exhausted_rate_limit() -> None:
    adapter = RetryExhaustedArxivAdapter()

    with pytest.raises(RuntimeError, match="rate limited"):
        adapter.search("graph anomaly detection", max_results=2)

    assert adapter.calls == 1


def test_doi_can_find_legal_pdf_through_unpaywall() -> None:
    client = UnpaywallClient(
        {
            "best_oa_location": {
                "url_for_pdf": "https://repository.example/oa-paper.pdf",
                "url_for_landing_page": "https://repository.example/oa-paper",
            }
        }
    )
    resolver = FullTextResolver(http_client=client, unpaywall_email="sensei@example.test")

    resolved, metrics = resolver.resolve(paper(doi="10.1234/example"))

    assert resolved.fulltext_status == "pdf_ready"
    assert resolved.selected_fulltext_url == "https://repository.example/oa-paper.pdf"
    assert resolved.can_deep_read is True
    assert metrics[0]["source"] == "unpaywall"
    assert metrics[0]["success"] is True


def test_doi_url_can_find_legal_pdf_from_secondary_unpaywall_location() -> None:
    client = UnpaywallClient(
        {
            "best_oa_location": None,
            "oa_locations": [
                {
                    "url_for_pdf": "https://repo.example.org/accepted-paper.pdf",
                    "url_for_landing_page": "https://repo.example.org/accepted-paper",
                }
            ],
        }
    )
    resolver = FullTextResolver(http_client=client, unpaywall_email="sensei@example.test")

    resolved, metrics = resolver.resolve(paper(doi="https://doi.org/10.1234/example"))

    assert resolved.fulltext_status == "pdf_ready"
    assert resolved.selected_fulltext_url == "https://repo.example.org/accepted-paper.pdf"
    assert resolved.can_deep_read is True
    assert "10.1234%2Fexample" in client.urls[0]
    assert metrics[0]["success"] is True


def test_doi_without_oa_fulltext_remains_metadata_only_with_reason() -> None:
    resolver = FullTextResolver(unpaywall_email="")

    resolved, metrics = resolver.resolve(paper(source="crossref", sources=["crossref"], doi="10.1234/closed"))

    assert resolved.fulltext_status == "metadata_only"
    assert resolved.can_deep_read is False
    assert resolved.needs_user_upload is True
    assert resolved.fulltext_failure_reason == "UNPAYWALL_EMAIL_MISSING"
    assert metrics[0]["error"] == "UNPAYWALL_EMAIL_MISSING"


def test_crossref_metadata_only_is_not_marked_fulltext_ready() -> None:
    resolver = FullTextResolver(unpaywall_email="")

    resolved, _ = resolver.resolve(paper(source="crossref", sources=["crossref"], doi="", pdf_url=""))

    assert resolved.fulltext_status == "metadata_only"
    assert resolved.can_deep_read is False
    assert resolved.needs_user_upload is True
    assert resolved.fulltext_failure_reason == "NO_ARXIV_OR_OA_PDF_URL"


def test_arxiv_source_first_still_precedes_pdf() -> None:
    resolver = FullTextResolver(unpaywall_email="")

    resolved, _ = resolver.resolve(
        paper(
            source="arxiv",
            sources=["arxiv"],
            arxiv_id="2401.00001",
            pdf_url="https://arxiv.org/pdf/2401.00001.pdf",
        )
    )

    assert resolved.selected_fulltext_source == "arxiv_source"
    assert resolved.fulltext_status == "source_ready"
    assert resolved.candidate_source_urls == ["https://arxiv.org/e-print/2401.00001"]


def test_openalex_arxiv_landing_gets_source_first_without_fake_id() -> None:
    resolver = FullTextResolver(unpaywall_email="")

    resolved, _ = resolver.resolve(
        paper(
            source="openalex",
            sources=["openalex"],
            doi="https://doi.org/10.48550/arxiv.2107.03502",
            landing_url="http://arxiv.org/abs/2107.03502",
            pdf_url="https://arxiv.org/pdf/2107.03502",
        )
    )

    assert resolved.arxiv_id == "2107.03502"
    assert resolved.selected_fulltext_source == "arxiv_source"
    assert resolved.fulltext_status == "source_ready"
    assert resolved.candidate_source_urls == ["https://arxiv.org/e-print/2107.03502"]


def test_multiple_sources_merge_preserves_discovery_and_fulltext_urls() -> None:
    service = SelectionService()

    merged = service.deduplicate(
        [
            paper(
                paper_id="openalex-1",
                source="openalex",
                sources=["openalex"],
                source_ids={"openalex": "openalex-1"},
                doi="10.1234/example",
                pdf_url="https://publisher.example/paper.pdf",
            ),
            paper(
                paper_id="crossref-1",
                source="crossref",
                sources=["crossref"],
                source_ids={"crossref": "crossref-1"},
                doi="10.1234/example",
                landing_url="https://doi.org/10.1234/example",
            ),
        ]
    )[0]

    assert set(merged.sources) == {"openalex", "crossref"}
    assert merged.source_ids["openalex"] == "openalex-1"
    assert merged.source_ids["crossref"] == "crossref-1"
    assert "https://publisher.example/paper.pdf" in merged.candidate_pdf_urls
    assert merged.candidate_html_urls == []


def test_acceptance_keeps_metadata_only_candidates_visible(tmp_path: Path) -> None:
    result = run_literature_acquisition_acceptance(
        query="time series anomaly detection",
        max_results=5,
        download_top_n=0,
        sources=["crossref"],
        workspace=tmp_path,
        adapters={"crossref": StaticAdapter([paper(source="crossref", sources=["crossref"], doi="")])},
        fulltext_resolver=FullTextResolver(unpaywall_email=""),
    )

    assert result["total_candidates"] == 1
    assert result["metadata_only_count"] == 1
    assert result["metadata_only_after_unpaywall_count"] == 0
    assert result["selected_fulltext_source_counts"] == {"metadata_only": 1}
    assert result["oa_pdf_found_count"] == 0
    assert result["top_candidates"][0]["needs_user_upload"] is True
    assert result["top_candidates"][0]["can_deep_read"] is False
    assert result["verdict"] == "DEGRADED"


def test_semantic_scholar_429_does_not_fail_entire_acceptance(tmp_path: Path) -> None:
    result = run_literature_acquisition_acceptance(
        query="time series anomaly detection",
        max_results=5,
        download_top_n=0,
        sources=["arxiv", "semantic_scholar"],
        workspace=tmp_path,
        adapters={
            "arxiv": StaticAdapter([paper(source="arxiv", sources=["arxiv"], arxiv_id="2401.00001")]),
            "semantic_scholar": FailingAdapter(),
        },
        fulltext_resolver=FullTextResolver(unpaywall_email=""),
    )

    assert result["total_candidates"] == 1
    assert result["source_metrics"]["semantic_scholar"]["failure_count"] == 1
    assert "ACQUISITION_FAILED:semantic_scholar" in result["warnings"][0]
    assert result["verdict"] == "PASS"


def test_acquisition_fixture_mode_checks_minimum_expectations(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.json"
    fixture.write_text(
        """
        {
          "queries": [
            {
              "query": "time series anomaly detection",
              "min_total_candidates": 1,
              "min_non_arxiv": 0,
              "min_legal_fulltext": 1,
              "min_source_ready": 1,
              "expected_attempted_sources": ["arxiv"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    result = run_literature_acquisition_fixture(
        fixture_path=fixture,
        max_results=5,
        download_top_n=0,
        sources=["arxiv"],
        workspace=tmp_path / "workspace",
        adapters={"arxiv": StaticAdapter([paper(source="arxiv", sources=["arxiv"], arxiv_id="2401.00001")])},
        fulltext_resolver=FullTextResolver(unpaywall_email=""),
    )

    assert result["verdict"] == "PASS"
    assert result["query_count"] == 1
    assert result["results"][0]["expectation_failures"] == []


def test_semantic_scholar_api_key_alias_is_supported(monkeypatch) -> None:
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    monkeypatch.setenv("S2_API_KEY", "alias-key")

    adapter = SemanticScholarAdapter()

    assert adapter.api_key == "alias-key"


def test_semantic_scholar_search_uses_shared_success_cache() -> None:
    SemanticScholarAdapter.clear_cache()
    client = SemanticScholarClient()
    adapter = SemanticScholarAdapter(
        http_client=client,
        cache_ttl_seconds=60,
        min_request_interval_seconds=0,
    )
    try:
        first = adapter.search("time series anomaly detection", max_results=3)
        second = adapter.search(" time series anomaly detection ", max_results=3)
    finally:
        SemanticScholarAdapter.clear_cache()

    assert len(client.calls) == 1
    assert first[0].title == "time series anomaly detection Result"
    assert second[0].title == first[0].title


def test_semantic_scholar_uncached_requests_share_polite_throttle() -> None:
    class ManualClock:
        def __init__(self) -> None:
            self.now = 100.0

        def __call__(self) -> float:
            return self.now

    clock = ManualClock()
    waits: list[float] = []

    def sleeper(seconds: float) -> None:
        waits.append(seconds)
        clock.now += seconds

    SemanticScholarAdapter.clear_cache()
    client = SemanticScholarClient()
    adapter = SemanticScholarAdapter(
        http_client=client,
        cache_ttl_seconds=0,
        min_request_interval_seconds=1.25,
        clock=clock,
        sleeper=sleeper,
    )
    try:
        adapter.search("query one", max_results=1)
        adapter.search("query two", max_results=1)
    finally:
        SemanticScholarAdapter.clear_cache()

    assert len(client.calls) == 2
    assert waits == [1.25]


def test_semantic_scholar_rate_limit_enters_shared_cooldown() -> None:
    class ManualClock:
        def __init__(self) -> None:
            self.now = 100.0

        def __call__(self) -> float:
            return self.now

    clock = ManualClock()
    waits: list[float] = []

    def sleeper(seconds: float) -> None:
        waits.append(seconds)
        clock.now += seconds

    SemanticScholarAdapter.clear_cache()
    client = RateLimitedSemanticScholarClient()
    adapter = SemanticScholarAdapter(
        http_client=client,
        cache_ttl_seconds=0,
        min_request_interval_seconds=0,
        rate_limit_cooldown_seconds=60,
        clock=clock,
        sleeper=sleeper,
    )
    try:
        try:
            adapter.search("rate limited query", max_results=1)
        except RuntimeError as exc:
            assert "rate limited" in str(exc).lower()
        try:
            adapter.search("second query", max_results=1)
        except RuntimeError as exc:
            assert "cooldown active" in str(exc)
    finally:
        SemanticScholarAdapter.clear_cache()

    assert client.calls == 1
    assert waits == [3.0]
