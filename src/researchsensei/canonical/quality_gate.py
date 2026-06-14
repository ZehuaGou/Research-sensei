"""M1 quality gate."""
from __future__ import annotations

import re

from pydantic import Field

from researchsensei.canonical.document_blocks import CanonicalDocumentBlock
from researchsensei.schemas.base import SenseiModel
from researchsensei.schemas.enums import CanonicalQualityStatus


class M1QualityGateResult(SenseiModel):
    status: CanonicalQualityStatus = CanonicalQualityStatus.FAIL
    blocking_reasons: list[str] = Field(default_factory=list)
    warning_reasons: list[str] = Field(default_factory=list)
    formula_understanding_reasons: list[str] = Field(default_factory=list)
    m2_ready_for_formula_understanding: bool = True
    all_formulas_in_abstract_suspicious: bool = False
    raw_only_formula_dense: bool = False
    formula_count: int = 0
    latex_count: int = 0
    raw_formula_text_count: int = 0
    section_contradiction_count: int = 0
    polluted_section_count: int = 0
    source_mismatch_count: int = 0
    missing_latex_count: int = 0
    missing_bbox_count: int = 0
    missing_crop_count: int = 0
    missing_overlay_count: int = 0
    review_disabled_count: int = 0
    severe_repetition_count: int = 0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0


class M1QualityGate:
    """Gate canonical blocks before allowing M2 handoff."""

    def evaluate(self, blocks: list[CanonicalDocumentBlock], formula_slots: list[dict]) -> M1QualityGateResult:
        formulas = [block for block in blocks if block.block_type == "formula"]
        result = M1QualityGateResult(status=CanonicalQualityStatus.PASS)
        result.formula_count = len(formulas)
        result.latex_count = sum(1 for block in formulas if block.latex.strip())
        result.raw_formula_text_count = sum(1 for block in formulas if block.text.strip() and not block.latex.strip())

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

        result.severe_repetition_count = self._count_severe_repetition(blocks)
        if result.severe_repetition_count:
            result.blocking_reasons.append("SEVERE_TEXT_REPETITION")

        result.missing_latex_count = sum(1 for block in formulas if not block.latex.strip())
        result.missing_bbox_count = sum(1 for block in formulas if len(block.bbox) != 4)
        if result.missing_latex_count:
            result.warning_reasons.append("MISSING_FORMULA_LATEX")
        if result.missing_bbox_count:
            result.blocking_reasons.append("MISSING_FORMULA_BBOX")

        if len(formulas) >= 5 and result.latex_count == 0:
            result.raw_only_formula_dense = True
            result.m2_ready_for_formula_understanding = False
            reason = "RAW_ONLY_FORMULA_DENSE_NO_LATEX"
            result.warning_reasons.append(reason)
            result.formula_understanding_reasons.append(reason)

        slots_by_block_id = {str(slot.get("block_id", "")): slot for slot in formula_slots if slot.get("block_id")}
        slots_by_formula_id = {str(slot.get("formula_id", "")): slot for slot in formula_slots if slot.get("formula_id")}
        for index, block in enumerate(formulas, start=1):
            formula_id = f"formula_{index:03d}"
            slot = slots_by_block_id.get(block.block_id) or slots_by_formula_id.get(formula_id) or {}
            if slot.get("review_disabled") is True:
                result.review_disabled_count += 1
                continue
            if slot.get("crop_required", True) and not slot.get("crop_path"):
                result.missing_crop_count += 1
            if slot.get("overlay_required", True) and not slot.get("overlay_path"):
                result.missing_overlay_count += 1

        result.source_mismatch_count = sum(1 for slot in formula_slots if slot.get("source_mismatch"))

        if result.source_mismatch_count:
            result.blocking_reasons.append("SOURCE_MISMATCH")
        if result.missing_crop_count:
            result.blocking_reasons.append("MISSING_FORMULA_CROP")
        if result.missing_overlay_count:
            result.blocking_reasons.append("MISSING_FORMULA_OVERLAY")

        result.high_risk_count = len(result.blocking_reasons) + (1 if result.raw_only_formula_dense else 0)
        result.medium_risk_count = len(result.warning_reasons)
        result.low_risk_count = max(0, sum(len(block.risk_flags) for block in blocks) - result.high_risk_count)

        if result.blocking_reasons:
            result.status = CanonicalQualityStatus.FAIL
        elif result.warning_reasons:
            result.status = CanonicalQualityStatus.DEGRADED
        else:
            result.status = CanonicalQualityStatus.PASS
        return result

    def _count_severe_repetition(self, blocks: list[CanonicalDocumentBlock]) -> int:
        count = 0
        for block in blocks:
            if block.block_type not in {"text", "caption", "reference"}:
                continue
            text = block.text.strip()
            if not text or "<table" in text.lower():
                continue
            if self._has_repeated_text_noise(text):
                count += 1
        return count

    @staticmethod
    def _has_repeated_text_noise(text: str) -> bool:
        lowered = text.lower()
        severe_phrases = (
            "source of the model to the source",
            "can be used to be used",
            "the model provides a more comprehensive and comprehensive",
        )
        if any(phrase in lowered for phrase in severe_phrases):
            return True
        tokens = re.findall(r"[a-z][a-z0-9_+-]*", lowered)
        if len(tokens) < 40:
            return False
        grams = [" ".join(tokens[index:index + 6]) for index in range(len(tokens) - 5)]
        seen: dict[str, int] = {}
        for gram in grams:
            seen[gram] = seen.get(gram, 0) + 1
            if seen[gram] >= 4:
                return True
        return False

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
