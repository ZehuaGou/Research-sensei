# pix2tex Model Installation Guide

## pix2tex Version

- **Package**: pix2tex 0.1.4
- **Package path**: `C:\self\anaconda3\Lib\site-packages\pix2tex\`
- **License**: MIT

## Model Files Required

| File | Size | Description |
|------|------|-------------|
| `weights.pth` | 97.4 MB | Main model weights |
| `image_resizer.pth` | ~1 MB | Image resizer weights (optional) |

## Download URLs

- **weights.pth**: https://github.com/lukas-blecher/LaTeX-OCR/releases/download/v0.0.1/weights.pth
- **image_resizer.pth**: https://github.com/lukas-blecher/LaTeX-OCR/releases/download/v0.0.1/image_resizer.pth

## Target Directory

```
C:\self\anaconda3\Lib\site-packages\pix2tex\model\checkpoints\
```

## Manual Download Steps

### Option 1: Browser download
1. Open https://github.com/lukas-blecher/LaTeX-OCR/releases/tag/v0.0.1
2. Download `weights.pth` (97.4 MB)
3. Download `image_resizer.pth` (~1 MB)
4. Copy both files to `C:\self\anaconda3\Lib\site-packages\pix2tex\model\checkpoints\`

### Option 2: PowerShell with proxy
```powershell
$env:HTTP_PROXY = "http://127.0.0.1:7890"
$env:HTTPS_PROXY = "http://127.0.0.1:7890"

$checkpointDir = "C:\self\anaconda3\Lib\site-packages\pix2tex\model\checkpoints"

# Download weights.pth
Invoke-WebRequest -Uri "https://github.com/lukas-blecher/LaTeX-OCR/releases/download/v0.0.1/weights.pth" -OutFile "$checkpointDir\weights.pth" -Proxy "http://127.0.0.1:7890"

# Download image_resizer.pth
Invoke-WebRequest -Uri "https://github.com/lukas-blecher/LaTeX-OCR/releases/download/v0.0.1/image_resizer.pth" -OutFile "$checkpointDir\image_resizer.pth" -Proxy "http://127.0.0.1:7890"
```

### Option 3: Python with proxy
```python
import os
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

from pix2tex.model.checkpoints.get_latest_checkpoint import download_checkpoints
download_checkpoints()
```

## Verification

After downloading, verify:

```python
import os
checkpoint_dir = r"C:\self\anaconda3\Lib\site-packages\pix2tex\model\checkpoints"
print("weights.pth exists:", os.path.exists(os.path.join(checkpoint_dir, "weights.pth")))
print("weights.pth size:", os.path.getsize(os.path.join(checkpoint_dir, "weights.pth")), "bytes")

# Test model loading
from pix2tex.cli import LatexOCR
model = LatexOCR()
print("Model loaded successfully!")
```

## Current Status

- pix2tex package: INSTALLED
- weights.pth: NOT DOWNLOADED (download was attempted but too slow at ~5KB/s through proxy)
- image_resizer.pth: NOT DOWNLOADED
- Model loading: BLOCKED (requires weights.pth)

## Why Download is Slow

The download goes through GitHub releases, which may be slow through the Clash proxy. Options:
1. Download directly via browser (may be faster)
2. Use a download manager with resume support
3. Wait for better network conditions
4. Use a VPN or different proxy

## After Model is Downloaded

Once weights.pth is in place, pix2tex can be used for formula OCR:
- Input: PIL Image of a formula
- Output: LaTeX string
- GPU: Optional (works on CPU, faster with GPU)
- Use case: On-demand formula OCR for PDF-parsed formulas
