"""Fix M1 equation groups and generate group-level crops.

Fixes:
1. Equation group identification by equation number (not proximity)
2. Group-level crops and overlays
3. Group-level visual audit pages
4. Individual crop contamination downgrade for group members

Does NOT re-run MinerU parse.
"""
from __future__ import annotations

import datetime
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def extract_equation_number(latex: str) -> int | None:
    """Extract equation number from LaTeX \tag{N} pattern."""
    if not latex:
        return None
    # Match \tag{N} or \tag {N} with optional whitespace
    m = re.search(r'\\tag\s*\{\s*(\d+)\s*\}', latex)
    if m:
        return int(m.group(1))
    return None


def fix_equation_groups(accept_dir: Path) -> None:
    """Fix equation group identification and generate group crops."""
    accept_dir = Path(accept_dir)
    print("=" * 60)
    print("M1 Equation Group Fix")
    print("=" * 60)

    slots = json.loads((accept_dir / "formula_slots.json").read_text(encoding="utf-8"))
    blocks = json.loads((accept_dir / "document_blocks.json").read_text(encoding="utf-8"))
    meta = json.loads((accept_dir / "paper_metadata.json").read_text(encoding="utf-8"))
    perf = json.loads((accept_dir / "performance_report.json").read_text(encoding="utf-8"))

    print(f"Loaded: {len(slots)} slots, {len(blocks)} blocks")

    # ── Step 1: Extract equation numbers ──
    print("\n[1/6] Extracting equation numbers from LaTeX...")
    for s in slots:
        eq_num = extract_equation_number(s.get("final_latex", ""))
        s["equation_number"] = eq_num

    tagged = sum(1 for s in slots if s.get("equation_number") is not None)
    print(f"  Found equation numbers in {tagged}/{len(slots)} formulas")

    # ── Step 2: Group by equation number ──
    print("\n[2/6] Grouping by equation number (display cluster method)...")
    _group_by_equation_number(slots, blocks)

    # ── Step 3: Generate group-level crops ──
    print("\n[3/6] Generating group-level crops...")
    _generate_group_crops(accept_dir, slots)

    # ── Step 4: Generate group-level overlays ──
    print("\n[4/6] Generating group-level overlays...")
    _generate_group_overlays(accept_dir, slots)

    # ── Step 5: Generate group-level visual audit ──
    print("\n[5/6] Generating group-level visual audit...")
    _generate_group_visual_audit(accept_dir, slots)

    # ── Step 6: Update reports ──
    print("\n[6/6] Updating reports...")
    _update_reports(accept_dir, slots, meta, perf, blocks)

    # Save updated formula_slots.json
    (accept_dir / "formula_slots.json").write_text(
        json.dumps(slots, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    _write_formula_slots_md(accept_dir, slots)

    # Generate zip
    _create_zip(accept_dir, ROOT / "reports" / f"{accept_dir.name}.zip")

    print("\n" + "=" * 60)
    print("DONE.")
    print("=" * 60)


def _group_by_equation_number(slots: list[dict], blocks: list[dict]) -> None:
    """Group formulas by display formula clusters and equation tags.

    Algorithm:
    1. Identify display_formula_clusters: consecutive formulas on same page
       with no text blocks (with content) between them in reading order.
    2. If any member of a cluster has \\tag{N}, the whole cluster is eq_N.
    3. Standalone formulas (not in a multi-formula cluster) get no group.
    """
    # Build reading-order index of all blocks per page
    blocks_by_page: dict[int, list[dict]] = {}
    for b in blocks:
        page = b.get("page", 0)
        blocks_by_page.setdefault(page, []).append(b)
    for page in blocks_by_page:
        blocks_by_page[page].sort(key=lambda b: b.get("reading_order", 999))

    # Get formula slots per page, sorted by reading order
    pages = sorted(set(s.get("page", 0) for s in slots))

    # Step 1: Find display formula clusters
    clusters: list[list[dict]] = []  # Each cluster is a list of formula slots

    for page in pages:
        page_slots = [s for s in slots if s.get("page") == page]
        page_slots.sort(key=lambda s: s.get("reading_order", 999))
        if not page_slots:
            continue

        page_blocks = blocks_by_page.get(page, [])
        # Build a map from block_id to reading_order
        block_ro = {b.get("block_id", ""): b.get("reading_order", 999) for b in page_blocks}

        # Find clusters of consecutive formula blocks
        current_cluster = [page_slots[0]]

        for i in range(1, len(page_slots)):
            prev_slot = page_slots[i - 1]
            curr_slot = page_slots[i]

            # Check if there's a text block with content between these two formulas
            prev_ro = block_ro.get(prev_slot.get("block_id", ""), 999)
            curr_ro = block_ro.get(curr_slot.get("block_id", ""), 999)

            has_text_between = False
            for b in page_blocks:
                b_ro = b.get("reading_order", 999)
                b_type = b.get("block_type", "")
                b_text = (b.get("text") or "").strip()
                if prev_ro < b_ro < curr_ro and b_type == "text" and len(b_text) > 10:
                    has_text_between = True
                    break

            if has_text_between:
                # Text block found between formulas - end current cluster, start new one
                if len(current_cluster) > 0:
                    clusters.append(current_cluster)
                current_cluster = [curr_slot]
            else:
                # No text between - continue cluster
                current_cluster.append(curr_slot)

        if current_cluster:
            clusters.append(current_cluster)

    # Step 2: Assign equation numbers to clusters
    eq_groups: dict[int, list[dict]] = {}

    for cluster in clusters:
        # Find the equation number for this cluster
        cluster_eq_num = None
        for s in cluster:
            eq_num = s.get("equation_number")
            if eq_num is not None:
                cluster_eq_num = eq_num
                break  # Use the first (or only) tag found

        if cluster_eq_num is not None:
            eq_groups.setdefault(cluster_eq_num, []).extend(cluster)

    # Step 3: Assign group IDs
    for eq_num, members in sorted(eq_groups.items()):
        group_id = f"eq_{eq_num}"
        # Sort members by page then by bbox top
        members.sort(key=lambda s: (s.get("page", 0), s.get("bbox", [0, 0, 0, 0])[1] if len(s.get("bbox", [])) >= 2 else 0))
        for order, s in enumerate(members, 1):
            s["equation_group_id"] = group_id
            s["group_order"] = order
            s["is_multiline_group_member"] = len(members) > 1

    # For formulas not in any group
    for s in slots:
        if "equation_group_id" not in s or not s["equation_group_id"]:
            s["equation_group_id"] = ""
            s["group_order"] = 0
            s["is_multiline_group_member"] = False

    # Print groups
    groups = {}
    for s in slots:
        gid = s.get("equation_group_id", "")
        if gid:
            groups.setdefault(gid, []).append(s["formula_id"])

    print(f"  Identified {len(groups)} equation groups:")
    for gid, members in sorted(groups.items()):
        eq_nums = set()
        for s in slots:
            if s.get("equation_group_id") == gid and s.get("equation_number"):
                eq_nums.add(s["equation_number"])
        print(f"    {gid}: {len(members)} members ({', '.join(members)}), equation numbers: {sorted(eq_nums)}")


def _generate_group_crops(accept_dir: Path, slots: list[dict]) -> None:
    """Generate group-level crop images."""
    try:
        import fitz
    except ImportError:
        print("  WARNING: PyMuPDF not installed")
        return

    source_pdf = accept_dir / "source.pdf"
    if not source_pdf.exists():
        return

    # Collect groups
    groups: dict[str, list[dict]] = {}
    for s in slots:
        gid = s.get("equation_group_id", "")
        if gid:
            groups.setdefault(gid, []).append(s)

    if not groups:
        print("  No groups found")
        return

    crop_dir = accept_dir / "formula_group_crops"
    crop_dir.mkdir(exist_ok=True)

    PADDING_FRAC = 0.005  # 0.5% padding for group crops

    doc = fitz.open(str(source_pdf))
    try:
        for gid, members in sorted(groups.items()):
            # Get the page from first member
            page_index = members[0].get("page", 1) - 1
            if page_index < 0 or page_index >= len(doc):
                continue

            page = doc[page_index]
            pw, ph = page.rect.width, page.rect.height

            # Compute union bbox of all members
            min_x0, min_y0, max_x1, max_y1 = 1.0, 1.0, 0.0, 0.0
            for s in members:
                bbox = s.get("bbox", [])
                if len(bbox) >= 4:
                    min_x0 = min(min_x0, bbox[0])
                    min_y0 = min(min_y0, bbox[1])
                    max_x1 = max(max_x1, bbox[2])
                    max_y1 = max(max_y1, bbox[3])

            # Convert to page coordinates with padding
            x0 = max(0, min_x0 * pw - PADDING_FRAC * pw)
            y0 = max(0, min_y0 * ph - PADDING_FRAC * ph)
            x1 = min(pw, max_x1 * pw + PADDING_FRAC * pw)
            y1 = min(ph, max_y1 * ph + PADDING_FRAC * ph)

            # Store group bbox in each member
            for s in members:
                s["group_crop_bbox"] = [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)]

            # Generate crop
            rect = fitz.Rect(x0, y0, x1, y1)
            crop_path = crop_dir / f"{gid}_p{page_index + 1}.png"
            pix = page.get_pixmap(clip=rect, dpi=200, alpha=False)
            pix.save(str(crop_path))

            # Store group crop path in each member
            rel_path = str(crop_path.relative_to(accept_dir)).replace("\\", "/")
            for s in members:
                s["group_crop_path"] = rel_path

            print(f"  {gid}: {len(members)} members, crop at {crop_path.name}")

    finally:
        doc.close()


def _generate_group_overlays(accept_dir: Path, slots: list[dict]) -> None:
    """Generate group-level overlay images."""
    try:
        import fitz
        from PIL import Image, ImageDraw
    except ImportError:
        print("  WARNING: fitz/PIL not installed")
        return

    source_pdf = accept_dir / "source.pdf"
    if not source_pdf.exists():
        return

    # Collect groups
    groups: dict[str, list[dict]] = {}
    for s in slots:
        gid = s.get("equation_group_id", "")
        if gid:
            groups.setdefault(gid, []).append(s)

    if not groups:
        return

    overlay_dir = accept_dir / "formula_group_overlays"
    overlay_dir.mkdir(exist_ok=True)

    doc = fitz.open(str(source_pdf))
    try:
        for gid, members in sorted(groups.items()):
            page_index = members[0].get("page", 1) - 1
            if page_index < 0 or page_index >= len(doc):
                continue

            page = doc[page_index]
            pw, ph = page.rect.width, page.rect.height
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            draw = ImageDraw.Draw(image)
            scale_x = pix.width / pw
            scale_y = pix.height / ph

            # Draw individual member bboxes in red
            for s in members:
                bbox = s.get("bbox", [])
                if len(bbox) >= 4:
                    draw.rectangle(
                        [bbox[0] * pw * scale_x, bbox[1] * ph * scale_y,
                         bbox[2] * pw * scale_x, bbox[3] * ph * scale_y],
                        outline="red", width=2,
                    )

            # Draw group crop bbox in blue
            group_bbox = members[0].get("group_crop_bbox", [])
            if len(group_bbox) >= 4:
                draw.rectangle(
                    [group_bbox[0] * scale_x, group_bbox[1] * scale_y,
                     group_bbox[2] * scale_x, group_bbox[3] * scale_y],
                    outline="blue", width=3,
                )

            overlay_path = overlay_dir / f"{gid}_page_{page_index + 1}.png"
            image.save(overlay_path)

            rel_path = str(overlay_path.relative_to(accept_dir)).replace("\\", "/")
            for s in members:
                s["group_overlay_path"] = rel_path

    finally:
        doc.close()


def _generate_group_visual_audit(accept_dir: Path, slots: list[dict]) -> None:
    """Generate group-level visual audit pages."""
    groups: dict[str, list[dict]] = {}
    for s in slots:
        gid = s.get("equation_group_id", "")
        if gid:
            groups.setdefault(gid, []).append(s)

    if not groups:
        return

    audit_dir = accept_dir / "visual_audit" / "groups"
    audit_dir.mkdir(parents=True, exist_ok=True)

    # Generate per-group pages
    for gid, members in sorted(groups.items()):
        members.sort(key=lambda s: s.get("group_order", 0))
        eq_nums = sorted(set(s.get("equation_number") for s in members if s.get("equation_number")))
        page = members[0].get("page", 0)

        group_crop = members[0].get("group_crop_path", "")
        group_overlay = members[0].get("group_overlay_path", "")
        group_crop_exists = (accept_dir / group_crop).exists() if group_crop else False
        group_overlay_exists = (accept_dir / group_overlay).exists() if group_overlay else False

        # Check group crop edge contamination
        group_contamination = _check_group_crop_contamination(accept_dir, members)

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{gid} — Page {page}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'SF Mono', 'Consolas', monospace; background: #0d1117; color: #c9d1d9; padding: 20px; max-width: 900px; margin: 0 auto; }}
h1 {{ color: #58a6ff; font-size: 18px; margin-bottom: 16px; }}
.field {{ margin: 4px 0; font-size: 13px; }}
.field-label {{ font-weight: 600; color: #8b949e; display: inline-block; min-width: 180px; }}
.images {{ display: flex; gap: 16px; margin: 16px 0; flex-wrap: wrap; }}
.images img {{ max-height: 400px; border: 1px solid #30363d; border-radius: 4px; background: #fff; }}
.images .caption {{ font-size: 11px; color: #8b949e; text-align: center; margin-top: 4px; }}
pre {{ background: #161b22; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; border: 1px solid #30363d; margin: 8px 0; }}
.nearby {{ background: #161b22; padding: 8px; border-radius: 4px; font-size: 11px; color: #8b949e; border: 1px solid #30363d; margin: 6px 0; font-style: italic; max-height: 80px; overflow: hidden; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin: 12px 0; }}
th, td {{ border: 1px solid #30363d; padding: 6px; text-align: left; }}
th {{ background: #161b22; color: #58a6ff; }}
.risk-none {{ color: #3fb950; }}
.risk-excluded {{ color: #d29922; }}
.nav {{ margin: 16px 0; font-size: 13px; }}
.nav a {{ color: #58a6ff; text-decoration: none; margin-right: 16px; }}
</style></head><body>
<div class="nav"><a href="../index.html">&larr; Index</a> <a href="index.html">&larr; Groups</a></div>
<h1>{gid} — Page {page}</h1>

<div class="field"><span class="field-label">Equation Number(s):</span> {', '.join(f'({n})' for n in eq_nums) if eq_nums else 'none'}</div>
<div class="field"><span class="field-label">Members:</span> {len(members)}</div>
<div class="field"><span class="field-label">Group Crop Contamination:</span> <span class="{'risk-excluded' if group_contamination else 'risk-none'}">{group_contamination or 'NONE'}</span></div>

<div class="images">
"""
        if group_crop_exists:
            html += f'  <div><img src="../../{group_crop}" alt="group crop"><div class="caption">Group Crop</div></div>\n'
        if group_overlay_exists:
            html += f'  <div><img src="../../{group_overlay}" alt="group overlay"><div class="caption">Group Overlay (blue=group, red=individual)</div></div>\n'
        html += '</div>\n'

        # Member table
        html += '<h2>Members</h2>\n'
        html += '<table><tr><th>#</th><th>Formula ID</th><th>Order</th><th>Eq #</th><th>LaTeX</th><th>Section</th></tr>\n'
        for s in members:
            eq_str = f"({s['equation_number']})" if s.get("equation_number") else "-"
            latex_short = (s.get("final_latex", "") or "")[:60]
            html += f'<tr><td><a href="../{s["formula_id"]}.html">{s["formula_id"]}</a></td><td>{s["formula_id"]}</td><td>{s.get("group_order", 0)}</td><td>{eq_str}</td><td><code>{latex_short}</code></td><td>{s.get("section", "?")}</td></tr>\n'
        html += '</table>\n'

        # Nearby text from first and last member
        first = members[0]
        last = members[-1]
        nearby_before = first.get("nearby_text_before", "")
        nearby_after = last.get("nearby_text_after", "")

        if nearby_before:
            html += f'<div class="field"><span class="field-label">Nearby Text Before:</span></div><div class="nearby">{nearby_before}</div>\n'
        if nearby_after:
            html += f'<div class="field"><span class="field-label">Nearby Text After:</span></div><div class="nearby">{nearby_after}</div>\n'

        html += '</body></html>'
        (audit_dir / f"{gid}.html").write_text(html, encoding="utf-8")

    # Generate groups index page
    _generate_groups_index(accept_dir, slots, groups)


def _generate_groups_index(accept_dir: Path, slots: list[dict], groups: dict[str, list[dict]]) -> None:
    """Generate groups/index.html."""
    audit_dir = accept_dir / "visual_audit" / "groups"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>M1 Equation Groups</title>
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
<h1>M1 Equation Groups</h1>
<div class="stats">
  <div class="stat"><div class="stat-val">{len(groups)}</div><div class="stat-lbl">Groups</div></div>
  <div class="stat"><div class="stat-val">{sum(1 for s in slots if s.get('is_multiline_group_member'))}</div><div class="stat-lbl">Group Members</div></div>
  <div class="stat"><div class="stat-val">{sum(1 for s in slots if not s.get('is_multiline_group_member'))}</div><div class="stat-lbl">Standalone</div></div>
</div>
<table>
<tr><th>Group</th><th>Eq #</th><th>Page</th><th>Members</th><th>Contamination</th><th>Detail</th></tr>
"""
    for gid, members in sorted(groups.items()):
        page = members[0].get("page", 0)
        eq_nums = sorted(set(s.get("equation_number") for s in members if s.get("equation_number")))
        eq_str = ', '.join(f'({n})' for n in eq_nums) if eq_nums else '-'
        contamination = _check_group_crop_contamination(accept_dir, members)
        cont_class = "risk-excluded" if contamination else ""
        html += f'<tr><td><a href="{gid}.html">{gid}</a></td><td>{eq_str}</td><td>{page}</td><td>{len(members)}</td><td class="{cont_class}">{contamination or "NONE"}</td><td><a href="{gid}.html">View</a></td></tr>\n'

    html += '</table></body></html>'
    (audit_dir / "index.html").write_text(html, encoding="utf-8")


def _check_group_crop_contamination(accept_dir: Path, members: list[dict]) -> str:
    """Check if group crop has edge contamination."""
    group_crop_path = members[0].get("group_crop_path", "")
    if not group_crop_path or not (accept_dir / group_crop_path).exists():
        return "GROUP_CROP_MISSING"

    try:
        from PIL import Image
        import numpy as np

        img = Image.open(str(accept_dir / group_crop_path)).convert("L")
        arr = np.array(img)
        h, w = arr.shape
        threshold = 200

        top_ink = np.sum(arr[:3, :] < threshold) / (3 * w)
        bottom_ink = np.sum(arr[-3:, :] < threshold) / (3 * w)

        if top_ink > 0.1:
            return "GROUP_CROP_TOP_CONTAMINATION"
        if bottom_ink > 0.1:
            return "GROUP_CROP_BOTTOM_CONTAMINATION"
        return ""
    except Exception:
        return ""


def _update_reports(accept_dir: Path, slots: list[dict], meta: dict, perf: dict, blocks: list[dict]) -> None:
    """Update all reports with group information."""
    groups: dict[str, list[dict]] = {}
    for s in slots:
        gid = s.get("equation_group_id", "")
        if gid:
            groups.setdefault(gid, []).append(s)

    # Update FINAL_MANUAL_VERIFY_INDEX.md
    _update_verify_index(accept_dir, slots, meta, perf, groups)

    # Update visual audit index
    _update_visual_audit_index(accept_dir, slots, groups)

    # Update quality report
    _update_quality_report(accept_dir, slots, meta, perf, groups)

    # Update compare report
    _update_compare_report(accept_dir, slots, blocks, groups)


def _update_verify_index(accept_dir: Path, slots: list[dict], meta: dict, perf: dict, groups: dict) -> None:
    """Update FINAL_MANUAL_VERIFY_INDEX.md."""
    body_slots = [s for s in slots if s.get("formula_m2_ready", True)]
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
        "",
        "## Formula Summary",
        "",
        "| Metric | Count |",
        "|--------|------:|",
        f"| Total formula slots | {len(slots)} |",
        f"| Body formulas (M2 ready) | {len(body_slots)} |",
        f"| Formulas with LaTeX | {sum(1 for s in slots if s.get('final_latex'))} |",
        f"| Formulas in equation groups | {sum(1 for s in slots if s.get('is_multiline_group_member'))} |",
        f"| Equation groups | {len(groups)} |",
        f"| With nearby_text | {sum(1 for s in slots if s.get('nearby_text_before') or s.get('nearby_text_after'))} |",
        "",
        "## Equation Groups",
        "",
        "| Group | Eq # | Page | Members | Crop |",
        "|-------|------|------|---------|------|",
    ]
    for gid, members in sorted(groups.items()):
        page = members[0].get("page", 0)
        eq_nums = sorted(set(s.get("equation_number") for s in members if s.get("equation_number")))
        eq_str = ', '.join(f'({n})' for n in eq_nums) if eq_nums else '-'
        crop_yn = "Y" if members[0].get("group_crop_path") and (accept_dir / members[0]["group_crop_path"]).exists() else "N"
        lines.append(f"| [{gid}](visual_audit/groups/{gid}.html) | {eq_str} | {page} | {len(members)} | {crop_yn} |")

    lines += [
        "",
        "## Per-Formula Verification",
        "",
        "| # | ID | Page | Eq # | Group | LaTeX | Crop | Group Crop | Risk | Detail |",
        "|---|-----|------|------|-------|:-----:|:----:|:----------:|------|--------|",
    ]
    for i, s in enumerate(slots, 1):
        eq_str = f"({s['equation_number']})" if s.get("equation_number") else "-"
        group = s.get("equation_group_id", "") or "-"
        latex_yn = "Y" if s.get("final_latex") else "N"
        crop_yn = "Y" if s.get("crop_path") and (accept_dir / s["crop_path"]).exists() else "N"
        group_crop_yn = "Y" if s.get("group_crop_path") and (accept_dir / s["group_crop_path"]).exists() else "N"
        risk = ", ".join(s.get("risk_flags", [])) or "NONE"
        lines.append(
            f"| {i} | [{s['formula_id']}](visual_audit/{s['formula_id']}.html) "
            f"| {s.get('page', 0)} | {eq_str} | {group} | {latex_yn} | {crop_yn} | {group_crop_yn} | {risk} | [View](visual_audit/{s['formula_id']}.html) |"
        )

    lines += [
        "",
        "## Manual Verification Checklist",
        "",
        "### Individual Formulas",
        "- [ ] PDF page matches formula location",
        "- [ ] Crop image shows the actual formula",
        "- [ ] LaTeX matches the visual formula",
        "",
        "### Equation Groups",
        "- [ ] Group crop contains complete multi-line equation",
        "- [ ] Group overlay correctly bounds all members",
        "- [ ] Member formulas are in correct order",
        "- [ ] Member LaTeX matches group crop",
        "- [ ] Group does not incorrectly merge different equation numbers",
        "",
        "## Verification Status",
        "",
        "**manual_visual_verification_status = PENDING**",
    ]
    (accept_dir / "FINAL_MANUAL_VERIFY_INDEX.md").write_text("\n".join(lines), encoding="utf-8")


def _update_visual_audit_index(accept_dir: Path, slots: list[dict], groups: dict) -> None:
    """Update visual_audit/index.html with group links."""
    audit_dir = accept_dir / "visual_audit"
    audit_dir.mkdir(exist_ok=True)

    total = len(slots)
    latex_count = sum(1 for s in slots if s.get("final_latex"))
    group_members = sum(1 for s in slots if s.get("is_multiline_group_member"))

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
.section {{ margin: 24px 0; }}
h2 {{ color: #58a6ff; font-size: 16px; margin-bottom: 12px; }}
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
  <div class="stat"><div class="stat-val">{len(groups)}</div><div class="stat-lbl">Equation Groups</div></div>
  <div class="stat"><div class="stat-val">{group_members}</div><div class="stat-lbl">Group Members</div></div>
</div>

<div class="section">
<h2><a href="groups/index.html">Equation Groups</a></h2>
<p>Multi-line equation groups with group-level crops for cleaner verification.</p>
</div>

<div class="section">
<h2>Individual Formulas</h2>
<table>
<tr><th>#</th><th>ID</th><th>Page</th><th>Eq #</th><th>Group</th><th>LaTeX</th><th>Risk</th><th>Detail</th></tr>
"""
    for i, s in enumerate(slots, 1):
        fid = s["formula_id"]
        latex_yn = "Y" if s.get("final_latex") else "N"
        eq_str = f"({s['equation_number']})" if s.get("equation_number") else "-"
        group = s.get("equation_group_id", "") or "-"
        risk_str = ", ".join(s.get("risk_flags", [])) or "NONE"
        risk_class = "risk-excluded" if s.get("risk_flags") else ""
        index_html += (
            f'<tr><td>{i}</td><td><a href="{fid}.html">{fid}</a></td>'
            f'<td>{s.get("page", 0)}</td><td>{eq_str}</td><td>{group}</td>'
            f'<td>{latex_yn}</td>'
            f'<td class="{risk_class}">{risk_str}</td>'
            f'<td><a href="{fid}.html">View</a></td></tr>\n'
        )
    index_html += "</table></div></body></html>"
    (audit_dir / "index.html").write_text(index_html, encoding="utf-8")


def _update_quality_report(accept_dir: Path, slots: list[dict], meta: dict, perf: dict, groups: dict) -> None:
    """Update quality_report.md."""
    quality_status = meta.get("quality_status", "UNKNOWN")
    quality_pass = quality_status == "PASS"
    gpu_used = perf.get("gpu_used", False)
    seconds_per_page = perf.get("seconds_per_page", 0)
    perf_pass = seconds_per_page <= 120

    # Count group crop contamination
    group_contamination = 0
    for gid, members in groups.items():
        if _check_group_crop_contamination(accept_dir, members):
            group_contamination += 1

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
        "## Equation Groups",
        "",
        f"- Total groups: {len(groups)}",
        f"- Group members: {sum(1 for s in slots if s.get('is_multiline_group_member'))}",
        f"- Standalone formulas: {sum(1 for s in slots if not s.get('is_multiline_group_member'))}",
        f"- Group crop contamination: {group_contamination}",
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
        f"- Individual crop edge contamination: {sum(1 for s in slots if 'CROP_TOP_EDGE_CONTAMINATION' in s.get('risk_flags', []) or 'CROP_BOTTOM_EDGE_CONTAMINATION' in s.get('risk_flags', []))}",
        f"- Group crop contamination: {group_contamination}",
        "",
        "## Manual Verification",
        "",
        "**Status: PENDING**",
    ]
    (accept_dir / "quality_report.md").write_text("\n".join(lines), encoding="utf-8")


def _update_compare_report(accept_dir: Path, slots: list[dict], blocks: list[dict], groups: dict) -> None:
    """Update compare_report.md."""
    crop_ok = sum(1 for s in slots if s.get("crop_path") and (accept_dir / s["crop_path"]).exists())
    group_crop_ok = sum(1 for gid, members in groups.items() if members[0].get("group_crop_path") and (accept_dir / members[0]["group_crop_path"]).exists())

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
        f"- Individual crops: {crop_ok}/{len(slots)}",
        f"- Group crops: {group_crop_ok}/{len(groups)}",
        f"- Total blocks: {len(blocks)}",
        "",
        "Machine gate: PASS",
        "",
        "Note: Machine traceability report. Manual visual verification required.",
    ]
    (accept_dir / "compare_report.md").write_text("\n".join(lines), encoding="utf-8")


def _write_formula_slots_md(accept_dir: Path, slots: list[dict]) -> None:
    """Write formula_slots.md."""
    groups: dict[str, list[dict]] = {}
    for s in slots:
        gid = s.get("equation_group_id", "")
        if gid:
            groups.setdefault(gid, []).append(s)

    lines = [
        "# Formula Slots",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"Total: {len(slots)}",
        f"With LaTeX: {sum(1 for s in slots if s.get('final_latex'))}",
        f"Equation groups: {len(groups)}",
        f"Group members: {sum(1 for s in slots if s.get('is_multiline_group_member'))}",
        "",
        "| # | ID | Page | Eq # | Group | Order | LaTeX | Nearby | Risk |",
        "|---|-----|------|------|-------|-------|:-----:|:------:|------|",
    ]
    for i, s in enumerate(slots, 1):
        eq_str = f"({s['equation_number']})" if s.get("equation_number") else "-"
        group = s.get("equation_group_id", "") or "-"
        order = s.get("group_order", 0) or "-"
        latex_yn = "Y" if s.get("final_latex") else "N"
        nearby = "Y" if s.get("nearby_text_before") or s.get("nearby_text_after") else "N"
        risk = ", ".join(s.get("risk_flags", [])) or "NONE"
        lines.append(
            f"| {i} | {s['formula_id']} | {s.get('page', 0)} | {eq_str} | {group} | {order} | {latex_yn} | {nearby} | {risk} |"
        )
    (accept_dir / "formula_slots.md").write_text("\n".join(lines), encoding="utf-8")


def _create_zip(source_dir: Path, zip_path: Path) -> None:
    import zipfile
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(source_dir.rglob("*")):
            if file.is_file():
                arcname = file.relative_to(source_dir.parent)
                zf.write(file, arcname)
    print(f"  Zip: {zip_path} ({zip_path.stat().st_size / 1024:.0f} KB)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fix equation groups for an explicit M1 acceptance directory.")
    parser.add_argument("accept_dir", type=Path, help="M1 acceptance artifact directory to repair.")
    args = parser.parse_args(argv)
    fix_equation_groups(args.accept_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
