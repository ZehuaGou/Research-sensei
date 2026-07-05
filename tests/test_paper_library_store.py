from __future__ import annotations

from pathlib import Path

from researchsensei.library import PaperLibraryStore
from researchsensei.schemas import CandidatePaper, PaperSourceStatus, PaperSourceType, ResolvedPaperSource, VenueRank


PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def _candidate(**overrides: object) -> CandidatePaper:
    base = {
        "paper_id": "paper-search-1",
        "title": "Graph Neural Network Based Anomaly Detection in Multivariate Time Series",
        "authors": ["A. Researcher", "B. Scientist"],
        "year": 2024,
        "venue": "Proceedings of the AAAI Conference on Artificial Intelligence",
        "venue_rank": VenueRank.A_STAR,
        "doi": "10.1234/example",
        "pdf_url": "https://example.test/paper.pdf",
        "landing_url": "https://example.test/paper",
        "source": "paper_search",
        "sources": ["paper_search"],
        "source_ids": {"paper_search": "paper-search-1"},
    }
    base.update(overrides)
    return CandidatePaper(**base)


def _resolved(paper: CandidatePaper, path: Path, strategy: str = "downloaded_validated_pdf") -> ResolvedPaperSource:
    return ResolvedPaperSource(
        paper_id=paper.paper_id,
        title=paper.title,
        doi=paper.doi,
        arxiv_id=paper.arxiv_id,
        pdf_url=paper.pdf_url,
        landing_url=paper.landing_url,
        source_type=PaperSourceType.PDF,
        status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,
        download_status="downloaded",
        local_path=str(path),
        sha256="a" * 64,
        file_size=path.stat().st_size,
        has_valid_deep_reading_source=True,
        metadata={"resolution_strategy": strategy},
    )


def test_paper_library_upserts_and_finds_downloaded_paper(tmp_path: Path) -> None:
    db = PaperLibraryStore(tmp_path / "sensei.sqlite3")
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(PDF_BYTES)
    paper = _candidate()

    record = db.upsert_download(paper, _resolved(paper, pdf))
    match = db.find_match(_candidate(paper_id="paper-search-2", doi="https://doi.org/10.1234/example"))

    assert record is not None
    assert match is not None
    assert match.paper_id == record.paper_id
    assert match.title == paper.title
    assert match.local_path == str(pdf.resolve())


def test_paper_library_records_search_actions(tmp_path: Path) -> None:
    db = PaperLibraryStore(tmp_path / "sensei.sqlite3")
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(PDF_BYTES)
    paper = _candidate(download_selected=True)

    summary = db.record_search(
        query="time series anomaly detection",
        candidates=[paper],
        items=[_resolved(paper, pdf, strategy="library_reuse")],
        topic_folder=str(tmp_path),
    )
    runs = db.list_search_runs()

    assert summary["reused_count"] == 1
    assert runs[0]["query"] == "time series anomaly detection"
    assert runs[0]["papers"][0]["action"] == "reused"
    assert runs[0]["papers"][0]["download_selected"] is True


def test_paper_library_records_original_search_rank(tmp_path: Path) -> None:
    db = PaperLibraryStore(tmp_path / "sensei.sqlite3")
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(PDF_BYTES)
    paper = _candidate(
        download_selected=True,
        raw_source_metadata={"rank": 7, "provider": "paper-search-mcp"},
    )

    db.record_search(
        query="graph anomaly detection",
        candidates=[paper],
        items=[_resolved(paper, pdf)],
        topic_folder=str(tmp_path),
    )
    runs = db.list_search_runs()

    assert runs[0]["papers"][0]["search_rank"] == 7


def test_paper_library_delete_marks_record_and_removes_file(tmp_path: Path) -> None:
    db = PaperLibraryStore(tmp_path / "sensei.sqlite3")
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(PDF_BYTES)
    paper = _candidate()
    record = db.upsert_download(paper, _resolved(paper, pdf))

    assert record is not None
    assert db.delete_paper(record.paper_id) is True

    assert not pdf.exists()
    assert db.find_match(paper) is None
    deleted = db.list_papers(include_deleted=True)
    assert deleted[0]["deleted_at"]
