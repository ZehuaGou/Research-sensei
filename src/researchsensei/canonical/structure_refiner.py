"""Rule-based structure refinement for M1 canonical pipeline."""
from __future__ import annotations

import re

from researchsensei.canonical.document_blocks import CanonicalDocumentBlock


TRUSTED_SECTIONS = {
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
    "framework": "Method",
    "architecture": "Method",
    "algorithm": "Method",
    "experiments": "Experiments",
    "experiment": "Experiments",
    "experimental results": "Experiments",
    "evaluation": "Experiments",
    "results": "Experiments",
    "discussion": "Experiments",
    "conclusion": "Conclusion",
    "conclusions": "Conclusion",
    "summary": "Conclusion",
    "references": "References",
    "bibliography": "References",
    "appendix": "Appendix",
}


def _looks_like_formula(text: str) -> bool:
    return bool(
        re.search(
            r"(=|[_^{}]|\\(?:frac|sum|int|sqrt|alpha|beta|gamma)|\b(?:softmax|argmax|argmin)\s*\()",
            text,
            re.I,
        )
    )


def _heading_parts(text: str) -> tuple[str, str] | None:
    """Return numbered heading prefix and title body when present."""
    value = re.sub(r"<[^>]+>", " ", (text or "").strip())
    value = re.sub(r"\s+", " ", value).strip()
    if not value or _looks_like_formula(value):
        return None
    match = re.match(
        r"^\s*(?:section\s+)?(?P<number>\d+(?:\.\d+)*)[\.\)]?\s+(?P<title>.+?)\s*$",
        value,
        flags=re.I,
    )
    if not match:
        return None
    return match.group("number"), match.group("title")


def _infer_unknown_top_level_section(
    *,
    heading_number: str,
    heading_title: str,
    current_section: str,
) -> str | None:
    """Infer a standard section for top-level numbered headings with paper-specific names."""
    if "." in heading_number:
        return None
    try:
        numeric = int(heading_number)
    except ValueError:
        return None
    title = heading_title.strip().lower()
    if not title or title in TRUSTED_SECTIONS:
        return None

    # Many ML papers name the method section after the system/model acronym
    # (e.g. "3. CARLA") instead of "Method". If it follows intro/background
    # and precedes experiments/results, M2 should see it as Method.
    if numeric >= 3 and current_section in {"Introduction", "Related Work"}:
        return "Method"
    return None


def extract_section_from_heading(text: str) -> str | None:
    """Extract a trusted section name from a heading-like block."""
    value = re.sub(r"<[^>]+>", " ", (text or "").strip())
    value = re.sub(r"\s+", " ", value).strip()
    if not value or len(value) > 100 or _looks_like_formula(value):
        return None

    value = re.sub(r"^\s*(?:section\s+)?(?:[ivxlcdm]+|\d+(?:\.\d+)*|[a-z])[\.\)]?\s+", "", value, flags=re.I)
    lowered = value.lower().strip(" .:-")
    if lowered in TRUSTED_SECTIONS:
        return TRUSTED_SECTIONS[lowered]
    for key, section in TRUSTED_SECTIONS.items():
        if re.search(rf"\b{re.escape(key)}\b", lowered):
            return section
    return None


def _starts_abstract_block(text: str) -> bool:
    value = re.sub(r"\s+", " ", (text or "").strip())
    return bool(re.match(r"^abstract\s*(?:[—\-:.\u2013]\s*)?", value, flags=re.I))


def _is_index_terms_block(text: str) -> bool:
    value = re.sub(r"\s+", " ", (text or "").strip())
    return bool(re.match(r"^index\s+terms\s*(?:[—\-:.\u2013]\s*)?", value, flags=re.I))


