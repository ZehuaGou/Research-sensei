"""M1 MinerU GPU Smoke Test — verify MinerU2.5-Pro runs on GPU.

Creates a minimal single-page PDF, runs MinerU parse on it,
and verifies device_mode_actual=cuda.

Outputs:
  reports/m1_gpu_smoke_test/gpu_smoke_report.md
  reports/m1_gpu_smoke_test/gpu_smoke_report.json
"""
from __future__ import annotations

import datetime
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "m1_gpu_smoke_test"


def _create_test_pdf(path: Path) -> Path:
    """Create a minimal 1-page PDF with some text and a formula."""
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    # Title
    page.insert_text((72, 72), "GPU Smoke Test Document", fontsize=18, fontname="helv")
    # Body text
    page.insert_text(
        (72, 120),
        "This is a minimal test document for verifying MinerU GPU acceleration.",
        fontsize=11,
        fontname="helv",
    )
    # Formula-like text
    page.insert_text(
        (72, 160),
        "L = E_q(z|x) [log p(x|z)] - KL(q(z|x) || p(z))",
        fontsize=12,
        fontname="cour",
    )
    # More text
    page.insert_text(
        (72, 200),
        "Time series anomaly detection using transformer-based models.",
        fontsize=11,
        fontname="helv",
    )
    doc.save(str(path))
    doc.close()
    return path


def _get_gpu_memory() -> dict:
    """Get current GPU memory stats via torch."""
    result = {"available": False, "allocated_mb": 0, "reserved_mb": 0}
    try:
        import torch
        if torch.cuda.is_available():
            result["available"] = True
            result["allocated_mb"] = round(torch.cuda.memory_allocated(0) / 1024 / 1024)
            result["reserved_mb"] = round(torch.cuda.memory_reserved(0) / 1024 / 1024)
    except Exception:
        pass
    return result


def run_smoke_test(device_mode: str = "auto") -> dict:
    """Run MinerU GPU smoke test on a minimal PDF."""
    print("=" * 60)
    print("M1 MinerU GPU Smoke Test")
    print("=" * 60)

    # Pre-checks
    torch_info = {"installed": False, "version": None, "cuda_version": None, "cuda_available": False, "gpu_name": None}
    try:
        import torch
        torch_info["installed"] = True
        torch_info["version"] = torch.__version__
        torch_info["cuda_version"] = getattr(torch.version, "cuda", None)
        torch_info["cuda_available"] = torch.cuda.is_available()
        if torch_info["cuda_available"]:
            torch_info["gpu_name"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass

    print(f"  torch: {torch_info['version']}")
    print(f"  torch.version.cuda: {torch_info['cuda_version']}")
    print(f"  torch.cuda.is_available(): {torch_info['cuda_available']}")
    print(f"  GPU: {torch_info['gpu_name']}")

    if not torch_info["cuda_available"]:
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "success": False,
            "failure_reason": "torch.cuda.is_available() is False — cannot test GPU",
            "device_mode_requested": device_mode,
            "device_mode_actual": "n/a",
            "torch": torch_info,
        }
        _write_report(report)
        return report

    # Create test PDF
    OUT.mkdir(parents=True, exist_ok=True)
    test_pdf = OUT / "_smoke_test_input.pdf"
    _create_test_pdf(test_pdf)
    print(f"  Test PDF: {test_pdf}")

    # Memory before
    mem_before = _get_gpu_memory()
    print(f"  GPU memory before: allocated={mem_before['allocated_mb']}MB, reserved={mem_before['reserved_mb']}MB")

    # Load MinerU adapter
    sys.path.insert(0, str(ROOT / "src"))
    from researchsensei.canonical.mineru25_adapter import MinerU25ProAdapter

    adapter = MinerU25ProAdapter(device_mode=device_mode)
    print(f"  device_mode_requested: {device_mode}")
    print(f"  model: {adapter.model_path}")

    # Load model
    print("  Loading model...")
    load_start = time.time()
    try:
        adapter.load()
    except Exception as e:
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "success": False,
            "failure_reason": f"Model load failed: {e}",
            "device_mode_requested": device_mode,
            "device_mode_actual": adapter._device_stats.get("device_mode_actual", "unknown"),
            "fallback_reason": adapter._device_stats.get("fallback_reason"),
            "warnings": list(adapter.warnings),
            "load_elapsed_seconds": round(time.time() - load_start, 3),
            "torch": torch_info,
        }
        _write_report(report)
        return report

    load_elapsed = time.time() - load_start
    print(f"  Model loaded in {load_elapsed:.1f}s")
    print(f"  device_mode_actual: {adapter._device_stats.get('device_mode_actual')}")

    # Memory after load
    mem_after_load = _get_gpu_memory()
    print(f"  GPU memory after load: allocated={mem_after_load['allocated_mb']}MB, reserved={mem_after_load['reserved_mb']}MB")

    # Parse
    print("  Parsing test PDF (1 page)...")
    parse_start = time.time()
    try:
        blocks, meta = adapter.parse_pdf(test_pdf, output_dir=OUT / "_smoke_output")
    except Exception as e:
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "success": False,
            "failure_reason": f"Parse failed: {e}",
            "device_mode_requested": device_mode,
            "device_mode_actual": adapter._device_stats.get("device_mode_actual", "unknown"),
            "fallback_reason": adapter._device_stats.get("fallback_reason"),
            "warnings": list(adapter.warnings),
            "load_elapsed_seconds": round(load_elapsed, 3),
            "torch": torch_info,
        }
        _write_report(report)
        return report

    parse_elapsed = time.time() - parse_start
    print(f"  Parse done in {parse_elapsed:.1f}s")

    # Memory after parse
    mem_after_parse = _get_gpu_memory()
    print(f"  GPU memory after parse: allocated={mem_after_parse['allocated_mb']}MB, reserved={mem_after_parse['reserved_mb']}MB")

    # Determine success
    actual_device = adapter._device_stats.get("device_mode_actual", "unknown")
    fallback = adapter._device_stats.get("fallback_reason")
    success = actual_device == "cuda" and fallback is None

    formula_count = len([b for b in blocks if b.block_type == "formula"])
    print(f"  Blocks extracted: {len(blocks)}")
    print(f"  Formulas extracted: {formula_count}")
    print(f"  device_mode_actual: {actual_device}")
    print(f"  fallback_reason: {fallback}")
    print(f"  SUCCESS: {success}")

    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "success": success,
        "input_pdf": str(test_pdf),
        "page_count_requested": 1,
        "model": adapter.model_path,
        "backend": adapter.backend,
        "device_mode_requested": device_mode,
        "device_mode_actual": actual_device,
        "torch_cuda_available": torch_info["cuda_available"],
        "torch_version": torch_info["version"],
        "torch_cuda_version": torch_info["cuda_version"],
        "gpu_name": torch_info["gpu_name"],
        "gpu_memory_before_mb": mem_before["allocated_mb"],
        "gpu_memory_after_load_mb": mem_after_load["allocated_mb"],
        "gpu_memory_after_parse_mb": mem_after_parse["allocated_mb"],
        "model_load_seconds": round(load_elapsed, 3),
        "parse_elapsed_seconds": round(parse_elapsed, 3),
        "blocks_extracted": len(blocks),
        "formulas_extracted": formula_count,
        "warnings": list(adapter.warnings),
        "fallback_reason": fallback,
        "failure_reason": None if success else f"device_mode_actual={actual_device}, expected cuda",
    }

    # Cleanup
    test_pdf.unlink(missing_ok=True)
    import shutil
    smoke_out = OUT / "_smoke_output"
    if smoke_out.exists():
        shutil.rmtree(smoke_out, ignore_errors=True)

    _write_report(report)
    return report


