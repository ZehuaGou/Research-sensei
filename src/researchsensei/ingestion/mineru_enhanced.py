"""Fast formula-aware PDF ingestion backed by MinerU2.5-Pro.

PyMuPDF extracts the complete text. A strict, cheap pre-screen then locates
numbered display equations and MinerU runs only on those crops. This preserves
trusted formula provenance without making users wait for full-page VLM parsing.
"""
from __future__ import annotations

import logging
import re
import threading
from collections.abc import Callable
from pathlib import Path

from researchsensei.canonical.mineru25_adapter import (
    FormulaRegionCandidate,
    MinerU25ProAdapter,
)
from researchsensei.ingestion.lightweight import LightweightIngestionService
from researchsensei.schemas import BlockType, DocumentBlock, DocumentIngestion, WarningItem

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, int], None]

_SECTION_ALIASES = {
    "abstract": "abstract",
    "introduction": "introduction",
    "related work": "related_work",
    "background": "related_work",
    "method": "method",
    "methodology": "method",
    "approach": "method",
    "experiments": "experiments",
    "experiment settings": "experiments",
    "results": "experiments",
    "evaluation": "experiments",
    "conclusion": "conclusion",
    "references": "references",
    "appendix": "appendix",
}


class MineruEnhancedIngestionService:
    """Combine fast PDF text extraction with targeted MinerU formula OCR."""

    def __init__(
        self,
        *,
        adapter: MinerU25ProAdapter | None = None,
        fallback: LightweightIngestionService | None = None,
        require_cuda: bool = True,
    ) -> None:
        self.adapter = adapter or MinerU25ProAdapter(
            device_mode="auto",
            render_scale=1.0,
            allow_cpu_fallback=not require_cuda,
        )
        self.fallback = fallback or LightweightIngestionService()
        self.require_cuda = require_cuda
        self._parse_lock = threading.Lock()

    def ingest_path(
        self,
        path: str | Path,
        paper_id: str | None = None,
        progress: ProgressCallback | None = None,
    ) -> DocumentIngestion:
        source = Path(path)
        actual_paper_id = paper_id or source.stem
        if source.suffix.lower() != ".pdf":
            return self.fallback.ingest_path(source, paper_id=actual_paper_id, progress=progress)

        report = progress or (lambda _stage, _value: None)
        base = self.fallback.ingest_path(source, paper_id=actual_paper_id, progress=progress)
        report("detecting_formula_regions", 21)
        regions = self._detect_numbered_formula_regions(source)
        if not regions:
            return base.model_copy(update={"parser_name": "pymupdf_formula_prescreen"})

        report("loading_formula_parser", 22)
        if not self.adapter.is_available():
            return self._degraded_base(
                base,
                "MINERU_UNAVAILABLE",
                "Formula regions were found, but MinerU is not installed; raw formulas remain blocked.",
            )
        device = self.adapter._probe_device()
        if self.require_cuda and device.get("device_mode_actual") != "cuda":
            return self._degraded_base(
                base,
                "MINERU_CUDA_REQUIRED",
                "Formula regions were found, but no supported CUDA GPU is available; raw formulas remain blocked.",
            )

        try:
            with self._parse_lock:
                formulas, payload = self.adapter.parse_formula_regions(
                    source,
                    regions,
                    progress=lambda completed, total: report(
                        f"parsing_formula_regions:{completed}/{total}",
                        22 + round(8 * completed / max(total, 1)),
                    ),
                )
        except Exception as error:
            logger.exception("MinerU formula-region parsing failed for %s", source)
            return self._degraded_base(
                base,
                "MINERU_PARSE_FAILED",
                f"MinerU formula parsing failed; raw formulas remain blocked. Detail: {str(error)[:240]}",
            )

        parsed_by_ref = {block.raw_payload_ref: block for block in formulas}
        formula_blocks: list[DocumentBlock] = []
        for index, region in enumerate(regions, start=1):
            block = parsed_by_ref.get(f"formula_region_{index:03d}")
            if block is None:
                continue
            formula_blocks.append(self._formula_block(actual_paper_id, index, region, block.latex))

        stats = payload.get("stats", {}) if isinstance(payload, dict) else {}
        warnings = list(base.warnings)
        partial = len(formula_blocks) != len(regions)
        if partial:
            warnings.append(
                WarningItem(
                    code="MINERU_FORMULA_REGION_PARTIAL",
                    message=(
                        f"MinerU parsed {len(formula_blocks)} of {len(regions)} numbered formula regions; "
                        "unparsed formulas were not promoted to trusted evidence."
                    ),
                )
            )
        if stats.get("device_mode_actual") not in {None, "cuda"}:
            warnings.append(
                WarningItem(
                    code="MINERU_DEVICE_DEGRADED",
                    message="MinerU formula crops were parsed without configured CUDA acceleration.",
                )
            )

        # Remove heuristic raw-formula blocks. The paragraph text remains
        # available, while only MinerU LaTeX is admitted as formula evidence.
        text_blocks = [block for block in base.blocks if block.type != BlockType.FORMULA]
        return base.model_copy(
            update={
                "parser_name": "pymupdf+mineru_formula_regions",
                "degraded": bool(base.degraded or partial),
                "warnings": warnings,
                "blocks": [*text_blocks, *formula_blocks],
            }
        )

    @staticmethod
    def _degraded_base(base: DocumentIngestion, code: str, message: str) -> DocumentIngestion:
        return base.model_copy(
            update={
                "degraded": True,
                "warnings": [*base.warnings, WarningItem(code=code, message=message)],
            }
        )

    def _detect_numbered_formula_regions(self, source: Path) -> list[FormulaRegionCandidate]:
        try:
            import fitz
        except ImportError:
            return []

        regions: list[FormulaRegionCandidate] = []
        current_section = "full_text"
        with fitz.open(str(source)) as document:
            for page_index, page in enumerate(document):
                lines = self._page_lines(page)
                equation_lines = [
                    line for line in lines if re.fullmatch(r"\(\s*\d+(?:\.\d+)*\s*\)", line[1])
                ]
                for bbox, tag_text in equation_lines:
                    center_y = (bbox[1] + bbox[3]) / 2
                    for heading_bbox, heading_text in lines:
                        if heading_bbox[1] >= center_y:
                            continue
                        section = self._heading_section(heading_text)
                        if section:
                            current_section = section
                    page_mid = page.rect.width / 2
                    if (bbox[0] + bbox[2]) / 2 < page_mid:
                        x0, x1 = page.rect.x0 + 38, page_mid - 8
                    else:
                        x0, x1 = page_mid + 8, page.rect.x1 - 38
                    y0 = max(page.rect.y0, center_y - 38)
                    y1 = min(page.rect.y1, center_y + 38)
                    crop = (float(x0), float(y0), float(x1), float(y1))
                    regions.append(
                        FormulaRegionCandidate(
                            page=page_index + 1,
                            bbox=crop,
                            equation_number=tag_text.strip()[1:-1].strip(),
                            section=current_section,
                            context_before=self._clip_context(page, x0, max(page.rect.y0, y0 - 110), x1, y0),
                            context_after=self._clip_context(page, x0, y1, x1, min(page.rect.y1, y1 + 110)),
                        )
                    )
                for _heading_bbox, heading_text in lines:
                    section = self._heading_section(heading_text)
                    if section:
                        current_section = section
        return sorted(
            regions,
            key=lambda region: (
                region.page,
                tuple(int(part) for part in region.equation_number.split(".")),
            ),
        )

    @staticmethod
    def _page_lines(page) -> list[tuple[tuple[float, float, float, float], str]]:
        lines: list[tuple[tuple[float, float, float, float], str]] = []
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                text = "".join(str(span.get("text") or "") for span in line.get("spans", [])).strip()
                bbox = line.get("bbox") or []
                if text and len(bbox) == 4:
                    x0, y0, x1, y1 = (float(value) for value in bbox)
                    lines.append(((x0, y0, x1, y1), text))
        return sorted(lines, key=lambda item: (item[0][1], item[0][0]))

    @staticmethod
    def _heading_section(text: str) -> str:
        cleaned = re.sub(r"^\s*\d+(?:\.\d+)*\s+", "", text).strip().lower().strip(" .:")
        if cleaned in _SECTION_ALIASES:
            return _SECTION_ALIASES[cleaned]
        for label, section in _SECTION_ALIASES.items():
            if re.fullmatch(rf"{re.escape(label)}(?:\s+stage)?", cleaned):
                return section
        return ""

    @staticmethod
    def _clip_context(page, x0: float, y0: float, x1: float, y1: float) -> str:
        import fitz

        text = page.get_text("text", clip=fitz.Rect(x0, y0, x1, y1))
        return re.sub(r"\s+", " ", text).strip()[:1200]

    @staticmethod
    def _formula_block(
        paper_id: str,
        index: int,
        region: FormulaRegionCandidate,
        latex: str,
    ) -> DocumentBlock:
        block_id = f"mineru_eq_{index:03d}"
        formula_id = f"mineru_formula_{index:03d}"
        return DocumentBlock(
            block_id=block_id,
            type=BlockType.FORMULA,
            text=latex,
            evidence_ref=f"{paper_id}:{block_id}",
            section=region.section,
            page=region.page,
            normalized_text=" ".join(latex.lower().split()),
            raw_latex=latex,
            bbox=region.bbox,
            formula_id=formula_id,
            formula_latex=latex,
            formula_origin="mineru_latex",
            formula_bbox=region.bbox,
            formula_page=region.page,
            formula_context_before=region.context_before,
            formula_context_after=region.context_after,
            formula_ocr_status="not_required",
            formula_explanation_status="parser_derived",
            equation_number=region.equation_number,
            equation_group_id=f"mineru_page_{region.page}",
            group_order=index,
            block_source="mineru25pro_formula_region",
            section_confidence="high" if region.section != "full_text" else "medium",
            parse_quality_status="mineru_latex",
            mineru_available=True,
        )
