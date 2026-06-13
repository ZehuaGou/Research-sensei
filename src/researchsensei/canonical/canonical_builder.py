"""CanonicalBuilder for M1 canonical pipeline."""
from __future__ import annotations
import re

import json
from pathlib import Path

from researchsensei.canonical.document_blocks import CanonicalDocumentBlock
from researchsensei.canonical.quality_gate import M1QualityGateResult
from researchsensei.schemas.canonical import CanonicalizationResult, FormulaBlock
from researchsensei.schemas.enums import CanonicalQualityStatus, CanonicalizationStatus, FormulaOcrStatus, FormulaOrigin, SourcePriority


SECTION_ORDER = [
    "Abstract",
    "Introduction",
    "Related Work",
    "Method",
    "Experiments",
    "Conclusion",
    "References",
    "Appendix",
    "Unknown",
]

SUPPRESSED_CANONICAL_RISK_FLAGS = {
    "PAGE_HEADER_REPEATED",
    "PAGE_NUMBER_FOOTER",
    "AUTHOR_FOOTER",
    "FUNDING_NOTE",
    "FRONT_MATTER_AFFILIATION",
}


class CanonicalBuilder:
    """Build M2-readable canonical artifacts from document blocks."""

    def build(
        self,
        *,
        paper_id: str,
        title: str,
        blocks: list[CanonicalDocumentBlock],
        quality: M1QualityGateResult,
        output_dir: str | Path,
        formula_slots: list[dict] | None = None,
        parser_name: str = "mineru25pro",
        source_pdf_path: str = "",
        metrics: dict | None = None,
    ) -> CanonicalizationResult:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        formula_blocks = self._formula_blocks(blocks)
        output_formula_slots = self._formula_slots(blocks, formula_slots)

        markdown = self._render_markdown(
            paper_id=paper_id,
            title=title,
            blocks=blocks,
            quality=quality,
            formula_blocks=formula_blocks,
            parser_name=parser_name,
            source_pdf_path=self._display_source_path(source_pdf_path, output_dir),
            metrics=metrics or {},
        )
        canonical_path = output_dir / "canonical_paper.md"
        canonical_path.write_text(markdown, encoding="utf-8")
        (output_dir / "document_blocks.json").write_text(
            json.dumps([block.model_dump(mode="json") for block in blocks], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (output_dir / "formula_slots.json").write_text(
            json.dumps(output_formula_slots, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (output_dir / "formula_slots.md").write_text(self._render_formula_slots(output_formula_slots), encoding="utf-8")

        status = self._canonical_status(quality.status)
        m2_ready = self._m2_ready(quality)
        return CanonicalizationResult(
            paper_id=paper_id,
            title=title,
            source_type="pdf",
            source_priority=SourcePriority.PDF,
            preferred_m2_input="pdf",
            has_valid_deep_reading_source=m2_ready,
            canonical_paper_path=str(canonical_path),
            canonicalization_status=status,
            canonical_quality_status=quality.status,
            m2_ready=m2_ready,
            m2_ready_for_formula_understanding=quality.m2_ready_for_formula_understanding,
            degradation_reason="; ".join(quality.blocking_reasons + quality.warning_reasons),
            formula_blocks=formula_blocks,
            warnings=quality.warning_reasons,
        )

    def _formula_blocks(self, blocks: list[CanonicalDocumentBlock]) -> list[FormulaBlock]:
        formulas: list[FormulaBlock] = []
        for index, block in enumerate((b for b in blocks if b.block_type == "formula"), start=1):
            origin = self._origin_for_block(block)
            formulas.append(
                FormulaBlock(
                    formula_id=f"formula_{index:03d}",
                    latex=block.latex if block.latex else "",
                    raw_formula_text="" if block.latex else block.text,
                    is_latex=bool(block.latex),
                    confidence=block.confidence,
                    origin=origin,
                    section=block.section,
                    page=block.page,
                    bbox=block.bbox,
                    ocr_status=FormulaOcrStatus.NOT_REQUIRED,
                    detector_confidence=block.confidence,
                    warnings=list(block.risk_flags),
                )
            )
        return formulas

    @staticmethod
    def _extract_equation_number(text: str) -> str:
        for pattern in (
            r"\\tag\{?\s*(\d+(?:\.\d+)*)\s*\}?",
            r"\((\d+(?:\.\d+)*)\)\s*$",
            r"^\((\d+(?:\.\d+)*)\)\s",
        ):
            m = re.search(pattern, text or "")
            if m:
                return m.group(1)
        return ""

    def _origin_for_block(self, block: CanonicalDocumentBlock) -> FormulaOrigin:
        if block.latex and block.source == "mineru25pro":
            return FormulaOrigin.MINERU_LATEX
        if block.latex and block.source == "marker_document":
            return FormulaOrigin.MARKER_LATEX
        if block.latex:
            return FormulaOrigin.PARSER_LATEX
        if block.text:
            return FormulaOrigin.RAW_FORMULA_TEXT
        return FormulaOrigin.UNRESOLVED

    def _formula_slots(self, blocks: list[CanonicalDocumentBlock], reviewed_slots: list[dict] | None = None) -> list[dict]:
        slots: list[dict] = []
        reviewed_by_block = {str(slot.get("block_id", "")): slot for slot in reviewed_slots or [] if slot.get("block_id")}
        reviewed_by_formula = {str(slot.get("formula_id", "")): slot for slot in reviewed_slots or [] if slot.get("formula_id")}
        for index, block in enumerate((b for b in blocks if b.block_type == "formula"), start=1):
            origin = self._origin_for_block(block)
            formula_id = f"formula_{index:03d}"
            reviewed = reviewed_by_block.get(block.block_id) or reviewed_by_formula.get(formula_id) or {}
            mineru_latex = reviewed.get("mineru_latex", block.latex if block.source == "mineru25pro" else "")
            marker_latex = reviewed.get("marker_latex", block.latex if block.source == "marker_document" else "")
            final_latex = reviewed.get("final_latex", block.latex)
            risk_flags = list(block.risk_flags)
            for risk in reviewed.get("risk_flags", []):
                if risk not in risk_flags:
                    risk_flags.append(risk)
            slots.append({
                "formula_id": formula_id,
                "block_id": block.block_id,
                "page": block.page,
                "bbox": block.bbox,
                "crop_required": reviewed.get("crop_required", True),
                "overlay_required": reviewed.get("overlay_required", True),
                "crop_path": reviewed.get("crop_path", ""),
                "overlay_path": reviewed.get("overlay_path", ""),
                "section": block.section,
                "section_confidence": block.section_confidence,
                "section_reason": block.section_reason,
                "block_source": block.source,
                "mineru_latex": mineru_latex,
                "marker_latex": marker_latex,
                "final_latex": final_latex,
                "final_origin": origin.value,
                "risk_flags": risk_flags,
            })
            # M2 contract fields: use reviewed values if present, else compute defaults
            eq_number = reviewed.get("equation_number", self._extract_equation_number(block.text or block.latex))
            group_id = reviewed.get("equation_group_id", "")
            group_order = reviewed.get("group_order", 0)
            group_crop = reviewed.get("group_crop_path", "")
            nearby_before = reviewed.get("nearby_text_before", "")
            nearby_after = reviewed.get("nearby_text_after", "")
            slots[-1]["equation_number"] = eq_number
            slots[-1]["equation_group_id"] = group_id
            slots[-1]["group_order"] = group_order
            slots[-1]["group_crop_path"] = group_crop
            slots[-1]["nearby_text_before"] = nearby_before
            slots[-1]["nearby_text_after"] = nearby_after
            for optional_key in (
                "mineru_latex_raw",
                "marker_latex_raw",
                "final_latex_raw",
                "latex_corrected_by",
                "latex_correction_confidence",
                "latex_correction_issues",
                "latex_tag_restored",
                "group_overlay_path",
                "nearby_block_ids",
            ):
                if optional_key in reviewed:
                    slots[-1][optional_key] = reviewed[optional_key]
        return slots

    def _render_markdown(
        self,
        *,
        paper_id: str,
        title: str,
        blocks: list[CanonicalDocumentBlock],
        quality: M1QualityGateResult,
        formula_blocks: list[FormulaBlock],
        parser_name: str,
        source_pdf_path: str,
        metrics: dict,
    ) -> str:
        lines = [
            "---",
            f"paper_id: {paper_id}",
            f'title: "{title}"',
            "source_type: pdf",
            "source_confidence: high",
            f"canonicalization_status: {self._canonical_status(quality.status).value}",
            f"canonical_quality_status: {quality.status.value}",
            f"primary_parser: {parser_name}",
            "fallback_used: false",
            f"m2_ready: {'true' if self._m2_ready(quality) else 'false'}",
            f"m2_ready_for_formula_understanding: {'true' if quality.m2_ready_for_formula_understanding else 'false'}",
            f"formula_slot_count: {len(formula_blocks)}",
            f"mineru_latex_count: {sum(1 for fb in formula_blocks if fb.origin == FormulaOrigin.MINERU_LATEX)}",
            f"raw_formula_text_count: {sum(1 for fb in formula_blocks if fb.origin == FormulaOrigin.RAW_FORMULA_TEXT)}",
            f"raw_only_formula_dense: {'true' if quality.raw_only_formula_dense else 'false'}",
            f"section_contradiction_count: {quality.section_contradiction_count}",
            f"all_formulas_in_Abstract_suspicious: {'true' if quality.all_formulas_in_abstract_suspicious else 'false'}",
        ]
        if quality.formula_understanding_reasons:
            lines.append(f'formula_understanding_reason: "{", ".join(quality.formula_understanding_reasons)}"')
        if source_pdf_path:
            lines.append(f'source_pdf_path: "{source_pdf_path}"')
        for key, value in sorted(metrics.items()):
            if isinstance(value, (str, int, float, bool)):
                lines.append(f"{key}: {json.dumps(value)}")
        lines += ["---", "", f"# {title}", ""]

        by_section: dict[str, list[CanonicalDocumentBlock]] = {}
        for block in blocks:
            by_section.setdefault(block.section or "Unknown", []).append(block)

        formula_by_block = {
            block.block_id: formula
            for block, formula in zip([b for b in blocks if b.block_type == "formula"], formula_blocks)
        }
        rendered_sections: set[str] = set()
        for section in SECTION_ORDER:
            section_blocks = by_section.get(section, [])
            if not section_blocks:
                continue
            # Skip Unknown section if it appears after References (front-matter leakage)
            if section == "Unknown" and rendered_sections.intersection({"References", "Appendix"}):
                continue
            lines += [f"## {section}", ""]
            rendered_sections.add(section)
            for block in sorted(section_blocks, key=lambda b: (b.page, b.reading_order, b.bbox[1] if b.bbox else 0)):
                # Skip layout/front-matter blocks marked by RuleBasedStructureRefiner.
                if any(flag in SUPPRESSED_CANONICAL_RISK_FLAGS for flag in block.risk_flags):
                    continue
                if block.block_type == "title" and block.text.strip().lower().endswith(section.lower()):
                    continue
                if block.block_type == "formula":
                    formula = formula_by_block.get(block.block_id)
                    if formula is None:
                        continue
                    lines.append(
                        "<!-- "
                        f"formula_id: {formula.formula_id} | origin: {formula.origin.value} | "
                        f"section: {formula.section} | page: {formula.page} | bbox: {formula.bbox} | "
                        f"source: {block.source} | block_id: {block.block_id}"
                        " -->"
                    )
                    if formula.is_latex:
                        lines += ["```latex", formula.latex, "```", ""]
                    else:
                        lines += ["```text", formula.raw_formula_text, "```", ""]
                elif block.block_type == "table":
                    lines += [block.html or block.text or "[TABLE]", ""]
                elif block.block_type in {"text", "caption", "reference", "title"} and block.text:
                    prefix = "### " if block.block_type == "title" else ""
                    lines += [prefix + block.text, ""]

        rendered: list[str] = []
        for line in lines:
            parts = str(line).splitlines()
            if parts:
                rendered.extend(part.rstrip() for part in parts)
            else:
                rendered.append("")
        return "\n".join(rendered)

    def _canonical_status(self, quality: CanonicalQualityStatus) -> CanonicalizationStatus:
        if quality == CanonicalQualityStatus.FAIL:
            return CanonicalizationStatus.FAILED
        if quality == CanonicalQualityStatus.DEGRADED:
            return CanonicalizationStatus.DEGRADED
        return CanonicalizationStatus.SUCCESS

    def _display_source_path(self, source_pdf_path: str, output_dir: Path) -> str:
        if not source_pdf_path:
            return ""
        path = Path(source_pdf_path)
        try:
            return path.resolve().relative_to(output_dir.resolve()).as_posix()
        except (OSError, ValueError):
            return path.as_posix()

    def _m2_ready(self, quality: M1QualityGateResult) -> bool:
        return (
            quality.status != CanonicalQualityStatus.FAIL
            and quality.m2_ready_for_formula_understanding
        )

    def _render_formula_slots(self, slots: list[dict]) -> str:
        lines = [
            "# Formula Slots",
            "",
            "| id | page | section | origin | bbox | risk_flags |",
            "| -- | ---: | ------- | ------ | ---- | ---------- |",
        ]
        for slot in slots:
            risks = ", ".join(slot.get("risk_flags", [])) or "none"
            lines.append(
                f"| {slot['formula_id']} | {slot['page']} | {slot['section']} | "
                f"{slot['final_origin']} | {slot['bbox']} | {risks} |"
            )
        return "\n".join(lines)