class RuleBasedStructureRefiner:
    """Assign sections from parser headings, reading order, and page timeline."""

    def refine(self, blocks: list[CanonicalDocumentBlock]) -> list[CanonicalDocumentBlock]:
        self._mark_page_headers_footers(blocks)
        ordered = sorted(blocks, key=lambda b: (b.page, b.reading_order, b.bbox[1] if b.bbox else 0))
        self._assign_ordered(ordered)
        self._detect_risks(ordered)
        self._repair_misplaced_references(blocks)
        return blocks

    def _assign_ordered(self, blocks: list[CanonicalDocumentBlock]) -> None:
        current = "Unknown"
        numbered_top_level: dict[str, str] = {}
        for block in blocks:
            if block.page <= 2 and block.block_type in {"text", "title"} and (
                _starts_abstract_block(block.text) or _is_index_terms_block(block.text)
            ):
                current = "Abstract"
                block.section = "Abstract"
                block.section_confidence = "high"
                block.section_reason = f"abstract_front_matter_match: {block.text[:80]}"
                continue
            if block.block_type == "title":
                heading = _heading_parts(block.text)
                section = None
                if heading:
                    number, title = heading
                    parent_number = number.split(".", 1)[0]
                    # Subsections inherit their top-level numbered parent before
                    # keyword matching; this keeps "4.2 Benchmark Methods" under
                    # "4 Experiments" rather than moving it to Method.
                    if "." in number and parent_number in numbered_top_level:
                        section = numbered_top_level[parent_number]
                    else:
                        section = extract_section_from_heading(block.text)
                        if "." not in number and section is None:
                            section = _infer_unknown_top_level_section(
                                heading_number=number,
                                heading_title=title,
                                current_section=current,
                            )
                    if section and "." not in number:
                        numbered_top_level[parent_number] = section
                else:
                    section = extract_section_from_heading(block.text)
                if section:
                    current = section
                    block.section = section
                    block.section_confidence = "high"
                    block.section_reason = f"title_block_match: {block.text[:80]}"
                    continue
            if block.section:
                current = block.section
                continue
            block.section = current
            block.section_confidence = "medium" if current != "Unknown" else "low"
            block.section_reason = f"reading_order_context: page {block.page}"

    def _mark_page_headers_footers(self, blocks: list[CanonicalDocumentBlock]) -> None:
        """Mark blocks that are repeated page headers, footers, or page numbers."""
        title_counts: dict[str, int] = {}
        repeated_counts: dict[str, int] = {}
        for block in blocks:
            normalized = re.sub(r"\s+", " ", block.text.strip()).lower()
            if block.block_type == "title":
                title_counts[normalized] = title_counts.get(normalized, 0) + 1
            if block.block_type != "formula" and normalized:
                repeated_counts[normalized] = repeated_counts.get(normalized, 0) + 1

        for block in blocks:
            text = block.text.strip()
            normalized = re.sub(r"\s+", " ", text).lower()

            # Repeated page headers (e.g. "EdgeConvFormer" on every page).
            # MinerU may label the same header as title, text, caption, or
            # figure across different pages, so rely on text repetition plus
            # top-of-page position instead of block type alone.
            repeated_title_header = block.block_type == "title" and title_counts.get(normalized, 0) >= 3
            repeated_top_header = (
                block.block_type != "formula"
                and repeated_counts.get(normalized, 0) >= 3
                and len(text) <= 120
                and self._is_top_edge_block(block)
            )
            if repeated_title_header or repeated_top_header:
                if "PAGE_HEADER_REPEATED" not in block.risk_flags:
                    block.risk_flags.append("PAGE_HEADER_REPEATED")

                continue

            # Page number lines: "Page N of M"
            if re.fullmatch(r"page\s+\d+\s+of\s+\d+", normalized, re.I):
                if "PAGE_NUMBER_FOOTER" not in block.risk_flags:
                    block.risk_flags.append("PAGE_NUMBER_FOOTER")

                continue

            # Bare page-number emitted by parsers as ordinary text.  Some
            # arXiv/IEEE PDFs place page numbers at the top-right edge rather
            # than the footer, so treat page-edge numerals as layout noise.
            if normalized.isdigit() and int(normalized) == block.page:
                x1 = block.bbox[0] if len(block.bbox) >= 1 else 0.0
                x2 = block.bbox[2] if len(block.bbox) >= 3 else 0.0
                y1 = block.bbox[1] if len(block.bbox) >= 2 else 0.0
                y2 = block.bbox[3] if len(block.bbox) >= 4 else 0.0
                near_top_right = x1 >= 0.85 and y1 <= 0.08
                near_footer = y1 >= 0.85 or y2 >= 0.90
                near_outer_edge = (x1 <= 0.05 or x2 >= 0.95) and (y1 <= 0.08 or y2 >= 0.90)
                if near_top_right or near_footer or near_outer_edge:
                    if "PAGE_NUMBER_FOOTER" not in block.risk_flags:
                        block.risk_flags.append("PAGE_NUMBER_FOOTER")
                    continue

            # Author/footer preprint lines
            if "preprint submitted to" in normalized or re.fullmatch(r"[a-z].*\bet al\.\s*:\s*preprint.*", normalized, re.I):
                if "AUTHOR_FOOTER" not in block.risk_flags:
                    block.risk_flags.append("AUTHOR_FOOTER")

                continue

            # First-page front matter should not become research-problem text
            # for M2. Keep it in document_blocks as traceable material, but
            # mark it so canonical/M2 summaries can suppress it.
            if block.page <= 1 and (
                "partially sponsored" in normalized
                or "fellowship grant" in normalized
                or "discovery and future fellowship" in normalized
            ):
                if "FUNDING_NOTE" not in block.risk_flags:
                    block.risk_flags.append("FUNDING_NOTE")
                continue

            if block.page <= 1 and (
                "e-mail:" in normalized
                or "email:" in normalized
                or re.search(r"\b(is|are)\s+with\s+the\b", normalized)
                or re.search(r"\bwith\s+the\s+(school|department|datax|faculty|college|university)\b", normalized)
            ):
                if "FRONT_MATTER_AFFILIATION" not in block.risk_flags:
                    block.risk_flags.append("FRONT_MATTER_AFFILIATION")
                continue

            # arXiv left-side running metadata is useful for provenance, but
            # should never be emitted as Introduction/Method body text.
            if re.match(r"^arxiv:\d{4}\.\d{4,5}(?:v\d+)?\b", normalized):
                if self._is_side_margin_block(block):
                    if "ARXIV_SIDEBAR_HEADER" not in block.risk_flags:
                        block.risk_flags.append("ARXIV_SIDEBAR_HEADER")
                    continue

            # Very short orphan title blocks that repeat on multiple pages
            if block.block_type == "title" and len(text) < 5 and title_counts.get(normalized, 0) >= 3:
                if "PAGE_HEADER_REPEATED" not in block.risk_flags:
                    block.risk_flags.append("PAGE_HEADER_REPEATED")

    @staticmethod
    def _is_top_edge_block(block: CanonicalDocumentBlock) -> bool:
        if len(block.bbox) < 4:
            return False
        y1 = float(block.bbox[1])
        y2 = float(block.bbox[3])
        max_coord = max(abs(float(v)) for v in block.bbox)
        if max_coord <= 1.5:
            return y1 <= 0.08 and y2 <= 0.12
        return y1 <= 100 and y2 <= 140

    @staticmethod
    def _is_side_margin_block(block: CanonicalDocumentBlock) -> bool:
        if len(block.bbox) < 4:
            return False
        x1 = float(block.bbox[0])
        x2 = float(block.bbox[2])
        max_coord = max(abs(float(v)) for v in block.bbox)
        if max_coord <= 1.5:
            return x2 <= 0.15 or x1 <= 0.08
        return x2 <= 120 or x1 <= 80


    def _repair_misplaced_references(self, blocks: list[CanonicalDocumentBlock]) -> None:
        """If the Introduction section contains high ratio of reference-like entries, mark it as contaminated."""
        for section_name in ("Introduction", "Method", "Experiments"):
            section_blocks = [
                b for b in blocks
                if b.section == section_name and b.block_type in {"text", "reference", "title"}
            ]
            if len(section_blocks) < 3:
                continue
            ref_like = sum(
                1 for b in section_blocks
                if re.match(r"^\[?\d+\]?\s", b.text.strip())
                or "doi:" in b.text.lower()
                or re.search(r"\b(19|20)\d{2}[a-z]?\b.*\b(proceedings|journal|conference|trans)\b", b.text.lower())
            )
            if ref_like / len(section_blocks) >= 0.35:
                for b in section_blocks:
                    if "SECTION_CONTAMINATED_BY_REFERENCES" not in b.risk_flags:
                        b.risk_flags.append("SECTION_CONTAMINATED_BY_REFERENCES")

    def _detect_risks(self, blocks: list[CanonicalDocumentBlock]) -> None:
        formulas = [block for block in blocks if block.block_type == "formula"]
        if len(formulas) >= 5 and all(block.section == "Abstract" for block in formulas):
            for block in formulas:
                if "ALL_FORMULAS_IN_ABSTRACT_SUSPICIOUS" not in block.risk_flags:
                    block.risk_flags.append("ALL_FORMULAS_IN_ABSTRACT_SUSPICIOUS")

        page_title_sections: dict[int, set[str]] = {}
        for block in blocks:
            if block.block_type == "title":
                section = extract_section_from_heading(block.text)
                if section:
                    page_title_sections.setdefault(block.page, set()).add(section)
        for block in formulas:
            title_sections = page_title_sections.get(block.page, set())
            if block.section == "Abstract" and (block.page > 2 or any(sec != "Abstract" for sec in title_sections)):
                if "SECTION_CONTRADICTION_POSSIBLE" not in block.risk_flags:
                    block.risk_flags.append("SECTION_CONTRADICTION_POSSIBLE")
