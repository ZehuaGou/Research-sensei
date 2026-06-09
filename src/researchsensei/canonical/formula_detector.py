"""MarkerDocumentFormulaDetector — extracts formula positions from Marker's internal Document.

Uses `converter.build_document()` to access Equation blocks with bbox coordinates.
The default MarkdownOutput and JSONRenderer discard block structure; only build_document()
provides position data.
"""
from __future__ import annotations

import logging
from pathlib import Path

from researchsensei.schemas.canonical import FormulaSlot

logger = logging.getLogger(__name__)


class MarkerDocumentFormulaDetector:
    """Detects formulas with positions using Marker's internal Document.

    Key finding from probe: MarkdownOutput and JSONRenderer do NOT preserve
    Equation blocks. Only `build_document()` returns the full block tree with
    bbox coordinates.

    Usage:
        detector = MarkerDocumentFormulaDetector()
        slots = detector.detect(pdf_path)
    """

    def __init__(self, timeout_seconds: float = 600.0) -> None:
        self.timeout_seconds = timeout_seconds

    def is_available(self) -> bool:
        try:
            import importlib
            spec = importlib.util.find_spec("marker")
            return spec is not None
        except (ImportError, ValueError):
            return False

    def detect(self, pdf_path: str | Path) -> list[FormulaSlot]:
        """Detect formula positions from a PDF using Marker's build_document().

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of FormulaSlot entries with position data.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            logger.warning("PDF not found: %s", pdf_path)
            return []

        if not self.is_available():
            logger.warning("marker-pdf not installed")
            return []

        try:
            slots = self._detect_via_build_document(pdf_path)
            if slots:
                self._enrich_with_pymupdf_context(pdf_path, slots)
            return slots
        except Exception as exc:
            logger.warning("MarkerDocumentFormulaDetector failed: %s", exc)
            return []

    def _detect_via_build_document(self, pdf_path: Path) -> list[FormulaSlot]:
        """Use Marker's build_document() to get Equation blocks with bbox."""
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from marker.schema import BlockTypes

        models = create_model_dict()
        converter = PdfConverter(artifact_dict=models)

        # build_document returns the internal Document with full block tree
        doc = converter.build_document(str(pdf_path))

        slots: list[FormulaSlot] = []
        formula_counter = 0

        # Use doc.pages (list of PageGroup), not doc.children
        for page in doc.pages:
            page_id = getattr(page, "page_id", 0)
            # Get blocks from page — use current_children or contained_blocks
            page_blocks = page.current_children if page.children else []

            # Get nearby text for context
            text_blocks = []
            for block in page_blocks:
                if block.block_type == BlockTypes.Text:
                    text_blocks.append(getattr(block, "text", ""))

            nearby_before = text_blocks[-1] if text_blocks else ""
            nearby_after = ""

            for block in page_blocks:
                if block.block_type not in (BlockTypes.Equation, BlockTypes.TextInlineMath):
                    continue

                block_type = block.block_type.name if hasattr(block.block_type, 'name') else str(block.block_type)

                # Get bbox from polygon
                polygon_obj = getattr(block, "polygon", None)
                if polygon_obj is None:
                    continue

                bbox = getattr(polygon_obj, "bbox", None)
                polygon = getattr(polygon_obj, "polygon", None)

                if bbox is None:
                    continue

                # Validate bbox
                if not _is_valid_bbox(bbox):
                    continue

                formula_counter += 1
                formula_id = f"formula_{formula_counter:03d}"

                # Extract text/latex from block
                block_text = getattr(block, "text", "")
                block_html = getattr(block, "html", "")
                marker_latex = _extract_latex_from_block(block_text, block_html)

                slots.append(FormulaSlot(
                    formula_id=formula_id,
                    page=page_id,
                    bbox=list(bbox) if isinstance(bbox, (list, tuple)) else [bbox[0], bbox[1], bbox[2], bbox[3]],
                    polygon=polygon if isinstance(polygon, list) else [],
                    block_type=block_type,
                    detection_source="marker_document",
                    detection_confidence=0.8 if marker_latex else 0.6,
                    marker_text=block_text,
                    marker_latex=marker_latex,
                    nearby_text_before=nearby_before[:500],
                    nearby_text_after=nearby_after[:500],
                    section="",
                    slot_marker=f"marker_{page_id}_{block_type.lower()}_{formula_counter}",
                ))

            # Update nearby text for next formula
            if text_blocks:
                nearby_before = text_blocks[-1]
                nearby_after = ""

        logger.info(
            "MarkerDocumentFormulaDetector found %d formula slots in %s",
            len(slots), pdf_path.name,
        )
        return slots

    def _enrich_with_pymupdf_context(self, pdf_path: Path, slots: list[FormulaSlot]) -> None:
        """Enrich formula slots with nearby text and section using PyMuPDF."""
        try:
            import fitz
        except ImportError:
            logger.warning("PyMuPDF not available for context enrichment")
            return

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as exc:
            logger.warning("Failed to open PDF for context enrichment: %s", exc)
            return

        try:
            for slot in slots:
                if not slot.bbox or len(slot.bbox) != 4:
                    continue
                page_idx = slot.page - 1  # Marker pages are 1-based, PyMuPDF is 0-based
                if page_idx < 0 or page_idx >= len(doc):
                    continue

                page = doc[page_idx]
                fx1, fy1, fx2, fy2 = slot.bbox

                # Extract all text blocks from the page
                blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

                text_before_parts = []
                text_after_parts = []
                section_heading = ""
                heading_y = -1

                for block in blocks:
                    if block.get("type") != 0:  # text block
                        continue
                    # Get block bbox
                    bb = block.get("bbox", (0, 0, 0, 0))
                    bx1, by1, bx2, by2 = bb

                    # Extract block text
                    block_text = ""
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            block_text += span.get("text", "")
                        block_text += "\n"
                    block_text = block_text.strip()
                    if not block_text:
                        continue

                    # Check if this block is a heading (larger font or bold)
                    is_heading = False
                    max_font_size = 0
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            fs = span.get("size", 0)
                            if fs > max_font_size:
                                max_font_size = fs
                            flags = span.get("flags", 0)
                            if flags & 2**4:  # bold bit
                                is_heading = True
                    if max_font_size >= 12:
                        is_heading = True

                    # Text above the formula
                    if by2 < fy1:
                        if is_heading and by1 > heading_y:
                            section_heading = block_text
                            heading_y = by1
                        else:
                            text_before_parts.append(block_text)

                    # Text below the formula
                    elif by1 > fy2:
                        text_after_parts.append(block_text)

                # Set nearby text (last 500 chars before, first 500 chars after)
                slot.nearby_text_before = "\n".join(text_before_parts)[-500:] if text_before_parts else ""
                slot.nearby_text_after = "\n".join(text_after_parts)[:500] if text_after_parts else ""

                # Set section from nearest heading above
                slot.section = _normalize_section_name(section_heading) if section_heading else ""
        finally:
            doc.close()


