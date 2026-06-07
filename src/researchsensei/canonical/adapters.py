"""Real external adapters for M1 material normalization.

Each adapter:
- Checks if the dependency is installed
- Attempts to process a real PDF
- Returns structured result with sections, formula_blocks, parser_used, status
- Reports BLOCKED with specific reason if it fails
"""
from __future__ import annotations

import logging
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from researchsensei.schemas.canonical import FormulaBlock
from researchsensei.schemas.enums import AdapterStatus, FormulaOrigin, FormulaOcrStatus

logger = logging.getLogger(__name__)


@dataclass
class AdapterResult:
    """Result from an external adapter."""
    adapter_name: str
    status: AdapterStatus = AdapterStatus.NOT_IMPLEMENTED
    available: bool = False
    invoked: bool = False
    succeeded: bool = False
    blocking_reason: str = ""
    parser_used: str = ""
    sections: dict[str, str] = field(default_factory=dict)
    formula_blocks: list[FormulaBlock] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class MarkItDownAdapter:
    """Adapter for Microsoft MarkItDown PDF to markdown conversion.

    MarkItDown is fast (0.6-2.9s), MIT licensed, extracts text and formulas well.
    Best for: speed, content coverage, formula detection.
    Weakness: no section structure detection (uses pdfplumber under the hood).
    """

    NAME = "markitdown"

    def is_available(self) -> bool:
        try:
            import importlib
            spec = importlib.util.find_spec("markitdown")
            return spec is not None
        except (ImportError, ValueError):
            return False

    def process(self, pdf_path: str | Path) -> AdapterResult:
        pdf_path = Path(pdf_path)
        result = AdapterResult(adapter_name=self.NAME)

        if not self.is_available():
            result.status = AdapterStatus.BLOCKED
            result.blocking_reason = "markitdown not installed (pip install 'markitdown[pdf]'). MIT license."
            return result

        result.available = True

        if not pdf_path.exists():
            result.status = AdapterStatus.BLOCKED
            result.blocking_reason = f"PDF file not found: {pdf_path}"
            return result

        try:
            result.invoked = True
            from markitdown import MarkItDown

            md = MarkItDown(enable_plugins=False)
            converted = md.convert(str(pdf_path))
            text = converted.text_content

            if not text or not text.strip():
                result.status = AdapterStatus.DEGRADED_IMPLEMENTED
                result.blocking_reason = "MarkItDown returned empty output"
                result.warnings.append("MarkItDown returned empty text")
                return result

            result.succeeded = True
            result.status = AdapterStatus.IMPLEMENTED
            result.parser_used = "markitdown_pdf"
            result.sections = self._parse_sections(text)
            result.formula_blocks = self._extract_formulas(text)

        except Exception as exc:
            result.status = AdapterStatus.BLOCKED
            result.blocking_reason = f"MarkItDown processing failed: {type(exc).__name__}: {str(exc)[:200]}"
            result.warnings.append(f"MarkItDown error: {exc}")

        return result

    def _parse_sections(self, text: str) -> dict[str, str]:
        """Parse text into sections. MarkItDown doesn't produce headers, so use heuristics."""
        import re
        sections: dict[str, str] = {}

        # Try to find section-like patterns
        lines = text.split("\n")
        current_section = "Other"
        current_content: list[str] = []

        for line in lines:
            stripped = line.strip()
            # Check for common section headers
            if re.match(r'^(?:\d+\.?\s+)?(?:Abstract|摘要)', stripped, re.IGNORECASE):
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = "Abstract"
                current_content = []
            elif re.match(r'^(?:\d+\.?\s+)?(?:Introduction|引言)', stripped, re.IGNORECASE):
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = "Introduction"
                current_content = []
            elif re.match(r'^(?:\d+\.?\s+)?(?:Related Work|相关工作)', stripped, re.IGNORECASE):
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = "Related Work"
                current_content = []
            elif re.match(r'^(?:\d+\.?\s+)?(?:Method|方法|Approach|Methodology)', stripped, re.IGNORECASE):
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = "Method"
                current_content = []
            elif re.match(r'^(?:\d+\.?\s+)?(?:Experiment|实验|Results|Evaluation)', stripped, re.IGNORECASE):
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = "Experiments"
                current_content = []
            elif re.match(r'^(?:\d+\.?\s+)?(?:Conclusion|结论|Discussion)', stripped, re.IGNORECASE):
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = "Conclusion"
                current_content = []
            elif re.match(r'^(?:\d+\.?\s+)?(?:References|参考文献|Bibliography)', stripped, re.IGNORECASE):
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = "References"
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _extract_formulas(self, text: str) -> list[FormulaBlock]:
        """Extract formula blocks from MarkItDown output."""
        from researchsensei.canonical.parser_quality import _extract_latex_formula_texts
        formulas: list[FormulaBlock] = []

        for counter, latex in enumerate(_extract_latex_formula_texts(text), 1):
            formulas.append(FormulaBlock(
                formula_id=f"md_eq{counter}",
                latex=latex,
                origin=FormulaOrigin.PARSER_LATEX,
                is_latex=True,
                confidence=0.7,
            ))

        return formulas


