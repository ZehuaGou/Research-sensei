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
        # Skip OCR — the PDF already has extractable text via PyMuPDF.
        # This avoids the 30+ minute OCR bottleneck.
        config = {"disable_ocr": True}
        converter = PdfConverter(artifact_dict=models, config=config)

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
        """Enrich formula slots with nearby text and section using PyMuPDF.

        Strategy:
        1. Scan ALL pages, extract first line of each text block as heading candidate
        2. Normalize heading candidates — only trust known section names
        3. Build page→section mapping via cross-page timeline
        4. For each formula, assign section from timeline + collect nearby text
        """
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
            # Step 1: Scan all pages for heading candidates
            # Extract first line of each text block, check if it's a heading
            page_headings: dict[int, list[tuple[float, str]]] = {}
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
                headings_on_page = []
                for block in blocks:
                    if block.get("type") != 0:
                        continue
                    bb = block.get("bbox", (0, 0, 0, 0))
                    # Extract first line text and its font info
                    first_line_text = ""
                    first_line_font_size = 0
                    first_line_bold = False
                    for line in block.get("lines", []):
                        line_text = ""
                        line_max_fs = 0
                        line_bold = False
                        for span in line.get("spans", []):
                            line_text += span.get("text", "")
                            fs = span.get("size", 0)
                            if fs > line_max_fs:
                                line_max_fs = fs
                            flags = span.get("flags", 0)
                            if flags & 2**4:
                                line_bold = True
                        line_text = line_text.strip()
                        if line_text:
                            first_line_text = line_text
                            first_line_font_size = line_max_fs
                            first_line_bold = line_bold
                            break  # Only need first line

                    if not first_line_text:
                        continue

                    # Check if first line looks like a heading
                    is_heading = False
                    if first_line_font_size >= 14:
                        is_heading = True
                    if first_line_bold and first_line_font_size >= 11:
                        is_heading = True
                    # IEEE-style: Roman numeral + uppercase, e.g. "V. EXPERIMENTS"
                    import re
                    if re.match(r'^[IVXLC]+\.\s+[A-Z]', first_line_text):
                        is_heading = True
                    # Numbered section: "1. Introduction", "2.1 Background"
                    if re.match(r'^\d+(\.\d+)?\.\s+\w', first_line_text):
                        is_heading = True

                    if is_heading:
                        headings_on_page.append((bb[1], first_line_text))

                page_headings[page_idx] = headings_on_page

            # Step 2: Build section timeline — walk pages in order, track last trusted section
            section_timeline: dict[int, tuple[str, str, str]] = {}
            last_section = ("Unknown", "low", "no_heading_found")
            for page_idx in range(len(doc)):
                for y_pos, heading_text in sorted(page_headings.get(page_idx, [])):
                    sec_name, sec_conf, sec_reason = _normalize_section_name(heading_text)
                    if sec_name != "Unknown":
                        last_section = (sec_name, sec_conf, sec_reason)
                section_timeline[page_idx] = last_section

            # Step 3: Enrich each formula slot
            for slot in slots:
                if not slot.bbox or len(slot.bbox) != 4:
                    continue
                page_idx = slot.page - 1
                if page_idx < 0 or page_idx >= len(doc):
                    continue

                page = doc[page_idx]
                fx1, fy1, fx2, fy2 = slot.bbox

                blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

                text_before_parts = []
                text_after_parts = []

                for block in blocks:
                    if block.get("type") != 0:
                        continue
                    bb = block.get("bbox", (0, 0, 0, 0))
                    bx1, by1, bx2, by2 = bb

                    block_text = ""
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            block_text += span.get("text", "")
                        block_text += "\n"
                    block_text = block_text.strip()
                    if not block_text:
                        continue

                    if by2 < fy1:
                        text_before_parts.append(block_text)
                    elif by1 > fy2:
                        text_after_parts.append(block_text)

                slot.nearby_text_before = "\n".join(text_before_parts)[-500:] if text_before_parts else ""
                slot.nearby_text_after = "\n".join(text_after_parts)[:500] if text_after_parts else ""

                sec_name, sec_conf, sec_reason = section_timeline.get(
                    page_idx, ("Unknown", "low", "no_heading_found")
                )
                slot.section = sec_name
                slot.section_confidence = sec_conf
                slot.section_source = "heading_above" if sec_name != "Unknown" else "unknown"
                slot.section_reason = sec_reason
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


