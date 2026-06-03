from __future__ import annotations

from pathlib import Path

from researchsensei.ingestion.lightweight import LightweightIngestionService
from researchsensei.parser.adapter import ParserAdapter
from researchsensei.schemas.document import ParseMetadata, ParserResult

SUPPORTED_SUFFIXES = {".md", ".txt", ".pdf"}


class LightweightParserAdapter(ParserAdapter):
    def __init__(self, ingestion: LightweightIngestionService | None = None) -> None:
        self.ingestion = ingestion or LightweightIngestionService()

    def supports(self, source: Path) -> bool:
        return source.suffix.lower() in SUPPORTED_SUFFIXES

    def parse(self, source: Path, paper_id: str) -> ParserResult:
        document = self.ingestion.ingest_path(source, paper_id=paper_id)
        return ParserResult(
            document=document,
            metadata=ParseMetadata(
                parser_name="lightweight",
                source_format=source.suffix.lower().lstrip("."),
            ),
        )
