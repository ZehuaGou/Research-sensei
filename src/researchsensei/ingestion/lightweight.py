from __future__ import annotations

import re
from pathlib import Path

from researchsensei.schemas import BlockType, DocumentBlock, DocumentIngestion, WarningItem


SECTION_ALIASES = {
    "abstract": "abstract",
    "摘要": "abstract",
    "introduction": "introduction",
    "引言": "introduction",
    "related work": "related_work",
    "method": "method",
    "methods": "method",
    "方法": "method",
    "experiments": "experiments",
    "experiment": "experiments",
    "results": "experiments",
    "实验": "experiments",
    "conclusion": "conclusion",
    "结论": "conclusion",
}

FORMULA_PATTERN = re.compile(
    r"(?P<formula>\b[A-Za-z][A-Za-z0-9_]*\s*=\s*[^.;\n]+|\\mathcal\{[^}]+\}\s*=\s*[^.;\n]+)"
)


class LightweightIngestionService:
    def ingest_path(self, path: str | Path, paper_id: str | None = None) -> DocumentIngestion:
        source = Path(path)
        actual_paper_id = paper_id or source.stem
        suffix = source.suffix.lower()
        warnings: list[WarningItem] = []
        degraded = False

        if suffix in {".md", ".txt"}:
            text = source.read_text(encoding="utf-8")
            parser_name = "markdown_text" if suffix == ".md" else "plain_text"
        elif suffix == ".pdf":
            text, pdf_warnings, degraded = self._extract_pdf_text(source)
            warnings.extend(pdf_warnings)
            parser_name = "pymupdf_lightweight"
        else:
            text = ""
            degraded = True
            parser_name = "unsupported"
            warnings.append(WarningItem(code="UNSUPPORTED_FILE_TYPE", message=f"Unsupported file type: {suffix}"))

        if not text.strip():
            warnings.append(WarningItem(code="NO_TEXT_EXTRACTED", message="No text could be extracted."))
            return DocumentIngestion(
                paper_id=actual_paper_id,
                source_path=str(source),
                parser_name=parser_name,
                degraded=True,
                warnings=warnings,
                blocks=[],
            )

        doc = self._ingest_text(actual_paper_id, text)
        return doc.model_copy(
            update={
                "source_path": str(source),
                "parser_name": parser_name,
                "degraded": degraded,
                "warnings": [*warnings, *doc.warnings],
            }
        )

    def _extract_pdf_text(self, path: Path) -> tuple[str, list[WarningItem], bool]:
        try:
            import fitz
        except ImportError:
            return "", [WarningItem(code="PYMUPDF_MISSING", message="PyMuPDF is not installed.")], True

        try:
            doc = fitz.open(str(path))
        except Exception as error:
            return (
                "",
                [WarningItem(code="PDF_PARSE_FAILED", message=f"PyMuPDF could not open PDF: {error}")],
                True,
            )

        pages: list[str] = []
        try:
            for page in doc:
                text = page.get_text()
                if text.strip():
                    pages.append(text)
        finally:
            doc.close()

        if not pages:
            return "", [WarningItem(code="PDF_TEXT_EMPTY", message="PDF parser returned empty text.")], True
        return "\n\n".join(pages), [], False

    def _ingest_text(self, paper_id: str, text: str) -> DocumentIngestion:
        detected_language = self._detect_language(text)
        blocks: list[DocumentBlock] = []
        formula_count = 0
        paragraph_count = 0
        heading_count = 0
        current_section = "full_text"
        paragraph_lines: list[str] = []
        offset = 0
        seen_sections: set[str] = set()

        def flush_paragraph() -> None:
            nonlocal formula_count, paragraph_count, offset
            paragraph = " ".join(line.strip() for line in paragraph_lines if line.strip()).strip()
            paragraph_lines.clear()
            if not paragraph:
                return
            formula_match = FORMULA_PATTERN.search(paragraph)
            if formula_match:
                formula_count += 1
                block_id = f"eq{formula_count:03d}"
                blocks.append(
                    DocumentBlock(
                        block_id=block_id,
                        type=BlockType.FORMULA,
                        section=current_section,
                        text=formula_match.group("formula").strip(),
                        raw_latex=formula_match.group("formula").strip(),
                        evidence_ref=f"{paper_id}:{block_id}",
                    )
                )
            paragraph_count += 1
            block_id = f"b{paragraph_count:03d}"
            block_type = BlockType.ABSTRACT if current_section == "abstract" else BlockType.PARAGRAPH
            blocks.append(
                DocumentBlock(
                    block_id=block_id,
                    type=block_type,
                    section=current_section,
                    text=paragraph,
                    normalized_text=" ".join(paragraph.lower().split()),
                    offset_start=offset,
                    offset_end=offset + len(paragraph),
                    evidence_ref=f"{paper_id}:{block_id}",
                )
            )
            offset += len(paragraph) + 1

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                flush_paragraph()
                continue

            heading = self._normalize_heading(line)
            if heading:
                flush_paragraph()
                current_section = heading
                seen_sections.add(heading)
                heading_count += 1
                block_id = f"h{heading_count:03d}"
                blocks.append(
                    DocumentBlock(
                        block_id=block_id,
                        type=BlockType.HEADING,
                        section=current_section,
                        text=current_section,
                        normalized_text=current_section,
                        offset_start=offset,
                        offset_end=offset + len(line),
                        evidence_ref=f"{paper_id}:{block_id}",
                    )
                )
                offset += len(line) + 1
            else:
                paragraph_lines.append(line)

        flush_paragraph()

        warnings: list[WarningItem] = []
        if formula_count == 0:
            warnings.append(WarningItem(code="FORMULA_UNAVAILABLE", message="No formula-like text was detected."))
        if "method" not in seen_sections:
            warnings.append(WarningItem(code="METHOD_SECTION_MISSING", message="No method section was detected."))
        if "experiments" not in seen_sections:
            warnings.append(
                WarningItem(code="EXPERIMENT_SECTION_MISSING", message="No experiment/results section was detected.")
            )

        return DocumentIngestion(
            paper_id=paper_id,
            detected_language=detected_language,
            warnings=warnings,
            blocks=blocks,
        )

    def _normalize_heading(self, line: str) -> str:
        markdown_match = re.match(r"^#{1,6}\s+(?P<title>.+)$", line)
        candidate = markdown_match.group("title") if markdown_match else line
        candidate = candidate.strip().strip(":：")
        lower = candidate.lower()
        if lower in SECTION_ALIASES:
            return SECTION_ALIASES[lower]
        if candidate in SECTION_ALIASES:
            return SECTION_ALIASES[candidate]
        if markdown_match:
            return lower.replace(" ", "_")
        return ""

    def _detect_language(self, text: str) -> str:
        if not text:
            return "unknown"
        zh_count = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        if zh_count > len(text) * 0.2:
            return "zh"
        if zh_count:
            return "mixed"
        return "en"
