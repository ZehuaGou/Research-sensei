"""M1 canonical pipeline orchestration."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from pydantic import Field

from researchsensei.canonical.canonical_builder import CanonicalBuilder
from researchsensei.canonical.document_blocks import CanonicalDocumentBlock
from researchsensei.canonical.latex_postprocessor import postprocess_latex
from researchsensei.canonical.mineru25_adapter import MinerU25ProAdapter
from researchsensei.canonical.ollama_latex_validator import OllamaLatexValidator
from researchsensei.canonical.ollama_refiner import OllamaSectionRefiner
from researchsensei.canonical.quality_gate import M1QualityGate, M1QualityGateResult
from researchsensei.canonical.structure_refiner import RuleBasedStructureRefiner
from researchsensei.canonical.visual_audit import M1VisualAuditReportGenerator, M1VisualAuditReport
from researchsensei.schemas.base import SenseiModel
from researchsensei.schemas.canonical import CanonicalizationResult


class M1PipelineResult(SenseiModel):
    canonicalization: CanonicalizationResult
    quality: M1QualityGateResult
    report: M1VisualAuditReport
    blocks: list[CanonicalDocumentBlock] = Field(default_factory=list)
    formula_slots: list[dict] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)


class M1CanonicalPipeline:
    """Run the MinerU-first M1 canonical path from parser blocks to reports."""

    def __init__(
        self,
        *,
        mineru_adapter: MinerU25ProAdapter | None = None,
        rule_refiner: RuleBasedStructureRefiner | None = None,
        ollama_refiner: OllamaSectionRefiner | None = None,
        latex_validator: OllamaLatexValidator | None = None,
        quality_gate: M1QualityGate | None = None,
        builder: CanonicalBuilder | None = None,
        report_generator: M1VisualAuditReportGenerator | None = None,
    ) -> None:
        self.mineru_adapter = mineru_adapter or MinerU25ProAdapter()
        self.rule_refiner = rule_refiner or RuleBasedStructureRefiner()
        self.ollama_refiner = ollama_refiner
        self.latex_validator = latex_validator
        self.quality_gate = quality_gate or M1QualityGate()
        self.builder = builder or CanonicalBuilder()
        self.report_generator = report_generator or M1VisualAuditReportGenerator()

    def run_pdf(
        self,
        *,
        paper_id: str,
        title: str,
        pdf_path: str | Path,
        output_dir: str | Path,
        apply_ollama: bool = False,
        apply_ollama_latex: bool = False,
        formula_slots: list[dict] | None = None,
    ) -> M1PipelineResult:
        start = time.perf_counter()
        blocks, raw_payload = self.mineru_adapter.parse_pdf(pdf_path, output_dir=output_dir)
        parse_seconds = time.perf_counter() - start
        self._write_raw_payload(output_dir, raw_payload)
        raw_payload_metrics = self._raw_payload_metrics(raw_payload)
        return self.run_from_blocks(
            paper_id=paper_id,
            title=title,
            blocks=blocks,
            output_dir=output_dir,
            source_pdf_path=str(pdf_path),
            apply_ollama=apply_ollama,
            apply_ollama_latex=apply_ollama_latex,
            formula_slots=formula_slots,
            initial_metrics={
                "primary_parser": "mineru25pro",
                "parser_runtime_seconds": round(parse_seconds, 3),
                "mineru_available": True,
                **raw_payload_metrics,
            },
        )

    def run_from_blocks(
        self,
        *,
        paper_id: str,
        title: str,
        blocks: list[CanonicalDocumentBlock],
        output_dir: str | Path,
        source_pdf_path: str = "",
        apply_rule_refiner: bool = True,
        apply_ollama: bool = False,
        apply_ollama_latex: bool = False,
        formula_slots: list[dict] | None = None,
        initial_metrics: dict | None = None,
    ) -> M1PipelineResult:
        start = time.perf_counter()
        working_blocks = [block.model_copy(deep=True) for block in blocks]

        if apply_rule_refiner:
            working_blocks = self.rule_refiner.refine(working_blocks)

        ollama_enabled = bool(apply_ollama and self.ollama_refiner is not None)
        if ollama_enabled:
            working_blocks = self.ollama_refiner.refine(working_blocks)

        output_dir_path = Path(output_dir)
        slots = formula_slots if formula_slots is not None else self._slots_from_blocks(working_blocks)
        if formula_slots is None and source_pdf_path:
            slots = self._generate_formula_review_artifacts(
                pdf_path=source_pdf_path,
                output_dir=output_dir_path,
                slots=slots,
            )

        slots = self._ensure_slot_latex_from_blocks(working_blocks, slots)

        # Apply regex-based LaTeX post-processing to all formula slots
        slots = self._postprocess_latex_slots(slots)

        # Optionally validate/correct LaTeX with Ollama
        latex_validated = False
        latex_requested = bool(apply_ollama or apply_ollama_latex)
        latex_available = False
        if latex_requested and self.latex_validator is not None and self.latex_validator.is_available():
            latex_available = True
            slots = self.latex_validator.validate_formulas(slots, output_dir_path)
            slots = self._postprocess_latex_slots(slots)
            latex_validated = True

        self._sync_formula_latex_from_slots(working_blocks, slots)

        quality = self.quality_gate.evaluate(working_blocks, slots)
        elapsed = time.perf_counter() - start
        metrics = {
            "primary_parser": "mineru25pro",
            "ollama_enabled": ollama_enabled,
            "ollama_latex_requested": latex_requested,
            "ollama_latex_enabled": latex_available,
            "latex_postprocessed": True,
            "latex_postprocessed_after_validation": latex_available,
            "latex_validated": latex_validated,
            "runtime_seconds": round(elapsed, 3),
            "mineru_available": True,
            "formula_slot_count": len(slots),
            "formula_crop_count": sum(1 for slot in slots if slot.get("crop_path")),
            "formula_overlay_count": sum(1 for slot in slots if slot.get("overlay_path")),
            "latex_corrected_count": sum(1 for slot in slots if slot.get("latex_corrected_by")),
        }
        metrics.update(initial_metrics or {})
        if self.ollama_refiner is not None:
            metrics.update({
                "ollama_json_valid": self.ollama_refiner.metrics.json_valid_count,
                "ollama_json_invalid": self.ollama_refiner.metrics.json_invalid_count,
                "ollama_retry_count": self.ollama_refiner.metrics.retry_count,
                "ollama_timeout_count": self.ollama_refiner.metrics.timeout_count,
                "ollama_changed_by_count": self.ollama_refiner.metrics.changed_by_count,
            })
        else:
            metrics.update({
                "ollama_json_valid": 0,
                "ollama_json_invalid": 0,
                "ollama_retry_count": 0,
                "ollama_timeout_count": 0,
                "ollama_changed_by_count": 0,
            })

        if self.latex_validator is not None:
            metrics.update({
                "latex_validator_checked": self.latex_validator.metrics.formulas_checked,
                "latex_validator_corrected": self.latex_validator.metrics.formulas_corrected,
                "latex_validator_low_confidence": self.latex_validator.metrics.low_confidence_count,
                "latex_validator_overexpanded": self.latex_validator.metrics.overexpanded_count,
                "latex_validator_anchor_mismatch": self.latex_validator.metrics.anchor_mismatch_count,
                "latex_validator_tag_restored": self.latex_validator.metrics.tag_restored_count,
                "latex_validator_json_valid": self.latex_validator.metrics.json_valid_count,
                "latex_validator_json_invalid": self.latex_validator.metrics.json_invalid_count,
                "latex_validator_timeout": self.latex_validator.metrics.timeout_count,
            })

        canonicalization = self.builder.build(
            paper_id=paper_id,
            title=title,
            blocks=working_blocks,
            quality=quality,
            output_dir=output_dir,
            formula_slots=slots,
            parser_name=metrics["primary_parser"],
            source_pdf_path=source_pdf_path,
            metrics=metrics,
        )
        report = self.report_generator.write(
            output_dir=output_dir,
            paper_id=paper_id,
            title=title,
            blocks=working_blocks,
            quality=quality,
            metrics=metrics,
        )
        return M1PipelineResult(
            canonicalization=canonicalization,
            quality=quality,
            report=report,
            blocks=working_blocks,
            formula_slots=slots,
            metrics=metrics,
        )

    def _slots_from_blocks(self, blocks: list[CanonicalDocumentBlock]) -> list[dict]:
        """Generate formula slots with M2 contract fields.

        Computes equation_number, equation_group_id, group_order, and
        nearby_text from block context so M2 can load formula_slots.json
        without a separate reviewed_slots pass.
        """
        formulas = [block for block in blocks if block.block_type == "formula"]
        text_blocks = [
            block for block in blocks
            if block.block_type in {"text", "caption"} and block.text.strip()
        ]
        grouped = self._assign_equation_groups(formulas)
        slots: list[dict] = []
        for index, block in enumerate(formulas, start=1):
            formula_id = f"formula_{index:03d}"
            eq_number = self._extract_equation_number(block.text or block.latex)
            group_id, group_order = grouped.get(block.block_id, ("", 0))
            nearby_before, nearby_after = self._nearby_text(block, text_blocks)
            slots.append({
                "formula_id": formula_id,
                "block_id": block.block_id,
                "page": block.page,
                "bbox": block.bbox,
                "crop_required": True,
                "overlay_required": True,
                "crop_path": "",
                "overlay_path": "",
                "source_mismatch": False,
                "review_disabled": False,
                "section": block.section,
                "section_confidence": block.section_confidence,
                "section_reason": block.section_reason,
                "block_source": block.source,
                "final_origin": "raw_formula_text" if not block.latex else "parser_latex",
                "risk_flags": list(block.risk_flags),
                "equation_number": eq_number,
                "equation_group_id": group_id,
                "group_order": group_order,
                "group_crop_path": "",
                "nearby_text_before": nearby_before,
                "nearby_text_after": nearby_after,
            })
        return slots

    @staticmethod
    def _extract_equation_number(text: str) -> str:
        import re
        for pattern in (
            r"\\tag\{?\s*(\d+(?:\.\d+)*)\s*\}?",
            r"\((\d+(?:\.\d+)*)\)\s*$",
            r"^\((\d+(?:\.\d+)*)\)\s",
        ):
            m = re.search(pattern, text or "")
            if m:
                return m.group(1)
        return ""

    @staticmethod
    def _assign_equation_groups(
        formulas: list[CanonicalDocumentBlock],
    ) -> dict[str, tuple[str, int]]:
        """Cluster formulas on the same page with matching tags or adjacent positions."""
        result: dict[str, tuple[str, int]] = {}
        pages: dict[int, list[CanonicalDocumentBlock]] = {}
        for block in formulas:
            pages.setdefault(block.page, []).append(block)
        group_counter = 0
        for page_blocks in pages.values():
            page_blocks.sort(key=lambda b: (b.bbox[1] if len(b.bbox) >= 2 else 0,))
            current_group: list[CanonicalDocumentBlock] = []
            for block in page_blocks:
                if current_group:
                    prev = current_group[-1]
                    prev_y2 = prev.bbox[3] if len(prev.bbox) >= 4 else 0
                    cur_y1 = block.bbox[1] if len(block.bbox) >= 2 else 0
                    vertical_gap = abs(cur_y1 - prev_y2)
                    same_section = block.section == prev.section
                    if same_section and vertical_gap < 0.15:
                        current_group.append(block)
                        continue
                if current_group:
                    group_counter += 1
                    gid = f"eq_group_{group_counter:03d}"
                    for order, member in enumerate(current_group, start=1):
                        result[member.block_id] = (gid, order)
                    current_group = []
                current_group.append(block)
            if current_group:
                group_counter += 1
                gid = f"eq_group_{group_counter:03d}"
                for order, member in enumerate(current_group, start=1):
                    result[member.block_id] = (gid, order)
        return result

    @staticmethod
    def _nearby_text(
        formula: CanonicalDocumentBlock,
        text_blocks: list[CanonicalDocumentBlock],
    ) -> tuple[str, str]:
        """Find the nearest text blocks before/after this formula by reading order."""
        same_page = [
            b for b in text_blocks
            if b.page == formula.page
            and b.block_type in {"text", "caption"}
            and b.text.strip()
        ]
        if not same_page:
            same_page = [b for b in text_blocks if abs(b.page - formula.page) <= 1 and b.text.strip()]
        same_page.sort(key=lambda b: (b.page, b.reading_order, b.bbox[1] if len(b.bbox) >= 2 else 0))
        formula_idx = (
            formula.reading_order,
            formula.bbox[1] if len(formula.bbox) >= 2 else 0,
        )
        before_texts: list[str] = []
        after_texts: list[str] = []
        for b in same_page:
            b_idx = (b.reading_order, b.bbox[1] if len(b.bbox) >= 2 else 0)
            if b.page < formula.page or (b.page == formula.page and b_idx < formula_idx):
                before_texts.append(b.text.strip())
            elif b.page > formula.page or (b.page == formula.page and b_idx > formula_idx):
                after_texts.append(b.text.strip())
        nearby_before = (before_texts[-1] if before_texts else "")[:200]
        nearby_after = (after_texts[0] if after_texts else "")[:200]
        return nearby_before, nearby_after

    def _postprocess_latex_slots(self, slots: list[dict]) -> list[dict]:
        """Apply regex-based LaTeX cleanup to all formula slots."""
        for slot in slots:
            for key in ("mineru_latex", "marker_latex", "final_latex"):
                original = slot.get(key, "")
                if original and isinstance(original, str) and original.strip():
                    cleaned = postprocess_latex(original)
                    if cleaned != original:
                        slot[f"{key}_raw"] = original
                        slot[key] = cleaned
        return slots

    def _ensure_slot_latex_from_blocks(
        self,
        blocks: list[CanonicalDocumentBlock],
        slots: list[dict],
    ) -> list[dict]:
        formulas = [block for block in blocks if block.block_type == "formula"]
        slots_by_block_id = {str(slot.get("block_id", "")): slot for slot in slots if slot.get("block_id")}
        slots_by_formula_id = {str(slot.get("formula_id", "")): slot for slot in slots if slot.get("formula_id")}
        for index, block in enumerate(formulas, start=1):
            formula_id = f"formula_{index:03d}"
            slot = slots_by_block_id.get(block.block_id) or slots_by_formula_id.get(formula_id)
            if not slot:
                continue
            if block.source == "mineru25pro" and not slot.get("mineru_latex"):
                slot["mineru_latex"] = block.latex
            if block.source == "marker_document" and not slot.get("marker_latex"):
                slot["marker_latex"] = block.latex
            if not slot.get("final_latex"):
                slot["final_latex"] = block.latex
        return slots

    def _sync_formula_latex_from_slots(
        self,
        blocks: list[CanonicalDocumentBlock],
        slots: list[dict],
    ) -> None:
        formulas = [block for block in blocks if block.block_type == "formula"]
        slots_by_block_id = {str(slot.get("block_id", "")): slot for slot in slots if slot.get("block_id")}
        slots_by_formula_id = {str(slot.get("formula_id", "")): slot for slot in slots if slot.get("formula_id")}
        for index, block in enumerate(formulas, start=1):
            formula_id = f"formula_{index:03d}"
            slot = slots_by_block_id.get(block.block_id) or slots_by_formula_id.get(formula_id)
            if not slot:
                continue
            final_latex = str(slot.get("final_latex") or slot.get("mineru_latex") or "").strip()
            if final_latex:
                block.latex = final_latex
            for risk in slot.get("risk_flags", []):
                if risk not in block.risk_flags:
                    block.risk_flags.append(str(risk))

    def _generate_formula_review_artifacts(
        self,
        *,
        pdf_path: str | Path,
        output_dir: Path,
        slots: list[dict],
    ) -> list[dict]:
        pdf_path = Path(pdf_path)
        if not slots or not pdf_path.exists():
            return slots

        try:
            import fitz
            from PIL import Image, ImageDraw
        except ImportError:
            return slots

        crop_dir = output_dir / "formula_crops"
        overlay_dir = output_dir / "formula_overlays"
        group_crop_dir = output_dir / "formula_group_crops"
        group_overlay_dir = output_dir / "formula_group_overlays"
        crop_dir.mkdir(parents=True, exist_ok=True)
        overlay_dir.mkdir(parents=True, exist_ok=True)
        group_crop_dir.mkdir(parents=True, exist_ok=True)
        group_overlay_dir.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(str(pdf_path))
        try:
            for slot in slots:
                rect = self._slot_rect(doc, slot)
                if rect is None:
                    continue
                formula_id = str(slot.get("formula_id") or slot.get("block_id") or "formula")
                page_index = int(slot.get("page") or 1) - 1
                page = doc[page_index]
                padded = self._pad_rect(rect, page.rect, padding=4.0)

                crop_path = crop_dir / f"{formula_id}_p{page_index + 1}.png"
                page.get_pixmap(clip=padded, dpi=200, alpha=False).save(str(crop_path))
                slot["crop_path"] = str(crop_path.relative_to(output_dir)).replace("\\", "/")

                overlay_path = overlay_dir / f"{formula_id}_page_{page_index + 1}.png"
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                draw = ImageDraw.Draw(image)
                scale_x = pix.width / page.rect.width
                scale_y = pix.height / page.rect.height
                draw.rectangle(
                    [
                        padded.x0 * scale_x,
                        padded.y0 * scale_y,
                        padded.x1 * scale_x,
                        padded.y1 * scale_y,
                    ],
                    outline="red",
                    width=3,
                )
                image.save(overlay_path)
                slot["overlay_path"] = str(overlay_path.relative_to(output_dir)).replace("\\", "/")

            self._generate_formula_group_review_artifacts(
                doc=doc,
                output_dir=output_dir,
                group_crop_dir=group_crop_dir,
                group_overlay_dir=group_overlay_dir,
                slots=slots,
            )
        finally:
            doc.close()
        return slots

    def _generate_formula_group_review_artifacts(
        self,
        *,
        doc: Any,
        output_dir: Path,
        group_crop_dir: Path,
        group_overlay_dir: Path,
        slots: list[dict],
    ) -> None:
        """Create one review crop/overlay per equation group for M2."""
        import fitz
        from PIL import Image, ImageDraw

        grouped: dict[str, list[dict]] = {}
        for slot in slots:
            group_id = str(slot.get("equation_group_id") or "").strip()
            if not group_id:
                continue
            grouped.setdefault(group_id, []).append(slot)

        for group_id, group_slots in grouped.items():
            page_indices = {int(slot.get("page") or 1) - 1 for slot in group_slots}
            if len(page_indices) != 1:
                continue
            page_index = next(iter(page_indices))
            if page_index < 0 or page_index >= len(doc):
                continue
            page = doc[page_index]

            rects = [self._slot_rect(doc, slot) for slot in group_slots]
            rects = [rect for rect in rects if rect is not None]
            if not rects:
                continue

            union = fitz.Rect(rects[0])
            for rect in rects[1:]:
                union.include_rect(rect)
            padded = self._pad_rect(union, page.rect, padding=8.0)

            safe_group_id = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in group_id)
            group_crop_path = group_crop_dir / f"{safe_group_id}_p{page_index + 1}.png"
            page.get_pixmap(clip=padded, dpi=200, alpha=False).save(str(group_crop_path))

            group_overlay_path = group_overlay_dir / f"{safe_group_id}_page_{page_index + 1}.png"
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            draw = ImageDraw.Draw(image)
            scale_x = pix.width / page.rect.width
            scale_y = pix.height / page.rect.height
            draw.rectangle(
                [
                    padded.x0 * scale_x,
                    padded.y0 * scale_y,
                    padded.x1 * scale_x,
                    padded.y1 * scale_y,
                ],
                outline="blue",
                width=4,
            )
            image.save(group_overlay_path)

            rel_group_crop = str(group_crop_path.relative_to(output_dir)).replace("\\", "/")
            rel_group_overlay = str(group_overlay_path.relative_to(output_dir)).replace("\\", "/")
            for slot in group_slots:
                slot["group_crop_path"] = rel_group_crop
                slot["group_overlay_path"] = rel_group_overlay

    def _slot_rect(self, doc: Any, slot: dict) -> Any | None:
        import fitz

        bbox = slot.get("bbox") or []
        if len(bbox) != 4:
            return None
        page_index = int(slot.get("page") or 1) - 1
        if page_index < 0 or page_index >= len(doc):
            return None
        page_rect = doc[page_index].rect
        x1, y1, x2, y2 = [float(value) for value in bbox]
        if all(0.0 <= value <= 1.0 for value in (x1, y1, x2, y2)):
            x1, x2 = x1 * page_rect.width, x2 * page_rect.width
            y1, y2 = y1 * page_rect.height, y2 * page_rect.height
        if x2 <= x1 or y2 <= y1:
            return None
        rect = fitz.Rect(x1, y1, x2, y2)
        return rect & page_rect

    def _pad_rect(self, rect: Any, page_rect: Any, *, padding: float) -> Any:
        import fitz

        return fitz.Rect(
            max(page_rect.x0, rect.x0 - padding),
            max(page_rect.y0, rect.y0 - padding),
            min(page_rect.x1, rect.x1 + padding),
            min(page_rect.y1, rect.y1 + padding),
        )

    def _write_raw_payload(self, output_dir: str | Path, raw_payload: dict[str, Any]) -> None:
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        (output_dir_path / "raw_mineru_output.json").write_text(
            json.dumps(self._json_safe(raw_payload), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _raw_payload_metrics(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(raw_payload, dict):
            return {"mineru_raw_payload_present": False}

        pages = raw_payload.get("pages")
        stats = raw_payload.get("stats") if isinstance(raw_payload.get("stats"), dict) else {}
        metrics: dict[str, Any] = {
            "mineru_raw_payload_present": True,
            "mineru_raw_payload_stats": stats,
        }
        if isinstance(pages, list):
            metrics["mineru_raw_payload_pages"] = len(pages)
            metrics["mineru_raw_payload_total_blocks"] = sum(
                len(page.get("blocks", [])) for page in pages if isinstance(page, dict)
            )
        for key, value in stats.items():
            if isinstance(value, (str, int, float, bool)):
                metrics[f"mineru_raw_payload_{key}"] = value
        return metrics

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._json_safe(item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if hasattr(value, "model_dump"):
            return self._json_safe(value.model_dump(mode="json"))
        return str(value)
