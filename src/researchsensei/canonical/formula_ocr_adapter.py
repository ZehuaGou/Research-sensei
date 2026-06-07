"""FormulaOCRAdapter — OCR formula regions to LaTeX.

Tries pix2tex / LaTeX-OCR with graceful degradation.
Policy: formula_ocr_enabled, on_demand mode, max 3 per paper, timeout configurable.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from researchsensei.schemas.canonical import FormulaOcrResult
from researchsensei.schemas.enums import FormulaOrigin, FormulaOcrStatus

logger = logging.getLogger(__name__)


class FormulaOCRAdapter:
    """OCR adapter for formula regions using pix2tex / LaTeX-OCR.

    Default policy:
    - formula_ocr_enabled: True
    - default_formula_ocr_mode: on_demand
    - max_formula_ocr_per_paper: 3
    - max_formula_ocr_batch: 10
    - formula_ocr_timeout_seconds: 30
    """

    def __init__(
        self,
        *,
        enabled: bool = True,
        mode: str = "on_demand",
        max_per_paper: int = 3,
        max_batch: int = 10,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.enabled = enabled
        self.mode = mode
        self.max_per_paper = max_per_paper
        self.max_batch = max_batch
        self.timeout_seconds = timeout_seconds
        self._ocr_count = 0
        self._model = None
        self._model_load_attempted = False

    def ocr(
        self,
        formula_id: str,
        source_path: str,
        page: int | None = None,
        bbox: list[float] | None = None,
    ) -> FormulaOcrResult:
        """OCR a formula region to LaTeX.

        Returns FormulaOcrResult with formula_ocr_status:
        - success: OCR succeeded
        - failed: OCR attempted but failed
        - unavailable: OCR model not available
        - not_triggered: OCR not triggered (policy or conditions)
        """
        if not self.enabled:
            return FormulaOcrResult(
                formula_id=formula_id,
                formula_ocr_status=FormulaOcrStatus.NOT_TRIGGERED,
                blocking_reason="Formula OCR is disabled.",
            )

        if self._ocr_count >= self.max_per_paper:
            return FormulaOcrResult(
                formula_id=formula_id,
                formula_ocr_status=FormulaOcrStatus.NOT_TRIGGERED,
                blocking_reason=f"Max OCR count reached ({self.max_per_paper}).",
            )

        if not source_path:
            return FormulaOcrResult(
                formula_id=formula_id,
                formula_ocr_status=FormulaOcrStatus.NOT_TRIGGERED,
                blocking_reason="No source path provided.",
            )

        source = Path(source_path)
        if not source.exists():
            return FormulaOcrResult(
                formula_id=formula_id,
                formula_ocr_status=FormulaOcrStatus.FAILED,
                blocking_reason=f"Source file not found: {source_path}",
            )

        # Try to load model if not loaded
        if not self._model_load_attempted:
            self._try_load_model()

        if self._model is None:
            return FormulaOcrResult(
                formula_id=formula_id,
                formula_ocr_status=FormulaOcrStatus.UNAVAILABLE,
                blocking_reason="Formula OCR model not available (pix2tex/LaTeX-OCR not installed or failed to load).",
            )

        # Extract formula image from PDF
        try:
            formula_image = self._extract_formula_image(source, page, bbox)
            if formula_image is None:
                return FormulaOcrResult(
                    formula_id=formula_id,
                    formula_ocr_status=FormulaOcrStatus.FAILED,
                    blocking_reason="Could not extract formula image from source.",
                )

            # Run OCR with timeout
            start_time = time.time()
            latex = self._run_ocr(formula_image)
            elapsed = time.time() - start_time

            if elapsed > self.timeout_seconds:
                return FormulaOcrResult(
                    formula_id=formula_id,
                    formula_ocr_status=FormulaOcrStatus.FAILED,
                    blocking_reason=f"OCR timeout ({elapsed:.1f}s > {self.timeout_seconds}s).",
                )

            if not latex or not latex.strip():
                return FormulaOcrResult(
                    formula_id=formula_id,
                    formula_ocr_status=FormulaOcrStatus.FAILED,
                    blocking_reason="OCR returned empty result.",
                )

            self._ocr_count += 1
            return FormulaOcrResult(
                formula_id=formula_id,
                formula_latex=latex.strip(),
                formula_origin=FormulaOrigin.OCR_LATEX,
                formula_ocr_status=FormulaOcrStatus.SUCCESS,
                ocr_confidence=0.7,  # Default confidence for successful OCR
            )

        except Exception as exc:
            logger.warning("FormulaOCR error for %s: %s", formula_id, exc)
            return FormulaOcrResult(
                formula_id=formula_id,
                formula_ocr_status=FormulaOcrStatus.FAILED,
                blocking_reason=f"OCR error: {str(exc)[:200]}",
            )

    def _try_load_model(self) -> None:
        """Try to load pix2tex / LaTeX-OCR model."""
        self._model_load_attempted = True

        try:
            # Try pix2tex first
            from pix2tex.cli import LatexOCR
            self._model = LatexOCR()
            logger.info("Loaded pix2tex LaTeX-OCR model.")
            return
        except ImportError:
            logger.debug("pix2tex not available.")
        except Exception as exc:
            logger.warning("pix2tex load failed (likely dependency issue): %s", exc)

        try:
            # Try latex_ocr
            import latex_ocr
            self._model = latex_ocr
            logger.info("Loaded latex_ocr model.")
            return
        except ImportError:
            logger.debug("latex_ocr not available.")
        except Exception as exc:
            logger.debug("latex_ocr load failed: %s", exc)

        logger.warning("No formula OCR model available. Install pix2tex or latex_ocr.")

    def _extract_formula_image(
        self, source_path: Path, page: int | None, bbox: list[float] | None
    ):
        """Extract formula image from PDF page."""
        try:
            import fitz  # PyMuPDF

            with fitz.open(str(source_path)) as doc:
                if page is not None and 1 <= page <= len(doc):
                    target_page = doc[page - 1]
                elif len(doc) > 0:
                    target_page = doc[0]
                else:
                    return None

                if bbox and len(bbox) == 4:
                    # Extract specific region
                    rect = fitz.Rect(bbox)
                    pix = target_page.get_pixmap(clip=rect)
                else:
                    # Extract full page
                    pix = target_page.get_pixmap()

                # Convert to PIL Image
                img_data = pix.tobytes("png")
                from PIL import Image
                import io
                return Image.open(io.BytesIO(img_data))

        except ImportError:
            logger.warning("PyMuPDF or PIL not available for image extraction.")
            return None
        except Exception as exc:
            logger.warning("Image extraction failed: %s", exc)
            return None

    def _run_ocr(self, image) -> str:
        """Run OCR on an image."""
        if hasattr(self._model, "latexocr"):
            # pix2tex interface
            return self._model.latexocr(image)
        elif callable(self._model):
            # Direct callable interface
            return self._model(image)
        else:
            raise RuntimeError("OCR model has no callable interface.")

    def reset_count(self) -> None:
        """Reset OCR count (call when processing a new paper)."""
        self._ocr_count = 0
