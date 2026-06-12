from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_M1_ARTIFACTS = [
    "canonical_paper.md",
    "document_blocks.json",
    "formula_slots.json",
    "formula_slots.md",
    "paper_metadata.json",
    "quality_report.md",
    "performance_report.json",
]

FORMULA_SLOT_CONTRACT_FIELDS = [
    "formula_id",
    "block_id",
    "page",
    "section",
    "final_latex",
    "equation_number",
    "equation_group_id",
    "group_order",
    "group_crop_path",
    "nearby_text_before",
    "nearby_text_after",
    "risk_flags",
    "final_origin",
    "block_source",
]


@dataclass(frozen=True)
class M1ArtifactBundle:
    input_dir: Path
    canonical_markdown: str
    document_blocks: list[dict[str, Any]]
    formula_slots: list[dict[str, Any]]
    formula_slots_markdown: str
    paper_metadata: dict[str, Any]
    quality_report_markdown: str
    performance_report: dict[str, Any]
    front_matter: dict[str, Any]
    input_hashes: dict[str, str]
    contract: dict[str, Any]


class M1ArtifactReader:
    """Read the M1 artifact contract for M2 without touching raw parser inputs."""

    def __init__(self, input_dir: str | Path) -> None:
        self.input_dir = Path(input_dir)

    def load(self) -> M1ArtifactBundle:
        missing = [name for name in REQUIRED_M1_ARTIFACTS if not (self.input_dir / name).exists()]
        if not (self.input_dir / "visual_audit").exists():
            missing.append("visual_audit/")
        if missing:
            raise FileNotFoundError(f"M1 artifact bundle missing required files: {', '.join(missing)}")

        canonical_markdown = self._read_text("canonical_paper.md")
        document_blocks = self._read_json_list("document_blocks.json")
        formula_slots = self._read_json_list("formula_slots.json")
        formula_slots_markdown = self._read_text("formula_slots.md")
        paper_metadata = self._read_json_dict("paper_metadata.json")
        quality_report_markdown = self._read_text("quality_report.md")
        performance_report = self._read_json_dict("performance_report.json")
        front_matter = parse_front_matter(canonical_markdown)
        input_hashes = self.hash_required_inputs()
        contract = validate_m1_contract(
            input_dir=self.input_dir,
            front_matter=front_matter,
            document_blocks=document_blocks,
            formula_slots=formula_slots,
            performance_report=performance_report,
            quality_report_markdown=quality_report_markdown,
        )
        return M1ArtifactBundle(
            input_dir=self.input_dir,
            canonical_markdown=canonical_markdown,
            document_blocks=document_blocks,
            formula_slots=formula_slots,
            formula_slots_markdown=formula_slots_markdown,
            paper_metadata=paper_metadata,
            quality_report_markdown=quality_report_markdown,
            performance_report=performance_report,
            front_matter=front_matter,
            input_hashes=input_hashes,
            contract=contract,
        )

    def hash_required_inputs(self) -> dict[str, str]:
        hashes: dict[str, str] = {}
        for name in REQUIRED_M1_ARTIFACTS:
            path = self.input_dir / name
            if path.exists():
                hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return hashes

    def _read_text(self, name: str) -> str:
        return (self.input_dir / name).read_text(encoding="utf-8")

    def _read_json_dict(self, name: str) -> dict[str, Any]:
        data = json.loads((self.input_dir / name).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{name} must contain a JSON object")
        return data

    def _read_json_list(self, name: str) -> list[dict[str, Any]]:
        data = json.loads((self.input_dir / name).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"{name} must contain a JSON array")
        return [item for item in data if isinstance(item, dict)]


def parse_front_matter(markdown: str) -> dict[str, Any]:
    lines = markdown.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    values: dict[str, Any] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        values[key.strip()] = _parse_scalar(raw_value.strip())
    return values


def _parse_scalar(value: str) -> Any:
    if value == "":
        return ""
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    if re.fullmatch(r"[-+]?\d+", value):
        try:
            return int(value)
        except ValueError:
            return value
    if re.fullmatch(r"[-+]?\d+\.\d+", value):
        try:
            return float(value)
        except ValueError:
            return value
    return value


def validate_m1_contract(
    *,
    input_dir: Path,
    front_matter: dict[str, Any],
    document_blocks: list[dict[str, Any]],
    formula_slots: list[dict[str, Any]],
    performance_report: dict[str, Any],
    quality_report_markdown: str,
) -> dict[str, Any]:
    checks: dict[str, str] = {}
    reasons: list[str] = []

    checks["candidate_consistency"] = _pass_fail(bool(front_matter.get("paper_id") or front_matter.get("title")))
    checks["document_blocks_schema"] = _pass_fail(all("block_id" in block and "block_type" in block for block in document_blocks))
    missing_slot_fields = _missing_formula_slot_fields(formula_slots)
    checks["formula_slots_schema"] = _pass_fail(not missing_slot_fields)
    if missing_slot_fields:
        reasons.append(f"missing formula slot fields: {missing_slot_fields[:5]}")

    body_slots = [slot for slot in formula_slots if str(slot.get("section", "")).lower() != "references"]
    reference_slots = [slot for slot in formula_slots if str(slot.get("section", "")).lower() == "references"]
    checks["reference_formula_exclusion"] = _pass_fail(bool(body_slots) or not formula_slots)
    if formula_slots and not body_slots:
        reasons.append("all formula slots are in References")

    checks["final_latex"] = _pass_fail(all(str(slot.get("final_latex", "")).strip() for slot in body_slots))
    checks["equation_group_fields"] = _pass_fail(
        all("equation_group_id" in slot and "group_order" in slot and "group_crop_path" in slot for slot in formula_slots)
    )
    checks["nearby_text"] = _pass_fail(
        all((slot.get("nearby_text_before") or slot.get("nearby_text_after")) for slot in body_slots)
    )
    checks["crop_overlay_path"] = _pass_fail(
        all(_relative_file_exists(input_dir, slot.get("crop_path")) and _relative_file_exists(input_dir, slot.get("overlay_path")) for slot in body_slots)
    )

    perf_warning = bool(performance_report.get("warnings")) or performance_report.get("perf_pass") is False
    performance_text = quality_report_markdown.lower()
    checks["performance_gate_not_promoted"] = _pass_fail(
        not perf_warning or "performance gate" in performance_text and "warning" in performance_text
    )
    if perf_warning and checks["performance_gate_not_promoted"] == "FAIL":
        reasons.append("performance warning was not preserved in quality report")

    status = "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL"
    return {
        "status": status,
        "checks": checks,
        "reasons": reasons,
        "formula_count": len(formula_slots),
        "body_formula_count": len(body_slots),
        "reference_formula_count": len(reference_slots),
        "required_artifacts": REQUIRED_M1_ARTIFACTS + ["visual_audit/"],
        "missing_slot_fields": missing_slot_fields,
    }


def _missing_formula_slot_fields(formula_slots: list[dict[str, Any]]) -> list[str]:
    missing: list[str] = []
    for index, slot in enumerate(formula_slots, start=1):
        for field in FORMULA_SLOT_CONTRACT_FIELDS:
            if field not in slot:
                missing.append(f"formula_{index}:{field}")
    return missing


def _relative_file_exists(input_dir: Path, maybe_path: Any) -> bool:
    path_text = str(maybe_path or "")
    if not path_text:
        return False
    path = Path(path_text)
    if path.is_absolute():
        return False
    return (input_dir / path).exists()


def _pass_fail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"
