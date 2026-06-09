"""FormulaRegionDetector — detects formula regions in PDF pages.

Supports multiple detection backends:
- MinerU output bbox
- Marker output bbox
- PDF layout bbox
- PyMuPDF fallback
- not_detected status
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from researchsensei.schemas.canonical import FormulaRegionResult

logger = logging.getLogger(__name__)


class FormulaRegionDetector:
    """Detects formula regions in PDF documents as a deprecated fallback.

    This v1 helper is superseded by MinerU25ProAdapter as the primary M1 v2
    parser and MarkerDocumentFormulaDetector as fallback/audit baseline. It
    remains only for low-confidence fallback/debug use.

    Supports multiple backends with graceful degradation.
    """

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    def detect(
        self,
        formula_id: str,
        source_path: str,
        page: int | None = None,
        context_text: str = "",
    ) -> FormulaRegionResult:
        """Detect formula region in a PDF page.

        Returns FormulaRegionResult with formula_region_status:
        - detected: formula region found with bbox
        - not_detected: no formula region found
        - unavailable: detector not available or source not accessible
        """
        if not self.enabled:
            return FormulaRegionResult(
                formula_id=formula_id,
                formula_region_status="unavailable",
                warnings=["FormulaRegionDetector is disabled."],
            )

        if not source_path:
            return FormulaRegionResult(
                formula_id=formula_id,
                formula_region_status="not_detected",
                warnings=["No source path provided."],
            )

        source = Path(source_path)
        if not source.exists():
            return FormulaRegionResult(
                formula_id=formula_id,
                formula_region_status="unavailable",
                warnings=[f"Source file not found: {source_path}"],
            )

        if source.suffix.lower() == ".pdf":
            return self._detect_in_pdf(formula_id, source, page)

        return FormulaRegionResult(
            formula_id=formula_id,
            formula_region_status="not_detected",
            warnings=[f"Unsupported source type: {source.suffix}"],
        )

    def _detect_in_pdf(
        self, formula_id: str, pdf_path: Path, page: int | None
    ) -> FormulaRegionResult:
        """Detect formula regions in a PDF using PyMuPDF."""
        try:
            import fitz  # PyMuPDF

            with fitz.open(str(pdf_path)) as doc:
                if page is not None and 1 <= page <= len(doc):
                    target_page = doc[page - 1]  # 0-indexed
                elif len(doc) > 0:
                    target_page = doc[0]
                else:
                    return FormulaRegionResult(
                        formula_id=formula_id,
                        formula_region_status="not_detected",
                        warnings=["PDF has no pages."],
                    )

                # Extract text blocks with position info
                blocks = target_page.get_text("dict")["blocks"]
                formula_regions = []

                for block in blocks:
                    if block.get("type") == 0:  # Text block
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                text = span.get("text", "")
                                # Check if text contains formula-like content
                                if self._looks_like_formula(text):
                                    bbox = span.get("bbox", [0, 0, 0, 0])
                                    formula_regions.append({
                                        "bbox": list(bbox),
                                        "text": text,
                                        "confidence": 0.6,
                                    })

                if formula_regions:
                    # Return the most formula-like region
                    best = max(formula_regions, key=lambda r: r["confidence"])
                    return FormulaRegionResult(
                        formula_id=formula_id,
                        formula_bbox=best["bbox"],
                        formula_page=page or 1,
                        detector_confidence=best["confidence"],
                        formula_region_status="detected",
                    )

                return FormulaRegionResult(
                    formula_id=formula_id,
                    formula_region_status="not_detected",
                    warnings=["No formula regions detected in page."],
                )

        except ImportError:
            return FormulaRegionResult(
                formula_id=formula_id,
                formula_region_status="unavailable",
                warnings=["PyMuPDF (fitz) not available for formula detection."],
            )
        except Exception as exc:
            logger.warning("FormulaRegionDetector error: %s", exc)
            return FormulaRegionResult(
                formula_id=formula_id,
                formula_region_status="unavailable",
                warnings=[f"Detection error: {str(exc)[:200]}"],
            )

    def _looks_like_formula(self, text: str) -> bool:
        """Heuristic check if text looks like a formula."""
        if not text or len(text.strip()) < 3:
            return False

        # Common formula indicators
        formula_indicators = [
            r"[=+\-*/^_{}]",
            r"\\[a-zA-Z]+",  # LaTeX commands
            r"\d+\.\d+",  # Decimal numbers
            r"[αβγδεζηθικλμνξπρστυφχψω]",  # Greek letters
            r"[∑∏∫∂∇∞≈≠≤≥±×÷]",  # Math symbols
        ]

        for pattern in formula_indicators:
            if re.search(pattern, text):
                return True

        return False
