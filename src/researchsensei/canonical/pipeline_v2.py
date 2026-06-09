"""M1 v2 canonical pipeline orchestration."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from pydantic import Field

from researchsensei.canonical.canonical_builder_v2 import CanonicalBuilderV2
from researchsensei.canonical.document_blocks import CanonicalDocumentBlock
from researchsensei.canonical.mineru25_adapter import MinerU25ProAdapter
from researchsensei.canonical.ollama_refiner import OllamaSectionRefiner
from researchsensei.canonical.quality_gate import M1QualityGate, M1QualityGateResult
from researchsensei.canonical.structure_refiner import RuleBasedStructureRefiner
from researchsensei.canonical.visual_audit import M1VisualAuditReport, M1VisualAuditReportGenerator
from researchsensei.schemas.base import SenseiModel
from researchsensei.schemas.canonical import CanonicalizationResult


class M1V2PipelineResult(SenseiModel):
    canonicalization: CanonicalizationResult
    quality: M1QualityGateResult
    report: M1VisualAuditReport
    blocks: list[CanonicalDocumentBlock] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)


class M1V2CanonicalPipeline:
    """Run the MinerU-first M1 canonical path from parser blocks to reports."""

    def __init__(
        self,
        *,
        mineru_adapter: MinerU25ProAdapter | None = None,
        rule_refiner: RuleBasedStructureRefiner | None = None,
        ollama_refiner: OllamaSectionRefiner | None = None,
        quality_gate: M1QualityGate | None = None,
        builder: CanonicalBuilderV2 | None = None,
        report_generator: M1VisualAuditReportGenerator | None = None,
    ) -> None:
        self.mineru_adapter = mineru_adapter or MinerU25ProAdapter()
        self.rule_refiner = rule_refiner or RuleBasedStructureRefiner()
        self.ollama_refiner = ollama_refiner
        self.quality_gate = quality_gate or M1QualityGate()
        self.builder = builder or CanonicalBuilderV2()
        self.report_generator = report_generator or M1VisualAuditReportGenerator()

    def run_pdf(
        self,
        *,
        paper_id: str,
        title: str,
        pdf_path: str | Path,
        output_dir: str | Path,
        apply_ollama: bool = False,
        formula_slots: list[dict] | None = None,
    ) -> M1V2PipelineResult:
        start = time.perf_counter()
        blocks, raw_payload = self.mineru_adapter.parse_pdf(pdf_path, output_dir=output_dir)
        parse_seconds = time.perf_counter() - start
        raw_payload_metrics = self._raw_payload_metrics(raw_payload)
        return self.run_from_blocks(
            paper_id=paper_id,
            title=title,
            blocks=blocks,
            output_dir=output_dir,
            source_pdf_path=str(pdf_path),
            apply_ollama=apply_ollama,
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
        formula_slots: list[dict] | None = None,
        initial_metrics: dict | None = None,
    ) -> M1V2PipelineResult:
        start = time.perf_counter()
        working_blocks = [block.model_copy(deep=True) for block in blocks]

        if apply_rule_refiner:
            working_blocks = self.rule_refiner.refine(working_blocks)

        ollama_enabled = bool(apply_ollama and self.ollama_refiner is not None)
        if ollama_enabled:
            working_blocks = self.ollama_refiner.refine(working_blocks)

        slots = formula_slots if formula_slots is not None else self._slots_from_blocks(working_blocks)
        quality = self.quality_gate.evaluate(working_blocks, slots)
        elapsed = time.perf_counter() - start
        metrics = {
            "primary_parser": "mineru25pro",
            "ollama_enabled": ollama_enabled,
            "runtime_seconds": round(elapsed, 3),
            "mineru_available": True,
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

        canonicalization = self.builder.build(
            paper_id=paper_id,
            title=title,
            blocks=working_blocks,
            quality=quality,
            output_dir=output_dir,
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
        return M1V2PipelineResult(
            canonicalization=canonicalization,
            quality=quality,
            report=report,
            blocks=working_blocks,
            metrics=metrics,
        )

    def _slots_from_blocks(self, blocks: list[CanonicalDocumentBlock]) -> list[dict]:
        slots: list[dict] = []
        for index, block in enumerate((b for b in blocks if b.block_type == "formula"), start=1):
            slots.append({
                "formula_id": f"formula_{index:03d}",
                "block_id": block.block_id,
                "page": block.page,
                "bbox": block.bbox,
                "crop_required": True,
                "overlay_required": True,
                "crop_path": "",
                "overlay_path": "",
                "source_mismatch": False,
                "review_disabled": False,
            })
        return slots

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
