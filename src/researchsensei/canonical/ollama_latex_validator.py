"""Optional Ollama-based LaTeX validator for M1 formula correction.

Uses a local LLM to compare MinerU LaTeX output against the cropped formula
image and correct semantic errors in visually similar symbols.
"""
from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

from pydantic import ConfigDict, Field, ValidationError

from researchsensei.canonical.ollama_refiner import OllamaStructuredClient
from researchsensei.schemas.base import SenseiModel

logger = logging.getLogger(__name__)


class LatexValidationMetrics(SenseiModel):
    available: bool = False
    model: str = ""
    formulas_checked: int = 0
    formulas_corrected: int = 0
    json_valid_count: int = 0
    json_invalid_count: int = 0
    timeout_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class LatexValidationResult(SenseiModel):
    model_config = ConfigDict(extra="ignore")

    formula_id: str
    corrected_latex: str = ""
    confidence: float = 0.0
    issues_found: list[str] = Field(default_factory=list)
    needs_human_check: bool = False


class LatexValidationResults(SenseiModel):
    model_config = ConfigDict(extra="ignore")

    results: list[LatexValidationResult] = Field(default_factory=list)


class OllamaLatexValidator:
    """Validate and correct MinerU LaTeX using Ollama plus formula crop images.

    This is an optional component. It requires:
    1. Ollama running locally.
    2. A vision-capable model, such as llava or minicpm-v.
    3. Formula crop images available.

    The validator sends the cropped formula image plus MinerU LaTeX to the LLM
    and asks it to correct semantic extraction errors.
    """

    def __init__(
        self,
        *,
        client: OllamaStructuredClient | None = None,
        model: str = "minicpm-v",
    ) -> None:
        self.client = client or OllamaStructuredClient(model=model)
        self.client.model = model
        self.metrics = LatexValidationMetrics(model=model)

    def is_available(self) -> bool:
        """Check whether Ollama is running and has the configured model."""
        return self.client.is_available()

    def validate_formulas(
        self,
        formula_slots: list[dict],
        output_dir: str | Path,
    ) -> list[dict]:
        """Validate and correct LaTeX for formula slots that have crop images."""
        if not self.is_available():
            self.metrics.warnings.append("ollama_unavailable")
            return formula_slots

        output_dir = Path(output_dir)
        self.metrics.available = True
        updated_slots = []

        for slot in formula_slots:
            updated_slot = dict(slot)
            formula_id = slot.get("formula_id", "")
            crop_path_str = slot.get("crop_path", "")

            if not crop_path_str:
                updated_slots.append(updated_slot)
                continue

            crop_path = output_dir / crop_path_str
            if not crop_path.exists():
                updated_slots.append(updated_slot)
                continue

            current_latex = slot.get("final_latex", "") or slot.get("mineru_latex", "")
            if not current_latex.strip():
                updated_slots.append(updated_slot)
                continue

            self.metrics.formulas_checked += 1
            result = self._validate_single(str(formula_id), crop_path, current_latex)

            if result and result.corrected_latex and result.corrected_latex != current_latex:
                updated_slot["mineru_latex_raw"] = current_latex
                updated_slot["final_latex"] = result.corrected_latex
                updated_slot["latex_corrected_by"] = "ollama_latex_validator"
                updated_slot["latex_correction_confidence"] = result.confidence
                updated_slot["latex_correction_issues"] = result.issues_found
                if result.needs_human_check:
                    updated_slot.setdefault("risk_flags", []).append("LATEX_NEEDS_HUMAN_CHECK")
                self.metrics.formulas_corrected += 1

            updated_slots.append(updated_slot)

        return updated_slots

    def _validate_single(
        self,
        formula_id: str,
        crop_path: Path,
        current_latex: str,
    ) -> LatexValidationResult | None:
        """Validate a single formula by sending image plus LaTeX to Ollama."""
        try:
            image_b64 = base64.b64encode(crop_path.read_bytes()).decode("utf-8")
        except Exception as exc:
            self.metrics.warnings.append(f"image_read_failed: {formula_id}: {exc}")
            return None

        prompt = self._build_prompt(current_latex)
        payload = {
            "model": self.client.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_b64],
                }
            ],
            "stream": False,
            "format": self._schema(),
            "temperature": 0,
            "options": {"temperature": 0},
        }

        try:
            import httpx

            response = httpx.post(
                f"{self.client.base_url}/api/chat",
                json=payload,
                timeout=self.client.timeout_seconds,
            )
            response.raise_for_status()
            content = response.json().get("message", {}).get("content", "")
            parsed = json.loads(content)
            self.metrics.json_valid_count += 1
        except Exception as exc:
            self.metrics.json_invalid_count += 1
            if "timeout" in str(type(exc).__name__).lower():
                self.metrics.timeout_count += 1
            self.metrics.warnings.append(f"validation_failed: {formula_id}: {exc}")
            return None

        try:
            return LatexValidationResult.model_validate(parsed)
        except ValidationError as exc:
            self.metrics.warnings.append(f"schema_validation_failed: {formula_id}: {exc}")
            return None

    def _build_prompt(self, current_latex: str) -> str:
        return (
            "You are a LaTeX formula validator. Compare the formula in the image "
            "with the MinerU-extracted LaTeX below. If there are any differences "
            "(wrong symbols, missing parts, incorrect subscripts/superscripts), "
            "return the corrected LaTeX. If the LaTeX is correct, return it as-is.\n\n"
            "IMPORTANT:\n"
            "- Pay close attention to theta vs 0, I vs t, u vs alpha, and similar-looking characters\n"
            "- Preserve the original LaTeX structure (\\frac, \\sum, \\mathcal, etc.)\n"
            "- Do not add or remove mathematical content\n"
            "- If unsure, set needs_human_check=true\n\n"
            f"MinerU LaTeX:\n{current_latex}\n\n"
            "Return JSON with: formula_id, corrected_latex, confidence (0-1), "
            "issues_found (list of strings), needs_human_check (bool)."
        )

    def _schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "formula_id": {"type": "string"},
                "corrected_latex": {"type": "string"},
                "confidence": {"type": "number"},
                "issues_found": {"type": "array", "items": {"type": "string"}},
                "needs_human_check": {"type": "boolean"},
            },
            "required": ["formula_id", "corrected_latex", "confidence"],
            "additionalProperties": False,
        }
