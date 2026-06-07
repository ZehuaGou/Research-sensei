"""M1.4 Material Normalizer — converts raw sources to canonical_paper.md.

M1 must produce a normalized canonical_paper.md for M2 consumption.
Source priority: latex_source > structured_html > marker_pdf > mineru_pdf > pymupdf > low_confidence_text > metadata_only.
metadata_only cannot enter M2.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from researchsensei.schemas.canonical import (
    AdapterInfo,
    CanonicalPaper,
    CanonicalPaperFrontMatter,
    CanonicalizationResult,
    FormulaBlock,
)
from researchsensei.schemas.common import WarningItem
from researchsensei.schemas.direction import CandidatePaper, ResolvedPaperSource
from researchsensei.schemas.enums import (
    AdapterStatus,
    CanonicalizationStatus,
    FormulaOrigin,
    FormulaOcrStatus,
    PaperSourceStatus,
    SourcePriority,
)

logger = logging.getLogger(__name__)

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
    ) -> None:
        self.formula_region_detector = formula_region_detector
        self.formula_ocr_adapter = formula_ocr_adapter

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
                m2_ready=False,
                degradation_reason="No content extracted from source.",
                warnings=parse_warnings,
            )

        # Determine degradation
        missing_sections = [s for s in _STANDARD_SECTIONS if not sections.get(s, "").strip()]
        degraded = len(missing_sections) > 3
        status = CanonicalizationStatus.DEGRADED if degraded else CanonicalizationStatus.SUCCESS
        m2_ready = has_content and source_priority != SourcePriority.METADATA_ONLY
        degradation_reason = f"Missing sections: {', '.join(missing_sections)}" if missing_sections else ""

        front_matter = CanonicalPaperFrontMatter(
            paper_id=paper.paper_id,
            title=paper.title or "Untitled",
            authors=paper.authors,
            year=paper.year,
            venue=paper.venue,
            source_type=source_priority.value,
            source_confidence=paper.source_confidence,
            canonicalization_status=status,
            parser_used=parser_used,
            m2_ready=m2_ready,
            degradation_reason=degradation_reason,
            # Parser quality selection fields
            parser_candidates=getattr(self, '_parser_quality_scores', []),
            selected_parser=parser_used,
            parser_quality_score=getattr(self, '_selected_parser_score', 0.0),
            parser_selection_reason=getattr(self, '_parser_selection_reason', ''),
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

        # Generate markdown AFTER all formula updates
        raw_md = self._render_markdown(canonical)
        canonical.raw_markdown = raw_md

        # Write to file AFTER formula detection and OCR
        canonical_path = ""
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            md_path = output_dir / "canonical_paper.md"
            md_path.write_text(raw_md, encoding="utf-8")
            canonical_path = str(md_path)

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

        # Run Marker only if quality is low (heavy parser, ~16min)
        # Check quality first
        from researchsensei.canonical.parser_quality import score_parser_output
        md_score = score_parser_output(md_text, "markitdown_pdf")
        pm_score = score_parser_output(pm_text, "pymupdf")

        # If both parsers have poor quality, try Marker
        if md_score.overall_score < 40 and pm_score.overall_score < 40:
            marker_adapter = MarkerPdfAdapter()
            if marker_adapter.is_available():
                try:
                    mk_result = marker_adapter.process(pdf_path)
                    if mk_result.succeeded:
                        mk_text = "\n".join(mk_result.sections.values())
                        warnings.append("Marker triggered due to low quality from MarkItDown/PyMuPDF")
                    else:
                        warnings.append(f"Marker: {mk_result.blocking_reason}")
                except Exception as exc:
                    warnings.append(f"Marker failed: {exc}")

        # Select best parser
        selection = select_best_parser(md_text, pm_text, mk_text)
        self._last_parser_used = selection.selected_parser
        self._parser_quality_scores = [c.parser_name for c in selection.candidates]
        self._selected_parser_score = next(c.overall_score for c in selection.candidates if c.parser_name == selection.selected_parser)
        self._parser_selection_reason = selection.selection_reason

        # Parse sections from selected text
        sections = self._parse_text_sections(selection.selected_text, paper.title or "")

        # Extract formula candidates
        for fc in selection.formula_candidates:
            origin = FormulaOrigin(fc["origin"]) if fc["origin"] in [e.value for e in FormulaOrigin] else FormulaOrigin.UNKNOWN
            formula_blocks.append(FormulaBlock(
                formula_id=f"fc_{len(formula_blocks)+1}",
                latex=fc["latex"],
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

    def _parse_text_sections(self, text: str, title: str) -> dict[str, str]:
        """Parse plain text into sections using heuristics.

        Supports multiple section header formats:
        - I. INTRODUCTION
        - II. RELATED WORK
        - 1 Introduction
        - 5 CONCLUSION AND FUTURE WORK
        - Table-style headers (| 5 CONCLUSION |)
        """
        sections: dict[str, str] = {}

        # Try to find section headers - support numbered and Roman numeral formats
        section_patterns = [
            r"(?i)^(?:[IVX]+\.?\s+)?(?:abstract|摘要)",
            r"(?i)^(?:[IVX]+\.?\s+)?(?:introduction|引言)",
            r"(?i)^(?:[IVX]+\.?\s+)?(?:related\s+work|相关工作)",
            r"(?i)^(?:[IVX]+\.?\s+)?(?:method(?:ology)?|方法|approach)",
            r"(?i)^(?:[IVX]+\.?\s+)?(?:experiment(?:s)?|实验|evaluation|results)",
            r"(?i)^(?:[IVX]+\.?\s+)?(?:conclusion|结论|discussion|future\s+work)",
            r"(?i)^(?:[IVX]+\.?\s+)?(?:reference|参考文献|bibliography)",
            r"(?i)^(?:[IVX]+\.?\s+)?(?:appendix|附录)",
            # Also match with numbers
            r"(?i)^(?:\d+\.?\s+)(?:abstract|introduction|related\s+work|method|experiment|conclusion|reference|appendix)",
        ]

        lines = text.split("\n")
        current_section = "Other"
        current_content: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check if this line is a section header
            is_header = False
            for pattern in section_patterns:
                if re.match(pattern, stripped, re.IGNORECASE):
                    # Save previous section
                    if current_content:
                        sections[current_section] = "\n".join(current_content)

                    # Start new section
                    current_section = self._map_section_name(stripped)
                    current_content = []
                    is_header = True
                    break

            if not is_header:
                current_content.append(stripped)

        # Save last section
        if current_content:
            sections[current_section] = "\n".join(current_content)

        # If no sections found, put everything in "Other"
        if not sections:
            sections["Other"] = text[:5000]  # Limit to 5000 chars

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
                        page=page,
                    ))

        return formula_blocks

    def _find_formula_dense_pages(self, text: str) -> list[int]:
        """Find pages with high math-token density.

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

    def _get_page_text(self, text: str, page_num: int) -> str:
        """Get text for a specific page."""
        pages = text.split("--- Page ")
        if 1 <= page_num < len(pages):
            return pages[page_num]
        return ""

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
            "参考文献": "References",
            "bibliography": "References",
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
        lines.append(f"parser_used: {fm.parser_used}")
        lines.append(f"m2_ready: {'true' if fm.m2_ready else 'false'}")
        if fm.degradation_reason:
            lines.append(f'degradation_reason: "{fm.degradation_reason}"')
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
                lines.append(f"<!-- formula_id: {fb.formula_id} | origin: {fb.origin.value} | section: {fb.section} | page: {fb.page or 'N/A'} | bbox: {bbox_str} | ocr_status: {fb.ocr_status.value} -->")
                lines.append("```latex")
                lines.append(fb.latex)
                lines.append("```")
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
            m2_ready=False,
            degradation_reason="metadata_only: no full-text source available. Cannot enter M2.",
            adapter_info=self._build_adapter_info(),
            warnings=["METADATA_ONLY cannot enter M2 deep reading."],
        )
