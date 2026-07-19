"""FormulaCropper — crops formula regions from PDF using PyMuPDF.

Takes FormulaSlot entries with bbox coordinates and produces cropped formula images.
Bbox coordinates are in PDF points (1/72 inch), which is exactly what PyMuPDF uses.
"""
from __future__ import annotations

import logging
from importlib.util import find_spec
from pathlib import Path

from researchsensei.schemas.canonical import FormulaSlot
from researchsensei.schemas.enums import FormulaOcrStatus

logger = logging.getLogger(__name__)

# Default padding in PDF points (1/72 inch)
DEFAULT_PADDING = 4.0


class FormulaCropper:
    """Crops formula regions from PDF using PyMuPDF.

    Usage:
        cropper = FormulaCropper(padding=4.0)
        slots = cropper.crop(pdf_path, slots, output_dir)
    """

    def __init__(self, padding: float = DEFAULT_PADDING, dpi: int = 200) -> None:
        self.padding = padding
        self.dpi = dpi

    def is_available(self) -> bool:
        return find_spec("fitz") is not None

    def crop(
        self,
        pdf_path: str | Path,
        slots: list[FormulaSlot],
        output_dir: str | Path,
    ) -> list[FormulaSlot]:
        """Crop formula regions from PDF and update slots with crop paths.

        Args:
            pdf_path: Path to the PDF file.
            slots: List of FormulaSlot entries with bbox coordinates.
            output_dir: Directory to save cropped images.

        Returns:
            Updated FormulaSlot list with crop_path and ocr_status set.
        """
        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)

        if not pdf_path.exists():
            logger.warning("PDF not found: %s", pdf_path)
            return slots

        if not self.is_available():
            logger.warning("PyMuPDF (fitz) not available for cropping")
            return slots

        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            import fitz
            doc = fitz.open(str(pdf_path))
        except Exception as exc:
            logger.warning("Failed to open PDF for cropping: %s", exc)
            return slots

        cropped_count = 0
        try:
            for slot in slots:
                if not slot.bbox or len(slot.bbox) != 4:
                    slot.ocr_status = FormulaOcrStatus.SKIPPED_BY_POLICY
                    slot.unresolved_reason = "invalid_bbox"
                    continue

                page_num = slot.page
                if page_num < 0 or page_num >= len(doc):
                    slot.ocr_status = FormulaOcrStatus.SKIPPED_BY_POLICY
                    slot.unresolved_reason = f"page_{page_num}_out_of_range"
                    continue

                try:
                    crop_path = self._crop_one(doc, page_num, slot, output_dir)
                    if crop_path:
                        slot.crop_path = str(crop_path.relative_to(output_dir))
                        slot.ocr_status = FormulaOcrStatus.CROPPED
                        cropped_count += 1
                    else:
                        slot.ocr_status = FormulaOcrStatus.SKIPPED_BY_POLICY
                        slot.unresolved_reason = "crop_failed"
                except Exception as exc:
                    logger.warning("Crop failed for %s: %s", slot.formula_id, exc)
                    slot.ocr_status = FormulaOcrStatus.SKIPPED_BY_POLICY
                    slot.unresolved_reason = f"crop_error: {type(exc).__name__}"
        finally:
            doc.close()

        logger.info(
            "FormulaCropper: cropped %d/%d formulas from %s",
            cropped_count, len(slots), pdf_path.name,
        )
        return slots

    def _crop_one(self, doc, page_num: int, slot: FormulaSlot, output_dir: Path) -> Path | None:
        """Crop a single formula from the PDF."""
        import fitz

        page = doc[page_num]
        x1, y1, x2, y2 = slot.bbox

        # Apply padding (clamped to page bounds)
        page_rect = page.rect
        x1 = max(0, x1 - self.padding)
        y1 = max(0, y1 - self.padding)
        x2 = min(page_rect.width, x2 + self.padding)
        y2 = min(page_rect.height, y2 + self.padding)

        rect = fitz.Rect(x1, y1, x2, y2)

        # Check minimum size
        if rect.width < 5 or rect.height < 5:
            return None

        pix = page.get_pixmap(clip=rect, dpi=self.dpi)

        # Save as PNG
        crop_filename = f"{slot.formula_id}_p{slot.page}.png"
        crop_path = output_dir / crop_filename
        pix.save(str(crop_path))

        return crop_path
