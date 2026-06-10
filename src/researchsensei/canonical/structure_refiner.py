"""Rule-based structure refinement for M1 v2."""
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


class RuleBasedStructureRefiner:
    """Assign sections from parser headings, reading order, and page timeline."""

    def refine(self, blocks: list[CanonicalDocumentBlock]) -> list[CanonicalDocumentBlock]:
        ordered = sorted(blocks, key=lambda b: (b.page, b.reading_order, b.bbox[1] if b.bbox else 0))
        self._assign_ordered(ordered)
        self._detect_risks(ordered)
        return blocks

    def _assign_ordered(self, blocks: list[CanonicalDocumentBlock]) -> None:
        current = "Unknown"
        for block in blocks:
            if block.block_type == "title":
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
