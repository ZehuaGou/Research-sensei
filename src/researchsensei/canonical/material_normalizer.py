"""M1.4 Material Normalizer — converts raw sources to canonical_paper.md.

Three-pipeline architecture:
1. Body pipeline: MarkItDown (default) → PyMuPDF (text fallback) → optional Marker
2. Formula pipeline: MarkerDocumentFormulaDetector → FormulaSlot → FormulaCropper
3. FormulaMerger: body sections + formula slots → canonical_paper.md

Source priority: latex_source > structured_html > marker_pdf > mineru_pdf > pymupdf > low_confidence_text > metadata_only.
metadata_only cannot enter M2.
"""
from __future__ import annotations

import json
import logging
import multiprocessing
import re
from pathlib import Path

from researchsensei.schemas.canonical import (
    AdapterInfo,
    CanonicalPaper,
    CanonicalPaperFrontMatter,
    CanonicalizationResult,
    FormulaBlock,
    FormulaSlot,
)
from researchsensei.schemas.common import WarningItem
from researchsensei.schemas.direction import CandidatePaper, ResolvedPaperSource
from researchsensei.schemas.enums import (
    AdapterStatus,
    CanonicalQualityStatus,
    CanonicalizationStatus,
    FormulaOrigin,
    FormulaOcrStatus,
    PaperSourceStatus,
    SourcePriority,
)

logger = logging.getLogger(__name__)


def _run_marker_pdf_adapter_worker(pdf_path: str, queue) -> None:
    """Run Marker in a child process so timeout can terminate heavy work."""
    try:
        from researchsensei.canonical.adapters import MarkerPdfAdapter

        result = MarkerPdfAdapter().process(Path(pdf_path))
        queue.put({
            "succeeded": result.succeeded,
            "text": "\n".join(result.sections.values()) if result.sections else "",
            "blocking_reason": result.blocking_reason,
            "warnings": result.warnings,
        })
    except Exception as exc:  # pragma: no cover - defensive child-process boundary
        queue.put({
            "succeeded": False,
            "text": "",
            "blocking_reason": f"{type(exc).__name__}: {str(exc)[:300]}",
            "warnings": [f"Marker worker failed: {exc}"],
        })

_STANDARD_SECTIONS = [
    "Abstract",
    "Introduction",
    "Related Work",
    "Method",
    "Experiments",
    "Conclusion",
    "References",
]


