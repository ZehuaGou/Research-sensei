from __future__ import annotations

from pathlib import Path

from researchsensei.ingestion.lightweight import LightweightIngestionService
from researchsensei.parser import LightweightParserAdapter, ParserAdapter
from researchsensei.schemas import DocumentIngestion, ParseMetadata, ParserResult


def test_parser_adapter_is_abstract() -> None:
    try:
        ParserAdapter()  # type: ignore[abstract]
        assert False, "Should have raised TypeError"
    except TypeError:
        pass


def test_lightweight_adapter_supports_md_txt_pdf(tmp_path: Path) -> None:
    adapter = LightweightParserAdapter()

    assert adapter.supports(tmp_path / "paper.md") is True
    assert adapter.supports(tmp_path / "paper.txt") is True
    assert adapter.supports(tmp_path / "paper.pdf") is True
    assert adapter.supports(tmp_path / "paper.MD") is True
    assert adapter.supports(tmp_path / "paper.TXT") is True
    assert adapter.supports(tmp_path / "paper.PDF") is True
    assert adapter.supports(tmp_path / "paper.markdown") is False
    assert adapter.supports(tmp_path / "paper.docx") is False


def test_lightweight_adapter_returns_parser_result(tmp_path: Path) -> None:
    path = tmp_path / "paper.md"
    path.write_text(
        "# Paper\n## Abstract\nWe study anomaly detection.\n\n## Method\nWe propose a model.",
        encoding="utf-8",
    )
    adapter = LightweightParserAdapter()

    result = adapter.parse(path, paper_id="p1")

    assert isinstance(result, ParserResult)
    assert isinstance(result.document, DocumentIngestion)
    assert isinstance(result.metadata, ParseMetadata)
    assert result.metadata.parser_name == "lightweight"
    assert result.metadata.source_format == "md"


def test_lightweight_adapter_matches_original_output(tmp_path: Path) -> None:
    path = tmp_path / "paper.md"
    path.write_text(
        "# Paper\n## Abstract\nWe study anomaly detection.\n\n## Method\nWe minimize L = L_rec.\n\n## Experiments\nTable 1 reports F1.",
        encoding="utf-8",
    )
    service = LightweightIngestionService()
    adapter = LightweightParserAdapter(ingestion=service)

    original = service.ingest_path(path, paper_id="p1")
    result = adapter.parse(path, paper_id="p1")

    assert result.document.paper_id == original.paper_id
    assert result.document.detected_language == original.detected_language
    assert result.document.degraded == original.degraded
    assert len(result.document.warnings) == len(original.warnings)
    assert len(result.document.blocks) == len(original.blocks)
    for result_block, original_block in zip(result.document.blocks, original.blocks):
        assert result_block.block_id == original_block.block_id
        assert result_block.type == original_block.type
        assert result_block.section == original_block.section
        assert result_block.text == original_block.text
        assert result_block.evidence_ref == original_block.evidence_ref


def test_lightweight_adapter_does_not_write_artifacts(tmp_path: Path) -> None:
    path = tmp_path / "paper.md"
    path.write_text("# Paper\n## Abstract\nSome text.", encoding="utf-8")
    adapter = LightweightParserAdapter()

    adapter.parse(path, paper_id="p1")

    json_files = list(tmp_path.rglob("*.json"))
    assert json_files == []


def test_lightweight_adapter_uses_injected_service(tmp_path: Path) -> None:
    path = tmp_path / "paper.md"
    path.write_text("# Paper\n## Abstract\nSome text.", encoding="utf-8")

    call_log: list[tuple[str, str | None]] = []

    class FakeService:
        def ingest_path(self, path: str | Path, paper_id: str | None = None) -> DocumentIngestion:
            call_log.append((str(path), paper_id))
            return DocumentIngestion(paper_id=paper_id or "fake", blocks=[])

    fake = FakeService()
    adapter = LightweightParserAdapter(ingestion=fake)  # type: ignore[arg-type]

    result = adapter.parse(path, paper_id="test-id")

    assert len(call_log) == 1
    assert call_log[0][1] == "test-id"
    assert result.document.paper_id == "test-id"


def test_lightweight_adapter_propagates_degraded(tmp_path: Path) -> None:
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"not a valid pdf")
    adapter = LightweightParserAdapter()

    result = adapter.parse(path, paper_id="p1")

    assert result.document.degraded is True
    assert len(result.document.warnings) > 0
