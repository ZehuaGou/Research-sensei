# M1 Three-Pipeline Architecture — Eval Report (2110.02642)

**Date**: 2026-06-09
**PDF**: reports\m1_parser_review\paper_1\source.pdf
**Title**: Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy

---

## Body Pipeline

| Question | Answer |
|----------|--------|
| body_selected_parser | `pymupdf` |
| body parser score | `84.8` |
| selection_reason | `Good quality` |

### Parser Scores

| parser | overall_score | sections | formulas | spacing |
|--------|--------------|----------|----------|---------|
| pymupdf | 84.8 | 0 | 91 | 1.000 |
| markitdown_pdf | 47.9 | 0 | 96 | 1.000 |

---

## Formula Pipeline

| Question | Answer |
|----------|--------|
| FormulaSlot total count | 9 |
| Equation count | 9 |
| TextInlineMath count | 0 |
| Math count | 0 |
| Formula count | 0 |
| Unknown formula block count | 0 |
| page_id count | 5 |
| bbox count | 9 |
| crop success count | 9 |
| crop success rate | 9/9 |
| section non-empty count | 9/9 |
| nearby_text_before non-empty | 9/9 |
| nearby_text_after non-empty | 9/9 |

### Block Type Distribution

| block_type | count |
|------------|-------|
| Equation | 9 |

### Origin Summary

| Origin | Count |
|--------|-------|
| parser_latex | 9 |

### Crop Paths (first 10)

1. `formula_001_p3.png`
2. `formula_002_p3.png`
3. `formula_003_p4.png`
4. `formula_004_p4.png`
5. `formula_005_p4.png`
6. `formula_006_p5.png`
7. `formula_007_p14.png`
8. `formula_008_p15.png`
9. `formula_009_p15.png`

---

## Canonical Paper

| Question | Answer |
|----------|--------|
| canonical_paper.md exists | YES |
| canonical_paper.md size | 106835 bytes |
| formula slot comments present | YES |
| unresolved slots present | NO |
| formula comments with empty section | 40 |

---

## Resolution Summary

| Metric | Value |
|--------|-------|
| parser_latex_count | 9 |
| ocr_latex_count | 0 |
| raw_formula_text_count | 0 |
| unresolved_formula_count | 0 |

---

## Formula Overlays

| Metric | Value |
|--------|-------|
| overlays generated | 5 |
| overlay_dir | formula_overlays/ |

---

## OCR Status

| Question | Answer |
|----------|--------|
| OCR enabled | NO |
| OCR reason | pix2tex model download too slow; blocked by policy |

---

## Remaining Work

- OCR blocked (pix2tex model unavailable)
