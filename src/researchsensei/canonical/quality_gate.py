"""M1 v2 quality gate."""
from __future__ import annotations

from pydantic import Field

from researchsensei.canonical.document_blocks import CanonicalDocumentBlock
from researchsensei.schemas.base import SenseiModel
from researchsensei.schemas.enums import CanonicalQualityStatus


class M1QualityGateResult(SenseiModel):
    status: CanonicalQualityStatus = CanonicalQualityStatus.FAIL
    blocking_reasons: list[str] = Field(default_factory=list)
    warning_reasons: list[str] = Field(default_factory=list)
    all_formulas_in_abstract_suspicious: bool = False
    section_contradiction_count: int = 0
    polluted_section_count: int = 0
    source_mismatch_count: int = 0
    missing_latex_count: int = 0
    missing_bbox_count: int = 0
    missing_crop_count: int = 0
    missing_overlay_count: int = 0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0


class M1QualityGate:
    """Gate canonical blocks before allowing M2 handoff."""

    def evaluate(self, blocks: list[CanonicalDocumentBlock], formula_slots: list[dict]) -> M1QualityGateResult:
        formulas = [block for block in blocks if block.block_type == "formula"]
        result = M1QualityGateResult(status=CanonicalQualityStatus.PASS)

        if len(formulas) >= 5 and all(block.section == "Abstract" for block in formulas):
            result.all_formulas_in_abstract_suspicious = True
            result.blocking_reasons.append("ALL_FORMULAS_IN_ABSTRACT_SUSPICIOUS")

        result.section_contradiction_count = sum(
            1
            for block in formulas
            if "SECTION_CONTRADICTION_POSSIBLE" in block.risk_flags
            or (block.section == "Abstract" and block.page > 2)
        )
        if result.section_contradiction_count:
            result.blocking_reasons.append("SECTION_CONTRADICTION_POSSIBLE")

        result.polluted_section_count = self._count_polluted_sections(blocks)
        if result.polluted_section_count:
            result.blocking_reasons.append("POLLUTED_SECTION")

        result.missing_latex_count = sum(1 for block in formulas if not block.latex.strip())
        result.missing_bbox_count = sum(1 for block in formulas if len(block.bbox) != 4)
        if result.missing_latex_count:
            result.warning_reasons.append("MISSING_FORMULA_LATEX")
        if result.missing_bbox_count:
            result.blocking_reasons.append("MISSING_FORMULA_BBOX")

        for slot in formula_slots:
            if slot.get("crop_required", True) and not slot.get("crop_path"):
                result.missing_crop_count += 1
            if slot.get("overlay_required", True) and not slot.get("overlay_path"):
                result.missing_overlay_count += 1
            if slot.get("source_mismatch"):
                result.source_mismatch_count += 1

        if result.source_mismatch_count:
            result.blocking_reasons.append("SOURCE_MISMATCH")
        if result.missing_crop_count:
            result.blocking_reasons.append("MISSING_FORMULA_CROP")
        if result.missing_overlay_count:
            result.blocking_reasons.append("MISSING_FORMULA_OVERLAY")

        result.high_risk_count = len(result.blocking_reasons)
        result.medium_risk_count = len(result.warning_reasons)
        result.low_risk_count = sum(len(block.risk_flags) for block in blocks) - result.high_risk_count

        if result.blocking_reasons:
            result.status = CanonicalQualityStatus.FAIL
        elif result.warning_reasons:
            result.status = CanonicalQualityStatus.DEGRADED
        else:
            result.status = CanonicalQualityStatus.PASS
        return result

    def _count_polluted_sections(self, blocks: list[CanonicalDocumentBlock]) -> int:
        polluted = 0
        by_section: dict[str, list[str]] = {}
        for block in blocks:
            if block.block_type in {"text", "reference"} and block.section:
                by_section.setdefault(block.section, []).append(block.text)
        for section in ("Introduction", "Method", "Experiments"):
            lines = "\n".join(by_section.get(section, [])).splitlines()
            if len(lines) < 4:
                continue
            refish = sum(1 for line in lines if line.strip().startswith("[") or "doi:" in line.lower() or "proceedings" in line.lower())
            if refish / max(len(lines), 1) >= 0.35:
                polluted += 1
        return polluted
