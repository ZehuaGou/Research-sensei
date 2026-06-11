"""M1 Environment Audit — version matrix for GPU/CUDA/dependencies.

Outputs:
  reports/m1_environment_audit/environment_version_matrix.md
  reports/m1_environment_audit/environment_version_matrix.json
"""
from __future__ import annotations

import datetime
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "m1_environment_audit"


def _is_project_venv() -> bool:
    """Check if sys.executable is inside the project .venv."""
    exe = Path(sys.executable).resolve()
    venv = (ROOT / ".venv").resolve()
    try:
        exe.relative_to(venv)
        return True
    except ValueError:
        return False


def _get_project_version() -> str:
    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists():
        for line in pyproject.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("version"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "unknown"


def _get_git_commit() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=ROOT, timeout=5,
        )
        return proc.stdout.strip() if proc.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _get_nvidia_info() -> dict:
    import shutil
    result = {"available": False, "driver_version": None, "cuda_version": None, "gpus": []}
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi is None:
        return result
    try:
        proc = subprocess.run([nvidia_smi], capture_output=True, text=True, timeout=10)
        if proc.returncode != 0:
            return result
        result["available"] = True
        for line in proc.stdout.splitlines():
            if "CUDA Version" in line:
                # Extract CUDA version from "CUDA UMD Version: 13.3" or "CUDA Version: 13.3"
                for part in line.split():
                    try:
                        v = float(part.rstrip("."))
                        if v > 10:
                            result["cuda_version"] = part.rstrip(".")
                            break
                    except ValueError:
                        continue
            if "KMD Version" in line or "Driver" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "NVIDIA-SMI" and i + 1 < len(parts):
                        result["driver_version"] = parts[i + 1]
                        break

        # Query GPU details
        proc2 = subprocess.run(
            [nvidia_smi, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        if proc2.returncode == 0:
            for line in proc2.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    result["gpus"].append({
                        "name": parts[0],
                        "memory_total": parts[1],
                        "driver_version": parts[2],
                    })
    except Exception:
        pass
    return result


def audit() -> dict:
    """Generate full environment version matrix."""
    nvidia_info = _get_nvidia_info()

    torch_info = {"installed": False, "version": None, "cuda_version": None, "cuda_available": False}
    gpu_name = None
    gpu_memory_mb = None
    try:
        import torch
        torch_info["installed"] = True
        torch_info["version"] = torch.__version__
        torch_info["cuda_version"] = getattr(torch.version, "cuda", None)
        torch_info["cuda_available"] = torch.cuda.is_available()
        if torch_info["cuda_available"]:
            gpu_name = torch.cuda.get_device_name(0)
            _props = torch.cuda.get_device_properties(0)
            gpu_memory_mb = round(getattr(_props, "total_memory", getattr(_props, "total_mem", 0)) / 1024 / 1024)
    except ImportError:
        pass

    transformers_info = {"installed": False, "version": None}
    try:
        import transformers
        transformers_info = {"installed": True, "version": transformers.__version__}
    except ImportError:
        pass

    accelerate_info = {"installed": False, "version": None}
    try:
        import accelerate
        accelerate_info = {"installed": True, "version": accelerate.__version__}
    except ImportError:
        pass

    mineru_info = {"installed": False, "version": None}
    try:
        import mineru_vl_utils
        mineru_info = {"installed": True, "version": getattr(mineru_vl_utils, "__version__", "unknown")}
    except ImportError:
        pass

    pymupdf_info = {"installed": False, "version": None}
    try:
        import fitz
        pymupdf_info = {"installed": True, "version": fitz.version[0] if hasattr(fitz, "version") else "unknown"}
    except ImportError:
        pass

    pillow_info = {"installed": False, "version": None}
    try:
        from PIL import __version__ as pillow_ver
        pillow_info = {"installed": True, "version": pillow_ver}
    except ImportError:
        pass

    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python_executable": str(Path(sys.executable).resolve()),
        "python_version": sys.version,
        "is_project_venv": _is_project_venv(),
        "virtualenv_path": str(Path(sys.executable).resolve().parents[1]),
        "project_version": _get_project_version(),
        "git_commit": _get_git_commit(),
        "torch": torch_info,
        "gpu_name": gpu_name,
        "gpu_memory_mb": gpu_memory_mb,
        "nvidia": nvidia_info,
        "transformers": transformers_info,
        "accelerate": accelerate_info,
        "mineru_vl_utils": mineru_info,
        "pymupdf": pymupdf_info,
        "pillow": pillow_info,
        "m1_parser_model": "opendatalab/MinerU2.5-Pro-2604-1.2B",
        "m1_primary_parser": "mineru25pro",
        "gpu_status_summary": {
            "hardware_gpu_detected": nvidia_info["available"] and len(nvidia_info["gpus"]) > 0,
            "torch_cuda_available": torch_info["cuda_available"],
            "is_cpu_only_build": torch_info["installed"] and torch_info["cuda_version"] is None,
            "verdict": _gpu_verdict(torch_info, nvidia_info),
        },
    }
    return report


def _gpu_verdict(torch_info: dict, nvidia_info: dict) -> str:
    if not torch_info["installed"]:
        return "FAIL: PyTorch not installed"
    if torch_info["cuda_version"] is None:
        return "FAIL: PyTorch is CPU-only build (torch.version.cuda is None)"
    if not torch_info["cuda_available"]:
        if nvidia_info["available"]:
            return "FAIL: GPU detected by nvidia-smi but torch.cuda.is_available() is False"
        return "FAIL: No GPU detected and CUDA not available"
    return "PASS: GPU available and PyTorch CUDA enabled"


def write_markdown(report: dict, path: Path) -> None:
    s = report["gpu_status_summary"]
    lines = [
        "# M1 Environment Version Matrix",
        "",
        f"Generated: {report['timestamp']}",
        "",
        "## GPU Status Verdict",
        "",
        f"**{s['verdict']}**",
        "",
        "| Layer | Status |",
        "|-------|--------|",
        f"| Hardware GPU (nvidia-smi) | {'YES' if s['hardware_gpu_detected'] else 'NO'} |",
        f"| PyTorch CUDA available | {'YES' if s['torch_cuda_available'] else 'NO'} |",
        f"| CPU-only build | {'YES' if s['is_cpu_only_build'] else 'NO'} |",
        "",
        "## System",
        "",
        f"- OS: {report['os']}",
        f"- Python: {report['python_version']}",
        f"- Executable: `{report['python_executable']}`",
        f"- Is project .venv: **{report['is_project_venv']}**",
        f"- Virtualenv: `{report['virtualenv_path']}`",
        f"- Project version: {report['project_version']}",
        f"- Git commit: {report['git_commit']}",
        "",
        "## PyTorch / CUDA",
        "",
        f"- torch: {report['torch']['version']}",
        f"- torch.version.cuda: {report['torch']['cuda_version']}",
        f"- torch.cuda.is_available(): **{report['torch']['cuda_available']}**",
        f"- GPU name: {report['gpu_name']}",
        f"- GPU memory: {report['gpu_memory_mb']} MB",
        "",
        "## NVIDIA",
        "",
        f"- nvidia-smi available: {report['nvidia']['available']}",
        f"- Driver: {report['nvidia']['driver_version']}",
        f"- CUDA (UMD): {report['nvidia']['cuda_version']}",
    ]
    for g in report["nvidia"]["gpus"]:
        lines.append(f"- GPU: {g['name']} ({g['memory_total']})")
    lines += [
        "",
        "## Dependencies",
        "",
        f"- transformers: {report['transformers']['version']}",
        f"- accelerate: {report['accelerate']['version']}",
        f"- mineru-vl-utils: {report['mineru_vl_utils']['version']}",
        f"- PyMuPDF: {report['pymupdf']['version']}",
        f"- Pillow: {report['pillow']['version']}",
        "",
        "## M1 Parser",
        "",
        f"- Model: {report['m1_parser_model']}",
        f"- Primary parser: {report['m1_primary_parser']}",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report = audit()

    (OUT / "environment_version_matrix.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_markdown(report, OUT / "environment_version_matrix.md")

    print("=" * 60)
    print("M1 Environment Audit")
    print("=" * 60)
    print(f"  Python: {report['python_version']}")
    print(f"  .venv: {report['is_project_venv']}")
    print(f"  torch: {report['torch']['version']}")
    print(f"  torch.version.cuda: {report['torch']['cuda_version']}")
    print(f"  torch.cuda.is_available(): {report['torch']['cuda_available']}")
    print(f"  GPU: {report['gpu_name']}")
    print(f"  Verdict: {report['gpu_status_summary']['verdict']}")
    print(f"  Reports: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