def _is_valid_bbox(bbox) -> bool:
    """Check if bbox is valid: 4 numeric values, min < max for x and y."""
    if bbox is None:
        return False
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        try:
            x1, y1, x2, y2 = [float(v) for v in bbox]
            return x1 < x2 and y1 < y2
        except (TypeError, ValueError):
            return False
    return False


def _normalize_section_name(heading_text: str) -> str:
    """Map a heading text to a standard section name."""
    import re
    text = heading_text.strip()
    # Remove leading numbers like "1.", "2.1", "I.", etc.
    text = re.sub(r'^[\d\.]+\s*', '', text)
    text = re.sub(r'^[IVXLC]+\.\s*', '', text, flags=re.IGNORECASE)
    text = text.strip().lower()

    section_map = {
        "abstract": "Abstract",
        "introduction": "Introduction",
        "related work": "Related Work",
        "related works": "Related Work",
        "background": "Related Work",
        "preliminaries": "Related Work",
        "method": "Method",
        "methods": "Method",
        "methodology": "Method",
        "approach": "Method",
        "proposed method": "Method",
        "proposed approach": "Method",
        "model": "Method",
        "experiments": "Experiments",
        "experimental results": "Experiments",
        "evaluation": "Experiments",
        "experiments and results": "Experiments",
        "results": "Experiments",
        "conclusion": "Conclusion",
        "conclusions": "Conclusion",
        "summary": "Conclusion",
        "references": "References",
    }

    for key, standard in section_map.items():
        if key in text:
            return standard

    # Return original heading if no match (title-case)
    return heading_text.strip()[:80]


def _extract_latex_from_block(text: str, html: str) -> str:
    """Extract LaTeX from Marker block text or HTML.

    Marker Equation blocks contain $...$ or $$...$$ LaTeX in their text,
    and <math> or <annotation> elements in HTML.
    """
    import re

    # Try to extract from HTML annotation (most reliable)
    if html:
        # LaTeX-OCR annotation
        ann_match = re.search(r'<annotation[^>]*>(.*?)</annotation>', html, re.DOTALL)
        if ann_match:
            latex = ann_match.group(1).strip()
            if latex:
                return latex

        # MathML text content
        math_match = re.search(r'<math[^>]*>(.*?)</math>', html, re.DOTALL)
        if math_match:
            # Extract text content from MathML
            math_text = re.sub(r'<[^>]+>', ' ', math_match.group(1))
            math_text = re.sub(r'\s+', ' ', math_text).strip()
            if math_text and len(math_text) > 2:
                return math_text

    # Fall back to text extraction
    if text:
        # Check for display math $$...$$
        display_match = re.search(r'\$\$(.*?)\$\$', text, re.DOTALL)
        if display_match:
            return display_match.group(1).strip()

        # Check for inline math $...$
        inline_match = re.search(r'\$([^$]+)\$', text)
        if inline_match:
            return inline_match.group(1).strip()

        # If text looks like LaTeX (contains common commands)
        if re.search(r'\\(?:frac|sum|int|partial|alpha|beta|mathcal|mathbb|mathrm)', text):
            return text.strip()

    return ""
