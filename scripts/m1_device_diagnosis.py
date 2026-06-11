"""M1 Device Diagnosis — GPU/CUDA/device audit for MinerU2.5-Pro pipeline.

Outputs:
  reports/m1_device_diagnosis/device_report.md
  reports/m1_device_diagnosis/device_report.json
"""
from __future__ import annotations

import datetime
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "m1_device_diagnosis"


def check_torch() -> dict:
    """Check PyTorch and CUDA availability."""
    result = {
        "installed": False,
        "version": None,
        "cuda_available": False,
        "cuda_version": None,
        "gpu_name": None,
        "gpu_memory_total_mb": None,
        "gpu_memory_allocated_mb": None,
        "gpu_memory_reserved_mb": None,
    }
    try:
        import torch
        result["installed"] = True
        result["version"] = torch.__version__
        result["cuda_available"] = torch.cuda.is_available()
        if result["cuda_available"]:
            result["cuda_version"] = torch.version.cuda
            result["gpu_name"] = torch.cuda.get_device_name(0)
            result["gpu_memory_total_mb"] = round(torch.cuda.get_device_properties(0).total_mem / 1024 / 1024)
            result["gpu_memory_allocated_mb"] = round(torch.cuda.memory_allocated(0) / 1024 / 1024)
            result["gpu_memory_reserved_mb"] = round(torch.cuda.memory_reserved(0) / 1024 / 1024)
    except ImportError:
        pass
    return result


