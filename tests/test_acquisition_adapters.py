from __future__ import annotations

import httpx

from researchsensei.acquisition.arxiv_adapter import ArxivAdapter
from researchsensei.acquisition.openalex_adapter import OpenAlexAdapter

# Sample arXiv Atom XML response
ARXIV_SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345v1</id>
    <title>Time Series Anomaly Detection with Transformers</title>
    <summary>We propose a transformer-based approach for detecting anomalies in multivariate time series data.</summary>
    <published>2023-01-30T00:00:00Z</published>
    <author><name>John Doe</name></author>
    <author><name>Jane Smith</name></author>
    <link title="pdf" href="http://arxiv.org/pdf/2301.12345v1"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2302.67890v1</id>
    <title>A Survey of Anomaly Detection Methods</title>
    <summary>This paper surveys modern anomaly detection techniques.</summary>
    <published>2022-06-15T00:00:00Z</published>
    <author><name>Alice Johnson</name></author>
  </entry>
</feed>
"""

# Sample OpenAlex JSON response
OPENALEX_SAMPLE_JSON = {
    "results": [
        {
            "id": "https://openalex.org/W1234567890",
            "title": "Deep Learning for Time Series Anomaly Detection",
            "publication_year": 2023,
            "doi": "https://doi.org/10.1234/example",
            "cited_by_count": 150,
            "primary_location": {
                "source": {"display_name": "ICML 2023"}
            },
            "authorships": [
                {"author": {"display_name": "Bob Wilson"}},
                {"author": {"display_name": "Carol Lee"}},
            ],
            "abstract_inverted_index": {
                "We": [0],
                "study": [1],
                "anomaly": [2],
                "detection": [3],
                "in": [4],
                "time": [5],
                "series": [6],
            },
        }
    ]
}


def test_arxiv_adapter_parses_xml() -> None:
    adapter = ArxivAdapter()
    results = adapter._parse_response(ARXIV_SAMPLE_XML)

    assert len(results) == 2
    assert results[0].title == "Time Series Anomaly Detection with Transformers"
    assert results[0].arxiv_id == "2301.12345v1"
    assert results[0].year == 2023
    assert results[0].venue == "arXiv"
    assert len(results[0].authors) == 2
    assert results[0].pdf_url == "http://arxiv.org/pdf/2301.12345v1"
    assert "transformer" in results[0].abstract.lower()


def test_arxiv_adapter_handles_empty_xml() -> None:
    adapter = ArxivAdapter()
    results = adapter._parse_response('<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>')

    assert len(results) == 0


def test_arxiv_adapter_handles_invalid_xml() -> None:
    adapter = ArxivAdapter()
    results = adapter._parse_response("not xml at all")

    assert len(results) == 0


def test_arxiv_adapter_mock_transport() -> None:
    """Test arXiv adapter with mocked HTTP transport."""

    def _mock_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=ARXIV_SAMPLE_XML, headers={"content-type": "application/atom+xml"})

    transport = httpx.MockTransport(_mock_request)
    client = httpx.Client(transport=transport)
    adapter = ArxivAdapter(http_client=client)

    results = adapter.search("time series anomaly detection")

    assert len(results) == 2
    assert results[0].source == "arxiv"


def test_openalex_adapter_parses_json() -> None:
    adapter = OpenAlexAdapter()
    results = adapter._parse_response(OPENALEX_SAMPLE_JSON)

    assert len(results) == 1
    assert results[0].title == "Deep Learning for Time Series Anomaly Detection"
    assert results[0].year == 2023
    assert results[0].venue == "ICML 2023"
    assert results[0].citation_count == 150
    assert len(results[0].authors) == 2
    assert "anomaly" in results[0].abstract.lower()


def test_openalex_adapter_handles_empty_results() -> None:
    adapter = OpenAlexAdapter()
    results = adapter._parse_response({"results": []})

    assert len(results) == 0


def test_openalex_adapter_mock_transport() -> None:
    """Test OpenAlex adapter with mocked HTTP transport."""
    import json

    def _mock_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=json.dumps(OPENALEX_SAMPLE_JSON), headers={"content-type": "application/json"})

    transport = httpx.MockTransport(_mock_request)
    client = httpx.Client(transport=transport)
    adapter = OpenAlexAdapter(http_client=client)

    results = adapter.search("time series anomaly detection")

    assert len(results) == 1
    assert results[0].source == "openalex"
