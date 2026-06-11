"""MinerU2.5-Pro adapter for M1 canonical pipeline.

The primary implementation uses ``mineru-vl-utils`` and the
``opendatalab/MinerU2.5-Pro-2604-1.2B`` model.
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
    """Adapter for MinerU2.5-Pro via mineru-vl-utils.

    Supports device_mode: "auto" (default), "cuda", "cpu".
    When auto: uses GPU if available and has enough memory, else CPU.
    Reports device stats in parse output for diagnostics.
    """

    NAME = "mineru25pro"
    DEFAULT_MODEL = "opendatalab/MinerU2.5-Pro-2604-1.2B"
    MIN_GPU_MEMORY_MB = 6000  # Minimum GPU memory to attempt GPU loading

    def __init__(
        self,
        *,
        model_path: str = DEFAULT_MODEL,
        backend: str = "transformers",
        device_mode: str = "auto",
        render_scale: float = 2.0,
        handle_equation_block: bool = True,
    ) -> None:
        self.model_path = model_path
        self.backend = backend
        self.device_mode = device_mode
        self.render_scale = render_scale
        self.handle_equation_block = handle_equation_block
        self.client: Any | None = None
        self.load_seconds: float = 0.0
        self.warnings: list[str] = []
        self._device_stats: dict[str, Any] = {}

    def is_available(self) -> bool:
        return importlib.util.find_spec("mineru_vl_utils") is not None

    def _probe_device(self) -> dict[str, Any]:
        """Probe GPU/CUDA status and determine actual device."""
        stats: dict[str, Any] = {
            "device_mode_requested": self.device_mode,
            "cuda_available": False,
            "gpu_name": None,
            "gpu_memory_total_mb": None,
            "torch_installed": False,
        }
        try:
            import torch
            stats["torch_installed"] = True
            stats["cuda_available"] = torch.cuda.is_available()
            if stats["cuda_available"]:
                stats["gpu_name"] = torch.cuda.get_device_name(0)
                stats["gpu_memory_total_mb"] = round(torch.cuda.get_device_properties(0).total_mem / 1024 / 1024)
        except ImportError:
            pass

        # Determine actual device
        if self.device_mode == "cuda":
            if not stats["cuda_available"]:
                self.warnings.append("device_mode=cuda requested but CUDA not available")
                stats["device_mode_actual"] = "cpu"
                stats["fallback_reason"] = "CUDA not available"
            elif stats["gpu_memory_total_mb"] and stats["gpu_memory_total_mb"] < self.MIN_GPU_MEMORY_MB:
                self.warnings.append(
                    f"GPU memory ({stats['gpu_memory_total_mb']}MB) < minimum ({self.MIN_GPU_MEMORY_MB}MB)"
                )
                stats["device_mode_actual"] = "cpu"
                stats["fallback_reason"] = f"GPU memory too small ({stats['gpu_memory_total_mb']}MB)"
            else:
                stats["device_mode_actual"] = "cuda"
        elif self.device_mode == "cpu":
            stats["device_mode_actual"] = "cpu"
        else:  # auto
            if stats["cuda_available"] and stats["gpu_memory_total_mb"] and stats["gpu_memory_total_mb"] >= self.MIN_GPU_MEMORY_MB:
                stats["device_mode_actual"] = "cuda"
            else:
                stats["device_mode_actual"] = "cpu"
                if stats["cuda_available"]:
                    stats["fallback_reason"] = f"GPU available but memory too small ({stats['gpu_memory_total_mb']}MB)"
                    self.warnings.append(f"GPU available but model will run on CPU ({stats['fallback_reason']})")
                elif not stats["cuda_available"]:
                    stats["fallback_reason"] = "CUDA not available"

        return stats

    def load(self) -> None:
        """Load MinerU2.5-Pro client lazily with GPU awareness."""
        if self.client is not None:
            return
        if not self.is_available():
            raise RuntimeError("mineru-vl-utils is not installed")

        self._device_stats = self._probe_device()
        actual_device = self._device_stats["device_mode_actual"]

        from mineru_vl_utils import MinerUClient

        start = time.time()
        load_error = None

        if actual_device == "cuda" and self.backend == "transformers":
            # Try GPU-aware loading with explicit model/processor
            try:
                self._load_gpu_transformers()
            except Exception as e:
                load_error = str(e)
                self.warnings.append(f"GPU loading failed: {e}. Falling back to CPU.")
                self._device_stats["device_mode_actual"] = "cpu"
                self._device_stats["fallback_reason"] = f"GPU load failed: {e}"
                actual_device = "cpu"

        if self.client is None:
            # Standard loading (CPU or non-transformers backend)
            self.client = MinerUClient(
                backend=self.backend,
                model_path=self.model_path,
                use_tqdm=True,
                handle_equation_block=self.handle_equation_block,
            )

        self.load_seconds = time.time() - start
        self._device_stats["model_load_seconds"] = round(self.load_seconds, 3)
        self._device_stats["model_load_backend"] = self.backend
        self._device_stats["model_load_error"] = load_error

        if actual_device == "cpu" and self.device_mode != "cpu":
            self.warnings.append(
                f"Model loaded on CPU. Requested: {self.device_mode}, Actual: cpu. "
                f"Parse will be slow (expect ~5-15 min/page on CPU)."
            )

    def _load_gpu_transformers(self) -> None:
        """Attempt GPU-aware loading with explicit model and processor."""
        try:
            from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
            from mineru_vl_utils import MinerUClient
        except ImportError as e:
            raise RuntimeError(f"Missing dependency for GPU loading: {e}") from e

        logger.info("Loading MinerU2.5-Pro on GPU with device_map=auto...")
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            self.model_path,
            torch_dtype="auto",
            device_map="auto",
        )
        processor = AutoProcessor.from_pretrained(self.model_path, use_fast=True)

        self.client = MinerUClient(
            backend="transformers",
            model=model,
            processor=processor,
            use_tqdm=True,
            handle_equation_block=self.handle_equation_block,
        )

    def parse_pdf(self, pdf_path: str | Path, *, output_dir: str | Path | None = None) -> tuple[list[CanonicalDocumentBlock], dict[str, Any]]:
        """Parse a PDF into canonical document blocks."""
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
            page_count = len(doc)
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

        elapsed = time.time() - start
        pages_per_second = page_count / elapsed if elapsed > 0 else 0
        seconds_per_page = elapsed / page_count if page_count > 0 else 0

        stats = {
            "parser": self.NAME,
            "model": self.model_path,
            "backend": self.backend,
            "pages": page_count,
            "total_blocks": len(blocks),
            "elapsed_seconds": round(elapsed, 3),
            "load_seconds": round(self.load_seconds, 3),
            "pages_per_second": round(pages_per_second, 3),
            "seconds_per_page": round(seconds_per_page, 1),
            # Device stats
            "device_mode_requested": self._device_stats.get("device_mode_requested", self.device_mode),
            "device_mode_actual": self._device_stats.get("device_mode_actual", "unknown"),
            "cuda_available": self._device_stats.get("cuda_available", False),
            "gpu_name": self._device_stats.get("gpu_name"),
            "gpu_memory_total_mb": self._device_stats.get("gpu_memory_total_mb"),
            "model_load_backend": self._device_stats.get("model_load_backend", self.backend),
            "fallback_reason": self._device_stats.get("fallback_reason"),
            "warnings": list(self.warnings),
        }

        # Performance warnings
        if stats["device_mode_actual"] == "cpu" and self.device_mode != "cpu":
            stats.setdefault("perf_warnings", []).append("GPU requested but running on CPU")
        if seconds_per_page > 120:
            stats.setdefault("perf_warnings", []).append(f"seconds_per_page={seconds_per_page:.0f} > 120s threshold")
        if elapsed > 3600:
            stats.setdefault("perf_warnings", []).append(f"total_parse_time={elapsed:.0f}s > 3600s threshold")

        return blocks, {"pages": raw_pages, "stats": stats}

    def normalize_page_result(
        self,
        raw_blocks: list[dict[str, Any]],
        *,
        page: int,
        block_offset: int = 0,
    ) -> list[CanonicalDocumentBlock]:
        """Normalize a MinerU page result into canonical document blocks."""
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