class MaterialNormalizer:
    """M1 material normalizer: produces canonical_paper.md from raw sources.

    Three-pipeline architecture:
    1. Body pipeline: MarkItDown (default) → PyMuPDF (text fallback) → optional Marker
    2. Formula pipeline: MarkerDocumentFormulaDetector → FormulaSlot → FormulaCropper
    3. FormulaMerger: body sections + formula slots → canonical_paper.md

    Source priority:
    1. latex_source (arXiv source, LaTeX package)
    2. structured_html (HTML/XML, DeepXiv)
    3. pdf (parsed PDF)
    4. low_confidence_text (low-quality text extraction)
    5. metadata_only (cannot enter M2)
    """

    def __init__(
        self,
        *,
        formula_region_detector=None,
        formula_ocr_adapter=None,
        marker_enabled: bool = False,
        marker_trigger_mode: str = "never",
        marker_timeout_seconds: float = 90.0,
        formula_detection_enabled: bool = True,
        formula_crop_enabled: bool = True,
    ) -> None:
        self.formula_region_detector = formula_region_detector
        self.formula_ocr_adapter = formula_ocr_adapter
        self.marker_enabled = marker_enabled
        self.marker_trigger_mode = marker_trigger_mode
        self.marker_timeout_seconds = marker_timeout_seconds
        self._marker_enabled = marker_enabled
        self._marker_trigger_mode = marker_trigger_mode
        self._marker_timeout_seconds = marker_timeout_seconds
        self.formula_detection_enabled = formula_detection_enabled
        self.formula_crop_enabled = formula_crop_enabled

    def normalize(
        self,
        paper: CandidatePaper,
        source: ResolvedPaperSource | None,
        *,
        output_dir: Path | None = None,
    ) -> CanonicalizationResult:
        """Normalize a paper to canonical_paper.md."""
        source_priority = self._determine_source_priority(paper, source)
        has_valid_source = source_priority not in (SourcePriority.METADATA_ONLY,)

        if source_priority == SourcePriority.METADATA_ONLY:
            return self._metadata_only_result(paper, source)

        # Try to extract content based on source type
        sections, formula_blocks, parser_used, parse_warnings = self._extract_content(
            paper, source, source_priority
        )

        # Determine canonicalization status
        has_content = any(v.strip() for v in sections.values())
        if not has_content:
            return CanonicalizationResult(
                paper_id=paper.paper_id,
                title=paper.title,
                source_type=source_priority.value,
                source_priority=source_priority,
                preferred_m2_input=source_priority.value,
                has_valid_deep_reading_source=False,
                canonicalization_status=CanonicalizationStatus.FAILED,
                canonical_quality_status=CanonicalQualityStatus.FAIL,
                m2_ready=False,
                degradation_reason="No content extracted from source.",
                warnings=parse_warnings,
            )

        sections, quality_status, quality_reasons = self._repair_and_assess_sections(sections)

        # === FORMULA PIPELINE: detect, crop, resolve ===
        formula_slots: list[FormulaSlot] = []
        formula_slot_count = 0
        formula_crop_count = 0
        parser_latex_count = 0
        ocr_latex_count = 0
        raw_formula_text_count = 0
        unresolved_formula_count = 0

        if self.formula_detection_enabled and source_priority == SourcePriority.PDF:
            pdf_path_for_formula = source.local_path if source else None
            if pdf_path_for_formula and Path(pdf_path_for_formula).exists():
                formula_slots = self._run_formula_pipeline(
                    Path(pdf_path_for_formula), formula_blocks, output_dir
                )
                # Count by origin
                for fs in formula_slots:
                    if fs.final_origin == FormulaOrigin.PARSER_LATEX:
                        parser_latex_count += 1
                    elif fs.final_origin == FormulaOrigin.OCR_LATEX:
                        ocr_latex_count += 1
                    elif fs.final_origin == FormulaOrigin.RAW_FORMULA_TEXT:
                        raw_formula_text_count += 1
                    elif fs.final_origin == FormulaOrigin.UNRESOLVED:
                        unresolved_formula_count += 1
                formula_slot_count = len(formula_slots)
                formula_crop_count = sum(1 for fs in formula_slots if fs.crop_path)

        # Determine degradation and M2 gate.
        missing_sections = [s for s in _STANDARD_SECTIONS if not sections.get(s, "").strip()]
        degraded = len(missing_sections) > 3 or quality_status == CanonicalQualityStatus.DEGRADED
        if quality_status == CanonicalQualityStatus.FAIL:
            status = CanonicalizationStatus.FAILED
        else:
            status = CanonicalizationStatus.DEGRADED if degraded else CanonicalizationStatus.SUCCESS
        m2_ready = has_content and source_priority != SourcePriority.METADATA_ONLY and quality_status != CanonicalQualityStatus.FAIL
        degradation_parts: list[str] = []
        if missing_sections:
            degradation_parts.append(f"Missing sections: {', '.join(missing_sections)}")
        degradation_parts.extend(quality_reasons)
        degradation_reason = "; ".join(degradation_parts)

        front_matter = CanonicalPaperFrontMatter(
            paper_id=paper.paper_id,
            title=paper.title or "Untitled",
            authors=paper.authors,
            year=paper.year,
            venue=paper.venue,
            source_type=source_priority.value,
            source_confidence=paper.source_confidence,
            canonicalization_status=status,
            canonical_quality_status=quality_status,
            parser_used=parser_used,
            m2_ready=m2_ready,
            degradation_reason=degradation_reason,
            # Parser quality selection fields
            parser_candidates=[c.parser_name for c in getattr(self, '_parser_quality_scores', [])],
            selected_parser=parser_used,
            parser_quality_score=getattr(self, '_selected_parser_score', 0.0),
            parser_selection_reason=getattr(self, '_parser_selection_reason', ''),
            # Store detailed scores as JSON
            parser_quality_details_json=json.dumps(getattr(self, '_parser_quality_details', {})),
            # Body parser selection (three-pipeline)
            body_selected_parser=parser_used,
            body_parser_quality_score=getattr(self, '_selected_parser_score', 0.0),
            body_parser_selection_reason=getattr(self, '_parser_selection_reason', ''),
            # Formula pipeline metadata
            formula_detector="marker_document" if formula_slots else "",
            formula_selected_parser="marker" if formula_slots else "",
            formula_slot_count=formula_slot_count,
            formula_crop_count=formula_crop_count,
            parser_latex_count=parser_latex_count,
            ocr_latex_count=ocr_latex_count,
            raw_formula_text_count=raw_formula_text_count,
            unresolved_formula_count=unresolved_formula_count,
            canonical_quality_status_formula=_formula_quality_status(formula_slots),
        )

        canonical = CanonicalPaper(
            front_matter=front_matter,
            sections=sections,
            formula_blocks=formula_blocks,
        )

        # Run formula region detection BEFORE writing file
        formula_region_results = []
        if self.formula_region_detector and formula_blocks:
            for fb in formula_blocks:
                try:
                    result = self.formula_region_detector.detect(
                        formula_id=fb.formula_id,
                        source_path=source.local_path if source else "",
                        page=fb.page,
                    )
                    formula_region_results.append(result)
                except Exception as exc:
                    logger.warning("FormulaRegionDetector failed for %s: %s", fb.formula_id, exc)

        # Run formula OCR BEFORE writing file (may update formula_blocks in-place)
        formula_ocr_results = []
        formulas_updated = False
        if self.formula_ocr_adapter and formula_blocks:
            for fb in formula_blocks:
                if fb.origin == FormulaOrigin.UNKNOWN or not fb.latex.strip():
                    try:
                        ocr_result = self.formula_ocr_adapter.ocr(
                            formula_id=fb.formula_id,
                            source_path=source.local_path if source else "",
                            page=fb.page,
                            bbox=fb.bbox,
                        )
                        formula_ocr_results.append(ocr_result)
                        if ocr_result.formula_latex:
                            fb.latex = ocr_result.formula_latex
                            fb.origin = ocr_result.formula_origin
                            fb.ocr_status = ocr_result.formula_ocr_status
                            fb.ocr_confidence = ocr_result.ocr_confidence
                            formulas_updated = True
                    except Exception as exc:
                        logger.warning("FormulaOCRAdapter failed for %s: %s", fb.formula_id, exc)

        # Re-render markdown if formulas were updated
        if formulas_updated:
            canonical = CanonicalPaper(
                front_matter=front_matter,
                sections=sections,
                formula_blocks=formula_blocks,
            )

        # Generate markdown AFTER all formula updates (new formula slot format)
        raw_md = self._render_markdown_with_slots(canonical, formula_slots)
        canonical.raw_markdown = raw_md

        # Write to file AFTER formula detection and OCR
        canonical_path = ""
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            md_path = output_dir / "canonical_paper.md"
            md_path.write_text(raw_md, encoding="utf-8")
            canonical_path = str(md_path)

            # Write formula_slots.json
            if formula_slots:
                slots_path = output_dir / "formula_slots.json"
                slots_data = [fs.model_dump() for fs in formula_slots]
                slots_path.write_text(json.dumps(slots_data, indent=2, ensure_ascii=False), encoding="utf-8")

        # Build adapter info
        adapter_info = self._build_adapter_info()

        return CanonicalizationResult(
            paper_id=paper.paper_id,
            title=paper.title,
            source_type=source_priority.value,
            source_priority=source_priority,
            preferred_m2_input=source_priority.value,
            has_valid_deep_reading_source=has_valid_source,
            canonical_paper=canonical,
            canonical_paper_path=canonical_path,
            canonicalization_status=status,
            canonical_quality_status=quality_status,
            m2_ready=m2_ready,
            degradation_reason=degradation_reason,
            formula_blocks=formula_blocks,
            formula_region_results=formula_region_results,
            formula_ocr_results=formula_ocr_results,
            adapter_info=adapter_info,
            warnings=parse_warnings,
        )

    def _determine_source_priority(
        self, paper: CandidatePaper, source: ResolvedPaperSource | None
    ) -> SourcePriority:
        """Determine source priority from paper and source metadata."""
        # Check for LaTeX source availability (arXiv e-print tar.gz)
        if source and source.source_type.value == "ARXIV_SOURCE":
            if source.status in (PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,):
                # Check if the downloaded file is actually a LaTeX source (tar.gz)
                if source.local_path:
                    from pathlib import Path
                    local = Path(source.local_path)
                    if local.exists() and local.suffix in ('.gz', '.tar', '.tgz'):
                        return SourcePriority.LATEX_SOURCE
                    # Otherwise it's a PDF downloaded from arXiv
                    return SourcePriority.PDF
                if paper.arxiv_id:
                    return SourcePriority.PDF  # PDF, not LaTeX source

        # Check for structured HTML
        if source and source.content_type and "html" in source.content_type.lower():
            return SourcePriority.STRUCTURED_HTML

        # Check for PDF
        if source and source.status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED:
            return SourcePriority.PDF

        if paper.pdf_downloaded:
            return SourcePriority.PDF

        if paper.pdf_url or paper.pdf_available:
            return SourcePriority.PDF

        # Metadata only
        return SourcePriority.METADATA_ONLY

    def _extract_content(
        self,
        paper: CandidatePaper,
        source: ResolvedPaperSource | None,
        source_priority: SourcePriority,
    ) -> tuple[dict[str, str], list[FormulaBlock], str, list[str]]:
        """Extract content from source based on priority."""
        sections: dict[str, str] = {}
        formula_blocks: list[FormulaBlock] = []
        parser_used = ""
        warnings: list[str] = []

        if source_priority == SourcePriority.LATEX_SOURCE:
            sections, formula_blocks, parser_used, warnings = self._extract_from_latex(paper, source)
        elif source_priority == SourcePriority.STRUCTURED_HTML:
            sections, formula_blocks, parser_used, warnings = self._extract_from_html(paper, source)
        elif source_priority == SourcePriority.PDF:
            sections, formula_blocks, parser_used, warnings = self._extract_from_pdf(paper, source)
        elif source_priority == SourcePriority.LOW_CONFIDENCE_TEXT:
            sections, formula_blocks, parser_used, warnings = self._extract_from_text(paper, source)

        # Always ensure title section
        if not sections.get("Title"):
            sections["Title"] = paper.title or ""

        return sections, formula_blocks, parser_used, warnings

    def _extract_from_latex(
        self, paper: CandidatePaper, source: ResolvedPaperSource | None
    ) -> tuple[dict[str, str], list[FormulaBlock], str, list[str]]:
        """Extract from LaTeX source (arXiv e-print)."""
        warnings: list[str] = []
        formula_blocks: list[FormulaBlock] = []
        sections: dict[str, str] = {}

        # Check if we have a local LaTeX source (tar.gz)
        source_path = None
        if source and source.local_path:
            source_path = Path(source.local_path)
            if source_path.exists() and source_path.suffix in ('.gz', '.tar', '.tgz'):
                # This is a LaTeX source archive
                try:
                    sections, formula_blocks = self._parse_latex_source(source_path)
                    return sections, formula_blocks, "latex_source_parser", warnings
                except Exception as exc:
                    warnings.append(f"LaTeX source parsing failed: {exc}")
            elif source_path.exists() and source_path.suffix == '.pdf':
                # This is a PDF, not LaTeX source - fall back to PDF extraction
                warnings.append("arXiv source is PDF, not LaTeX archive. Using PDF extraction.")
                return self._extract_from_pdf(paper, source)

        # Try to download arXiv source (tar.gz)
        if paper.arxiv_id:
            try:
                source_path = self._download_arxiv_source(paper.arxiv_id, source)
                if source_path and source_path.exists():
                    sections, formula_blocks = self._parse_latex_source(source_path)
                    return sections, formula_blocks, "latex_source_parser", warnings
            except Exception as exc:
                warnings.append(f"Failed to download arXiv source: {exc}")

        # Fallback to PDF
        warnings.append("LaTeX source unavailable, falling back to PDF.")
        return self._extract_from_pdf(paper, source)

    def _extract_from_html(
        self, paper: CandidatePaper, source: ResolvedPaperSource | None
    ) -> tuple[dict[str, str], list[FormulaBlock], str, list[str]]:
        """Extract from structured HTML/XML."""
        warnings: list[str] = []
        formula_blocks: list[FormulaBlock] = []
        sections: dict[str, str] = {}

        if source and source.local_path:
            try:
                html_path = Path(source.local_path)
                if html_path.exists():
                    content = html_path.read_text(encoding="utf-8", errors="ignore")
                    sections = self._parse_html_sections(content)
                    return sections, formula_blocks, "structured_html_parser", warnings
            except Exception as exc:
                warnings.append(f"HTML parsing failed: {exc}")

        warnings.append("Structured HTML unavailable, falling back to PDF.")
        return self._extract_from_pdf(paper, source)

    def _extract_from_pdf(
        self, paper: CandidatePaper, source: ResolvedPaperSource | None
    ) -> tuple[dict[str, str], list[FormulaBlock], str, list[str]]:
        """Extract from PDF using parser quality selection.

        Runs MarkItDown and PyMuPDF in parallel, scores quality, selects best.
        Only triggers Marker if quality is low and paper is high priority.
        """
        from researchsensei.canonical.adapters import MarkItDownAdapter, MarkerPdfAdapter, MinerUPdfAdapter
        from researchsensei.canonical.parser_quality import select_best_parser, extract_formula_candidates

        warnings: list[str] = []
        formula_blocks: list[FormulaBlock] = []
        sections: dict[str, str] = {}

        pdf_path = None
        if source and source.local_path:
            pdf_path = Path(source.local_path)

        if not pdf_path or not pdf_path.exists():
            warnings.append("No PDF available for extraction.")
            return sections, formula_blocks, "none", warnings

        # Run MarkItDown and PyMuPDF in parallel
        md_text = ""
        pm_text = ""
        mk_text = None

        markitdown_adapter = MarkItDownAdapter()
        if markitdown_adapter.is_available():
            try:
                md_result = markitdown_adapter.process(pdf_path)
                if md_result.succeeded:
                    md_text = "\n".join(md_result.sections.values())
                else:
                    warnings.append(f"MarkItDown: {md_result.blocking_reason}")
            except Exception as exc:
                warnings.append(f"MarkItDown failed: {exc}")

        try:
            import fitz
            with fitz.open(str(pdf_path)) as doc:
                for page in doc:
                    pm_text += page.get_text()
        except Exception as exc:
            warnings.append(f"PyMuPDF failed: {exc}")

        # Run Marker based on trigger strategy
        from researchsensei.canonical.parser_quality import score_parser_output
        md_score = score_parser_output(md_text, "markitdown_pdf")
        pm_score = score_parser_output(pm_text, "pymupdf")

        # Marker configuration (default: disabled for speed)
        marker_enabled = self.marker_enabled
        marker_trigger_mode = self.marker_trigger_mode  # never / on_demand / a_read / review / heavy / always
        marker_timeout_seconds = self.marker_timeout_seconds

        should_trigger_marker = False
        trigger_reason = ""

        if marker_enabled and marker_trigger_mode != 'never':
            # Condition 1: Both parsers very low quality
            if marker_trigger_mode in {"always", "review", "heavy"}:
                should_trigger_marker = True
                trigger_reason = f"marker trigger_mode={marker_trigger_mode}"
            elif md_score.overall_score < 30 and pm_score.overall_score < 30:
                should_trigger_marker = True
                trigger_reason = "both light parsers have very low quality"

            # Condition 2: Formula candidates exist but no LaTeX formulas
            md_formula_count = md_score.formula_candidate_count
            pm_formula_count = pm_score.formula_candidate_count
            if (md_formula_count > 5 or pm_formula_count > 5) and md_score.overall_score < 60:
                should_trigger_marker = True
                trigger_reason = "formula candidates detected but light parser quality is low"
        elif not marker_enabled:
            warnings.append(
                "marker_status=skipped_by_policy "
                f"(marker_enabled=false, trigger_mode={marker_trigger_mode}, timeout_seconds={marker_timeout_seconds})"
            )

        if should_trigger_marker:
            marker_adapter = MarkerPdfAdapter()
            if marker_adapter.is_available():
                mk_text, marker_warning = self._run_marker_with_timeout(pdf_path, marker_timeout_seconds)
                warnings.append(f"Marker triggered: {trigger_reason}; timeout_seconds={marker_timeout_seconds}")
                if mk_text:
                    warnings.append("marker_status=completed")
                if marker_warning:
                    warnings.append(marker_warning)
            else:
                warnings.append("marker_status=blocked (marker-pdf not installed)")

        # Select best parser
        selection = select_best_parser(md_text, pm_text, mk_text)
        self._last_parser_used = selection.selected_parser
        self._parser_quality_scores = selection.candidates  # Store full score objects
        selected_score = next(c for c in selection.candidates if c.parser_name == selection.selected_parser)
        self._selected_parser_score = selected_score.overall_score
        self._parser_selection_reason = selection.selection_reason
        # Store detailed scores for front matter
        self._parser_quality_details = {
            c.parser_name: {
                "overall_score": round(c.overall_score, 1),
                "output_length": c.output_length,
                "section_count": c.section_count,
                "long_concat_count": c.long_concat_count,
                "spacing_quality": round(c.spacing_quality, 3),
                "cid_token_count": c.cid_token_count,
                "formula_candidate_count": c.formula_candidate_count,
                "garbled_line_ratio": round(c.garbled_line_ratio, 3),
            }
            for c in selection.candidates
        }

        # Parse sections from selected text
        sections = self._parse_text_sections(selection.selected_text, paper.title or "")

        # Extract formula candidates
        for fc in selection.formula_candidates:
            origin = FormulaOrigin(fc["origin"]) if fc["origin"] in [e.value for e in FormulaOrigin] else FormulaOrigin.UNKNOWN
            if origin == FormulaOrigin.RAW_FORMULA_TEXT:
                # Raw text goes to raw_formula_text field, not latex
                formula_blocks.append(FormulaBlock(
                    formula_id=f"fc_{len(formula_blocks)+1}",
                    latex="",
                    raw_formula_text=fc.get("raw_formula_text", ""),
                    is_latex=False,
                    confidence=fc.get("confidence", 0.3),
                    origin=origin,
                    section="",
                ))
            else:
                # LaTeX goes to latex field
                formula_blocks.append(FormulaBlock(
                    formula_id=f"fc_{len(formula_blocks)+1}",
                    latex=fc.get("latex", ""),
                    raw_formula_text="",
                    is_latex=fc.get("is_latex", True),
                    confidence=fc.get("confidence", 0.7),
                    origin=origin,
                    section="",
                ))

        # Also detect formulas in text using math-token density
        formula_pages = self._find_formula_dense_pages(selection.selected_text)
        for page_num in formula_pages:
            page_text = self._get_page_text(selection.selected_text, page_num)
            if page_text:
                page_formulas = self._detect_formulas_in_text(page_text, page_num)
                formula_blocks.extend(page_formulas)

        warnings.append(f"Selected parser: {selection.selected_parser} ({selection.selection_reason})")

        return sections, formula_blocks, selection.selected_parser, warnings

    def _run_marker_with_timeout(self, pdf_path: Path, timeout_seconds: float) -> tuple[str | None, str]:
        """Run Marker with a hard timeout and return markdown text plus warning."""
        ctx = multiprocessing.get_context("spawn")
        queue = ctx.Queue()
        process = ctx.Process(target=_run_marker_pdf_adapter_worker, args=(str(pdf_path), queue))
        process.start()
        process.join(timeout_seconds)

        if process.is_alive():
            process.terminate()
            process.join(5)
            return None, f"marker_status=timeout_degraded (timeout_seconds={timeout_seconds})"

        if queue.empty():
            return None, "marker_status=failed (no result returned)"

        payload = queue.get()
        if payload.get("succeeded") and payload.get("text"):
            return str(payload["text"]), ""

        reason = payload.get("blocking_reason", "unknown Marker failure")
        return None, f"marker_status=failed ({reason})"

    def _run_formula_pipeline(
        self,
        pdf_path: Path,
        text_formula_blocks: list[FormulaBlock],
        output_dir: Path | None,
    ) -> list[FormulaSlot]:
        """Run the formula pipeline: detect → crop → resolve.

        1. MarkerDocumentFormulaDetector finds Equation blocks with bbox
        2. FormulaCropper crops formula images
        3. Resolve final_latex and final_origin via priority merge
        """
        from researchsensei.canonical.formula_detector import MarkerDocumentFormulaDetector
        from researchsensei.canonical.formula_cropper import FormulaCropper

        slots: list[FormulaSlot] = []

        # Step 1: Detect formula positions via Marker build_document()
        detector = MarkerDocumentFormulaDetector()
        if detector.is_available():
            try:
                slots = detector.detect(pdf_path)
            except Exception as exc:
                logger.warning("MarkerDocumentFormulaDetector failed: %s", exc)

        # Step 2: Crop formula images
        if slots and self.formula_crop_enabled and output_dir:
            crop_dir = output_dir / "formula_crops"
            cropper = FormulaCropper()
            if cropper.is_available():
                try:
                    slots = cropper.crop(pdf_path, slots, crop_dir)
                except Exception as exc:
                    logger.warning("FormulaCropper failed: %s", exc)

        # Step 3: Resolve final_latex and final_origin via priority merge
        slots = _resolve_formula_slots(slots, text_formula_blocks)

        return slots

    def _render_markdown_with_slots(
        self, paper: CanonicalPaper, formula_slots: list[FormulaSlot]
    ) -> str:
        """Render canonical_paper.md with new formula slot format.

        Formula blocks use HTML comment metadata + LaTeX code block:
        <!-- formula_id: formula_001 | origin: parser_latex | ... -->
        ```latex
        \\mathcal{L} = ...
        ```

        Unresolved formulas use:
        {{FORMULA:formula_002 unresolved}}
        """
        lines: list[str] = []

        # YAML front matter
        fm = paper.front_matter
        lines.append("---")
        lines.append(f"paper_id: {fm.paper_id}")
        lines.append(f'title: "{fm.title}"')
        if fm.authors:
            lines.append("authors:")
            for author in fm.authors:
                lines.append(f'  - "{author}"')
        if fm.year:
            lines.append(f"year: {fm.year}")
        if fm.venue:
            lines.append(f'venue: "{fm.venue}"')
        lines.append(f"source_type: {fm.source_type}")
        lines.append(f"source_confidence: {fm.source_confidence}")
        lines.append(f"canonicalization_status: {fm.canonicalization_status.value}")
        lines.append(f"canonical_quality_status: {fm.canonical_quality_status.value}")
        lines.append(f"parser_used: {fm.parser_used}")
        lines.append(f"m2_ready: {'true' if fm.m2_ready else 'false'}")
        if fm.degradation_reason:
            lines.append(f'degradation_reason: "{fm.degradation_reason}"')
        # Parser quality selection fields
        if fm.parser_candidates:
            lines.append(f"parser_candidates: {fm.parser_candidates}")
        if fm.selected_parser:
            lines.append(f"selected_parser: {fm.selected_parser}")
        if fm.parser_quality_score > 0:
            lines.append(f"parser_quality_score: {fm.parser_quality_score:.1f}")
        if fm.parser_selection_reason:
            lines.append(f'parser_selection_reason: "{fm.parser_selection_reason}"')
        # Body parser selection
        if fm.body_selected_parser:
            lines.append(f"body_selected_parser: {fm.body_selected_parser}")
        if fm.body_parser_quality_score > 0:
            lines.append(f"body_parser_quality_score: {fm.body_parser_quality_score:.1f}")
        if fm.body_parser_selection_reason:
            lines.append(f'body_parser_selection_reason: "{fm.body_parser_selection_reason}"')
        # Formula pipeline metadata
        if fm.formula_detector:
            lines.append(f"formula_detector: {fm.formula_detector}")
        if fm.formula_slot_count > 0:
            lines.append(f"formula_slot_count: {fm.formula_slot_count}")
        if fm.formula_crop_count > 0:
            lines.append(f"formula_crop_count: {fm.formula_crop_count}")
        if fm.parser_latex_count > 0:
            lines.append(f"parser_latex_count: {fm.parser_latex_count}")
        if fm.ocr_latex_count > 0:
            lines.append(f"ocr_latex_count: {fm.ocr_latex_count}")
        if fm.raw_formula_text_count > 0:
            lines.append(f"raw_formula_text_count: {fm.raw_formula_text_count}")
        if fm.unresolved_formula_count > 0:
            lines.append(f"unresolved_formula_count: {fm.unresolved_formula_count}")
        if fm.canonical_quality_status_formula:
            lines.append(f"canonical_quality_status_formula: {fm.canonical_quality_status_formula}")
        # Detailed parser quality scores
        if fm.parser_quality_details_json:
            try:
                details = json.loads(fm.parser_quality_details_json)
                if details:
                    lines.append("parser_quality_details:")
                    for parser_name, scores in details.items():
                        lines.append(f"  {parser_name}:")
                        for key, value in scores.items():
                            lines.append(f"    {key}: {value}")
            except json.JSONDecodeError:
                pass
        lines.append("---")
        lines.append("")

        # Title
        lines.append(f"# {fm.title}")
        lines.append("")

        # Group formula slots by section for insertion
        from collections import defaultdict
        formulas_by_section: dict[str, list] = defaultdict(list)
        unmatched_formulas: list = []
        if formula_slots:
            for fs in formula_slots:
                sec = fs.section.strip() if fs.section else ""
                if sec in _STANDARD_SECTIONS:
                    formulas_by_section[sec].append(fs)
                elif sec and sec != "Unknown":
                    # Non-standard section — try to match
                    matched = False
                    for std in _STANDARD_SECTIONS:
                        if sec.lower() == std.lower():
                            formulas_by_section[std].append(fs)
                            matched = True
                            break
                    if not matched:
                        unmatched_formulas.append(fs)
                else:
                    # Unknown or empty section
                    unmatched_formulas.append(fs)

        def _render_formula_slot(fs):
            """Render a single formula slot as markdown lines."""
            result = []
            bbox_str = str(fs.bbox) if fs.bbox else "[]"
            origin_val = fs.final_origin.value if fs.final_origin else "unresolved"
            ocr_val = fs.ocr_status.value if hasattr(fs.ocr_status, 'value') else str(fs.ocr_status)
            unresolved_reason = f" | unresolved_reason: {fs.unresolved_reason}" if fs.unresolved_reason else ""
            sec_conf = getattr(fs, 'section_confidence', 'low')
            sec_source = getattr(fs, 'section_source', 'unknown')
            sec_reason = getattr(fs, 'section_reason', '')
            result.append(
                f"<!-- formula_id: {fs.formula_id} | origin: {origin_val} | "
                f"section: {fs.section} | page: {fs.page} | bbox: {bbox_str} | "
                f"ocr_status: {ocr_val} | section_confidence: {sec_conf} | "
                f"section_source: {sec_source} | section_reason: {sec_reason}{unresolved_reason} -->"
            )
            if fs.final_latex:
                result.append("```latex")
                result.append(fs.final_latex)
                result.append("```")
            elif fs.final_origin == FormulaOrigin.UNRESOLVED:
                result.append(f"{{{{FORMULA:{fs.formula_id} unresolved}}}}")
            else:
                result.append(f"<!-- No formula content for {fs.formula_id} -->")
            result.append("")
            return result

        # Sections in standard order — insert formulas into matching sections
        # Stop at References (unmatched formulas go before References)
        sections_to_render = [s for s in _STANDARD_SECTIONS if s != "References"]
        for section_name in sections_to_render:
            content = paper.sections.get(section_name, "").strip()
            lines.append(f"## {section_name}")
            lines.append("")
            if content:
                lines.append(content)
                lines.append("")
            else:
                lines.append(f"<!-- Section not available: {section_name} -->")
                lines.append("")
            # Append formulas that belong to this section
            if section_name in formulas_by_section:
                lines.append(f"### Formula Slots")
                lines.append("")
                for fs in formulas_by_section[section_name]:
                    lines.extend(_render_formula_slot(fs))

        # Unmatched formulas — group by page, insert BEFORE References
        if unmatched_formulas:
            by_page: dict[int, list] = defaultdict(list)
            for fs in unmatched_formulas:
                by_page[fs.page].append(fs)
            for page_num in sorted(by_page.keys()):
                lines.append(f"## Page {page_num} Formulas")
                lines.append("")
                for fs in by_page[page_num]:
                    lines.extend(_render_formula_slot(fs))

        # Any non-standard sections (after References position)
        for section_name, content in paper.sections.items():
            if section_name not in _STANDARD_SECTIONS and section_name != "Title" and content.strip():
                lines.append(f"## {section_name}")
                lines.append("")
                lines.append(content)
                lines.append("")
                if section_name in formulas_by_section:
                    lines.append(f"### Formula Slots")
                    lines.append("")
                    for fs in formulas_by_section[section_name]:
                        lines.extend(_render_formula_slot(fs))

        # References always comes last
        ref_content = paper.sections.get("References", "").strip()
        lines.append("## References")
        lines.append("")
        if ref_content:
            lines.append(ref_content)
            lines.append("")
        else:
            lines.append("<!-- Section not available: References -->")
            lines.append("")

        if paper.formula_blocks:
            # Fallback to legacy formula block format
            lines.append("## Formula Blocks")
            lines.append("")
            for fb in paper.formula_blocks:
                bbox_str = str(fb.bbox) if fb.bbox else "[]"
                lines.append(f"<!-- formula_id: {fb.formula_id} | origin: {fb.origin.value} | section: {fb.section} | page: {fb.page or 'N/A'} | bbox: {bbox_str} | ocr_status: {fb.ocr_status.value} | is_latex: {fb.is_latex} | confidence: {fb.confidence} -->")
                if fb.origin == FormulaOrigin.RAW_FORMULA_TEXT:
                    lines.append("```text")
                    lines.append(fb.raw_formula_text)
                    lines.append("```")
                elif fb.is_latex and fb.latex:
                    lines.append("```latex")
                    lines.append(fb.latex)
                    lines.append("```")
                else:
                    lines.append(f"<!-- No formula content -->")
                lines.append("")

        return "\n".join(lines)

    def _extract_from_text(
        self, paper: CandidatePaper, source: ResolvedPaperSource | None
    ) -> tuple[dict[str, str], list[FormulaBlock], str, list[str]]:
        """Extract from low-confidence text."""
        warnings: list[str] = ["Low-confidence text extraction."]
        formula_blocks: list[FormulaBlock] = []
        sections: dict[str, str] = {}

        if source and source.local_path:
            try:
                text_path = Path(source.local_path)
                if text_path.exists():
                    content = text_path.read_text(encoding="utf-8", errors="ignore")
                    sections = self._parse_text_sections(content, paper.title or "")
                    return sections, formula_blocks, "text_fallback", warnings
            except Exception as exc:
                warnings.append(f"Text extraction failed: {exc}")

        return sections, formula_blocks, "none", warnings

    def _download_arxiv_source(self, arxiv_id: str, source: ResolvedPaperSource | None) -> Path | None:
        """Download arXiv source (LaTeX) for a paper."""
        import httpx

        clean_id = arxiv_id.strip().removeprefix("arXiv:").removeprefix("arxiv:")
        source_url = f"https://arxiv.org/e-print/{clean_id}"

        try:
            client = httpx.Client(
                headers={"User-Agent": "ResearchSensei/0.5 (+https://github.com/ZehuaGou/Research-sensei)"},
                trust_env=True,
                timeout=60.0,
            )
            response = client.get(source_url, follow_redirects=True)
            response.raise_for_status()

            # Save to temp location
            import tempfile
            tmp_dir = Path(tempfile.mkdtemp(prefix="rs_latex_"))
            source_path = tmp_dir / f"{clean_id}.tar.gz"
            source_path.write_bytes(response.content)
            return source_path
        except Exception as exc:
            logger.warning("Failed to download arXiv source for %s: %s", arxiv_id, exc)
            raise

    def _parse_latex_source(self, source_path: Path) -> tuple[dict[str, str], list[FormulaBlock]]:
        """Parse LaTeX source file or archive."""
        sections: dict[str, str] = {}
        formula_blocks: list[FormulaBlock] = []

        if source_path.suffix == ".tex":
            content = source_path.read_text(encoding="utf-8", errors="ignore")
            sections, formula_blocks = self._parse_latex_content(content)
        elif source_path.suffix in (".tar", ".gz", ".tgz"):
            # Try to extract and find main .tex file
            import tarfile
            import tempfile

            try:
                tmp_dir = Path(tempfile.mkdtemp(prefix="rs_latex_extract_"))
                with tarfile.open(str(source_path)) as tar:
                    tar.extractall(tmp_dir, filter="data")

                # Find .tex files
                tex_files = list(tmp_dir.rglob("*.tex"))
                if tex_files:
                    # Use largest .tex file as main
                    main_tex = max(tex_files, key=lambda f: f.stat().st_size)
                    content = main_tex.read_text(encoding="utf-8", errors="ignore")
                    sections, formula_blocks = self._parse_latex_content(content)
            except Exception as exc:
                logger.warning("Failed to extract LaTeX archive: %s", exc)

        return sections, formula_blocks

    def _parse_latex_content(self, content: str) -> tuple[dict[str, str], list[FormulaBlock]]:
        """Parse LaTeX content into sections and formula blocks."""
        sections: dict[str, str] = {}
        formula_blocks: list[FormulaBlock] = []
        formula_counter = 0

        # Extract title
        title_match = re.search(r"\\title\{([^}]+)\}", content)
        if title_match:
            sections["Title"] = title_match.group(1).strip()

        # Extract abstract
        abstract_match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", content, re.DOTALL)
        if abstract_match:
            sections["Abstract"] = abstract_match.group(1).strip()

        # Extract sections
        section_pattern = re.compile(r"\\(?:sub)*section\{([^}]+)\}(.*?)(?=\\(?:sub)*section\{|\\end\{document\})", re.DOTALL)
        for match in section_pattern.finditer(content):
            section_name = match.group(1).strip()
            section_text = match.group(2).strip()
            # Map to standard sections
            mapped = self._map_section_name(section_name)
            sections[mapped] = section_text

        # Extract display formulas
        formula_patterns = [
            (r"\\begin\{equation\}(.*?)\\end\{equation\}", "equation"),
            (r"\\begin\{equation\*\}(.*?)\\end\{equation\*\}", "equation*"),
            (r"\\begin\{align\}(.*?)\\end\{align\}", "align"),
            (r"\\begin\{align\*\}(.*?)\\end\{align\*\}", "align*"),
            (r"\$\$(.*?)\$\$", "display_math"),
            (r"\\\[(.*?)\\\]", "display_math"),
        ]

        for pattern, env_name in formula_patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                formula_counter += 1
                latex = match.group(1).strip()
                if latex:
                    formula_blocks.append(FormulaBlock(
                        formula_id=f"eq{formula_counter}",
                        latex=latex,
                        origin=FormulaOrigin.SOURCE_LATEX,
                        is_latex=True,
                        confidence=0.95,
                        section=self._find_section_for_position(content, match.start()),
                    ))

        # Extract inline formulas (limited)
        inline_count = 0
        for match in re.finditer(r"\$([^$]+)\$", content):
            inline_count += 1
            if inline_count > 50:  # Limit inline formulas
                break
            latex = match.group(1).strip()
            if len(latex) > 3:  # Skip trivial inline math
                formula_blocks.append(FormulaBlock(
                    formula_id=f"inline{inline_count}",
                    latex=latex,
                    origin=FormulaOrigin.SOURCE_LATEX,
                    is_latex=True,
                    confidence=0.9,
                    section=self._find_section_for_position(content, match.start()),
                ))

        return sections, formula_blocks

    def _parse_html_sections(self, html_content: str) -> dict[str, str]:
        """Parse HTML content into sections."""
        sections: dict[str, str] = {}

        # Simple regex-based HTML section extraction
        # Look for h1-h3 headings
        heading_pattern = re.compile(r"<h[1-3][^>]*>(.*?)</h[1-3]>", re.DOTALL | re.IGNORECASE)
        headings = list(heading_pattern.finditer(html_content))

        for i, match in enumerate(headings):
            heading_text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            mapped = self._map_section_name(heading_text)

            # Get content until next heading
            start = match.end()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(html_content)
            section_html = html_content[start:end]
            section_text = re.sub(r"<[^>]+>", " ", section_html)
            section_text = re.sub(r"\s+", " ", section_text).strip()

            if section_text:
                sections[mapped] = section_text

        return sections

    def _detect_formulas_in_text(self, text: str, page: int) -> list[FormulaBlock]:
        """Detect formula-like content in text."""
        formula_blocks: list[FormulaBlock] = []
        formula_counter = 0

        # Look for LaTeX-like patterns
        patterns = [
            (r"\$([^$]+)\$", "inline"),
            (r"\$\$([^$]+)\$\$", "display"),
            (r"\\\[([^\]]+)\\\]", "display"),
            (r"\\begin\{equation\}(.*?)\\end\{equation\}", "equation"),
        ]

        for pattern, fmt in patterns:
            for match in re.finditer(pattern, text, re.DOTALL):
                formula_counter += 1
                latex = match.group(1).strip()
                if latex and len(latex) > 2:
                    formula_blocks.append(FormulaBlock(
                        formula_id=f"pdf_eq{formula_counter}",
                        latex=latex,
                        origin=FormulaOrigin.PARSER_LATEX,
                        is_latex=True,
                        confidence=0.6,
                        page=page,
                    ))

        return formula_blocks

    def _find_formula_dense_pages(self, text: str) -> list[int]:
        """Find pages with high math-token density using page markers in text.

        Math tokens include:
        - =, ∑, √, σ, λ, τ, π, ∈, ⊙, KL
        - Softmax, Attention, MultiHead
        - Gumbel, argmax
        - AssDis, AnomalyScore
        - Q, K, V
        - R^{N×d}, R^{M×n}
        """
        pages = text.split("--- Page ")
        page_scores = []

        math_patterns = [
            r'[=∑√σλτπ∈⊙]', r'KL\s*\(', r'Softmax', r'Attention', r'MultiHead',
            r'Gumbel', r'argmax', r'argmin', r'AssDis', r'AnomalyScore',
            r'R\^?\{?[NM×x]\s*[×x]\s*[dn]\}?', r'\b[QKV]\b',
            r'\\frac', r'\\sum', r'\\int', r'\\partial',
            r'\\alpha', r'\\beta', r'\\gamma', r'\\delta',
        ]

        for i, page_text in enumerate(pages[1:], 1):
            score = 0
            for pattern in math_patterns:
                score += len(re.findall(pattern, page_text, re.IGNORECASE))
            page_scores.append((i, score))

        # Sort by score and return top pages
        page_scores.sort(key=lambda x: x[1], reverse=True)
        # Return pages with score > 0, up to 5 pages
        return [p for p, s in page_scores if s > 0][:5]

    def find_formula_dense_pages_from_pdf(self, pdf_path: Path) -> list[dict]:
        """Find formula-dense pages directly from PDF using PyMuPDF.

        Returns list of dicts with:
        - page_num: 1-indexed page number
        - math_token_count: number of math tokens found
        - density: math tokens per 1000 chars
        - sample_lines: sample formula-like lines
        """
        results = []
        try:
            import fitz
            with fitz.open(str(pdf_path)) as doc:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    page_text = page.get_text()

                    math_patterns = [
                        r'[=∑√σλτπ∈⊙]', r'KL\s*\(', r'Softmax', r'Attention', r'MultiHead',
                        r'Gumbel', r'argmax', r'argmin', r'AssDis', r'AnomalyScore',
                        r'R\^?\{?[NM×x]\s*[×x]\s*[dn]\}?', r'\b[QKV]\b',
                        r'\\frac', r'\\sum', r'\\int', r'\\partial',
                        r'\\alpha', r'\\beta', r'\\gamma', r'\\delta',
                    ]

                    math_count = 0
                    for pattern in math_patterns:
                        math_count += len(re.findall(pattern, page_text, re.IGNORECASE))

                    text_len = max(len(page_text), 1)
                    density = (math_count / text_len) * 1000

                    # Find sample formula-like lines
                    sample_lines = []
                    for line in page_text.split('\n'):
                        line = line.strip()
                        if len(line) > 10 and any(re.search(p, line, re.IGNORECASE) for p in math_patterns):
                            sample_lines.append(line[:150])
                        if len(sample_lines) >= 3:
                            break

                    results.append({
                        "page": page_num + 1,
                        "page_num": page_num + 1,
                        "math_token_count": math_count,
                        "density": round(density, 2),
                        "sample_lines": sample_lines,
                    })
        except Exception as exc:
            logger.warning("Failed to scan PDF pages: %s", exc)

        # Sort by density and return
        results.sort(key=lambda x: x["density"], reverse=True)
        return results

    def _get_page_text(self, text: str, page_num: int) -> str:
        """Get text for a specific page."""
        pages = text.split("--- Page ")
        if 1 <= page_num < len(pages):
            return pages[page_num]
        return ""

    def _parse_text_sections(self, text: str, title: str) -> dict[str, str]:
        """Parse plain text into canonical sections using conservative headings."""
        sections: dict[str, str] = {}
        current_section = "Other"
        current_content: list[str] = []

        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue

            header = self._detect_section_header(stripped, current_section)
            if header:
                next_section, inline_content = header
                self._flush_section(sections, current_section, current_content)
                current_section = next_section
                current_content = []
                if inline_content:
                    current_content.append(inline_content)
                continue

            current_content.append(stripped)

        self._flush_section(sections, current_section, current_content)

        if not sections:
            sections["Other"] = text[:5000]

        return sections

    def _flush_section(self, sections: dict[str, str], section: str, content: list[str]) -> None:
        text = "\n".join(line for line in content if line.strip()).strip()
        if not text:
            return
        if section in sections and sections[section].strip():
            sections[section] = sections[section].rstrip() + "\n" + text
        else:
            sections[section] = text

    def _detect_section_header(self, line: str, current_section: str) -> tuple[str, str] | None:
        candidate = self._clean_heading_candidate(line)
        if not candidate or len(candidate) > 140:
            return None
        if self._looks_like_reference_line(candidate):
            return None
        if re.match(r"(?i)^(?:table|figure|fig\.|algorithm)\b", candidate):
            return None
        if current_section == "Experiments" and candidate.lower() in {"method", "methods", "model", "dataset", "datasets"}:
            return None

        heading_re = re.compile(
            r"^(?:(?:section\s+)?(?:[ivxlcdm]+|\d+|[a-z])[\.\)]?\s+)?"
            r"(?P<title>abstract|introduction|related\s+work|background|"
            r"methodology|methods?|approach|proposed\s+method|"
            r"experiments?|experimental\s+results|evaluation|results|"
            r"discussion|conclusion(?:\s+and\s+future\s+work)?|"
            r"references?|bibliography|appendix)"
            r"\b(?P<rest>.*)$",
            re.IGNORECASE,
        )
        match = heading_re.match(candidate)
        if not match:
            return None

        mapped = self._map_section_name(match.group("title"))
        if current_section == "References" and mapped != "Appendix":
            return None

        rest = match.group("rest").strip()
        rest = re.sub(r"^\s*[:.\-–—]\s*", "", rest)
        if rest and len(rest.split()) > 35:
            return None
        return mapped, rest

    def _clean_heading_candidate(self, line: str) -> str:
        candidate = line.strip()
        candidate = re.sub(r"^#{1,6}\s*", "", candidate)
        candidate = re.sub(r"<[^>]+>", " ", candidate)
        candidate = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", candidate)
        candidate = candidate.replace("&nbsp;", " ")
        if candidate.startswith("|") and candidate.endswith("|"):
            candidate = candidate.strip("|")
            candidate = " ".join(part.strip() for part in candidate.split("|") if part.strip())
        candidate = candidate.strip("*_` ")
        candidate = re.sub(r"\s+", " ", candidate)
        return candidate.strip()

    def _repair_and_assess_sections(
        self,
        sections: dict[str, str],
    ) -> tuple[dict[str, str], CanonicalQualityStatus, list[str]]:
        repaired = dict(sections)
        reasons: list[str] = []
        status = CanonicalQualityStatus.PASS

        for section in ("Introduction", "Method", "Experiments"):
            content = repaired.get(section, "")
            if not content.strip() or not self._section_is_reference_contaminated(content):
                continue
            kept, references = self._split_reference_contamination(content)
            if references:
                repaired["References"] = "\n".join(
                    part for part in [repaired.get("References", "").strip(), references.strip()] if part
                )
            if len(kept) >= 200 and not self._section_is_reference_contaminated(kept):
                repaired[section] = kept
                reasons.append(f"{section} repaired by moving trailing reference entries to References")
                if status != CanonicalQualityStatus.FAIL:
                    status = CanonicalQualityStatus.DEGRADED
            else:
                repaired[section] = ""
                reasons.append(f"{section} contaminated by reference entries")
                status = CanonicalQualityStatus.FAIL

        selected = getattr(self, "_last_parser_used", "")
        selected_score = next(
            (score for score in getattr(self, "_parser_quality_scores", []) if score.parser_name == selected),
            None,
        )
        if selected_score:
            if selected_score.long_concat_count > 80 or selected_score.spacing_quality < 0.5:
                reasons.append("Body text has large-scale concatenation")
                status = CanonicalQualityStatus.FAIL
            elif selected_score.long_concat_count > 20 or selected_score.spacing_quality < 0.75:
                reasons.append("Body text has noticeable concatenation")
                if status != CanonicalQualityStatus.FAIL:
                    status = CanonicalQualityStatus.DEGRADED

            if selected_score.garbled_line_ratio > 0.55:
                reasons.append("Body text has high garbled-line ratio")
                status = CanonicalQualityStatus.FAIL
            elif selected_score.garbled_line_ratio > 0.3 and status != CanonicalQualityStatus.FAIL:
                reasons.append("Body text has elevated garbled-line ratio")
                status = CanonicalQualityStatus.DEGRADED

        if not repaired.get("Introduction", "").strip():
            reasons.append("Introduction missing or unusable")
            if status != CanonicalQualityStatus.FAIL:
                status = CanonicalQualityStatus.DEGRADED

        return repaired, status, reasons

    def _section_is_reference_contaminated(self, content: str) -> bool:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if len(lines) < 4:
            return False
        refish = sum(1 for line in lines if self._looks_like_reference_line(line))
        first_ref_index = next((i for i, line in enumerate(lines) if re.match(r"^\[\d+\]", line)), None)
        early_ref_entries = sum(1 for line in lines[:20] if re.match(r"^\[\d+\]", line))
        return (
            refish / len(lines) >= 0.35
            or early_ref_entries >= 2
            or (first_ref_index is not None and first_ref_index <= 5 and refish / len(lines) >= 0.2)
        )

    def _split_reference_contamination(self, content: str) -> tuple[str, str]:
        lines = [line.rstrip() for line in content.splitlines()]
        first_ref_index = next((i for i, line in enumerate(lines) if re.match(r"^\s*\[\d+\]", line)), None)
        if first_ref_index is None:
            return "", content
        kept = "\n".join(lines[:first_ref_index]).strip()
        refs = "\n".join(lines[first_ref_index:]).strip()
        return kept, refs

    def _looks_like_reference_line(self, line: str) -> bool:
        stripped = line.strip()
        lower = stripped.lower()
        if re.match(r"^\[\d+\]\s+", stripped):
            return True
        if re.search(r"\b(?:corr|vol\.|pp\.|proceedings|conference|journal|trans\.|doi:|arxiv|iclr|neurips|sigkdd|vldb)\b", lower):
            return True
        if re.match(r"^[A-Z][A-Za-z'`\-]+,\s+[A-Z](?:\.|\s)", stripped):
            return True
        return False

    def _map_section_name(self, name: str) -> str:
        """Map a section name to a standard section."""
        name_lower = name.lower().strip()
        mapping = {
            "abstract": "Abstract",
            "摘要": "Abstract",
            "introduction": "Introduction",
            "引言": "Introduction",
            "related work": "Related Work",
            "相关工作": "Related Work",
            "background": "Related Work",
            "method": "Method",
            "方法": "Method",
            "approach": "Method",
            "methodology": "Method",
            "proposed method": "Method",
            "model": "Method",
            "architecture": "Method",
            "experiments": "Experiments",
            "实验": "Experiments",
            "evaluation": "Experiments",
            "results": "Experiments",
            "conclusion": "Conclusion",
            "结论": "Conclusion",
            "discussion": "Conclusion",
            "references": "References",
            "reference": "References",
            "参考文献": "References",
            "bibliography": "References",
            "appendix": "Appendix",
        }

        for key, value in mapping.items():
            if key in name_lower:
                return value

        return name.title() if len(name) < 50 else "Other"

    def _find_section_for_position(self, content: str, position: int) -> str:
        """Find which section a position in the content belongs to."""
        # Find the last section header before this position
        section_pattern = re.compile(r"\\(?:sub)*section\{([^}]+)\}")
        last_section = "Other"

        for match in section_pattern.finditer(content):
            if match.start() <= position:
                last_section = self._map_section_name(match.group(1))
            else:
                break

        return last_section

    def _render_markdown(self, paper: CanonicalPaper) -> str:
        """Render a CanonicalPaper to markdown with YAML front matter."""
        lines: list[str] = []

        # YAML front matter
        fm = paper.front_matter
        lines.append("---")
        lines.append(f"paper_id: {fm.paper_id}")
        lines.append(f'title: "{fm.title}"')
        if fm.authors:
            lines.append("authors:")
            for author in fm.authors:
                lines.append(f'  - "{author}"')
        if fm.year:
            lines.append(f"year: {fm.year}")
        if fm.venue:
            lines.append(f'venue: "{fm.venue}"')
        lines.append(f"source_type: {fm.source_type}")
        lines.append(f"source_confidence: {fm.source_confidence}")
        lines.append(f"canonicalization_status: {fm.canonicalization_status.value}")
        lines.append(f"canonical_quality_status: {fm.canonical_quality_status.value}")
        lines.append(f"parser_used: {fm.parser_used}")
        lines.append(f"m2_ready: {'true' if fm.m2_ready else 'false'}")
        if fm.degradation_reason:
            lines.append(f'degradation_reason: "{fm.degradation_reason}"')
        # Parser quality selection fields
        if fm.parser_candidates:
            lines.append(f"parser_candidates: {fm.parser_candidates}")
        if fm.selected_parser:
            lines.append(f"selected_parser: {fm.selected_parser}")
        if fm.parser_quality_score > 0:
            lines.append(f"parser_quality_score: {fm.parser_quality_score:.1f}")
        if fm.parser_selection_reason:
            lines.append(f'parser_selection_reason: "{fm.parser_selection_reason}"')
        # Detailed parser quality scores
        if fm.parser_quality_details_json:
            try:
                details = json.loads(fm.parser_quality_details_json)
                if details:
                    lines.append("parser_quality_details:")
                    for parser_name, scores in details.items():
                        lines.append(f"  {parser_name}:")
                        for key, value in scores.items():
                            lines.append(f"    {key}: {value}")
            except json.JSONDecodeError:
                pass
        lines.append("---")
        lines.append("")

        # Title
        lines.append(f"# {fm.title}")
        lines.append("")

        # Sections in standard order
        for section_name in _STANDARD_SECTIONS:
            content = paper.sections.get(section_name, "").strip()
            if content:
                lines.append(f"## {section_name}")
                lines.append("")
                lines.append(content)
                lines.append("")
            else:
                lines.append(f"## {section_name}")
                lines.append("")
                lines.append(f"<!-- Section not available: {section_name} -->")
                lines.append("")

        # Any non-standard sections
        for section_name, content in paper.sections.items():
            if section_name not in _STANDARD_SECTIONS and section_name != "Title" and content.strip():
                lines.append(f"## {section_name}")
                lines.append("")
                lines.append(content)
                lines.append("")

        # Formula blocks
        if paper.formula_blocks:
            lines.append("## Formula Blocks")
            lines.append("")
            for fb in paper.formula_blocks:
                bbox_str = str(fb.bbox) if fb.bbox else "[]"
                lines.append(f"<!-- formula_id: {fb.formula_id} | origin: {fb.origin.value} | section: {fb.section} | page: {fb.page or 'N/A'} | bbox: {bbox_str} | ocr_status: {fb.ocr_status.value} | is_latex: {fb.is_latex} | confidence: {fb.confidence} -->")
                if fb.origin == FormulaOrigin.RAW_FORMULA_TEXT:
                    # Raw text uses ```text block
                    lines.append("```text")
                    lines.append(fb.raw_formula_text)
                    lines.append("```")
                elif fb.is_latex and fb.latex:
                    # LaTeX uses ```latex block
                    lines.append("```latex")
                    lines.append(fb.latex)
                    lines.append("```")
                else:
                    # Unknown/empty - skip
                    lines.append(f"<!-- No formula content -->")
                lines.append("")

        return "\n".join(lines)

    def _build_adapter_info(self) -> list[AdapterInfo]:
        """Build adapter status report using real adapter probes."""
        from researchsensei.canonical.adapters import (
            MarkItDownAdapter, MarkerPdfAdapter, MinerUPdfAdapter, Pix2TexFormulaOCRAdapter, DeepXivProbe,
        )

        adapters = []

        # arXiv source
        adapters.append(AdapterInfo(
            name="arxiv_source",
            status=AdapterStatus.IMPLEMENTED,
            attempt_details=["Uses httpx with User-Agent, retry/backoff on 429/503"],
        ))

        # Semantic Scholar
        adapters.append(AdapterInfo(
            name="semantic_scholar",
            status=AdapterStatus.IMPLEMENTED,
            attempt_details=["Uses httpx REST API with proxy support"],
        ))

        # OpenAlex
        adapters.append(AdapterInfo(
            name="openalex",
            status=AdapterStatus.IMPLEMENTED,
            attempt_details=["Uses pyalex library"],
        ))

        # Crossref
        adapters.append(AdapterInfo(
            name="crossref",
            status=AdapterStatus.IMPLEMENTED,
            attempt_details=["Uses habanero library"],
        ))

        # MarkItDown - real probe
        markitdown_adapter = MarkItDownAdapter()
        if markitdown_adapter.is_available():
            md_used = getattr(self, '_last_parser_used', '') == 'markitdown_pdf'
            adapters.append(AdapterInfo(
                name="markitdown",
                status=AdapterStatus.IMPLEMENTED if md_used else AdapterStatus.DEPENDENCY_AVAILABLE_NOT_WIRED,
                blocking_reason="" if md_used else "markitdown installed but not yet invoked in this run",
                attempt_details=["markitdown installed (MIT)", f"invoked={md_used}"],
            ))
        else:
            adapters.append(AdapterInfo(
                name="markitdown",
                status=AdapterStatus.BLOCKED,
                blocking_reason="markitdown not installed (pip install 'markitdown[pdf]'). MIT license.",
            ))

        # LaTeX parser
        adapters.append(AdapterInfo(
            name="latex_parser",
            status=AdapterStatus.DEGRADED_IMPLEMENTED,
            attempt_details=["Basic regex-based LaTeX parsing; LaTeXML/pylatexenc not yet integrated"],
        ))

        # PyMuPDF
        try:
            import fitz
            adapters.append(AdapterInfo(
                name="pymupdf",
                status=AdapterStatus.IMPLEMENTED,
                attempt_details=["PyMuPDF available for PDF text extraction"],
            ))
        except ImportError:
            adapters.append(AdapterInfo(
                name="pymupdf",
                status=AdapterStatus.BLOCKED,
                blocking_reason="PyMuPDF (fitz) not installed",
            ))

        # Formula region detector
        adapters.append(AdapterInfo(
            name="formula_region_detector",
            status=AdapterStatus.DEGRADED_IMPLEMENTED,
            attempt_details=["Basic text-based formula detection; layout-based detection not yet implemented"],
        ))

        # Formula OCR (pix2tex) - real probe
        pix2tex = Pix2TexFormulaOCRAdapter()
        if pix2tex.is_available():
            ocr_invoked = getattr(self, '_last_ocr_invoked', False)
            ocr_succeeded = getattr(self, '_last_ocr_succeeded', False)
            adapters.append(AdapterInfo(
                name="formula_ocr",
                status=AdapterStatus.IMPLEMENTED if ocr_succeeded else (AdapterStatus.DEGRADED_IMPLEMENTED if ocr_invoked else AdapterStatus.DEPENDENCY_AVAILABLE_NOT_WIRED),
                blocking_reason="" if ocr_succeeded else ("OCR attempted but failed" if ocr_invoked else "pix2tex installed but not yet invoked"),
                attempt_details=["pix2tex installed", f"invoked={ocr_invoked}", f"succeeded={ocr_succeeded}"],
            ))
        else:
            adapters.append(AdapterInfo(
                name="formula_ocr",
                status=AdapterStatus.BLOCKED,
                blocking_reason="pix2tex not installed (pip install pix2tex)",
            ))

        # DeepXiv - real probe
        deepxiv = DeepXivProbe()
        deepxiv_result = deepxiv.probe()
        adapters.append(AdapterInfo(
            name="deepxiv",
            status=deepxiv_result.status,
            blocking_reason=deepxiv_result.blocking_reason,
            attempt_details=deepxiv_result.warnings,
        ))

        # Marker - real probe
        marker_adapter = MarkerPdfAdapter()
        if marker_adapter.is_available():
            # Check if Marker was actually used in this run
            marker_used = getattr(self, '_last_parser_used', '') == 'marker_pdf'
            adapters.append(AdapterInfo(
                name="marker",
                status=AdapterStatus.IMPLEMENTED if marker_used else AdapterStatus.DEPENDENCY_AVAILABLE_NOT_WIRED,
                blocking_reason="" if marker_used else "marker-pdf installed but not yet invoked in this run",
                attempt_details=["marker-pdf installed", f"invoked={marker_used}"],
            ))
        else:
            adapters.append(AdapterInfo(
                name="marker",
                status=AdapterStatus.BLOCKED,
                blocking_reason="marker-pdf not installed. GPL-3.0 license. pip install marker-pdf",
            ))

        # MinerU - real probe
        mineru_adapter = MinerUPdfAdapter()
        if mineru_adapter.is_available():
            mineru_used = getattr(self, '_last_parser_used', '') == 'mineru_pdf'
            adapters.append(AdapterInfo(
                name="mineru",
                status=AdapterStatus.IMPLEMENTED if mineru_used else AdapterStatus.DEPENDENCY_AVAILABLE_NOT_WIRED,
                blocking_reason="" if mineru_used else "magic-pdf installed but not yet invoked in this run",
                attempt_details=["magic-pdf installed", f"invoked={mineru_used}"],
            ))
        else:
            adapters.append(AdapterInfo(
                name="mineru",
                status=AdapterStatus.BLOCKED,
                blocking_reason="magic-pdf not installed. AGPL-3.0 license. pip install magic-pdf",
            ))

        return adapters

    def _metadata_only_result(self, paper: CandidatePaper, source: ResolvedPaperSource | None) -> CanonicalizationResult:
        """Return result for metadata-only papers (cannot enter M2)."""
        return CanonicalizationResult(
            paper_id=paper.paper_id,
            title=paper.title,
            source_type="metadata_only",
            source_priority=SourcePriority.METADATA_ONLY,
            preferred_m2_input="none",
            has_valid_deep_reading_source=False,
            canonicalization_status=CanonicalizationStatus.FAILED,
            canonical_quality_status=CanonicalQualityStatus.FAIL,
            m2_ready=False,
            degradation_reason="metadata_only: no full-text source available. Cannot enter M2.",
            adapter_info=self._build_adapter_info(),
            warnings=["METADATA_ONLY cannot enter M2 deep reading."],
        )


