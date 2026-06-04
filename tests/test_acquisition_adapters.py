from __future__ import annotations

from datetime import datetime, timezone

from researchsensei.acquisition import ArxivAdapter, CrossrefAdapter, OpenAlexAdapter, SemanticScholarAdapter


class _Author:
    def __init__(self, name: str) -> None:
        self.name = name


class _ArxivResult:
    title = "Time Series Anomaly Detection with Transformers"
    summary = "We propose a transformer approach for anomaly detection in time series."
    entry_id = "https://arxiv.org/abs/2301.12345v1"
    pdf_url = "https://arxiv.org/pdf/2301.12345v1.pdf"
    published = datetime(2023, 1, 1, tzinfo=timezone.utc)
    updated = datetime(2023, 1, 2, tzinfo=timezone.utc)
    authors = [_Author("John Doe"), _Author("Jane Smith")]

    def get_short_id(self) -> str:
        return "2301.12345v1"


class _ArxivClient:
    def results(self, search):
        assert search.query == "time series anomaly detection"
        return [_ArxivResult()]


def test_arxiv_adapter_uses_arxiv_package_client() -> None:
    results = ArxivAdapter(client=_ArxivClient()).search("time series anomaly detection", max_results=1)

    assert len(results) == 1
    paper = results[0]
    assert paper.source == "arxiv"
    assert paper.sources == ["arxiv"]
    assert paper.arxiv_id == "2301.12345v1"
    assert paper.pdf_available is True
    assert paper.source_url == "https://arxiv.org/e-print/2301.12345v1"


class _OpenAlexQuery:
    def get(self, per_page: int):
        assert per_page == 1
        return [
            {
                "id": "https://openalex.org/W123",
                "title": "Deep Learning for Time Series Anomaly Detection",
                "publication_year": 2023,
                "doi": "https://doi.org/10.1234/example",
                "cited_by_count": 150,
                "primary_location": {
                    "source": {"display_name": "ICML 2023"},
                    "landing_page_url": "https://example.org/paper",
                },
                "best_oa_location": {
                    "pdf_url": "https://example.org/paper.pdf",
                    "landing_page_url": "https://example.org/paper",
                },
                "open_access": {"is_oa": True, "oa_status": "gold"},
                "authorships": [{"author": {"display_name": "Bob Wilson"}}],
                "abstract_inverted_index": {"We": [0], "study": [1], "anomaly": [2], "detection": [3]},
            }
        ]


class _OpenAlexWorks:
    def search(self, query: str):
        assert query == "time series anomaly detection"
        return _OpenAlexQuery()


def test_openalex_adapter_uses_pyalex_works() -> None:
    results = OpenAlexAdapter(works=_OpenAlexWorks()).search("time series anomaly detection", max_results=1)

    assert len(results) == 1
    paper = results[0]
    assert paper.source == "openalex"
    assert paper.doi == "https://doi.org/10.1234/example"
    assert paper.venue == "ICML 2023"
    assert paper.citation_count == 150
    assert paper.pdf_available is True


class _SemanticScholarClient:
    def search_paper(self, query: str, *, limit: int, fields: list[str]):
        assert query == "time series anomaly detection"
        assert limit == 1
        assert "paperId" in fields
        return [
            {
                "paperId": "S2-123",
                "title": "Graph Neural Network-Based Anomaly Detection in Multivariate Time Series",
                "authors": [{"name": "Alice"}],
                "year": 2021,
                "venue": "AAAI",
                "abstract": "Graph anomaly detection for multivariate time series.",
                "tldr": {"text": "GNN for TSAD."},
                "citationCount": 200,
                "externalIds": {"DOI": "10.5555/tsad", "ArXiv": "2101.00001"},
                "openAccessPdf": {"url": "https://example.org/gdn.pdf"},
                "url": "https://semanticscholar.org/paper/S2-123",
            }
        ]


def test_semantic_scholar_adapter_uses_package_client() -> None:
    results = SemanticScholarAdapter(client=_SemanticScholarClient()).search("time series anomaly detection", max_results=1)

    assert len(results) == 1
    paper = results[0]
    assert paper.source == "semantic_scholar"
    assert paper.semantic_scholar_id == "S2-123"
    assert paper.arxiv_id == "2101.00001"
    assert paper.pdf_available is True


class _CrossrefClient:
    def works(self, *, query: str, limit: int):
        assert query == "time series anomaly detection"
        assert limit == 1
        return {
            "message": {
                "items": [
                    {
                        "DOI": "10.1000/example",
                        "title": ["A Survey of Time Series Anomaly Detection"],
                        "container-title": ["Proceedings of the IEEE"],
                        "author": [{"given": "Carol", "family": "Lee"}],
                        "issued": {"date-parts": [[2022]]},
                        "URL": "https://doi.org/10.1000/example",
                        "abstract": "Survey abstract.",
                        "type": "journal-article",
                        "publisher": "IEEE",
                    }
                ]
            }
        }


def test_crossref_adapter_uses_habanero_client() -> None:
    results = CrossrefAdapter(client=_CrossrefClient()).search("time series anomaly detection", max_results=1)

    assert len(results) == 1
    paper = results[0]
    assert paper.source == "crossref"
    assert paper.doi == "10.1000/example"
    assert paper.venue == "Proceedings of the IEEE"
    assert paper.year == 2022
