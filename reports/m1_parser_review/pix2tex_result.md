# pix2tex OCR Test Result

## Test Info
- **Input image**: `reports/m1_parser_review/paper_1/formula_page_1.png`
- **Crop region**: (100, 200, 500, 350) - top portion of page 1
- **pix2tex version**: 0.0.31
- **Checkpoint**: v0.0.1 (weights.pth, 102MB)

## Model Loading
- **Load time**: 0.8s
- **Status**: SUCCESS
- **Device**: CPU

## OCR Result
- **OCR time**: 3.9s
- **Output LaTeX**:
```latex
\qquad{\frac{\mathrm{l}\operatorname{vnonte}\mathbf{\hat{e}}\cdot\operatorname{antrosile}\ n o}{\operatorname{srancois}\operatorname{xavie}}}
```

## Analysis
- **LaTeX structure**: Yes, produces valid LaTeX commands (`\frac`, `\mathrm`, `\mathbf`, `\hat`)
- **Content accuracy**: Low - the OCR output does not match the actual formula content. The model is recognizing formula structure but not the actual text/symbols correctly.
- **Formula type**: Fraction with numerator and denominator
- **Issues**: Character recognition is poor - "l", "vnonte", "antrosile", "srancois", "xavie" are not real mathematical terms

## Verdict
- **Formula structure preservation**: GOOD - LaTeX structure is preserved
- **Content accuracy**: POOR - characters are not correctly recognized
- **Recommendation**: pix2tex can detect formula structure but needs better training data or fine-tuning for academic paper formulas. The current v0.0.1 checkpoint is trained on a general dataset and may not work well for specialized academic formulas.

## pix2tex Version Fix Summary
- **Root cause**: pix2tex 0.1.4 (latest) uses a different model architecture than the v0.0.1 checkpoint
- **Fix**: Install pix2tex 0.0.31 with `x-transformers==0.15.0` and `timm==0.5.4`
- **Required packages**:
  - pix2tex==0.0.31
  - x-transformers==0.15.0
  - timm==0.5.4
- **Checkpoint**: v0.0.1 from https://github.com/lukas-blecher/LaTeX-OCR/releases/download/v0.0.1/weights.pth

## Recommendation for M1
- **Current status**: pix2tex can be loaded and produces LaTeX output
- **Quality**: Formula structure is preserved but content accuracy is low
- **Use case**: On-demand formula OCR for PDF-parsed formulas (when MarkItDown/PyMuPDF don't preserve LaTeX)
- **Limitation**: Not suitable for high-fidelity formula extraction without fine-tuning
