# M1 Three-Pipeline Architecture — Live Eval Report (paper_1)

**Date**: 2026-06-08
**PDF**: reports/m1_parser_review/paper_1/source.pdf
**Eval script**: reports/m1_three_pipeline_architecture/eval_paper1.py

---

## Body Pipeline

| Question | Answer |
|----------|--------|
| body_selected_parser | `pymupdf` |
| selection_reason | `Good quality` |
| MarkItDown available | True |
| PyMuPDF available | True |

### Parser Scores

| pymupdf | overall=78.9 | sections=0 | formulas=0 | spacing=1.000 |
| markitdown_pdf | overall=39.4 | sections=0 | formulas=0 | spacing=0.928 |

---

## Formula Pipeline

| Question | Answer |
|----------|--------|
| FormulaSlot total count | 3 |
| Equation block count | 0 |
| TextInlineMath block count | 0 |
| Pages with formulas | [1, 2] |
| page_id exists | YES |
| bbox exists | YES |
| bbox count | 3 |
| crop success count | 3 |
| crop success rate | 3/3 |

### Origin Summary

| Origin | Count |
|--------|-------|
| parser_latex | 3 |

### First 5 Crop Paths

1. `formula_001_p1.png`
2. `formula_002_p2.png`
3. `formula_003_p2.png`

---

## Canonical Paper

| Question | Answer |
|----------|--------|
| canonical_paper.md exists | YES |
| formula slot comments present | YES (3 formula_id comments) |
| unresolved slots present | NO (0 unresolved) |

---

## Resolution Summary

| Metric | Value |
|--------|-------|
| parser_latex_count | 3 |
| ocr_latex_count | 0 |
| raw_formula_text_count | 0 |
| unresolved_formula_count | 0 |

---

## Remaining Work

- formula_overlays/ not yet implemented (placeholder only)
- OCR blocked (pix2tex model unavailable)
- Section inference for FormulaSlots not yet implemented
