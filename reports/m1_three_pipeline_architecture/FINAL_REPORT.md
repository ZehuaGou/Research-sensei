# M1 Three-Pipeline Architecture — Final Report (Post-Fix)

**Date**: 2026-06-09
**Branch**: `codex/m1-canonical-parser-fixes`
**Commit**: `67c8968`
**Status**: COMPLETE

---

## Executive Summary

Four small fixes applied to existing M1 three-pipeline reports. No architecture changes. All 3 papers re-evaluated with fixes. pytest: 307 passed, 0 failed. All reports committed and pushed to GitHub.

---

## Four Fixes Applied

### Fix 1: REPORT.md canonical exists bug
**Problem**: REPORT.md said `canonical_paper.md exists = NO` but file existed.
**Root cause**: `generate_report()` was called BEFORE `run_canonical_normalizer()`.
**Fix**: Reordered steps — canonical normalizer is now STEP 6, report generation is STEP 7.

### Fix 2: FormulaSlot section/context enrichment
**Problem**: `nearby_text_before`, `nearby_text_after`, `section` were empty in formula_slots.json.
**Root cause**: Marker's `build_document()` only provides block structure, not text extraction.
**Fix**: Added `_enrich_with_pymupdf_context()` post-processing in `formula_detector.py` that uses PyMuPDF to extract text blocks near each formula's bbox and infers section from nearest heading above.

### Fix 3: FormulaMerger section placement
**Problem**: Formulas in canonical_paper.md were appended at end in a "Formula Blocks" section.
**Root cause**: `_render_markdown_with_slots()` collected all formulas into one bucket.
**Fix**: Modified `_render_markdown_with_slots()` in `material_normalizer.py` to group formulas by section and insert them under `### Formula Slots` subsections within each matching section.

### Fix 4: formula_overlays implementation
**Problem**: `formula_overlays/` was placeholder only (README.md).
**Root cause**: Not implemented.
**Fix**: Added `generate_formula_overlays()` in `eval_all_papers.py` that renders PDF pages at 2x resolution via PyMuPDF and draws red bbox rectangles with formula_id labels using PIL.

---

## Per-Paper Results

### paper_1 (2112.14436 — Anomaly Transformer)

| Metric | Value |
|--------|-------|
| REPORT canonical exists | **YES** (fixed) |
| FormulaSlot section non-empty | **3/3** |
| nearby_text_before non-empty | **3/3** |
| nearby_text_after non-empty | **3/3** |
| Formula comments in canonical | 3 |
| Formula comments with empty section | 0 |
| Formula overlays generated | 2 PNGs (overlay_page1.png, overlay_page2.png) |
| Crop success | 3/3 (100%) |
| Unresolved formulas | 0 |

### paper_2 (W3184127157 — Graph Structures Transformer)

| Metric | Value |
|--------|-------|
| REPORT canonical exists | **YES** (fixed) |
| FormulaSlot section non-empty | **9/16** |
| nearby_text_before non-empty | **16/16** |
| nearby_text_after non-empty | **15/16** |
| Formula comments in canonical | 16 |
| Formula comments with empty section | 7 |
| Formula overlays generated | 2 PNGs (overlay_page3.png, overlay_page4.png) |
| Crop success | 16/16 (100%) |
| Unresolved formulas | 0 |

Note: 7 formula comments have empty section because PyMuPDF heading detection didn't find a heading above those formulas on their respective pages. 7 formulas have non-standard section values (e.g., "A(2) = Global(X(2))") because the heading detector picked up formula text instead of a section heading.

### paper_3 (2510.18998 — Encode-then-Decompose)

| Metric | Value |
|--------|-------|
| REPORT canonical exists | **YES** (fixed) |
| FormulaSlot section non-empty | **18/18** |
| nearby_text_before non-empty | **18/18** |
| nearby_text_after non-empty | **18/18** |
| Formula comments in canonical | 18 |
| Formula comments with empty section | 0 |
| Formula overlays generated | 2 PNGs (overlay_page2.png, overlay_page3.png) |
| Crop success | 18/18 (100%) |
| Unresolved formulas | 0 |

---

## Aggregate Statistics

| Metric | paper_1 | paper_2 | paper_3 | Total |
|--------|---------|---------|---------|-------|
| REPORT canonical exists | YES | YES | YES | 3/3 |
| FormulaSlot total | 3 | 16 | 18 | 37 |
| section non-empty | 3/3 | 9/16 | 18/18 | 30/37 |
| nearby_before non-empty | 3/3 | 16/16 | 18/18 | 37/37 |
| nearby_after non-empty | 3/3 | 15/16 | 18/18 | 36/37 |
| Crop success | 3/3 | 16/16 | 18/18 | 37/37 |
| parser_latex resolved | 3 | 16 | 18 | 37 |
| Unresolved | 0 | 0 | 0 | 0 |
| Overlays generated | 2 | 2 | 2 | 6 |
| Formula comments in canonical | 3 | 16 | 18 | 37 |
| Comments with empty section | 0 | 7 | 0 | 7 |

---

## Code Changes

| File | Change |
|------|--------|
| `src/researchsensei/canonical/formula_detector.py` | Added `_enrich_with_pymupdf_context()` and `_normalize_section_name()` |
| `src/researchsensei/canonical/material_normalizer.py` | Modified `_render_markdown_with_slots()` for section-based formula insertion |
| `reports/m1_three_pipeline_architecture/eval_all_papers.py` | Reordered steps, added `generate_formula_overlays()`, updated REPORT generation |
| `reports/m1_three_pipeline_architecture/regen_paper2_paper3.py` | New script to regenerate paper_2/3 artifacts without re-running Marker |

---

## Test Results

```
307 passed, 3 skipped, 7 warnings in 191.65s (0:03:11)
0 failed
```

---

## Git

```
Commit: 67c8968
Branch: codex/m1-canonical-parser-fixes
Push: SUCCESS (e4781cf..67c8968)
Files: 19 changed, 2011 insertions, 1239 deletions
```

---

## Known Limitations

1. **OCR blocked**: pix2tex model download too slow; no OCR fallback available
2. **TextInlineMath not detected**: Marker's `build_document()` only captures Equation blocks, not inline math
3. **paper_2 section detection**: 7/16 formulas have empty section because PyMuPDF heading detection missed headings on those pages
4. **Section name pollution**: Some formula comments have formula text as section value (e.g., "A(2) = Global(X(2))") because `_normalize_section_name()` returns the raw heading text when no standard section matches