def _resolve_formula_slots(
    slots: list[FormulaSlot],
    text_formula_blocks: list[FormulaBlock] | list[dict],
) -> list[FormulaSlot]:
    """Resolve final_latex and final_origin for each FormulaSlot.

    Priority: source_latex > parser_latex (Marker/MinerU) > ocr_latex > raw_formula_text > unresolved

    Also cross-references with text-based FormulaBlock entries from body pipeline
    to fill in LaTeX when Marker block doesn't have it.
    text_formula_blocks can be FormulaBlock objects or dicts from select_best_parser.
    """
    # Normalize text_formula_blocks to FormulaBlock-like objects
    normalized: list[FormulaBlock] = []
    for fb in text_formula_blocks:
        if isinstance(fb, dict):
            normalized.append(FormulaBlock(
                formula_id=fb.get("formula_id", ""),
                latex=fb.get("latex", ""),
                raw_formula_text=fb.get("raw_formula_text", ""),
                is_latex=fb.get("is_latex", True),
                confidence=fb.get("confidence", 0.7),
                origin=FormulaOrigin(fb["origin"]) if fb.get("origin") in [e.value for e in FormulaOrigin] else FormulaOrigin.UNKNOWN,
                section=fb.get("section", ""),
                page=fb.get("page"),
                bbox=fb.get("bbox", []),
            ))
        else:
            normalized.append(fb)

    # Build a lookup from text-based formula blocks by page and approximate position
    text_by_page: dict[int, list[FormulaBlock]] = {}
    for fb in normalized:
        page = fb.page or 0
        text_by_page.setdefault(page, []).append(fb)

    for slot in slots:
        # Priority 1: source_latex (from LaTeX source — not expected from Marker)
        # Priority 2: parser_latex from Marker block
        if slot.marker_latex and slot.marker_latex.strip():
            slot.final_latex = slot.marker_latex.strip()
            slot.final_origin = FormulaOrigin.PARSER_LATEX
            continue

        # Priority 3: Cross-reference with text-based formula blocks
        page_formulas = text_by_page.get(slot.page, [])
        matched_fb = _find_matching_text_formula(slot, page_formulas)
        if matched_fb and matched_fb.latex and matched_fb.latex.strip():
            slot.final_latex = matched_fb.latex.strip()
            slot.final_origin = matched_fb.origin
            if matched_fb.origin == FormulaOrigin.PARSER_LATEX:
                slot.marker_latex = matched_fb.latex.strip()
            continue

        # Priority 4: raw_formula_text from marker_text
        if slot.marker_text and _looks_like_formula(slot.marker_text):
            slot.final_latex = slot.marker_text.strip()
            slot.final_origin = FormulaOrigin.RAW_FORMULA_TEXT
            continue

        # Priority 5: unresolved
        slot.final_origin = FormulaOrigin.UNRESOLVED
        slot.unresolved_reason = "no_latex_from_any_source"

    return slots


