from __future__ import annotations

from pathlib import Path

import httpx

from researchsensei.schemas import CandidatePaper, PaperSourceStatus, SourcePriority
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
