"""Visual/public audit report generation for M1 canonical pipeline."""
from __future__ import annotations

import html
import json
from pathlib import Path

from pydantic import Field

from researchsensei.canonical.document_blocks import CanonicalDocumentBlock
from researchsensei.canonical.quality_gate import M1QualityGateResult
from researchsensei.schemas.base import SenseiModel


class M1VisualAuditReport(SenseiModel):
    html_path: str
    public_report_path: str
    compare_report_path: str = ""
    metrics: dict = Field(default_factory=dict)


class M1VisualAuditReportGenerator:
    """Write lightweight visual/public audit reports for review."""

    def write(
        self,
        *,
        output_dir: str | Path,
        paper_id: str,
        title: str,
        blocks: list[CanonicalDocumentBlock],
        quality: M1QualityGateResult,
        metrics: dict,
        compare_markdown: str = "",
    ) -> M1VisualAuditReport:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        computed = self._metrics(blocks, quality, metrics)

        html_path = output_dir / "visual_audit.html"
        html_path.write_text(self._html(paper_id, title, blocks, quality, computed), encoding="utf-8")
        public_path = output_dir / "PUBLIC_VERIFY_REPORT.md"
        public_path.write_text(self._public_report(paper_id, title, quality, computed), encoding="utf-8")
        compare_path = output_dir / "compare_report.md"
        compare_path.write_text(compare_markdown or self._compare_report(paper_id, title, computed), encoding="utf-8")
        return M1VisualAuditReport(
            html_path=str(html_path),
            public_report_path=str(public_path),
            compare_report_path=str(compare_path),
            metrics=computed,
        )

    def _metrics(self, blocks: list[CanonicalDocumentBlock], quality: M1QualityGateResult, metrics: dict) -> dict:
        formulas = [block for block in blocks if block.block_type == "formula"]
        section_distribution: dict[str, int] = {}
        for block in blocks:
            section_distribution[block.section or "Unknown"] = section_distribution.get(block.section or "Unknown", 0) + 1
        computed = {
            "formula_count": len(formulas),
            "latex_count": sum(1 for block in formulas if block.latex),
            "raw_formula_text_count": sum(1 for block in formulas if block.text and not block.latex),
            "bbox_count": sum(1 for block in formulas if len(block.bbox) == 4),
            "section_distribution": section_distribution,
            "section_contradiction_count": quality.section_contradiction_count,
            "all_formulas_in_Abstract_suspicious": quality.all_formulas_in_abstract_suspicious,
            "polluted_section_count": quality.polluted_section_count,
            "missing_crop_count": quality.missing_crop_count,
            "missing_overlay_count": quality.missing_overlay_count,
            "raw_only_formula_dense": quality.raw_only_formula_dense,
            "m2_ready_for_formula_understanding": quality.m2_ready_for_formula_understanding,
            "formula_understanding_reasons": list(quality.formula_understanding_reasons),
            "high_risk_count": quality.high_risk_count,
            "medium_risk_count": quality.medium_risk_count,
            "low_risk_count": quality.low_risk_count,
            "canonical_quality_status": quality.status.value,
        }
        computed.update(metrics)
        return computed

    def _html(self, paper_id: str, title: str, blocks: list[CanonicalDocumentBlock], quality: M1QualityGateResult, metrics: dict) -> str:
        rows = []
        for block in blocks:
            if block.block_type != "formula":
                continue
            rows.append(
                "<tr>"
                f"<td>{html.escape(block.block_id)}</td>"
                f"<td>{block.page}</td>"
                f"<td>{html.escape(block.section)}</td>"
                f"<td>{html.escape(str(block.bbox))}</td>"
                f"<td><code>{html.escape(block.latex or block.text)}</code></td>"
                f"<td>{html.escape(', '.join(block.risk_flags) or 'none')}</td>"
                "</tr>"
            )
        return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{html.escape(title)} M1 audit</title>
<style>body{{font-family:Arial,sans-serif;margin:24px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:6px;vertical-align:top}}code{{white-space:pre-wrap}}</style>
</head><body>
<h1>M1 Visual Audit: {html.escape(title)}</h1>
<p>paper_id: {html.escape(paper_id)}</p>
<h2>Metrics</h2>
<pre>{html.escape(json.dumps(metrics, indent=2, ensure_ascii=False))}</pre>
<h2>Formula Blocks</h2>
<table><thead><tr><th>block</th><th>page</th><th>section</th><th>bbox</th><th>latex/text</th><th>risk</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
</body></html>"""

    def _public_report(self, paper_id: str, title: str, quality: M1QualityGateResult, metrics: dict) -> str:
        lines = [
            f"# Public M1 Verify Report: {title}",
            "",
            f"- paper_id: {paper_id}",
            f"- canonical_quality_status: {quality.status.value}",
            f"- high_risk_count: {metrics['high_risk_count']}",
            f"- medium_risk_count: {metrics['medium_risk_count']}",
            f"- low_risk_count: {metrics['low_risk_count']}",
            "",
            "## Metrics",
            "",
        ]
        for key, value in metrics.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def _compare_report(self, paper_id: str, title: str, metrics: dict) -> str:
        lines = [f"# M1 Compare Report: {title}", "", f"- paper_id: {paper_id}", ""]
        for key, value in metrics.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)
