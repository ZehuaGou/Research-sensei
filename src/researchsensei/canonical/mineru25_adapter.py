"""MinerU2.5-Pro adapter for M1 v2.

The primary implementation uses ``mineru-vl-utils`` and the
``opendatalab/MinerU2.5-Pro-2604-1.2B`` model.  The older MinerU CLI remains a
separate fallback/debug path in the legacy adapter and is not part of this
primary implementation.
"""
from __future__ import annotations

import importlib.util
import logging
import re
import time
from pathlib import Path
from typing import Any

from researchsensei.canonical.document_blocks import CanonicalDocumentBlock

logger = logging.getLogger(__name__)


class MinerU25ProAdapter:
    """Adapter for MinerU2.5-Pro via mineru-vl-utils."""

    NAME = "mineru25pro"
    DEFAULT_MODEL = "opendatalab/MinerU2.5-Pro-2604-1.2B"

    def __init__(
        self,
        *,
        model_path: str = DEFAULT_MODEL,
        backend: str = "transformers",
        render_scale: float = 2.0,
        handle_equation_block: bool = True,
    ) -> None:
        self.model_path = model_path
        self.backend = backend
        self.render_scale = render_scale
        self.handle_equation_block = handle_equation_block
        self.client: Any | None = None
        self.load_seconds: float = 0.0
        self.warnings: list[str] = []

    def is_available(self) -> bool:
        return importlib.util.find_spec("mineru_vl_utils") is not None

    def load(self) -> None:
        """Load MinerU2.5-Pro client lazily."""
        if self.client is not None:
            return
        if not self.is_available():
            raise RuntimeError("mineru-vl-utils is not installed")

        from mineru_vl_utils import MinerUClient

        start = time.time()
        self.client = MinerUClient(
            backend=self.backend,
            model_path=self.model_path,
            use_tqdm=True,
            handle_equation_block=self.handle_equation_block,
        )
        self.load_seconds = time.time() - start

    def parse_pdf(self, pdf_path: str | Path, *, output_dir: str | Path | None = None) -> tuple[list[CanonicalDocumentBlock], dict[str, Any]]:
        """Parse a PDF into canonical document blocks.

        This method is intentionally heavyweight and should be run only in
        review/manual/nightly paths unless a caller explicitly opts in.
        """
        self.load()
        if self.client is None:  # pragma: no cover - defensive
            raise RuntimeError("MinerU2.5-Pro client did not load")

        import fitz
        from PIL import Image

        pdf_path = Path(pdf_path)
        temp_dir = Path(output_dir or pdf_path.parent)
        temp_dir.mkdir(parents=True, exist_ok=True)

        blocks: list[CanonicalDocumentBlock] = []
        raw_pages: list[dict[str, Any]] = []
        start = time.time()

        with fitz.open(str(pdf_path)) as doc:
            for page_idx, page in enumerate(doc):
                pix = page.get_pixmap(matrix=fitz.Matrix(self.render_scale, self.render_scale))
                image_path = temp_dir / f"_mineru25_page_{page_idx + 1}.png"
                pix.save(str(image_path))
                try:
                    image = Image.open(str(image_path))
                    raw_blocks = self.client.two_step_extract(image)
                finally:
                    image_path.unlink(missing_ok=True)

                raw_pages.append({"page": page_idx + 1, "blocks": list(raw_blocks)})
                blocks.extend(self.normalize_page_result(raw_blocks, page=page_idx + 1, block_offset=len(blocks)))

        stats = {
            "parser": self.NAME,
            "model": self.model_path,
            "backend": self.backend,
            "pages": len(raw_pages),
            "total_blocks": len(blocks),
            "elapsed_seconds": round(time.time() - start, 3),
            "load_seconds": round(self.load_seconds, 3),
        }
        return blocks, {"pages": raw_pages, "stats": stats}

    def normalize_page_result(
        self,
        raw_blocks: list[dict[str, Any]],
        *,
        page: int,
        block_offset: int = 0,
    ) -> list[CanonicalDocumentBlock]:
        """Normalize a MinerU page result into M1 v2 blocks."""
        normalized: list[CanonicalDocumentBlock] = []
        for index, raw in enumerate(raw_blocks, start=1):
            raw_type = str(raw.get("type", raw.get("block_type", "text")))
            content = str(raw.get("content", raw.get("text", "")) or "")
            block_type = self._normalize_block_type(raw_type, content)
            latex = self._extract_latex(content) if block_type == "formula" else ""
            normalized.append(
                CanonicalDocumentBlock(
                    block_id=f"b{block_offset + index:04d}",
                    page=page,
                    bbox=raw.get("bbox", []),
                    block_type=block_type,
                    text="" if block_type == "formula" else content,
                    latex=latex,
                    html=str(raw.get("html", "") or ""),
                    reading_order=index,
                    source=self.NAME,
                    confidence=float(raw.get("confidence", 0.9) or 0.9),
                    raw_payload_ref=f"page_{page}_block_{index}",
                )
            )
        return normalized

    def _normalize_block_type(self, raw_type: str, content: str) -> str:
        raw = raw_type.lower()
        if "formula" in raw or "equation" in raw:
            return "formula"
        if "title" in raw or "heading" in raw:
            return "title"
        if "table" in raw:
            return "table"
        if "figure" in raw or "image" in raw:
            return "figure"
        if "caption" in raw:
            return "caption"
        if "reference" in raw or raw in {"ref", "ref_text"} or raw.startswith("ref_"):
            return "reference"
        return "text" if content else "unknown"

    def _extract_latex(self, content: str) -> str:
        content = content.strip()
        for pattern in [
            r"\$\$(.*?)\$\$",
            r"\\\[(.*?)\\\]",
            r"\\\((.*?)\\\)",
            r"(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)",
        ]:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1).strip()
        return content
