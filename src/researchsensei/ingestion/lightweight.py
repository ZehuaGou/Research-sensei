from __future__ import annotations

import re
from collections.abc import Callable
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
SECTION_ALIASES.update(
    {
        "methodology": "method",
        "approach": "method",
        "model": "method",
        "framework": "method",
        "architecture": "method",
        "proposed method": "method",
        "the proposed method": "method",
        "evaluation": "experiments",
        "experimental results": "experiments",
    }
)

FORMULA_PATTERN = re.compile(
    r"(?P<formula>\b[A-Za-z][A-Za-z0-9_]*\s*=\s*[^.;\n]+|\\mathcal\{[^}]+\}\s*=\s*[^.;\n]+)"
)

LATEX_TOKEN_PATTERN = re.compile(
    r"\\begin\{abstract\}(?P<abstract>.*?)\\end\{abstract\}"
    r"|\\(?P<section_cmd>section|subsection|subsubsection)\*?\{(?P<section_title>[^{}]+)\}"
    r"|\\begin\{(?P<env>equation\*?|align\*?|alignat\*?|gather\*?|multline\*?)\}(?P<env_body>.*?)\\end\{(?P=env)\}"
    r"|\\\[(?P<bracket_body>.*?)\\\]"
    r"|\$\$(?P<display_body>.*?)\$\$",
    re.DOTALL,
)


def _is_plausible_raw_formula(candidate: str) -> bool:
    """Reject prose assignments before they become formula evidence.

    PDF text extraction frequently flattens table labels and sentences into
    fragments such as ``lines = parent root`` or ``d = B)``. An equals sign is
    not sufficient evidence of a formula. Conservative raw-text detection
    requires mathematical structure and balanced delimiters; true visual
    formulas are recovered by the formula-region parser instead.
    """
    text = " ".join(candidate.split()).strip()
    if not text or len(text) > 240 or "=" not in text:
        return False
    _left, right = text.split("=", 1)
    if not right.strip():
        return False
    for opening, closing in (("(", ")"), ("[", "]"), ("{", "}")):
        if text.count(opening) != text.count(closing):
            return False
    math_symbols = "_+*/^<>≤≥∑Σ∫√\\()[]{}"
    return any(char.isdigit() or char in math_symbols for char in right)


