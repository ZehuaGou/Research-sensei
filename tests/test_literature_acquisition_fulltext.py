from __future__ import annotations

from pathlib import Path

import pytest

from researchsensei.acquisition.arxiv_adapter import ArxivAdapter
from researchsensei.acquisition import FullTextResolver
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
