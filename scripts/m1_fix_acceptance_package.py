"""Fix M1 acceptance package: search consistency, crop padding, groups, nearby text.

Does NOT re-run MinerU parse. Reads existing artifacts and fixes:
1. candidate_papers.json consistency with metadata_candidates.json
2. Crop padding (increase from ~4px to 12px)
3. Equation group identification for multi-line formulas
4. nearby_text_before/after from document_blocks.json
5. Re-generate crops, overlays, visual audit, reports, zip
"""
from __future__ import annotations

import datetime
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fix_acceptance_package(accept_dir: Path) -> None:
    """Fix all issues in the acceptance package."""
    accept_dir = Path(accept_dir)
    print("=" * 60)
    print("M1 Acceptance Package Fix")
    print("=" * 60)

    # Load existing artifacts
    slots = json.loads((accept_dir / "formula_slots.json").read_text(encoding="utf-8"))
    blocks = json.loads((accept_dir / "document_blocks.json").read_text(encoding="utf-8"))
    meta = json.loads((accept_dir / "paper_metadata.json").read_text(encoding="utf-8"))
    perf = json.loads((accept_dir / "performance_report.json").read_text(encoding="utf-8"))

    print(f"Loaded: {len(slots)} slots, {len(blocks)} blocks")

    # ── Fix 1: candidate_papers.json consistency ──
    print("\n[1/7] Fixing candidate_papers.json...")
    _fix_candidate_papers(accept_dir, meta)

    # ── Fix 2: Add nearby_text from document_blocks ──
    print("\n[2/7] Adding nearby_text from document_blocks...")
    _add_nearby_text(slots, blocks)

    # ── Fix 3: Add equation group info ──
    print("\n[3/7] Adding equation group info...")
    _add_equation_groups(slots, blocks)

    # ── Fix 4: Re-generate crops with more padding ──
    print("\n[4/7] Re-generating crops with increased padding...")
    _regenerate_crops(accept_dir, slots)

    # ── Fix 5: Re-generate overlays ──
    print("\n[5/7] Re-generating overlays...")
    _regenerate_overlays(accept_dir, slots)

    # ── Fix 6: Save updated formula_slots.json ──
    print("\n[6/7] Saving updated formula_slots.json...")
    (accept_dir / "formula_slots.json").write_text(
        json.dumps(slots, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    # Also update formula_slots.md
    _write_formula_slots_md(accept_dir, slots)

    # ── Fix 7: Re-generate all reports and zip ──
    print("\n[7/7] Re-generating reports and zip...")
    _regenerate_all_reports(accept_dir, slots, blocks, meta, perf)

    print("\n" + "=" * 60)
    print("DONE. All fixes applied.")
    print("=" * 60)


def _fix_candidate_papers(accept_dir: Path, meta: dict) -> None:
    """Replace candidate_papers.json with metadata_candidates.json data."""
    mc_path = accept_dir / "metadata_candidates.json"
    if not mc_path.exists():
        print("  WARNING: metadata_candidates.json not found, skipping")
        return

    mc = json.loads(mc_path.read_text(encoding="utf-8"))
    # Write as candidate_papers.json (same data, consistent name)
    (accept_dir / "candidate_papers.json").write_text(
        json.dumps(mc, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    selected = [c for c in mc if c.get("selected_candidate")]
    print(f"  Wrote {len(mc)} candidates, selected: {[c['arxiv_id'] for c in selected]}")


def _add_nearby_text(slots: list[dict], blocks: list[dict]) -> None:
    """Add nearby_text_before/after to each formula slot from adjacent blocks."""
    # Group blocks by page and sort by reading_order
    blocks_by_page: dict[int, list[dict]] = {}
    for b in blocks:
        page = b.get("page", 0)
        blocks_by_page.setdefault(page, []).append(b)
    for page in blocks_by_page:
        blocks_by_page[page].sort(key=lambda b: b.get("reading_order", 999))

    THRESHOLD = 0.02  # 2% of page height for normalized bboxes

    for slot in slots:
        page = slot.get("page", 0)
        slot_bbox = slot.get("bbox", [])
        if not slot_bbox or page not in blocks_by_page:
            slot["nearby_text_before"] = ""
            slot["nearby_text_after"] = ""
            slot["nearby_block_ids"] = []
            continue

        # Find blocks on same page that are above/below the formula
        page_blocks = blocks_by_page[page]
        formula_top = slot_bbox[1] if len(slot_bbox) >= 4 else 0
        formula_bottom = slot_bbox[3] if len(slot_bbox) >= 4 else 0

        nearby_before = []
        nearby_after = []
        nearby_ids = []

        for b in page_blocks:
            if b.get("block_type") == "formula":
                continue  # Skip other formulas
            b_bbox = b.get("bbox", [])
            if len(b_bbox) < 4:
                continue
            b_top = b_bbox[1]
            b_bottom = b_bbox[3]
            b_text = (b.get("text") or "").strip()
            if not b_text:
                continue

            # Block is above the formula (with threshold for normalized coords)
            if b_bottom <= formula_top + THRESHOLD:
                nearby_before.append(b_text[:200])
                nearby_ids.append(b.get("block_id", ""))
            # Block is below the formula
            elif b_top >= formula_bottom - THRESHOLD:
                nearby_after.append(b_text[:200])
                nearby_ids.append(b.get("block_id", ""))
                break  # Only take the first block below

        slot["nearby_text_before"] = " ".join(nearby_before[-2:])[-300:]  # Last 2 blocks, max 300 chars
        slot["nearby_text_after"] = " ".join(nearby_after[:1])[:300]  # First block below, max 300 chars
        slot["nearby_block_ids"] = nearby_ids[:4]

    filled = sum(1 for s in slots if s.get("nearby_text_before") or s.get("nearby_text_after"))
    print(f"  Added nearby_text to {filled}/{len(slots)} formulas")


def _add_equation_groups(slots: list[dict], blocks: list[dict]) -> None:
    """Identify multi-line equation groups on the same page."""
    # Group formula slots by page
    slots_by_page: dict[int, list[dict]] = {}
    for s in slots:
        page = s.get("page", 0)
        slots_by_page.setdefault(page, []).append(s)

    group_counter = 0
    for page, page_slots in slots_by_page.items():
        if len(page_slots) < 2:
            for s in page_slots:
                s["equation_group_id"] = ""
                s["group_order"] = 0
                s["is_multiline_group_member"] = False
            continue

        # Sort by bbox top coordinate
        page_slots.sort(key=lambda s: s.get("bbox", [0, 0, 0, 0])[1] if len(s.get("bbox", [])) >= 2 else 0)

        # Find clusters of formulas that are close together vertically
        clusters: list[list[dict]] = []
        current_cluster = [page_slots[0]]

        for i in range(1, len(page_slots)):
            prev_bottom = current_cluster[-1].get("bbox", [0, 0, 0, 0])[3] if len(current_cluster[-1].get("bbox", [])) >= 4 else 0
            curr_top = page_slots[i].get("bbox", [0, 0, 0, 0])[1] if len(page_slots[i].get("bbox", [])) >= 2 else 0

            # If formulas are within 30px of each other, they're likely part of a group
            if curr_top - prev_bottom < 30:
                current_cluster.append(page_slots[i])
            else:
                if len(current_cluster) > 1:
                    clusters.append(current_cluster)
                current_cluster = [page_slots[i]]

        if len(current_cluster) > 1:
            clusters.append(current_cluster)

        # Assign group IDs
        for cluster in clusters:
            group_counter += 1
            group_id = f"group_p{page}_{group_counter}"
            for order, s in enumerate(cluster, 1):
                s["equation_group_id"] = group_id
                s["group_order"] = order
                s["is_multiline_group_member"] = True

        # Non-grouped formulas
        for s in page_slots:
            if "equation_group_id" not in s:
                s["equation_group_id"] = ""
                s["group_order"] = 0
                s["is_multiline_group_member"] = False

    groups = sum(1 for s in slots if s.get("is_multiline_group_member"))
    print(f"  Identified {groups} formulas in multi-line groups")


def _regenerate_crops(accept_dir: Path, slots: list[dict]) -> None:
    """Re-generate crop images with increased padding."""
    try:
        import fitz
    except ImportError:
        print("  WARNING: PyMuPDF not installed, skipping crop regeneration")
        return

    source_pdf = accept_dir / "source.pdf"
    if not source_pdf.exists():
        print("  WARNING: source.pdf not found, skipping crop regeneration")
        return

    crop_dir = accept_dir / "formula_crops"
    crop_dir.mkdir(exist_ok=True)

    # Padding in points (not pixels) - bboxes are normalized 0-1
    # We need to convert: padding_points = padding_pixels / dpi * 72
    # But since bboxes are normalized, we work in page coordinates
    PADDING_FRAC = 0.01  # 1% of page height as padding

    doc = fitz.open(str(source_pdf))
    try:
        for slot in slots:
            formula_id = slot.get("formula_id", "unknown")
            page_index = slot.get("page", 1) - 1
            if page_index < 0 or page_index >= len(doc):
                continue

            bbox = slot.get("bbox", [])
            if len(bbox) < 4:
                continue

            # Store original bbox
            slot["original_bbox"] = list(bbox)

            # Convert normalized bbox to page coordinates
            page = doc[page_index]
            pw, ph = page.rect.width, page.rect.height
            x0 = bbox[0] * pw
            y0 = bbox[1] * ph
            x1 = bbox[2] * pw
            y1 = bbox[3] * ph

            # Apply padding in page coordinates
            pad_x = PADDING_FRAC * pw
            pad_y = PADDING_FRAC * ph
            padded_x0 = max(0, x0 - pad_x)
            padded_y0 = max(0, y0 - pad_y)
            padded_x1 = min(pw, x1 + pad_x)
            padded_y1 = min(ph, y1 + pad_y)

            # Store crop_bbox in page coordinates (not normalized)
            slot["crop_bbox"] = [round(padded_x0, 1), round(padded_y0, 1), round(padded_x1, 1), round(padded_y1, 1)]
            slot["crop_padding_applied"] = f"{PADDING_FRAC*100:.0f}%"

            # Generate crop
            rect = fitz.Rect(padded_x0, padded_y0, padded_x1, padded_y1)
            crop_path = crop_dir / f"{formula_id}_p{page_index + 1}.png"
            pix = page.get_pixmap(clip=rect, dpi=200, alpha=False)
            pix.save(str(crop_path))
            slot["crop_path"] = str(crop_path.relative_to(accept_dir)).replace("\\", "/")

            # Detect edge contamination
            _detect_edge_contamination(slot, crop_path)
    finally:
        doc.close()

    print(f"  Re-generated {len(slots)} crops with {PADDING_FRAC*100:.0f}% padding")


def _detect_edge_contamination(slot: dict, crop_path: Path) -> None:
    """Check if crop has ink touching edges (potential contamination)."""
    try:
        from PIL import Image
        import numpy as np

        img = Image.open(str(crop_path)).convert("L")
        arr = np.array(img)

        # Check top and bottom 3 rows for dark pixels (ink)
        threshold = 200  # pixels darker than this are "ink"
        h, w = arr.shape

        top_ink = np.sum(arr[:3, :] < threshold) / (3 * w)
        bottom_ink = np.sum(arr[-3:, :] < threshold) / (3 * w)

        risk_flags = slot.get("risk_flags", [])
        if top_ink > 0.05:
            risk_flags.append("CROP_TOP_EDGE_CONTAMINATION")
        if bottom_ink > 0.05:
            risk_flags.append("CROP_BOTTOM_EDGE_CONTAMINATION")
        slot["risk_flags"] = risk_flags
        slot["edge_ink_ratio_top"] = round(top_ink, 4)
        slot["edge_ink_ratio_bottom"] = round(bottom_ink, 4)
    except Exception:
        pass


def _regenerate_overlays(accept_dir: Path, slots: list[dict]) -> None:
    """Re-generate overlay images showing both original and padded bbox."""
    try:
        import fitz
        from PIL import Image, ImageDraw
    except ImportError:
        print("  WARNING: fitz/PIL not installed, skipping overlay regeneration")
        return

    source_pdf = accept_dir / "source.pdf"
    if not source_pdf.exists():
        return

    overlay_dir = accept_dir / "formula_overlays"
    overlay_dir.mkdir(exist_ok=True)

    doc = fitz.open(str(source_pdf))
    try:
        for slot in slots:
            formula_id = slot.get("formula_id", "unknown")
            page_index = slot.get("page", 1) - 1
            if page_index < 0 or page_index >= len(doc):
                continue

            page = doc[page_index]
            pw, ph = page.rect.width, page.rect.height
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            draw = ImageDraw.Draw(image)
            scale_x = pix.width / pw
            scale_y = pix.height / ph

            # Draw original bbox in red (normalized coords -> pixel coords)
            orig = slot.get("original_bbox", slot.get("bbox", []))
            if len(orig) >= 4:
                draw.rectangle(
                    [orig[0] * pw * scale_x, orig[1] * ph * scale_y, orig[2] * pw * scale_x, orig[3] * ph * scale_y],
                    outline="red", width=3,
                )

            # Draw padded crop bbox in blue (already in page coords)
            crop = slot.get("crop_bbox", [])
            if len(crop) >= 4:
                draw.rectangle(
                    [crop[0] * scale_x, crop[1] * scale_y, crop[2] * scale_x, crop[3] * scale_y],
                    outline="blue", width=2,
                )

            overlay_path = overlay_dir / f"{formula_id}_page_{page_index + 1}.png"
            image.save(overlay_path)
            slot["overlay_path"] = str(overlay_path.relative_to(accept_dir)).replace("\\", "/")
    finally:
        doc.close()

    print(f"  Re-generated {len(slots)} overlays")


def _write_formula_slots_md(accept_dir: Path, slots: list[dict]) -> None:
    """Write formula_slots.md with all fields."""
    lines = [
        "# Formula Slots",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"Total: {len(slots)}",
        f"With LaTeX: {sum(1 for s in slots if s.get('final_latex'))}",
        f"In groups: {sum(1 for s in slots if s.get('is_multiline_group_member'))}",
        f"With nearby_text: {sum(1 for s in slots if s.get('nearby_text_before') or s.get('nearby_text_after'))}",
        "",
        "| # | ID | Page | Section | Origin | LaTeX | Group | Nearby | Risk |",
        "|---|-----|------|---------|--------|:-----:|:-----:|:------:|------|",
    ]
    for i, s in enumerate(slots, 1):
        latex_yn = "Y" if s.get("final_latex") else "N"
        group = s.get("equation_group_id", "") or "-"
        nearby = "Y" if s.get("nearby_text_before") or s.get("nearby_text_after") else "N"
        risk = ", ".join(s.get("risk_flags", [])) or "NONE"
        lines.append(
            f"| {i} | {s['formula_id']} | {s.get('page', 0)} | {s.get('section', '?')} "
            f"| {s.get('final_origin', '')} | {latex_yn} | {group} | {nearby} | {risk} |"
        )
    (accept_dir / "formula_slots.md").write_text("\n".join(lines), encoding="utf-8")


def _regenerate_all_reports(accept_dir: Path, slots: list[dict], blocks: list[dict], meta: dict, perf: dict) -> None:
    """Re-generate all report files."""
    # FINAL_MANUAL_VERIFY_INDEX.md
    _gen_verify_index(accept_dir, slots, meta, perf)
    # Visual audit HTML
    _gen_visual_audit(accept_dir, slots)
    # Quality report
    _gen_quality_report(accept_dir, slots, meta, perf)
    # Compare report
    _gen_compare_report(accept_dir, slots, blocks)
    # Performance report
    _gen_performance_report(accept_dir, slots, meta, perf)
    # Performance diagnosis
    _gen_performance_diagnosis(accept_dir, perf)
    # Zip
    _create_zip(accept_dir, ROOT / "reports" / f"{accept_dir.name}.zip")


def _gen_verify_index(accept_dir: Path, slots: list[dict], meta: dict, perf: dict) -> None:
    body_slots = [s for s in slots if s.get("formula_m2_ready", True)]
    ref_slots = [s for s in slots if not s.get("formula_m2_ready", True)]
    quality_status = meta.get("quality_status", "UNKNOWN")
    gpu_used = perf.get("gpu_used", False)
    seconds_per_page = perf.get("seconds_per_page", 0)
    perf_pass = seconds_per_page <= 120

    lines = [
        "# M1 Final Manual Verify Index",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Status Summary",
        "",
        "| Gate | Status |",
        "|------|--------|",
        f"| Machine quality gate | **{'PASS' if quality_status == 'PASS' else 'FAIL'}** |",
        f"| GPU path | **{'PASS' if gpu_used else 'FAIL'}** |",
        f"| Performance gate | **{'PASS' if perf_pass else 'WARNING'}** |",
        f"| Manual visual verification | **PENDING** |",
        "",
        "## Paper Information",
        "",
        f"- **Title**: {meta.get('title', 'N/A')}",
        f"- **arXiv ID**: {meta.get('arxiv_id', 'N/A')}",
        f"- **PDF URL**: {meta.get('pdf_url', 'N/A')}",
        f"- **Search Query**: `{meta.get('search_query_that_found_it', 'N/A')}`",
        "",
        "## Formula Summary",
        "",
        "| Metric | Count |",
        "|--------|------:|",
        f"| Total formula slots | {len(slots)} |",
        f"| Body formulas (M2 ready) | {len(body_slots)} |",
        f"| Reference formulas (excluded) | {len(ref_slots)} |",
        f"| Formulas with LaTeX | {sum(1 for s in slots if s.get('final_latex'))} |",
        f"| Formulas with crop | {sum(1 for s in slots if s.get('crop_path'))} |",
        f"| Formulas with overlay | {sum(1 for s in slots if s.get('overlay_path'))} |",
        f"| Multi-line group members | {sum(1 for s in slots if s.get('is_multiline_group_member'))} |",
        f"| With nearby_text | {sum(1 for s in slots if s.get('nearby_text_before') or s.get('nearby_text_after'))} |",
        "",
        "## Per-Formula Verification",
        "",
        "| # | ID | Page | Section | Origin | LaTeX | Group | Nearby | Crop | Overlay | Risk | Detail |",
        "|---|-----|------|---------|--------|:-----:|:-----:|:------:|:----:|:-------:|------|--------|",
    ]
    for i, s in enumerate(slots, 1):
        latex_yn = "Y" if s.get("final_latex") else "N"
        crop_yn = "Y" if s.get("crop_path") and (accept_dir / s["crop_path"]).exists() else "N"
        overlay_yn = "Y" if s.get("overlay_path") and (accept_dir / s["overlay_path"]).exists() else "N"
        group = s.get("equation_group_id", "") or "-"
        nearby = "Y" if s.get("nearby_text_before") or s.get("nearby_text_after") else "N"
        risk = ", ".join(s.get("risk_flags", [])) or "NONE"
        lines.append(
            f"| {i} | [{s['formula_id']}](visual_audit/{s['formula_id']}.html) "
            f"| {s.get('page', 0)} | {s.get('section', '?')} | {s.get('final_origin', '')} "
            f"| {latex_yn} | {group} | {nearby} | {crop_yn} | {overlay_yn} | {risk} | [View](visual_audit/{s['formula_id']}.html) |"
        )

    lines += [
        "",
        "## Manual Verification Checklist",
        "",
        "- [ ] PDF page matches formula location",
        "- [ ] Overlay red box (original bbox) correctly bounds the formula",
        "- [ ] Blue box (padded crop) does not include adjacent formulas",
        "- [ ] Crop image shows the actual formula (not surrounding text)",
        "- [ ] LaTeX matches the visual formula in the crop",
        "- [ ] Section assignment is correct",
        "- [ ] Multi-line equation groups are correctly identified",
        "- [ ] nearby_text is relevant to the formula",
        "",
        "## Verification Status",
        "",
        "**manual_visual_verification_status = PENDING**",
    ]
    (accept_dir / "FINAL_MANUAL_VERIFY_INDEX.md").write_text("\n".join(lines), encoding="utf-8")


def _gen_visual_audit(accept_dir: Path, slots: list[dict]) -> None:
    audit_dir = accept_dir / "visual_audit"
    audit_dir.mkdir(exist_ok=True)

    total = len(slots)
    latex_count = sum(1 for s in slots if s.get("final_latex"))

    for slot in slots:
        fid = slot["formula_id"]
        page = slot.get("page", 0)
        section = slot.get("section", "Unknown")
        section_conf = slot.get("section_confidence", "low")
        final_latex = slot.get("final_latex", "")
        final_origin = slot.get("final_origin", "")
        risk_flags = slot.get("risk_flags", [])
        m2_ready = slot.get("formula_m2_ready", True)
        group_id = slot.get("equation_group_id", "")
        group_order = slot.get("group_order", 0)
        nearby_before = slot.get("nearby_text_before", "")
        nearby_after = slot.get("nearby_text_after", "")
        edge_top = slot.get("edge_ink_ratio_top", 0)
        edge_bottom = slot.get("edge_ink_ratio_bottom", 0)
        padding = slot.get("crop_padding_applied", 0)

        crop_path = slot.get("crop_path", "")
        overlay_path = slot.get("overlay_path", "")
        crop_exists = (accept_dir / crop_path).exists() if crop_path else False
        overlay_exists = (accept_dir / overlay_path).exists() if overlay_path else False

        risk_str = ", ".join(risk_flags) if risk_flags else "NONE"
        m2_str = "YES" if m2_ready else "NO (excluded)"
        group_str = f"{group_id} (order {group_order})" if group_id else "none"

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{fid} — {page}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'SF Mono', 'Consolas', monospace; background: #0d1117; color: #c9d1d9; padding: 20px; max-width: 900px; margin: 0 auto; }}
h1 {{ color: #58a6ff; font-size: 18px; margin-bottom: 16px; }}
.field {{ margin: 4px 0; font-size: 13px; }}
.field-label {{ font-weight: 600; color: #8b949e; display: inline-block; min-width: 180px; }}
.images {{ display: flex; gap: 16px; margin: 16px 0; flex-wrap: wrap; }}
.images img {{ max-height: 300px; border: 1px solid #30363d; border-radius: 4px; background: #fff; }}
.images .caption {{ font-size: 11px; color: #8b949e; text-align: center; margin-top: 4px; }}
pre {{ background: #161b22; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; border: 1px solid #30363d; margin: 8px 0; }}
.nearby {{ background: #161b22; padding: 8px; border-radius: 4px; font-size: 11px; color: #8b949e; border: 1px solid #30363d; margin: 6px 0; font-style: italic; max-height: 80px; overflow: hidden; }}
.risk-none {{ color: #3fb950; }}
.risk-excluded {{ color: #d29922; }}
.nav {{ margin: 16px 0; font-size: 13px; }}
.nav a {{ color: #58a6ff; text-decoration: none; margin-right: 16px; }}
</style></head><body>
<div class="nav"><a href="index.html">&larr; Index</a></div>
<h1>{fid} — Page {page}</h1>

<div class="field"><span class="field-label">Section:</span> {section} (conf={section_conf})</div>
<div class="field"><span class="field-label">Final Origin:</span> {final_origin}</div>
<div class="field"><span class="field-label">Equation Group:</span> {group_str}</div>
<div class="field"><span class="field-label">Crop Padding:</span> {padding}px</div>
<div class="field"><span class="field-label">Edge Ink (top/bottom):</span> {edge_top:.3f} / {edge_bottom:.3f}</div>
<div class="field"><span class="field-label">Risk Flags:</span> <span class="{'risk-excluded' if risk_flags else 'risk-none'}">{risk_str}</span></div>
<div class="field"><span class="field-label">Formula M2 Ready:</span> <span class="{'risk-none' if m2_ready else 'risk-excluded'}">{m2_str}</span></div>

<div class="images">
"""
        if crop_exists:
            html += f'  <div><img src="../{crop_path}" alt="crop"><div class="caption">Crop (padded {padding}px)</div></div>\n'
        else:
            html += f'  <div><div style="width:200px;height:60px;background:#333;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#f85149;">CROP MISSING</div><div class="caption">Crop</div></div>\n'
        if overlay_exists:
            html += f'  <div><img src="../{overlay_path}" alt="overlay"><div class="caption">Overlay (red=original, blue=padded)</div></div>\n'
        else:
            html += f'  <div><div style="width:300px;height:200px;background:#333;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#f85149;">OVERLAY MISSING</div><div class="caption">Overlay</div></div>\n'
        html += '</div>\n'

        # Nearby text
        before_display = nearby_before if nearby_before else "<em>EMPTY</em>"
        after_display = nearby_after if nearby_after else "<em>EMPTY</em>"
        html += f'<div class="field"><span class="field-label">Nearby Text Before:</span></div><div class="nearby">{before_display}</div>\n'
        html += f'<div class="field"><span class="field-label">Nearby Text After:</span></div><div class="nearby">{after_display}</div>\n'

        if final_latex:
            html += f'<div class="field"><span class="field-label">LaTeX:</span></div><pre>{final_latex}</pre>\n'

        html += "</body></html>"
        (audit_dir / f"{fid}.html").write_text(html, encoding="utf-8")

    # Index page
    index_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>M1 Visual Audit</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'SF Mono', 'Consolas', monospace; background: #0d1117; color: #c9d1d9; padding: 20px; }}
h1 {{ text-align: center; margin-bottom: 8px; color: #58a6ff; font-size: 22px; }}
.stats {{ display: flex; gap: 12px; justify-content: center; margin-bottom: 24px; flex-wrap: wrap; }}
.stat {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 10px 16px; text-align: center; }}
.stat-val {{ font-size: 20px; font-weight: 700; color: #58a6ff; }}
.stat-lbl {{ font-size: 11px; color: #8b949e; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
th, td {{ border: 1px solid #30363d; padding: 8px; text-align: left; }}
th {{ background: #161b22; color: #58a6ff; }}
a {{ color: #58a6ff; text-decoration: none; }}
.risk-excluded {{ color: #d29922; }}
</style></head><body>
<h1>M1 Visual Audit</h1>
<div class="stats">
  <div class="stat"><div class="stat-val">{total}</div><div class="stat-lbl">Total Formulas</div></div>
  <div class="stat"><div class="stat-val">{latex_count}</div><div class="stat-lbl">LaTeX</div></div>
  <div class="stat"><div class="stat-val">{sum(1 for s in slots if s.get('is_multiline_group_member'))}</div><div class="stat-lbl">Group Members</div></div>
  <div class="stat"><div class="stat-val">{sum(1 for s in slots if s.get('nearby_text_before') or s.get('nearby_text_after'))}</div><div class="stat-lbl">With Nearby Text</div></div>
</div>
<table>
<tr><th>#</th><th>ID</th><th>Page</th><th>Section</th><th>Origin</th><th>LaTeX</th><th>Group</th><th>Nearby</th><th>Risk</th><th>Detail</th></tr>
"""
    for i, s in enumerate(slots, 1):
        fid = s["formula_id"]
        latex_yn = "Y" if s.get("final_latex") else "N"
        group = s.get("equation_group_id", "") or "-"
        nearby = "Y" if s.get("nearby_text_before") or s.get("nearby_text_after") else "N"
        risk_str = ", ".join(s.get("risk_flags", [])) or "NONE"
        risk_class = "risk-excluded" if s.get("risk_flags") else ""
        index_html += (
            f'<tr><td>{i}</td><td><a href="{fid}.html">{fid}</a></td>'
            f'<td>{s.get("page", 0)}</td><td>{s.get("section", "?")}</td>'
            f'<td>{s.get("final_origin", "")}</td><td>{latex_yn}</td>'
            f'<td>{group}</td><td>{nearby}</td>'
            f'<td class="{risk_class}">{risk_str}</td>'
            f'<td><a href="{fid}.html">View</a></td></tr>\n'
        )
    index_html += "</table></body></html>"
    (audit_dir / "index.html").write_text(index_html, encoding="utf-8")


def _gen_quality_report(accept_dir: Path, slots: list[dict], meta: dict, perf: dict) -> None:
    body_slots = [s for s in slots if s.get("formula_m2_ready", True)]
    ref_slots = [s for s in slots if not s.get("formula_m2_ready", True)]
    quality_status = meta.get("quality_status", "UNKNOWN")
    quality_pass = quality_status == "PASS"
    gpu_used = perf.get("gpu_used", False)
    seconds_per_page = perf.get("seconds_per_page", 0)
    perf_pass = seconds_per_page <= 120

    lines = [
        "# M1 Quality Report",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Status Summary",
        "",
        "| Gate | Status |",
        "|------|--------|",
        f"| Machine quality gate | **{'PASS' if quality_pass else 'FAIL'}** |",
        f"| GPU path | **{'PASS' if gpu_used else 'FAIL'}** |",
        f"| Performance gate | **{'PASS' if perf_pass else 'WARNING'}** |",
        f"| Manual visual verification | **PENDING** |",
        "",
        "## Paper",
        "",
        f"- Title: {meta.get('title', 'N/A')} (arXiv {meta.get('arxiv_id', 'N/A')})",
        f"- Final formula slots: {len(slots)} (MinerU full parse)",
        "",
        "## Machine Gate",
        "",
        f"- Quality: **{quality_status}**",
        f"- M2 ready: **{meta.get('m2_ready', 'N/A')}**",
        "",
        "## Device",
        "",
        f"- Device: {perf.get('device_mode_actual', 'N/A')}",
        f"- Seconds/page: {seconds_per_page:.1f}",
        "",
        "## Known Risks",
        "",
        f"- Multi-line equation groups identified: {sum(1 for s in slots if s.get('is_multiline_group_member'))}",
        f"- Formulas with edge contamination risk: {sum(1 for s in slots if 'CROP_TOP_EDGE_CONTAMINATION' in s.get('risk_flags', []) or 'CROP_BOTTOM_EDGE_CONTAMINATION' in s.get('risk_flags', []))}",
        f"- Formulas with nearby_text: {sum(1 for s in slots if s.get('nearby_text_before') or s.get('nearby_text_after'))}",
        "",
        "## Manual Verification",
        "",
        "**Status: PENDING**",
        "",
        "## Exclusions",
        "",
        f"- Reference formulas: {len(ref_slots)}",
    ]
    (accept_dir / "quality_report.md").write_text("\n".join(lines), encoding="utf-8")


def _gen_compare_report(accept_dir: Path, slots: list[dict], blocks: list[dict]) -> None:
    crop_ok = sum(1 for s in slots if s.get("crop_path") and (accept_dir / s["crop_path"]).exists())
    overlay_ok = sum(1 for s in slots if s.get("overlay_path") and (accept_dir / s["overlay_path"]).exists())

    canonical_path = accept_dir / "canonical_paper.md"
    canonical = canonical_path.read_text(encoding="utf-8") if canonical_path.exists() else ""
    matched = sum(1 for s in slots if s["formula_id"] in canonical)

    all_ok = (
        (accept_dir / "source.pdf").exists()
        and (accept_dir / "document_blocks.json").exists()
        and (accept_dir / "formula_slots.json").exists()
        and crop_ok == len(slots)
        and overlay_ok == len(slots)
    )

    lines = [
        "# M1 Compare Report: Artifact Traceability",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Artifact Cross-Reference",
        "",
        f"- source.pdf exists: {(accept_dir / 'source.pdf').exists()}",
        f"- document_blocks.json exists: {(accept_dir / 'document_blocks.json').exists()}",
        f"- formula_slots.json exists: {(accept_dir / 'formula_slots.json').exists()}",
        f"- canonical_paper.md exists: {canonical_path.exists()}",
        f"- Crops: {crop_ok}/{len(slots)}",
        f"- Overlays: {overlay_ok}/{len(slots)}",
        f"- Formulas in canonical: {matched}/{len(slots)}",
        f"- Visual audit index: {(accept_dir / 'visual_audit' / 'index.html').exists()}",
        f"- Total blocks: {len(blocks)}",
        "",
        "Machine gate: " + ("PASS" if all_ok else "CHECK REQUIRED"),
        "",
        "Note: Machine traceability report. Manual visual verification required.",
    ]
    (accept_dir / "compare_report.md").write_text("\n".join(lines), encoding="utf-8")


def _gen_performance_report(accept_dir: Path, slots: list[dict], meta: dict, perf: dict) -> None:
    quality_status = meta.get("quality_status", "UNKNOWN")
    quality_pass = quality_status == "PASS"
    gpu_used = perf.get("gpu_used", False)
    seconds_per_page = perf.get("seconds_per_page", 0)
    perf_pass = seconds_per_page <= 120

    lines = [
        "# M1 Performance Report",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Status Summary",
        "",
        "| Gate | Status |",
        "|------|--------|",
        f"| Machine quality gate | **{'PASS' if quality_pass else 'FAIL'}** |",
        f"| GPU path | **{'PASS' if gpu_used else 'FAIL'}** |",
        f"| Performance gate | **{'PASS' if perf_pass else 'WARNING'}** |",
        f"| Manual visual verification | **PENDING** |",
        "",
        "**Note**: M1 is NOT fully verified until all gates pass AND manual visual verification is complete.",
        "",
        "## Paper",
        "",
        f"- Title: {meta.get('title', 'N/A')}",
        f"- arXiv: {meta.get('arxiv_id', 'N/A')}",
        f"- Pages: {perf.get('page_count', 'N/A')}",
        "",
        "## Device",
        "",
        f"- Requested: {perf.get('device_mode_requested', 'N/A')}",
        f"- Actual: **{perf.get('device_mode_actual', 'N/A')}**",
        f"- GPU used: {gpu_used}",
        f"- GPU name: {perf.get('gpu_name', 'N/A')}",
        "",
        "## Timing",
        "",
        f"- Full parse: {perf.get('parse_elapsed_seconds', 'N/A')}s",
        f"- Seconds/page: {seconds_per_page:.1f}",
        "",
        "## Output",
        "",
        f"- Blocks: {perf.get('block_count', 'N/A')}",
        f"- Formula slots: {len(slots)}",
        f"- Quality: {quality_status}",
        f"- M2 ready: {meta.get('m2_ready', 'N/A')}",
        "",
        "## Warnings",
        "",
    ]
    warnings = perf.get("warnings", [])
    if warnings:
        for w in warnings:
            lines.append(f"- **{w}**")
    else:
        lines.append("- None")
    lines += [
        "",
        "## Conclusion",
        "",
    ]
    if perf_pass and quality_pass:
        lines.append("All automated gates passed. Manual visual verification still required.")
    elif quality_pass and not perf_pass:
        lines.append("Machine quality gate passed, but performance gate has warnings. M1 can be used for manual review but not recommended for batch processing.")
    elif not quality_pass:
        lines.append("Machine quality gate failed. Review blocking reasons before proceeding.")
    else:
        lines.append("GPU path used but some warnings detected.")
    (accept_dir / "performance_report.md").write_text("\n".join(lines), encoding="utf-8")


def _gen_performance_diagnosis(accept_dir: Path, perf: dict) -> None:
    seconds_per_page = perf.get("seconds_per_page", 0)
    backend = perf.get("backend", "transformers")
    gpu_name = perf.get("gpu_name", "N/A")
    gpu_mem = perf.get("gpu_memory_total_mb", 0)
    device_actual = perf.get("device_mode_actual", "unknown")
    parse_elapsed = perf.get("parse_elapsed_seconds", 0)
    page_count = perf.get("page_count", 0)

    lines = [
        "# M1 Performance Diagnosis",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Current Performance",
        "",
        f"- Backend: {backend}",
        f"- GPU: {gpu_name} ({gpu_mem} MB)",
        f"- device_mode_actual: {device_actual}",
        f"- Parse elapsed: {parse_elapsed:.0f}s ({parse_elapsed/60:.1f} min)",
        f"- Pages: {page_count}",
        f"- Seconds/page: {seconds_per_page:.1f}",
        f"- Performance gate: **{'PASS' if seconds_per_page <= 120 else 'WARNING (>120s/page)'}**",
        "",
        "## Analysis",
        "",
        f"MinerU2.5-Pro is running on GPU ({gpu_name}) via the `{backend}` backend. "
        f"Each page takes ~{seconds_per_page:.0f} seconds, which exceeds the 120s/page warning threshold.",
        "",
        "## Suitability",
        "",
        "- **Manual review / single paper**: Acceptable. 45 minutes is tolerable for one-off acceptance.",
        "- **Batch processing**: Not recommended at current speed.",
        "",
        "## Optimization Directions",
        "",
        "1. **vLLM backend**: Evaluate if mineru-vl-utils supports vLLM for faster inference.",
        "2. **Reduce render_scale**: Current default is 2.0. Lowering to 1.5 or 1.0 reduces image size and inference time.",
        "3. **Page-level cache**: Cache layout detection results to avoid re-processing unchanged pages.",
        "4. **Selective parsing**: Only run full MinerU on pages with formula candidates (from prescreen).",
        "5. **Batch/async page pipeline**: Process multiple pages in parallel if GPU memory allows.",
        "6. **Per-page profiling**: Record each page's layout + OCR time to identify slow pages.",
        "7. **Model quantization**: If supported, use INT8/FP16 quantized model for faster inference.",
    ]
    (accept_dir / "performance_diagnosis.md").write_text("\n".join(lines), encoding="utf-8")


def _create_zip(source_dir: Path, zip_path: Path) -> None:
    import zipfile
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(source_dir.rglob("*")):
            if file.is_file():
                arcname = file.relative_to(source_dir.parent)
                zf.write(file, arcname)
    print(f"  Zip: {zip_path} ({zip_path.stat().st_size / 1024:.0f} KB)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fix an explicit M1 acceptance package directory.")
    parser.add_argument("accept_dir", type=Path, help="M1 acceptance artifact directory to repair.")
    args = parser.parse_args(argv)
    fix_acceptance_package(args.accept_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
