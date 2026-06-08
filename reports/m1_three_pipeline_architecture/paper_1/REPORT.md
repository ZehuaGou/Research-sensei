# M1 Three-Pipeline Architecture — Eval Report (2112.14436)

**Date**: 2026-06-08
**PDF**: reports\m1_parser_review\paper_1\source.pdf
**Title**: Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy

---

## Body Pipeline

| Question | Answer |
|----------|--------|
| body_selected_parser | `pymupdf` |
| body parser score | `78.9` |
| selection_reason | `Good quality` |

### Parser Scores

| parser | overall_score | sections | formulas | spacing |
|--------|--------------|----------|----------|---------|
| pymupdf | 78.9 | 0 | 0 | 1.000 |
| markitdown_pdf | 39.4 | 0 | 0 | 0.928 |

---

## Formula Pipeline

| Question | Answer |
|----------|--------|
| FormulaSlot total count | 3 |
| Equation count | 3 |
| TextInlineMath count | 0 |
| Math count | 0 |
| Formula count | 0 |
| Unknown formula block count | 0 |
| page_id count | 2 |
| bbox count | 3 |
| crop success count | 3 |
| crop success rate | 3/3 |

### Block Type Distribution

| block_type | count |
|------------|-------|
| Equation | 3 |

### Origin Summary

| Origin | Count |
|--------|-------|
| parser_latex | 3 |

### Crop Paths (first 10)

1. `formula_001_p1.png`
2. `formula_002_p2.png`
3. `formula_003_p2.png`

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
| parser_latex_count | 3 |
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