class LightweightIngestionService:
    def ingest_path(
        self,
        path: str | Path,
        paper_id: str | None = None,
        progress: Callable[[str, int], None] | None = None,
    ) -> DocumentIngestion:
        source = Path(path)
        actual_paper_id = paper_id or source.stem
        suffix = source.suffix.lower()
        warnings: list[WarningItem] = []
        degraded = False

        if suffix in {".md", ".txt"}:
            text = source.read_text(encoding="utf-8")
            parser_name = "markdown_text" if suffix == ".md" else "plain_text"
        elif suffix == ".tex":
            text = source.read_text(encoding="utf-8", errors="ignore")
            # Resolve \input{} commands. Check both the file's directory and
            # common extracted-source subdirectories (source/extracted/).
            resolve_dirs = [source.parent]
            extracted = source.parent / "source" / "extracted"
            if extracted.is_dir():
                resolve_dirs.append(extracted)
            for resolve_dir in resolve_dirs:
                text = _resolve_latex_inputs(text, resolve_dir)
            parser_name = "latex_source_lightweight"
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

        doc = self._ingest_latex(actual_paper_id, text) if suffix == ".tex" else self._ingest_text(actual_paper_id, text)
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

    def _ingest_latex(self, paper_id: str, text: str) -> DocumentIngestion:
        cleaned = _strip_latex_comments(text)
        detected_language = self._detect_language(cleaned)
        blocks: list[DocumentBlock] = []
        warnings: list[WarningItem] = []
        offset = 0
        paragraph_count = 0
        heading_count = 0
        formula_count = 0
        current_section = "full_text"
        seen_sections: set[str] = set()

        title_match = re.search(r"\\title\{(?P<title>.*?)\}", cleaned, re.DOTALL)
        if title_match:
            title = _latex_to_plain(title_match.group("title"))
            if title:
                blocks.append(
                    DocumentBlock(
                        block_id="title001",
                        type=BlockType.TITLE,
                        section="title",
                        text=title,
                        normalized_text=" ".join(title.lower().split()),
                        evidence_ref=f"{paper_id}:title001",
                        block_source="latex_source",
                    )
                )

        def add_heading(section: str, raw_title: str = "") -> None:
            nonlocal heading_count, offset, current_section
            current_section = section
            seen_sections.add(section)
            heading_count += 1
            text_value = raw_title or section
            block_id = f"h{heading_count:03d}"
            blocks.append(
                DocumentBlock(
                    block_id=block_id,
                    type=BlockType.HEADING,
                    section=section,
                    text=text_value,
                    normalized_text=section,
                    offset_start=offset,
                    offset_end=offset + len(text_value),
                    evidence_ref=f"{paper_id}:{block_id}",
                    block_source="latex_source",
                )
            )
            offset += len(text_value) + 1

        def add_paragraphs(raw_segment: str) -> None:
            nonlocal paragraph_count, offset
            plain = _latex_to_plain(raw_segment)
            for paragraph in _split_paragraphs(plain):
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
                        block_source="latex_source",
                        section_confidence="high",
                    )
                )
                offset += len(paragraph) + 1

        def add_formula(raw_formula: str) -> None:
            nonlocal formula_count, offset
            formula = raw_formula.strip()
            if not formula:
                return
            formula_count += 1
            block_id = f"eq{formula_count:03d}"
            blocks.append(
                DocumentBlock(
                    block_id=block_id,
                    type=BlockType.FORMULA,
                    section=current_section,
                    text=formula,
                    raw_latex=formula,
                    evidence_ref=f"{paper_id}:{block_id}",
                    formula_id=f"source_latex_formula_{formula_count:03d}",
                    formula_latex=formula,
                    formula_origin="source_latex",
                    formula_ocr_status="not_required",
                    formula_explanation_status="available",
                    equation_group_id=f"source_latex_group_{formula_count:03d}",
                    group_order=formula_count,
                    block_source="latex_source",
                    parse_quality_status="source_latex",
                )
            )
            offset += len(formula) + 1

        cursor = 0
        for match in LATEX_TOKEN_PATTERN.finditer(cleaned):
            add_paragraphs(cleaned[cursor:match.start()])
            cursor = match.end()

            if match.group("abstract") is not None:
                add_heading("abstract", "Abstract")
                add_paragraphs(match.group("abstract") or "")
                continue

            section_title = match.group("section_title")
            if section_title is not None:
                plain_title = _latex_to_plain(section_title)
                add_heading(self._section_from_title(plain_title), plain_title)
                continue

            formula = match.group("env_body") or match.group("bracket_body") or match.group("display_body") or ""
            add_formula(formula)

        add_paragraphs(cleaned[cursor:])

        if formula_count == 0:
            warnings.append(WarningItem(code="FORMULA_UNAVAILABLE", message="No LaTeX display formula was detected."))
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
            if formula_match and _is_plausible_raw_formula(formula_match.group("formula")):
                formula_count += 1
                block_id = f"eq{formula_count:03d}"
                formula_text = formula_match.group("formula").strip()
                blocks.append(
                    DocumentBlock(
                        block_id=block_id,
                        type=BlockType.FORMULA,
                        section=current_section,
                        text=formula_text,
                        raw_latex=formula_text,
                        evidence_ref=f"{paper_id}:{block_id}",
                        formula_id=f"raw_formula_{formula_count:03d}",
                        formula_latex=formula_text,
                        formula_origin="raw_formula_text",
                        formula_ocr_status="not_available",
                        formula_explanation_status="degraded",
                        risk_flags=["RAW_FORMULA_TEXT"],
                        parse_quality_status="raw_text_formula",
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

    def _section_from_title(self, title: str) -> str:
        lower = " ".join(title.lower().split()).strip(":")
        if lower in SECTION_ALIASES:
            return SECTION_ALIASES[lower]
        if any(term in lower for term in ("method", "methodology", "approach", "architecture", "framework", "proposed model")):
            return "method"
        if any(term in lower for term in ("experiment", "result", "evaluation", "benchmark")):
            return "experiments"
        if "abstract" in lower:
            return "abstract"
        if "intro" in lower:
            return "introduction"
        return lower.replace(" ", "_") or "full_text"

    def _detect_language(self, text: str) -> str:
        if not text:
            return "unknown"
        zh_count = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        if zh_count > len(text) * 0.2:
            return "zh"
        if zh_count:
            return "mixed"
        return "en"


def _strip_latex_comments(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        lines.append(re.sub(r"(?<!\\)%.*$", "", line))
    return "\n".join(lines)


def _latex_to_plain(text: str) -> str:
    value = text
    value = re.sub(r"\\(cite|citep|citet|ref|eqref|label|url)\*?(?:\[[^\]]*\])?\{[^{}]*\}", " ", value)
    value = re.sub(r"\\(begin|end)\{[^{}]*\}", " ", value)
    for _ in range(4):
        updated = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", value)
        if updated == value:
            break
        value = updated
    value = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", value)
    value = value.replace("~", " ").replace("$", " ")
    value = re.sub(r"[{}]", " ", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _split_paragraphs(text: str) -> list[str]:
    paragraphs = []
    for chunk in re.split(r"\n\s*\n", text):
        paragraph = " ".join(line.strip() for line in chunk.splitlines() if line.strip()).strip()
        if paragraph:
            paragraphs.append(paragraph)
    return paragraphs


def _resolve_latex_inputs(text: str, source_dir: Path, depth: int = 0) -> str:
    """Resolve \\input{} and \\include{} commands in LaTeX source.

    Reads included .tex files from the same directory and replaces the
    commands with their content. Limited to 5 levels of nesting to avoid
    infinite recursion.
    """
    if depth > 5:
        return text

    def replace_input(match: re.Match) -> str:
        filename = match.group(1).strip()
        if not filename.endswith(".tex"):
            filename = filename + ".tex"
        included_path = source_dir / filename
        if included_path.exists() and included_path.is_file():
            try:
                included_text = included_path.read_text(encoding="utf-8", errors="ignore")
                # Recursively resolve nested inputs
                return _resolve_latex_inputs(included_text, included_path.parent, depth + 1)
            except OSError:
                return match.group(0)
        return match.group(0)

    # Match \input{filename} and \include{filename}
    text = re.sub(r"\\input\{([^{}]+)\}", replace_input, text)
    text = re.sub(r"\\include\{([^{}]+)\}", replace_input, text)
    return text
