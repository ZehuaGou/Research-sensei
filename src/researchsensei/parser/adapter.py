from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from researchsensei.schemas.document import ParserResult


class ParserAdapter(ABC):
    @abstractmethod
    def supports(self, source: Path) -> bool:
        """Return True if this adapter can parse the given source file."""
        ...

    @abstractmethod
    def parse(self, source: Path, paper_id: str) -> ParserResult:
        """Parse source into ParserResult. Must not write artifacts."""
        ...
