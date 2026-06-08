# M1 Three-Pipeline Architecture — Eval Report (2510.18998)

**Date**: 2026-06-08
**PDF**: reports\m1_parser_review\paper_3\source.pdf
**Title**: An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection

---

## Body Pipeline

| Question | Answer |
|----------|--------|
| body_selected_parser | `pymupdf` |
| body parser score | `87.6` |
| selection_reason | `Good quality` |

### Parser Scores

| parser | overall_score | sections | formulas | spacing |
|--------|--------------|----------|----------|---------|
| pymupdf | 87.6 | 0 | 10 | 1.000 |
| markitdown_pdf | 43.5 | 0 | 2 | 1.000 |

---

## Formula Pipeline

| Question | Answer |
|----------|--------|
| FormulaSlot total count | 18 |
| Equation count | 18 |
| TextInlineMath count | 0 |
| Math count | 0 |
| Formula count | 0 |
| Unknown formula block count | 0 |
| page_id count | 5 |
| bbox count | 18 |
| crop success count | 18 |
| crop success rate | 18/18 |

### Block Type Distribution

| block_type | count |
|------------|-------|
| Equation | 18 |

### Origin Summary

| Origin | Count |
|--------|-------|
| parser_latex | 18 |

### Crop Paths (first 10)

1. `formula_001_p2.png`
2. `formula_002_p2.png`
3. `formula_003_p2.png`
4. `formula_004_p3.png`
5. `formula_005_p3.png`
6. `formula_006_p3.png`
7. `formula_007_p3.png`
8. `formula_008_p3.png`
9. `formula_009_p3.png`
10. `formula_010_p4.png`

---

## Canonical Paper

| Question | Answer |
|----------|--------|
| canonical_paper.md exists | NO |
| formula slot comments present | NO |
| unresolved slots present | NO |

---

## Resolution Summary

| Metric | Value |
|--------|-------|
| parser_latex_count | 18 |
| ocr_latex_count | 0 |
| raw_formula_text_count | 0 |
| unresolved_formula_count | 0 |

---

## OCR Status

| Question | Answer |
|----------|--------|
| OCR enabled | NO |
| OCR reason | pix2tex model download too slow; blocked by policy |

---

## Remaining Work

- formula_overlays/ not yet implemented (placeholder only)
- OCR blocked (pix2tex model unavailable)
- Section inference for FormulaSlots not yet implemented
