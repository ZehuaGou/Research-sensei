"""Optional Ollama structured section refiner for M1 canonical pipeline."""
from __future__ import annotations

import json

import httpx
from pydantic import ConfigDict, Field, ValidationError

from researchsensei.canonical.document_blocks import CanonicalDocumentBlock
from researchsensei.schemas.base import SenseiModel


ALLOWED_SECTIONS = {
    "Abstract",
    "Introduction",
    "Related Work",
    "Method",
    "Experiments",
    "Conclusion",
    "References",
    "Appendix",
    "Unknown",
}


class OllamaRefinerMetrics(SenseiModel):
    available: bool = False
    model: str = ""
    json_valid_count: int = 0
    json_invalid_count: int = 0
    retry_count: int = 0
    timeout_count: int = 0
    changed_by_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class OllamaAssignment(SenseiModel):
    model_config = ConfigDict(extra="ignore")

    block_id: str
    section: str
    rationale: str = ""
    risk_flags: list[str] = Field(default_factory=list)


class OllamaAssignments(SenseiModel):
    model_config = ConfigDict(extra="ignore")

    assignments: list[OllamaAssignment] = Field(default_factory=list)


class OllamaStructuredClient:
    """Small native Ollama /api/chat client with JSON-Schema format."""

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:0.5b",
        timeout_seconds: float = 30.0,
        max_retries: int = 1,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.json_valid_count = 0
        self.json_invalid_count = 0
        self.retry_count = 0
        self.timeout_count = 0
        self.warnings: list[str] = []

    def is_available(self) -> bool:
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=3)
            return response.status_code == 200
        except Exception:
            return False

    def chat_json(self, prompt: str, schema: dict) -> dict | None:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": schema,
            "temperature": 0,
            "options": {"temperature": 0},
        }
        last_warning = ""
        for attempt in range(self.max_retries + 1):
            try:
                response = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout_seconds)
                response.raise_for_status()
                content = response.json().get("message", {}).get("content", "")
                parsed = json.loads(content)
                self.json_valid_count += 1
                return parsed
            except httpx.TimeoutException:
                self.timeout_count += 1
                self.json_invalid_count += 1
                self.warnings.append("ollama_timeout")
                return None
            except Exception as exc:
                self.json_invalid_count += 1
                last_warning = f"invalid_json: {type(exc).__name__}"
                if attempt < self.max_retries:
                    self.retry_count += 1
                    continue
                self.warnings.append(last_warning)
                return None
        return None


class OllamaSectionRefiner:
    """Optional refiner; never owns source identity or formula fields."""

    def __init__(self, *, client: OllamaStructuredClient | None = None) -> None:
        self.client = client or OllamaStructuredClient()
        self.metrics = OllamaRefinerMetrics(model=self.client.model)

    def refine(self, blocks: list[CanonicalDocumentBlock]) -> list[CanonicalDocumentBlock]:
        prompt = self._build_prompt(blocks)
        payload = self.client.chat_json(prompt, self._schema())
        self._sync_metrics()
        if payload is None:
            self.metrics.warnings.append("ollama_noop_invalid_json")
            return blocks

        try:
            assignments = OllamaAssignments.model_validate(payload)
        except ValidationError as exc:
            self.client.json_invalid_count += 1
            self.client.warnings.append(f"schema_validation_failed: {exc.errors()[0]['type']}")
            self._sync_metrics()
            return blocks

        by_id = {block.block_id: block for block in blocks}
        for assignment in assignments.assignments:
            if assignment.block_id not in by_id:
                continue
            section = assignment.section if assignment.section in ALLOWED_SECTIONS else "Unknown"
            block = by_id[assignment.block_id]
            if section and section != block.section:
                block.section = section
                block.section_confidence = "ollama"
                block.section_reason = assignment.rationale or "ollama_refined"
                self.metrics.changed_by_count += 1
            for flag in assignment.risk_flags:
                if flag not in block.risk_flags:
                    block.risk_flags.append(flag)

        self._sync_metrics()
        return blocks

    def _sync_metrics(self) -> None:
        self.metrics.json_valid_count = self.client.json_valid_count
        self.metrics.json_invalid_count = self.client.json_invalid_count
        self.metrics.retry_count = self.client.retry_count
        self.metrics.timeout_count = self.client.timeout_count
        self.metrics.warnings = list(self.client.warnings)

    def _build_prompt(self, blocks: list[CanonicalDocumentBlock]) -> str:
        lines = [
            "Assign canonical paper sections to blocks.",
            "Only return JSON. Do not rewrite latex, bbox, page, or source identity.",
            "Allowed sections: " + ", ".join(sorted(ALLOWED_SECTIONS)),
            "",
        ]
        for block in blocks[:80]:
            content = block.content.replace("\n", " ")[:180]
            lines.append(
                f"{block.block_id} | page={block.page} | type={block.block_type} | "
                f"current={block.section or 'Unknown'} | content={content}"
            )
        return "\n".join(lines)

    def _schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "assignments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "block_id": {"type": "string"},
                            "section": {"type": "string", "enum": sorted(ALLOWED_SECTIONS)},
                            "rationale": {"type": "string"},
                            "risk_flags": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["block_id", "section"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["assignments"],
            "additionalProperties": False,
        }