_TRUSTED_SECTIONS = {
    "abstract": "Abstract",
    "introduction": "Introduction",
    "related work": "Related Work",
    "related works": "Related Work",
    "background": "Related Work",
    "preliminaries": "Related Work",
    "problem statement": "Related Work",
    "method": "Method",
    "methods": "Method",
    "methodology": "Method",
    "approach": "Method",
    "proposed method": "Method",
    "proposed approach": "Method",
    "model": "Method",
    "model architecture": "Method",
    "experiments": "Experiments",
    "experimental results": "Experiments",
    "evaluation": "Experiments",
    "experiments and results": "Experiments",
    "results": "Experiments",
    "discussion": "Experiments",
    "conclusion": "Conclusion",
    "conclusions": "Conclusion",
    "summary": "Conclusion",
    "conclusion and future work": "Conclusion",
    "references": "References",
    "appendix": "Appendix",
}

_FORMULA_TEXT_PATTERNS = [
    r'[=∑√σλτπ∈⊙]',
    r'\\(?:frac|sum|int|partial|alpha|beta|gamma|delta|mathcal|mathbb|mathrm|sqrt|oplus|otimes)',
    r'(?:Attention|Softmax|Gumbel|argmax|argmin|Sigmoid|ReLU|ELU|LeakyReLU)\s*\(',
    r'[A-Z]\(\d+\)\s*=\s*\w',  # A(2) = Global(X(2))
    r'[A-Z]\(\d\)\s*[=∈⊂⊂≥≤]',  # A(2) = ... or X(2) ∈ ...
    r'(?:Global|Local|Encoder|Decoder|Attention)\s*\(',
    r'\b[A-Z]\s*=\s*(?:Softmax|Linear|Conv|Norm)',
    r'(?:Q|K|V)\s*=\s*(?:Softmax|Linear)',
    r'\\\[|\\\]',
    r'\$\$',
    r'j\s*∈\s*N',  # j∈N
    r'[a-z]\s*∈\s*[A-Z]',  # i ∈ N
]


def _looks_like_formula_text(text: str) -> bool:
    """Check if text looks like a formula rather than a section heading."""
    import re
    for pattern in _FORMULA_TEXT_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def _normalize_section_name(heading_text: str) -> tuple[str, str, str]:
    """Map a heading text to a standard section name.

    Returns:
        (section_name, confidence, reason) where:
        - section_name: trusted section name or "Unknown"
        - confidence: "high", "medium", or "low"
        - reason: human-readable explanation
    """
    import re
    text = heading_text.strip()
    if not text:
        return ("Unknown", "low", "empty_heading")

    # Reject formula text early
    if _looks_like_formula_text(text):
        return ("Unknown", "low", f"formula_text_detected: {text[:50]}")

    # Reject very long headings (likely not a section title)
    if len(text) > 80:
        return ("Unknown", "low", f"heading_too_long: {len(text)} chars")

    # Reject headings with too many special characters
    alpha_ratio = sum(c.isalpha() or c.isspace() for c in text) / max(len(text), 1)
    if alpha_ratio < 0.5:
        return ("Unknown", "low", f"low_alpha_ratio: {alpha_ratio:.2f}")

    # Remove leading numbers like "1.", "2.1", "I.", etc.
    cleaned = re.sub(r'^[\d\.]+\s*', '', text)
    cleaned = re.sub(r'^[IVXLC]+\.\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip().lower()

    # Exact match first
    if cleaned in _TRUSTED_SECTIONS:
        return (_TRUSTED_SECTIONS[cleaned], "high", f"exact_match: {cleaned}")

    # Substring match
    for key, standard in _TRUSTED_SECTIONS.items():
        if key in cleaned:
            return (standard, "medium", f"substring_match: '{key}' in '{cleaned}'")

    # No trusted match — return Unknown
    return ("Unknown", "low", f"no_trusted_match: {text[:50]}")


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