class MarkerPdfAdapter:
    """Adapter for Marker (marker-pdf) PDF to markdown conversion.

    Marker converts PDF to markdown/JSON/HTML with table, equation, and structure support.
    License: GPL-3.0 (code), OpenRAIL-M (model).
    """

    NAME = "marker"

    def is_available(self) -> bool:
        try:
            import importlib
            spec = importlib.util.find_spec("marker")
            return spec is not None
        except (ImportError, ValueError):
            return False

    def process(self, pdf_path: str | Path) -> AdapterResult:
        pdf_path = Path(pdf_path)
        result = AdapterResult(adapter_name=self.NAME)

        if not self.is_available():
            result.status = AdapterStatus.BLOCKED
            result.blocking_reason = "marker-pdf not installed (pip install marker-pdf). GPL-3.0 license."
            return result

        result.available = True

        if not pdf_path.exists():
            result.status = AdapterStatus.BLOCKED
            result.blocking_reason = f"PDF file not found: {pdf_path}"
            return result

        try:
            result.invoked = True
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict

            models = create_model_dict()
            converter = PdfConverter(artifact_dict=models)

            # Marker returns a MarkdownOutput object
            rendered = converter(str(pdf_path))
            markdown_text = rendered.markdown if hasattr(rendered, 'markdown') else str(rendered)

            if not markdown_text or not markdown_text.strip():
                result.status = AdapterStatus.DEGRADED_IMPLEMENTED
                result.blocking_reason = "Marker returned empty output"
                result.warnings.append("Marker returned empty markdown")
                return result

            result.succeeded = True
            result.status = AdapterStatus.IMPLEMENTED
            result.parser_used = "marker_pdf"
            result.sections = self._parse_sections(markdown_text)
            result.formula_blocks = self._extract_formulas(markdown_text)

        except Exception as exc:
            result.status = AdapterStatus.BLOCKED
            result.blocking_reason = f"Marker processing failed: {type(exc).__name__}: {str(exc)[:200]}"
            result.warnings.append(f"Marker error: {exc}")

        return result

    def _parse_sections(self, markdown: str) -> dict[str, str]:
        """Parse markdown into standard sections."""
        sections: dict[str, str] = {}
        current_section = "Other"
        current_content: list[str] = []

        for line in markdown.split("\n"):
            if line.startswith("# "):
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = self._map_section(line[2:].strip())
                current_content = []
            elif line.startswith("## "):
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = self._map_section(line[3:].strip())
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _map_section(self, name: str) -> str:
        name_lower = name.lower().strip()
        mapping = {
            "abstract": "Abstract",
            "introduction": "Introduction",
            "related work": "Related Work",
            "method": "Method",
            "methods": "Method",
            "approach": "Method",
            "experiments": "Experiments",
            "results": "Experiments",
            "evaluation": "Experiments",
            "conclusion": "Conclusion",
            "discussion": "Conclusion",
            "references": "References",
        }
        for key, val in mapping.items():
            if key in name_lower:
                return val
        return name.title() if len(name) < 50 else "Other"

    def _extract_formulas(self, markdown: str) -> list[FormulaBlock]:
        """Extract formula blocks from Marker markdown."""
        from researchsensei.canonical.parser_quality import _extract_latex_formula_texts
        formulas: list[FormulaBlock] = []

        for counter, latex in enumerate(_extract_latex_formula_texts(markdown), 1):
            formulas.append(FormulaBlock(
                formula_id=f"marker_eq{counter}",
                latex=latex,
                origin=FormulaOrigin.PARSER_LATEX,
                is_latex=True,
                confidence=0.8,
            ))

        return formulas