def check_nvidia_smi() -> dict:
    """Check nvidia-smi availability and output."""
    result = {"available": False, "output": None, "gpus": []}
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi is None:
        return result
    try:
        proc = subprocess.run(
            [nvidia_smi, "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode == 0:
            result["available"] = True
            result["output"] = proc.stdout.strip()
            for line in proc.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 6:
                    result["gpus"].append({
                        "name": parts[0],
                        "memory_total_mb": int(parts[1]),
                        "memory_used_mb": int(parts[2]),
                        "memory_free_mb": int(parts[3]),
                        "temperature_c": int(parts[4]),
                        "utilization_pct": int(parts[5]),
                    })
    except Exception as e:
        result["error"] = str(e)
    return result


def check_transformers() -> dict:
    result = {"installed": False, "version": None}
    try:
        import transformers
        result["installed"] = True
        result["version"] = transformers.__version__
    except ImportError:
        pass
    return result


def check_accelerate() -> dict:
    result = {"installed": False, "version": None}
    try:
        import accelerate
        result["installed"] = True
        result["version"] = accelerate.__version__
    except ImportError:
        pass
    return result


def check_mineru() -> dict:
    result = {"installed": False, "version": None, "backend": None}
    try:
        import mineru_vl_utils
        result["installed"] = True
        result["version"] = getattr(mineru_vl_utils, "__version__", "unknown")
    except ImportError:
        pass
    return result


def diagnose_cuda_unavailable(torch_info: dict) -> list[str]:
    """Determine why CUDA might be unavailable."""
    reasons = []
    if not torch_info["installed"]:
        reasons.append("PyTorch not installed")
        return reasons
    if not torch_info["cuda_available"]:
        # Check if it's a CPU-only build
        try:
            import torch
            if not hasattr(torch.version, "cuda") or torch.version.cuda is None:
                reasons.append("PyTorch installed but CUDA version is None (CPU-only build)")
            else:
                reasons.append(f"PyTorch has CUDA {torch.version.cuda} but torch.cuda.is_available() returned False")
                reasons.append("Possible causes: NVIDIA driver not installed, CUDA toolkit mismatch, no GPU detected")
        except Exception:
            reasons.append("Could not determine CUDA availability reason")
    return reasons


def generate_report() -> dict:
    """Run full device diagnosis."""
    print("=" * 60)
    print("M1 Device Diagnosis")
    print("=" * 60)

    # Python & OS
    py_version = sys.version
    os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
    print(f"  Python: {py_version}")
    print(f"  OS: {os_info}")

    # PyTorch / CUDA
    torch_info = check_torch()
    print(f"  torch: {'v' + torch_info['version'] if torch_info['installed'] else 'NOT INSTALLED'}")
    print(f"  CUDA available: {torch_info['cuda_available']}")
    if torch_info["cuda_available"]:
        print(f"  GPU: {torch_info['gpu_name']}")
        print(f"  GPU memory: {torch_info['gpu_memory_total_mb']} MB total, {torch_info['gpu_memory_allocated_mb']} MB allocated")

    # nvidia-smi
    nvidia_info = check_nvidia_smi()
    print(f"  nvidia-smi: {'available' if nvidia_info['available'] else 'NOT AVAILABLE'}")
    if nvidia_info["gpus"]:
        for g in nvidia_info["gpus"]:
            print(f"    {g['name']}: {g['memory_total_mb']}MB total, {g['memory_free_mb']}MB free, {g['temperature_c']}C, {g['utilization_pct']}% util")

    # Transformers / Accelerate
    tf_info = check_transformers()
    acc_info = check_accelerate()
    print(f"  transformers: {'v' + tf_info['version'] if tf_info['installed'] else 'NOT INSTALLED'}")
    print(f"  accelerate: {'v' + acc_info['version'] if acc_info['installed'] else 'NOT INSTALLED'}")

    # MinerU
    mineru_info = check_mineru()
    print(f"  mineru-vl-utils: {'v' + str(mineru_info['version']) if mineru_info['installed'] else 'NOT INSTALLED'}")

    # CUDA diagnosis
    cuda_issues = diagnose_cuda_unavailable(torch_info)
    if cuda_issues:
        print("\n  CUDA Issues:")
        for issue in cuda_issues:
            print(f"    - {issue}")

    # Build report
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "python_version": py_version,
        "os": os_info,
        "torch": torch_info,
        "nvidia_smi": nvidia_info,
        "transformers": tf_info,
        "accelerate": acc_info,
        "mineru_vl_utils": mineru_info,
        "cuda_issues": cuda_issues,
        "summary": {
            "gpu_available": torch_info["cuda_available"],
            "gpu_name": torch_info.get("gpu_name"),
            "gpu_memory_total_mb": torch_info.get("gpu_memory_total_mb"),
            "recommendation": _recommendation(torch_info, nvidia_info, tf_info, acc_info),
        },
    }
    return report


def _recommendation(torch_info: dict, nvidia_info: dict, tf_info: dict, acc_info: dict) -> str:
    if torch_info["cuda_available"]:
        gpu_mem = torch_info.get("gpu_memory_total_mb", 0)
        if gpu_mem >= 8000:
            return f"GPU available ({torch_info['gpu_name']}, {gpu_mem}MB). MinerU should use GPU. Use --device-mode=auto or cuda."
        else:
            return f"GPU available but only {gpu_mem}MB. MinerU may need to fall back to CPU for large models."
    else:
        if not torch_info["installed"]:
            return (
                "PyTorch not installed. Visit https://pytorch.org/get-started/locally/ "
                "to find the correct install command for your OS, Python version, and CUDA version. "
                "Example: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124"
            )
        if not tf_info["installed"]:
            return "transformers not installed. Install with: pip install transformers accelerate"
        return "CUDA not available. MinerU will run on CPU (very slow). Check NVIDIA driver and PyTorch CUDA build."


def write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# M1 Device Diagnosis Report",
        "",
        f"Generated: {report['timestamp']}",
        "",
        "## System",
        "",
        f"- Python: {report['python_version']}",
        f"- OS: {report['os']}",
        "",
        "## GPU / CUDA",
        "",
        f"- torch installed: {report['torch']['installed']}",
        f"- torch version: {report['torch']['version']}",
        f"- CUDA available: **{report['torch']['cuda_available']}**",
        f"- CUDA version: {report['torch']['cuda_version']}",
        f"- GPU name: {report['torch']['gpu_name']}",
        f"- GPU memory total: {report['torch']['gpu_memory_total_mb']} MB",
        f"- GPU memory allocated: {report['torch']['gpu_memory_allocated_mb']} MB",
        "",
        "## nvidia-smi",
        "",
        f"- Available: {report['nvidia_smi']['available']}",
    ]
    if report["nvidia_smi"]["gpus"]:
        for g in report["nvidia_smi"]["gpus"]:
            lines.append(f"- {g['name']}: {g['memory_total_mb']}MB total, {g['memory_free_mb']}MB free, {g['temperature_c']}C, {g['utilization_pct']}% util")
    lines += [
        "",
        "## Dependencies",
        "",
        f"- transformers: {'v' + report['transformers']['version'] if report['transformers']['installed'] else 'NOT INSTALLED'}",
        f"- accelerate: {'v' + report['accelerate']['version'] if report['accelerate']['installed'] else 'NOT INSTALLED'}",
        f"- mineru-vl-utils: {'v' + str(report['mineru_vl_utils']['version']) if report['mineru_vl_utils']['installed'] else 'NOT INSTALLED'}",
        "",
        "## CUDA Issues",
        "",
    ]
    if report["cuda_issues"]:
        for issue in report["cuda_issues"]:
            lines.append(f"- {issue}")
    else:
        lines.append("- None")
    lines += [
        "",
        "## Recommendation",
        "",
        report["summary"]["recommendation"],
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report = generate_report()

    (OUT / "device_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report, OUT / "device_report.md")

    print(f"\n  Reports written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
