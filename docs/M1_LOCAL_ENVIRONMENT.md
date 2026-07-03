# M1 Local Environment & GPU Setup

## Overview

The M1 canonical pipeline uses MinerU2.5-Pro for PDF parsing. GPU acceleration is **required** for acceptable performance — CPU-only runs take ~5-15 minutes per page, making the system impractical.

**Standard**: `nvidia-smi` seeing a GPU does NOT mean GPU is working. Only `torch.cuda.is_available() == True` counts.

## Project Environment

This project uses a **project-local `.venv`** virtual environment. All dependencies must be installed there.

```bash
# Activate .venv (Windows)
.\.venv\Scripts\activate

# Verify you're in .venv
python -c "import sys; print(sys.executable)"
# Should show: <project-root>\.venv\Scripts\python.exe

# Verify pip points to .venv
python -m pip --version
# Should show: ...\.venv\lib\site-packages\pip
```

**Never install packages into global Python or Anaconda base.**

## Checking if PyTorch Uses GPU

```bash
# Quick check
python -c "import torch; print('cuda:', torch.version.cuda); print('available:', torch.cuda.is_available())"

# Expected output for working GPU:
# cuda: 12.6          (or similar, NOT None)
# available: True     (NOT False)
```

### Red Flags

| Symptom | Meaning |
|---------|---------|
| `torch.version.cuda is None` | CPU-only PyTorch build |
| `torch.__version__` contains `+cpu` | CPU-only PyTorch build |
| `torch.cuda.is_available() == False` | CUDA not usable |

## Installing CUDA-enabled PyTorch

1. **Uninstall existing CPU-only PyTorch**:
   ```bash
   .\.venv\Scripts\python.exe -m pip uninstall -y torch torchvision torchaudio
   ```

2. **Go to [PyTorch Start Locally](https://pytorch.org/get-started/locally/)** and select:
   - OS: Windows
   - Package: Pip
   - Language: Python
   - Compute Platform: your CUDA version (check `nvidia-smi` output)

3. **Run the generated command**, for example:
   ```bash
   .\.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
   ```

4. **Verify**:
   ```bash
   .\.venv\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO CUDA')"
   ```

**Do not hardcode a specific CUDA version** — use the PyTorch selector to find the right one for your system.

## Running Device Diagnosis

```bash
.\.venv\Scripts\python.exe scripts\m1_device_diagnosis.py
```

Outputs: `reports/m1_device_diagnosis/device_report.md`

The report shows **3-layer GPU status**:

| Layer | What it checks | What "working" means |
|-------|---------------|---------------------|
| 1. Hardware GPU | nvidia-smi detects a GPU | GPU physically present |
| 2. PyTorch CUDA | `torch.cuda.is_available()` | PyTorch can use the GPU |
| 3. Not CPU-only | `torch.version.cuda` is not None | Correct PyTorch build installed |

## Running MinerU GPU Check

```bash
.\.venv\Scripts\python.exe scripts\run_m1_mineru_gpu_check.py
```

Outputs: `reports/m1_gpu_check/gpu_check_report.md`

**Pass criteria**:
- `device_mode_actual == "cuda"` (not "cpu")
- `fallback_reason` is empty
- `success == True`

## Running Environment Audit

```bash
.\.venv\Scripts\python.exe scripts\m1_environment_audit.py
```

Outputs: `reports/m1_environment_audit/environment_version_matrix.md`

## Common Issues

### "PyTorch installed but CUDA version is None (CPU-only build)"

You installed the CPU-only PyTorch wheel. Uninstall and reinstall using the PyTorch selector (see above).

### "GPU detected by nvidia-smi but torch.cuda.is_available() is False"

Possible causes:
- PyTorch is CPU-only build (most common)
- NVIDIA driver too old for the PyTorch CUDA version
- CUDA toolkit not installed or mismatched

### "GPU available but model will run on CPU (memory too small)"

MinerU2.5-Pro needs ~6GB GPU memory. If your GPU has less, it falls back to CPU.