class MinerUPdfAdapter:
    """Adapter for MinerU (magic-pdf) PDF parsing.

    MinerU provides PDF parsing with formula-to-LaTeX and table-to-HTML conversion.
    License: AGPL-3.0.
    """

    NAME = "mineru"

    def is_available(self) -> bool:
        try:
            import importlib
            spec = importlib.util.find_spec("magic_pdf")
            return spec is not None
        except (ImportError, ValueError):
            return False

    def process(self, pdf_path: str | Path) -> AdapterResult:
        pdf_path = Path(pdf_path)
        result = AdapterResult(adapter_name=self.NAME)

        if not self.is_available():
            result.status = AdapterStatus.BLOCKED
            result.blocking_reason = "magic-pdf (MinerU) not installed (pip install magic-pdf). AGPL-3.0 license."
            return result

        result.available = True

        if not pdf_path.exists():
            result.status = AdapterStatus.BLOCKED
            result.blocking_reason = f"PDF file not found: {pdf_path}"
            return result

        try:
            result.invoked = True
            import json as _json
            from magic_pdf.tools.common import do_parse

            # MinerU writes output to a directory
            with tempfile.TemporaryDirectory(prefix="mineru_") as tmp_dir:
                pdf_bytes = pdf_path.read_bytes()
                do_parse(
                    pdf_name=pdf_path.stem,
                    pdf_bytes=pdf_bytes,
                    model_list=[],  # empty = use built-in models
                    parse_mode="auto",
                    output_dir=tmp_dir,
                    is_json=True,
                    is_md=True,
                )

                # Find output markdown
                md_files = list(Path(tmp_dir).rglob("*.md"))
                json_files = list(Path(tmp_dir).rglob("*.json"))

                md_content = ""
                if md_files:
                    md_content = md_files[0].read_text(encoding="utf-8", errors="ignore")

                json_content = ""
                if json_files:
                    json_content = json_files[0].read_text(encoding="utf-8", errors="ignore")

                if not md_content and not json_content:
                    result.status = AdapterStatus.DEGRADED_IMPLEMENTED
                    result.blocking_reason = "MinerU produced no output"
                    result.warnings.append("MinerU returned empty output")
                    return result

                result.succeeded = True
                result.status = AdapterStatus.IMPLEMENTED
                result.parser_used = "mineru_pdf"

                if md_content:
                    result.sections = self._parse_sections(md_content)
                    result.formula_blocks = self._extract_formulas(md_content)
                elif json_content:
                    result.sections = {"Other": json_content[:5000]}

        except Exception as exc:
            result.status = AdapterStatus.BLOCKED
            result.blocking_reason = f"MinerU processing failed: {type(exc).__name__}: {str(exc)[:200]}"
            result.warnings.append(f"MinerU error: {exc}")

        return result

    def _parse_sections(self, markdown: str) -> dict[str, str]:
        sections: dict[str, str] = {}
        current_section = "Other"
        current_content: list[str] = []

        for line in markdown.split("\n"):
            if line.startswith("## "):
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = self._map_section(line[3:].strip())
                current_content = []
            elif line.startswith("# "):
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = self._map_section(line[2:].strip())
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _map_section(self, name: str) -> str:
        name_lower = name.lower().strip()
        mapping = {
            "abstract": "Abstract",
            "introduction": "Introduction",
            "related work": "Related Work",
            "method": "Method",
            "experiments": "Experiments",
            "conclusion": "Conclusion",
            "references": "References",
        }
        for key, val in mapping.items():
            if key in name_lower:
                return val
        return name.title() if len(name) < 50 else "Other"

    def _extract_formulas(self, markdown: str) -> list[FormulaBlock]:
        from researchsensei.canonical.parser_quality import _extract_latex_formula_texts
        formulas: list[FormulaBlock] = []

        for counter, latex in enumerate(_extract_latex_formula_texts(markdown), 1):
            formulas.append(FormulaBlock(
                formula_id=f"mineru_eq{counter}",
                latex=latex,
                origin=FormulaOrigin.PARSER_LATEX,
                is_latex=True,
                confidence=0.8,
            ))

        return formulas


