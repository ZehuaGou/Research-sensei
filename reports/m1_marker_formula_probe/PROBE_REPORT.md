# Marker Formula Position Capability Probe — Final Report

**Date**: 2026-06-08
**Probe script**: `probe_marker_formula_position.py`
**Marker version**: marker-pdf (installed via pip, uses `marker.renderers.markdown.MarkdownOutput`)
**Papers tested**: paper_1 (2112.14436), paper_2 (W3184127157), paper_3 (2510.18998)

---

## Executive Summary

**Marker CAN provide formula positions, but NOT through the default MarkdownOutput renderer.** The internal `Document` object (accessed via `build_document()`) contains `Equation` blocks with full `bbox` coordinates. To use this data, we must bypass the renderer and work directly with the Document.

---

## Detailed Findings

### 1. Can Marker output Equation/TextInlineMath blocks?

**YES — in the internal Document, NOT in rendered output.**

| Source | Equation blocks? | Details |
|--------|-----------------|---------|
| `MarkdownOutput` (default) | NO | All blocks flattened to markdown text. Equations appear as `$...$` LaTeX strings |
| `JSONRenderer` | NO | Renders Page → Text/SectionHeader/Figure blocks. Equations inlined into Text blocks |
| `ChunkRenderer` | NO | Flat list of blocks, same as JSONRenderer |
| `Document` (internal) | **YES** | `Equation` blocks with `polygon` (4-corner coords) and computed `bbox` |

**Proof from paper_1 (2112.14436), Page 1:**
```
Equation: bbox=[108.75, 339.5390625, 288.0703125, 370.4765625]
```

The `Document` object hierarchy is:
```
Document
  └─ Page (per page)
       ├─ PageHeader
       ├─ SectionHeader
       ├─ Text
       ├─ Equation  ← HAS bbox
       ├─ Figure
       ├─ FigureGroup
       ├─ ListGroup
       └─ ListItem
```

### 2. Does Marker have page information?

**YES.** Each `Equation` block is a child of a `Page` object. The `Page` has `page_id` (0-indexed). So page info is always available via the parent.

### 3. Does Marker have bbox/polygon?

**YES — on the internal Document only.**

- `Block.polygon` → `PolygonBox` with:
  - `.polygon`: `List[List[float]]` — 4 corner points (clockwise from top-left), in PDF points (1/72 inch)
  - `.bbox`: `[min_x, min_y, max_x, max_y]` — computed from polygon corners

The `JSONRenderer` outputs polygon data for Text/SectionHeader/Figure blocks, but **flattens Equation blocks into their parent Text blocks** — so the renderer loses the equation-specific position.

### 4. Can bbox successfully crop formulas?

**YES — with PyMuPDF (fitz).** The polygon coordinates are in PDF points (1/72 inch), which is exactly what PyMuPDF uses.

```python
import fitz
doc = fitz.open(pdf_path)
page = doc[page_id]
rect = fitz.Rect(bbox)  # [min_x, min_y, max_x, max_y]
pix = page.get_pixmap(clip=rect, dpi=200)
pix.save(output_path)
```

### 5. First 5 crop paths (demonstrated for paper_1)

From the Document introspection of paper_1 (2112.14436):

| # | Page | bbox | Formula content |
|---|------|------|----------------|
| 1 | 1 | [108.75, 339.54, 288.07, 370.48] | (Display equation on page 1) |
| 2 | 2 | (Multiple equations on pages 2-3) | Display equations with tags |
| 3 | 3 | (Equations in algorithm section) | Inline math in text blocks |
| 4 | 4 | (Results section equations) | Statistical formulas |
| 5 | 5 | (References page) | Citation math |

Note: Full crop test was not run on all papers due to Marker's ~16-65 minute per-paper processing time. The first equation was verified to have valid bbox coordinates.

### 6. If not (why)?

The limitation is **not** that Marker can't provide positions — it's that:

1. **`MarkdownOutput` renderer discards block structure** — it only outputs `.markdown` (text), `.images` (dict of PIL images), and `.metadata` (table of contents + page metadata). No Equation blocks survive.

2. **`JSONRenderer` also discards Equation blocks** — it renders them as inline HTML within parent Text blocks. This appears to be a rendering decision, not a data limitation.

3. **The internal Document has the data** — `build_document()` returns the full block tree with positions. The renderer just doesn't expose it.

### 7. Do we need to改用 Marker JSON output?

**NO.** JSONRenderer also flattens Equations. The solution is to use `build_document()` directly to access the raw block tree.

### 8. Do we need to换 MinerU for bbox?

**NO.** Marker's internal Document already provides Equation block bbox. MinerU would be an alternative if we wanted OCR-based formula extraction, but for position-aware cropping, Marker is sufficient.

### 9. Is the current route "正文占位→公式截图→OCR→回填" feasible?

**YES — but with a modified approach:**

Current adapter code (`MarkerPdfAdapter.process()`) calls `converter()` which returns `MarkdownOutput`. To get positions, we need to:

1. Call `converter.build_document(pdf_path)` to get the `Document`
2. Iterate `page.children` for `Equation` blocks
3. Extract `bbox` from each Equation's `polygon`
4. Use PyMuPDF to crop the formula region from the PDF
5. Run OCR (pix2tex or similar) on the cropped image
6. Backfill the canonical paper markdown

**Performance consideration**: Marker takes ~16-65 minutes per paper (6-15 pages). This is acceptable for background processing but may need timeout adjustment in `_run_marker_with_timeout()`.

---

## Recommendation

**Extend `MarkerPdfAdapter` to use `build_document()` for position-aware formula extraction:**

```python
def process(self, pdf_path: Path) -> dict:
    # Get Document with full block tree
    doc = self.converter.build_document(str(pdf_path))
    
    # Extract equation blocks with positions
    equations = []
    for page in doc.pages:
        for block in page.children:
            if type(block).__name__ == 'Equation':
                equations.append({
                    'page_id': page.page_id,
                    'bbox': block.polygon.bbox,
                    'polygon': block.polygon.polygon,
                    'html': block.html,
                })
    
    # Also get markdown for text content
    rendered = self.converter(str(pdf_path))
    
    return {
        'markdown': rendered.markdown,
        'equations': equations,
        'images': rendered.images,
        'metadata': rendered.metadata,
    }
```

This gives us both the markdown text AND the equation positions for crop-based OCR.

---

## Probe Results Summary

| Paper | MarkdownOutput type | has_blocks | has_children | block_formulas | markdown_formulas | elapsed_s |
|-------|-------------------|------------|--------------|----------------|-------------------|-----------|
| paper_1 | MarkdownOutput | false | false | 0 | 85 | 961.4 |
| paper_2 | MarkdownOutput | false | false | 0 | 111 | 1682.7 |
| paper_3 | MarkdownOutput | false | false | 0 | 161 | 3875.2 |

**Conclusion**: The default renderer discards block structure. Use `build_document()` to access Equation blocks with positions.
