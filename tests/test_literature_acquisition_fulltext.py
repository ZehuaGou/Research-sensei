from __future__ import annotations

from pathlib import Path

from researchsensei.acquisition import FullTextResolver
from researchsensei.schemas import CandidatePaper
from researchsensei.selection import SelectionService

from scripts.run_literature_acquisition_smoke import run_literature_acquisition_smoke


class StubResponse:
    def __init__(self, payload: dict[str, object], *, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, object]:
        return self.payload


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


def test_smoke_keeps_metadata_only_candidates_visible(tmp_path: Path) -> None:
    result = run_literature_acquisition_smoke(
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
    assert result["verdict"] == "DEGRADED_PASS"


def test_semantic_scholar_429_does_not_fail_entire_smoke(tmp_path: Path) -> None:
    result = run_literature_acquisition_smoke(
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