def _write_report(report: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gpu_smoke_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    success_str = "PASS" if report.get("success") else "FAIL"
    lines = [
        "# M1 MinerU GPU Smoke Test Report",
        "",
        f"Generated: {report.get('timestamp', 'unknown')}",
        "",
        f"## Result: {success_str}",
        "",
        f"- Success: **{report.get('success')}**",
        f"- Failure reason: {report.get('failure_reason', 'none')}",
        "",
        "## Device",
        "",
        f"- device_mode_requested: {report.get('device_mode_requested')}",
        f"- device_mode_actual: **{report.get('device_mode_actual')}**",
        f"- fallback_reason: {report.get('fallback_reason', 'none')}",
        "",
        "## PyTorch",
        "",
        f"- torch: {report.get('torch_version')}",
        f"- torch.version.cuda: {report.get('torch_cuda_version')}",
        f"- torch.cuda.is_available(): {report.get('torch_cuda_available')}",
        f"- GPU: {report.get('gpu_name')}",
        "",
        "## Parse",
        "",
        f"- Input PDF: {report.get('input_pdf', 'n/a')}",
        f"- Pages: {report.get('page_count_requested')}",
        f"- Model: {report.get('model')}",
        f"- Backend: {report.get('backend')}",
        f"- Model load: {report.get('model_load_seconds')}s",
        f"- Parse elapsed: {report.get('parse_elapsed_seconds')}s",
        f"- Blocks: {report.get('blocks_extracted')}",
        f"- Formulas: {report.get('formulas_extracted')}",
        "",
        "## GPU Memory",
        "",
        f"- Before: {report.get('gpu_memory_before_mb', 0)} MB allocated",
        f"- After load: {report.get('gpu_memory_after_load_mb', 0)} MB allocated",
        f"- After parse: {report.get('gpu_memory_after_parse_mb', 0)} MB allocated",
        "",
        "## Warnings",
        "",
    ]
    for w in report.get("warnings", []):
        lines.append(f"- {w}")
    if not report.get("warnings"):
        lines.append("- None")

    (OUT / "gpu_smoke_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    device_mode = "auto"
    if len(sys.argv) > 1:
        device_mode = sys.argv[1]

    report = run_smoke_test(device_mode)
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
