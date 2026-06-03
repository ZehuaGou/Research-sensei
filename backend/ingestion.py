from __future__ import annotations

import re

from backend.schemas import BlockType, DocumentBlock, DocumentIngestion


SECTION_ALIASES = {
    "abstract": "abstract",
    "introduction": "introduction",
    "related work": "related_work",
    "method": "method",
    "methods": "method",
    "experiments": "experiments",
    "experiment": "experiments",
    "results": "experiments",
    "conclusion": "conclusion",
}


class IngestionService:
    """Safe lightweight text ingestion with block-level output."""

    def ingest_text(self, paper_id: str, text: str) -> DocumentIngestion:
        detected_language = self._detect_language(text)
        sections = self._split_sections(text)
        blocks: list[DocumentBlock] = []
        formula_count = 0
        paragraph_count = 0
        offset = 0
        for section, body in sections.items():
            blocks.append(DocumentBlock(
                block_id=f"h{len(blocks)+1:03d}",
                type=BlockType.HEADING,
                section=section,
                text=section,
                normalized_text=section,
                offset_start=offset,
                offset_end=offset + len(section),
                evidence_ref=f"{paper_id}:h{len(blocks)+1:03d}",
            ))
            for para in [p.strip() for p in re.split(r"\n\s*\n|(?<=\.)\s+(?=[A-Z])", body) if p.strip()]:
                formula_match = re.search(r"\b([A-Z]\s*=\s*[^.;\n]+|\\mathcal\{[^}]+\}\s*=.+)", para)
                if formula_match:
                    formula_count += 1
                    block_id = f"eq{formula_count:03d}"
                    blocks.append(DocumentBlock(
                        block_id=block_id,
                        type=BlockType.FORMULA,
                        section=section,
                        raw_latex=formula_match.group(1).strip(),
                        nearby_text=para,
                        equation_number=str(formula_count),
                        evidence_ref=f"{paper_id}:{block_id}",
                    ))
                paragraph_count += 1
                block_id = f"b{paragraph_count:03d}"
                blocks.append(DocumentBlock(
                    block_id=block_id,
                    type=BlockType.PARAGRAPH if section != "abstract" else BlockType.ABSTRACT,
                    section=section,
                    text=para,
                    normalized_text=" ".join(para.lower().split()),
                    offset_start=offset,
                    offset_end=offset + len(para),
                    evidence_ref=f"{paper_id}:{block_id}",
                ))
                offset += len(para) + 1
        formulas = [block for block in blocks if block.type == BlockType.FORMULA]
        warnings = []
        if not formulas:
            warnings.append("FORMULA_UNAVAILABLE")
        if "method" not in sections:
            warnings.append("METHOD_SECTION_MISSING")
        if "experiments" not in sections:
            warnings.append("EXPERIMENT_SECTION_MISSING")
        return DocumentIngestion(
            paper_id=paper_id,
            detected_language=detected_language,
            sections=sections,
            formulas=formulas,
            extraction_warnings=warnings,
            blocks=blocks,
        )

    def _detect_language(self, text: str) -> str:
        zh_count = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        if zh_count > len(text) * 0.2:
            return "zh"
        if zh_count:
            return "mixed"
        return "en"

    def _split_sections(self, text: str) -> dict[str, str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        sections: dict[str, list[str]] = {"full_text": []}
        current = "full_text"
        for line in lines:
            key = SECTION_ALIASES.get(line.lower().strip(":"))
            if key:
                current = key
                sections.setdefault(current, [])
            else:
                sections.setdefault(current, []).append(line)
        return {key: "\n".join(value).strip() for key, value in sections.items() if "\n".join(value).strip()}

# PDF extraction
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PdfTextExtractor:
    """Multi-layer PDF parser with fallback chain: Docling → Marker → PyMuPDF."""

    def extract(self, pdf_path: Path) -> tuple[str, list[str]]:
        warnings: list[str] = []
        for name, parser_fn in [
            ("docling", self._try_docling),
            ("marker", self._try_marker),
            ("pymupdf", self._try_pymupdf),
        ]:
            try:
                result = parser_fn(pdf_path)
                if result is not None:
                    text, parse_warnings = result
                    if text.strip():
                        return text, warnings + parse_warnings
                    warnings.append(f"{name}: extracted empty text, trying next parser")
            except Exception as e:
                logger.warning(f"Parser {name} failed: {e}")
                warnings.append(f"{name} failed: {str(e)[:200]}")
        return "", warnings + ["ALL_PARSERS_FAILED: no parser could extract text from PDF"]

    def _try_docling(self, pdf_path: Path) -> tuple[str, list[str]] | None:
        try:
            from docling.document_converter import DocumentConverter
            converter = DocumentConverter()
            result = converter.convert(str(pdf_path))
            text = result.document.export_to_markdown()
            return text, []
        except ImportError:
            return None
        except Exception as e:
            return None

    def _try_marker(self, pdf_path: Path) -> tuple[str, list[str]] | None:
        try:
            from marker.converters.pdf import PdfConverter
            config = PdfConverter()
            text = config.convert(str(pdf_path))
            return text, []
        except ImportError:
            return None
        except Exception as e:
            return None

    def _try_pymupdf(self, pdf_path: Path) -> tuple[str, list[str]] | None:
        try:
            import fitz
        except ImportError:
            return None

        warnings: list[str] = []
        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            return None

        pages: list[str] = []
        for page_index in range(len(doc)):
            text = doc[page_index].get_text()
            if text.strip():
                pages.append(text)
        metadata = doc.metadata or {}
        doc.close()

        if not pages:
            return None

        if metadata.get("title"):
            pages.insert(0, f"Title\n{metadata['title']}")

        return "\n\n".join(pages), warnings