def _find_matching_text_formula(
    slot: FormulaSlot, page_formulas: list[FormulaBlock]
) -> FormulaBlock | None:
    """Find the text-based formula block that best matches a FormulaSlot.

    Uses bbox overlap heuristic: if the text formula has a bbox that overlaps
    with the slot's bbox, it's a match.
    """
    if not page_formulas or not slot.bbox:
        return None

    slot_area = _bbox_area(slot.bbox)
    best_match = None
    best_overlap = 0.0

    for fb in page_formulas:
        if not fb.bbox:
            # No bbox — can't match by position, but if only one formula on page, match it
            if len(page_formulas) == 1:
                return fb
            continue

        overlap = _bbox_overlap_ratio(slot.bbox, fb.bbox)
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = fb

    # Require at least 30% overlap for a confident match
    if best_overlap >= 0.3:
        return best_match

    # Fallback: if only one formula on page and slot has no match, use it
    if len(page_formulas) == 1 and best_overlap < 0.3:
        return page_formulas[0]

    return None


def _bbox_area(bbox: list[float]) -> float:
    """Calculate area of a bbox."""
    if len(bbox) != 4:
        return 0.0
    return max(0, bbox[2] - bbox[0]) * max(0, bbox[3] - bbox[1])


def _bbox_overlap_ratio(bbox_a: list[float], bbox_b: list[float]) -> float:
    """Calculate overlap ratio between two bboxes (intersection / min area)."""
    if len(bbox_a) != 4 or len(bbox_b) != 4:
        return 0.0

    x1 = max(bbox_a[0], bbox_b[0])
    y1 = max(bbox_a[1], bbox_b[1])
    x2 = min(bbox_a[2], bbox_b[2])
    y2 = min(bbox_a[3], bbox_b[3])

    if x1 >= x2 or y1 >= y2:
        return 0.0

    intersection = (x2 - x1) * (y2 - y1)
    area_a = _bbox_area(bbox_a)
    area_b = _bbox_area(bbox_b)
    min_area = min(area_a, area_b)

    if min_area <= 0:
        return 0.0

    return intersection / min_area


def _looks_like_formula(text: str) -> bool:
    """Check if text looks like a formula (contains math-like patterns)."""
    import re
    patterns = [
        r'\\(?:frac|sum|int|partial|alpha|beta|gamma|delta|mathcal|mathbb|mathrm|sqrt)',
        r'[=∑√σλτπ∈⊙]',
        r'\$[^$]+\$',
        r'R\^?\{',
        r'\\\[|\\\]',
    ]
    return any(re.search(p, text) for p in patterns)


def _formula_quality_status(slots: list[FormulaSlot]) -> str:
    """Determine formula quality status from resolved slots."""
    if not slots:
        return "no_formulas"

    total = len(slots)
    unresolved = sum(1 for s in slots if s.final_origin == FormulaOrigin.UNRESOLVED)
    resolved = total - unresolved

    if unresolved == 0:
        return "all_resolved"
    elif resolved > unresolved:
        return "mostly_resolved"
    elif resolved > 0:
        return "partially_resolved"
    else:
        return "all_unresolved"