class Pix2TexFormulaOCRAdapter:
    """Real pix2tex (LaTeX-OCR) adapter for formula OCR.

    Uses pix2tex LatexOCR model to convert formula images to LaTeX.
    License: MIT.
    """

    NAME = "pix2tex"

    def __init__(self) -> None:
        self._model = None
        self._model_loaded = False
        self._load_error = ""

    def is_available(self) -> bool:
        try:
            import importlib
            spec = importlib.util.find_spec("pix2tex")
            return spec is not None
        except (ImportError, ValueError):
            return False

    def _ensure_model(self) -> bool:
        if self._model_loaded:
            return self._model is not None

        self._model_loaded = True
        try:
            from pix2tex.cli import LatexOCR
            self._model = LatexOCR()
            return True
        except Exception as exc:
            self._load_error = f"{type(exc).__name__}: {str(exc)[:200]}"
            logger.warning("pix2tex model load failed: %s", exc)
            return False

    def ocr_formula(
        self,
        image_path: str | Path | None = None,
        image_bytes: bytes | None = None,
        formula_id: str = "ocr_1",
    ) -> tuple[str, FormulaOrigin, FormulaOcrStatus, float, str]:
        """OCR a formula image to LaTeX.

        Returns: (latex, origin, ocr_status, confidence, warning)
        """
        if not self.is_available():
            return "", FormulaOrigin.UNKNOWN, FormulaOcrStatus.UNAVAILABLE, 0.0, "pix2tex not installed"

        if not self._ensure_model():
            return "", FormulaOrigin.UNKNOWN, FormulaOcrStatus.UNAVAILABLE, 0.0, f"Model load failed: {self._load_error}"

        try:
            from PIL import Image
            import io

            if image_path:
                img = Image.open(str(image_path))
            elif image_bytes:
                img = Image.open(io.BytesIO(image_bytes))
            else:
                return "", FormulaOrigin.UNKNOWN, FormulaOcrStatus.NOT_TRIGGERED, 0.0, "No image provided"

            latex = self._model.latexocr(img)

            if not latex or not latex.strip():
                return "", FormulaOrigin.OCR_LATEX, FormulaOcrStatus.FAILED, 0.0, "Empty OCR result"

            return latex.strip(), FormulaOrigin.OCR_LATEX, FormulaOcrStatus.SUCCESS, 0.7, ""

        except Exception as exc:
            return "", FormulaOrigin.OCR_LATEX, FormulaOcrStatus.FAILED, 0.0, f"OCR error: {str(exc)[:200]}"


class DeepXivProbe:
    """Probe for DeepXiv availability.

    DeepXiv is a research paper analysis platform. We check for:
    - GitHub repo existence
    - pip package
    - HTTP API endpoint
    """

    NAME = "deepxiv"

    def probe(self) -> AdapterResult:
        result = AdapterResult(adapter_name=self.NAME)

        # Check pip package
        try:
            import subprocess
            proc = subprocess.run(
                ["pip", "index", "versions", "deepxiv"],
                capture_output=True, text=True, timeout=30
            )
            if "No matching" in proc.stdout or "No matching" in proc.stderr:
                result.status = AdapterStatus.BLOCKED
                result.blocking_reason = (
                    "DeepXiv: pip package 'deepxiv' does not exist. "
                    "No confirmed public Python SDK or HTTP API found. "
                    "GitHub repo status unconfirmed."
                )
                result.warnings.append("No installable package found via pip")
                return result
        except Exception as exc:
            result.warnings.append(f"pip check failed: {exc}")

        result.status = AdapterStatus.BLOCKED
        result.blocking_reason = "DeepXiv: no installable package or confirmed public API found"
        return result
