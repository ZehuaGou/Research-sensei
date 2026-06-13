"""Optional Ollama-based LaTeX validator for M1 formula correction.

Uses a local LLM to compare MinerU LaTeX output against the cropped formula
image and correct semantic errors in visually similar symbols.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path

from pydantic import ConfigDict, Field, ValidationError, field_validator

from researchsensei.canonical.latex_postprocessor import postprocess_latex
from researchsensei.canonical.ollama_refiner import OllamaStructuredClient
from researchsensei.schemas.base import SenseiModel

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"\\tag\s*\{[^}]+\}")
_DISPLAY_MATH_LINE_RE = re.compile(
    r"^\s*\$(?P<body>.*?)\$\s*(?P<trailer>(?:\([^)]*\)\s*)?(?:\\tag\s*\{[^}]+\})?)\s*$"
)
_TAG_VALUE_RE = re.compile(r"\\tag\s*\{\s*(?P<value>[^}]+?)\s*\}")
_TRAILING_LINE_BREAK_RE = re.compile(r"\s*\\\\\s*$")
_LATEX_WRAPPER_COMMAND_RE = re.compile(
    r"\\(?:mathbf|mathrm|mathcal|mathbb|mathit|text|operatorname)\s*\{\s*([^{}]+?)\s*\}"
)


class LatexValidationMetrics(SenseiModel):
    available: bool = False
    model: str = ""
    formulas_checked: int = 0
    formulas_corrected: int = 0
    low_confidence_count: int = 0
    overexpanded_count: int = 0
    anchor_mismatch_count: int = 0
    tag_restored_count: int = 0
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

    @field_validator("formula_id", mode="before")
    @classmethod
    def _coerce_formula_id(cls, value: object) -> str:
        return str(value)


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
        model: str = "qwen3.5:4b",
        min_confidence: float = 0.8,
    ) -> None:
        self.client = client or OllamaStructuredClient(model=model)
        self.client.model = model
        self.min_confidence = min(max(min_confidence, 0.0), 1.0)
        self.metrics = LatexValidationMetrics(model=model)

    def is_available(self) -> bool:
        """Check whether Ollama is running and has the configured vision model."""
        try:
            import httpx

            response = httpx.get(f"{self.client.base_url}/api/tags", timeout=3)
            if response.status_code != 200:
                return False
            models = response.json().get("models", [])
        except Exception:
            return False

        if not models:
            return True

        configured = self.client.model
        for model in models:
            names = {str(model.get("name") or ""), str(model.get("model") or "")}
            if configured not in names:
                continue
            capabilities = model.get("capabilities")
            if isinstance(capabilities, list) and capabilities and "vision" not in capabilities:
                warning = f"ollama_model_not_vision: {configured}"
                if warning not in self.metrics.warnings:
                    self.metrics.warnings.append(warning)
                return False
            return True

        warning = f"ollama_model_unavailable: {configured}"
        if warning not in self.metrics.warnings:
            self.metrics.warnings.append(warning)
        return False

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
            crop_path_str = slot.get("group_crop_path") or slot.get("crop_path", "")

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

            if result and result.corrected_latex:
                candidate_latex, tag_restored = self._sanitize_candidate_latex(
                    current_latex,
                    result.corrected_latex,
                )
                if candidate_latex == current_latex:
                    updated_slots.append(updated_slot)
                    continue
                risk_flags = updated_slot.setdefault("risk_flags", [])
                if self._looks_overexpanded(current_latex, result.corrected_latex) or self._looks_overexpanded(
                    current_latex,
                    candidate_latex,
                ):
                    self.metrics.overexpanded_count += 1
                    if "OLLAMA_LATEX_OVEREXPANDED_GROUP" not in risk_flags:
                        risk_flags.append("OLLAMA_LATEX_OVEREXPANDED_GROUP")
                    self.metrics.warnings.append(f"overexpanded_group: {formula_id}")
                    updated_slots.append(updated_slot)
                    continue
                if self._lhs_anchor_changed(current_latex, candidate_latex):
                    self.metrics.anchor_mismatch_count += 1
                    if "OLLAMA_LATEX_LHS_MISMATCH" not in risk_flags:
                        risk_flags.append("OLLAMA_LATEX_LHS_MISMATCH")
                    self.metrics.warnings.append(f"lhs_mismatch: {formula_id}")
                    updated_slots.append(updated_slot)
                    continue
                if self._relation_operands_changed(current_latex, candidate_latex):
                    self.metrics.anchor_mismatch_count += 1
                    if "OLLAMA_LATEX_RELATION_OPERAND_MISMATCH" not in risk_flags:
                        risk_flags.append("OLLAMA_LATEX_RELATION_OPERAND_MISMATCH")
                    self.metrics.warnings.append(f"relation_operand_mismatch: {formula_id}")
                    updated_slots.append(updated_slot)
                    continue
                if result.needs_human_check:
                    if "LATEX_NEEDS_HUMAN_CHECK" not in risk_flags:
                        risk_flags.append("LATEX_NEEDS_HUMAN_CHECK")
                if result.confidence < self.min_confidence or result.needs_human_check:
                    self.metrics.low_confidence_count += 1
                    if "OLLAMA_LATEX_LOW_CONFIDENCE" not in risk_flags:
                        risk_flags.append("OLLAMA_LATEX_LOW_CONFIDENCE")
                    self.metrics.warnings.append(f"low_confidence: {formula_id}: {result.confidence:.3f}")
                else:
                    updated_slot.setdefault("mineru_latex_raw", updated_slot.get("mineru_latex") or current_latex)
                    updated_slot.setdefault("final_latex_raw", current_latex)
                    updated_slot["final_latex"] = candidate_latex
                    updated_slot["latex_corrected_by"] = "ollama_latex_validator"
                    updated_slot["latex_correction_confidence"] = result.confidence
                    updated_slot["latex_correction_issues"] = result.issues_found
                    if tag_restored:
                        updated_slot["latex_tag_restored"] = True
                        self.metrics.tag_restored_count += 1
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

        prompt = self._build_prompt(formula_id, current_latex)
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
            "think": False,
            "temperature": 0,
            "options": {"temperature": 0, "think": False},
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
            parsed = self._parse_json_content(content)
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

    def _restore_missing_tag(self, original_latex: str, corrected_latex: str) -> tuple[str, bool]:
        original_tag = _TAG_RE.search(original_latex)
        if original_tag is None:
            return corrected_latex, False
        candidate = self._remove_duplicate_parenthetical_tag(corrected_latex, original_tag.group(0))
        corrected_tag = _TAG_RE.search(candidate)
        if corrected_tag is not None:
            if corrected_tag.group(0) == original_tag.group(0):
                return candidate, False
            return (
                f"{candidate[:corrected_tag.start()]}{original_tag.group(0)}{candidate[corrected_tag.end():]}",
                True,
            )
        candidate = self._strip_single_formula_math_wrappers(candidate)
        return f"{candidate.rstrip()} {original_tag.group(0)}", True

    def _sanitize_candidate_latex(self, original_latex: str, corrected_latex: str) -> tuple[str, bool]:
        candidate = self._strip_single_formula_math_wrappers(corrected_latex)
        candidate = self._strip_trailing_single_line_break(original_latex, candidate)
        candidate = postprocess_latex(candidate)
        original_tag = _TAG_RE.search(original_latex)
        if original_tag is not None:
            candidate = self._remove_duplicate_parenthetical_tag(candidate, original_tag.group(0))
            candidate = self._strip_single_formula_math_wrappers(candidate)
            candidate = self._strip_trailing_single_line_break(original_latex, candidate)
            candidate = postprocess_latex(candidate)
        candidate, tag_restored = self._restore_missing_tag(original_latex, candidate)
        return candidate.strip(), tag_restored

    def _strip_single_formula_math_wrappers(self, latex: str) -> str:
        candidate = latex.strip()
        lines = [line.strip() for line in candidate.splitlines() if line.strip()]
        if len(lines) != 1:
            return candidate
        match = _DISPLAY_MATH_LINE_RE.match(lines[0])
        if match:
            trailer = (match.group("trailer") or "").strip()
            if trailer:
                return f"{match.group('body').strip()} {trailer}".strip()
            return match.group("body").strip()
        return candidate

    def _remove_duplicate_parenthetical_tag(self, latex: str, original_tag: str) -> str:
        tag_value = _TAG_VALUE_RE.search(original_tag)
        if tag_value is None:
            return latex
        escaped_value = re.escape(tag_value.group("value").strip())
        duplicate_re = re.compile(rf"\s*\(\s*{escaped_value}\s*\)(?=\s*(?:\\tag\s*\{{|$))")
        return duplicate_re.sub("", latex).rstrip()

    def _strip_trailing_single_line_break(self, original_latex: str, candidate_latex: str) -> str:
        if "\\\\" in original_latex:
            return candidate_latex.strip()
        candidate_lines = [line.strip() for line in candidate_latex.splitlines() if line.strip()]
        if len(candidate_lines) != 1:
            return candidate_latex.strip()
        return _TRAILING_LINE_BREAK_RE.sub("", candidate_latex).strip()

    def _looks_overexpanded(self, original_latex: str, candidate_latex: str) -> bool:
        original_lines = [line.strip() for line in original_latex.splitlines() if line.strip()]
        candidate_lines = [line.strip() for line in candidate_latex.splitlines() if line.strip()]
        if len(original_lines) <= 1 and len(candidate_lines) > 1:
            return True
        if candidate_latex.count("$") >= 4:
            return True
        original_equals = original_latex.count("=")
        candidate_equals = candidate_latex.count("=")
        return original_equals <= 1 and candidate_equals > original_equals + 1

    def _lhs_anchor_changed(self, original_latex: str, candidate_latex: str) -> bool:
        if "=" not in original_latex or "=" not in candidate_latex:
            return False
        original_lhs = self._normalize_formula_anchor(original_latex.split("=", 1)[0])
        candidate_lhs = self._normalize_formula_anchor(candidate_latex.split("=", 1)[0])
        return bool(original_lhs and candidate_lhs and original_lhs != candidate_lhs)

    def _relation_operands_changed(self, original_latex: str, candidate_latex: str) -> bool:
        """Reject LLM corrections that alter operands around inequalities.

        The vision model may clean up formatting, but it must not swap or rewrite
        the mathematical objects around relations such as ``\\geq``. This catches
        cases where a piecewise condition changes from ``phi_s^{C_m} >= phi_s^c``
        to ``phi_s^c >= phi_s^{C_m}``.
        """
        original_relations = self._relation_anchors(original_latex)
        candidate_relations = self._relation_anchors(candidate_latex)
        if not original_relations or not candidate_relations:
            return False
        if len(original_relations) != len(candidate_relations):
            return True
        for original, candidate in zip(original_relations, candidate_relations):
            if original != candidate:
                return True
        return False

    def _relation_anchors(self, latex: str) -> list[tuple[str, str, str]]:
        relation_re = re.compile(r"(\\geq|\\leq|\\gt|\\lt|>=|<=|>|<)")
        anchors: list[tuple[str, str, str]] = []
        for match in relation_re.finditer(latex):
            left = self._math_object_anchor(latex[: match.start()], last=True)
            right = self._math_object_anchor(latex[match.end() :], last=False)
            if left and right:
                anchors.append((self._normalize_relation_operator(match.group(1)), left, right))
        return anchors

    def _math_object_anchor(self, latex: str, *, last: bool) -> str:
        matches = list(re.finditer(r"\\phi", latex))
        if not matches:
            return ""
        match = matches[-1] if last else matches[0]
        token = self._consume_symbol_token(latex[match.start() :])
        return self._normalize_symbol_token(token)

    def _consume_symbol_token(self, latex: str) -> str:
        compact = re.sub(r"\s+", "", latex)
        end = compact.find(")")
        if end >= 0:
            return compact[: end + 1]
        stop = re.search(r"(?:\\\\|&|,|;|\\tag\b|\\text\b)", compact)
        if stop:
            return compact[: stop.start()]
        return compact

    def _normalize_symbol_token(self, token: str) -> str:
        compact = re.sub(r"\s+", "", token)
        if not compact.startswith(r"\phi"):
            return self._normalize_formula_anchor(compact)
        index = len(r"\phi")
        subscript = ""
        superscript = ""
        while index < len(compact) and compact[index] in "_^":
            marker = compact[index]
            index += 1
            value, index = self._read_script_value(compact, index)
            if marker == "_":
                subscript = self._normalize_formula_anchor(value)
            else:
                superscript = self._normalize_formula_anchor(value)
        argument = ""
        if index < len(compact) and compact[index] == "(":
            argument, _ = self._read_balanced(compact, index, "(", ")")
            argument = self._normalize_formula_anchor(argument)
        return f"phi|sub={subscript}|sup={superscript}|arg={argument}"

    def _read_script_value(self, text: str, index: int) -> tuple[str, int]:
        if index < len(text) and text[index] == "{":
            return self._read_balanced(text, index, "{", "}")
        start = index
        while index < len(text) and text[index] not in "_^(),;:&<>":
            index += 1
        return text[start:index], index

    def _read_balanced(self, text: str, index: int, open_char: str, close_char: str) -> tuple[str, int]:
        depth = 0
        start = index
        while index < len(text):
            char = text[index]
            if char == open_char:
                depth += 1
            elif char == close_char:
                depth -= 1
                if depth == 0:
                    return text[start + 1 : index], index + 1
            index += 1
        return text[start:], len(text)

    def _normalize_relation_operator(self, operator: str) -> str:
        return {
            r"\geq": ">=",
            r"\leq": "<=",
            r"\gt": ">",
            r"\lt": "<",
        }.get(operator, operator)

    def _normalize_formula_anchor(self, latex: str) -> str:
        value = _TAG_RE.sub("", latex)
        previous = None
        while previous != value:
            previous = value
            value = _LATEX_WRAPPER_COMMAND_RE.sub(r"\1", value)
        return re.sub(r"[^0-9A-Za-z]+", "", value).lower()

    def _build_prompt(self, formula_id: str, current_latex: str) -> str:
        return (
            "You are a LaTeX formula validator. Compare the formula in the image "
            "with the MinerU-extracted LaTeX below. If there are any differences "
            "(wrong symbols, missing parts, incorrect subscripts/superscripts), "
            "return the corrected LaTeX. If the LaTeX is correct, return it as-is.\n\n"
            "IMPORTANT:\n"
            "- Pay close attention to theta vs 0, I vs t, u vs alpha, and similar-looking characters\n"
            "- Preserve the original LaTeX structure (\\frac, \\sum, \\mathcal, etc.)\n"
            "- Preserve equation number tags such as \\tag{4} exactly if they are present\n"
            "- Do not add or remove mathematical content\n"
            "- Never swap the left/right operands of =, <, >, \\leq, or \\geq relations\n"
            "- If the image contains a multi-line formula group, correct only the MinerU LaTeX line below; do not return other lines from the group\n"
            "- If unsure, set needs_human_check=true\n\n"
            f"Return formula_id exactly as: {formula_id}\n\n"
            f"MinerU LaTeX:\n{current_latex}\n\n"
            "Return JSON with: formula_id, corrected_latex, confidence (0-1), "
            "issues_found (list of strings), needs_human_check (bool)."
        )

    def _parse_json_content(self, content: str) -> dict:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            stripped = content.strip()
            if stripped.startswith("```"):
                stripped = stripped.strip("`")
                if "\n" in stripped:
                    stripped = stripped.split("\n", 1)[1].strip()
            start = stripped.find("{")
            end = stripped.rfind("}")
            if start >= 0 and end > start:
                return json.loads(stripped[start : end + 1])
            raise

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
