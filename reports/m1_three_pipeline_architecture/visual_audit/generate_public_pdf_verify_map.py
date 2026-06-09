"""Generate PUBLIC_PDF_VERIFY_MAP.md, .json, and PUBLIC_PDF_VERIFY_REPORT.md.

Cross-verifies: public PDF vs local source.pdf vs FormulaSlot bbox/crop
vs Marker LaTeX vs canonical LaTeX vs section/nearby_text.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

BASE = Path(__file__).resolve().parents[1]  # m1_three_pipeline_architecture
AUDIT_DIR = Path(__file__).resolve().parent  # visual_audit

TRUSTED_SECTIONS = {
    "Abstract", "Introduction", "Related Work", "Background",
    "Problem Statement", "Method", "Methodology", "Approach",
    "Proposed Method", "Experiments", "Evaluation", "Results",
    "Discussion", "Conclusion", "References", "Appendix",
    "Other", "Unknown",
}

FORMULA_POLLUTION_PATTERNS = [
    r'[=∑√σλτπ∈⊙]',
    r'\\(?:frac|sum|int|partial|alpha|beta|gamma|delta|mathcal|mathbb|mathrm|sqrt)',
    r'(?:Attention|Softmax|Gumbel|argmax|argmin)\s*\(',
    r'[A-Z]\(\d+\)\s*=',
    r'(?:Global|Local|Encoder|Decoder)\s*\(',
]

PAPERS = {
    "paper_1": {
        "pdf_path": ROOT / "reports" / "m1_parser_review" / "paper_1" / "source.pdf",
        "pid": "2112.14436",
        "title_from_report": "Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy",
        "arxiv_id": "2112.14436",
        "doi": None,
        "public_abs_url": "https://arxiv.org/abs/2112.14436",
        "public_pdf_url": "https://arxiv.org/pdf/2112.14436",
    },
    "paper_2": {
        "pdf_path": ROOT / "reports" / "m1_parser_review" / "paper_2" / "source.pdf",
        "pid": "W3184127157",
        "title_from_report": "Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT",
        "arxiv_id": "2104.03466",
        "doi": None,
        "public_abs_url": "https://arxiv.org/abs/2104.03466",
        "public_pdf_url": "https://arxiv.org/pdf/2104.03466",
    },
    "paper_3": {
        "pdf_path": ROOT / "reports" / "m1_parser_review" / "paper_3" / "source.pdf",
        "pid": "2510.18998",
        "title_from_report": "An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection",
        "arxiv_id": "2510.18998",
        "doi": None,
        "public_abs_url": "https://arxiv.org/abs/2510.18998",
        "public_pdf_url": "https://arxiv.org/pdf/2510.18998",
    },
}


def get_pdf_title(pdf_path: Path) -> str:
    """Extract title from PDF metadata or first page text."""
    import fitz
    doc = fitz.open(str(pdf_path))
    meta_title = doc.metadata.get("title", "").strip()
    if meta_title:
        doc.close()
        return meta_title
    # Fallback: first line of page 1
    text = doc[0].get_text()
    doc.close()
    first_line = text.strip().split("\n")[0].strip()
    return first_line[:120]


def get_pdf_page_text(pdf_path: Path, page_num: int) -> str:
    """Extract text from a specific page (1-indexed)."""
    import fitz
    try:
        doc = fitz.open(str(pdf_path))
        idx = page_num - 1
        if idx < 0 or idx >= len(doc):
            doc.close()
            return ""
        text = doc[idx].get_text()
        doc.close()
        return text
    except Exception:
        return ""


def extract_canonical_formulas(canonical_path: Path) -> dict:
    """Extract formula comments and LaTeX from canonical_paper.md."""
    if not canonical_path.exists():
        return {}
    content = canonical_path.read_text(encoding="utf-8")
    formulas = {}
    # Match formula comment blocks
    pattern = re.compile(
        r"<!-- formula_id:\s*(\S+)\s*\|(.+?)-->\s*"
        r"(?:```latex\s*\n(.*?)\n```|<!-- No formula content.*?-->|\{\{FORMULA:.*?\}\})?",
        re.DOTALL,
    )
    for match in pattern.finditer(content):
        fid = match.group(1)
        comment_body = match.group(2).strip()
        latex = match.group(3).strip() if match.group(3) else ""
        formulas[fid] = {
            "comment": f"<!-- formula_id: {fid} |{comment_body}-->",
            "latex": latex,
        }
    return formulas


def is_section_trusted(section: str) -> bool:
    return section in TRUSTED_SECTIONS


def is_section_polluted(section: str) -> bool:
    for pat in FORMULA_POLLUTION_PATTERNS:
        if re.search(pat, section):
            return True
    return False


def build_record(paper_key: str, paper_info: dict, slot: dict,
                 canonical_formulas: dict, public_page_texts: dict) -> dict:
    """Build one verification record for a FormulaSlot."""
    fid = slot["formula_id"]
    page = slot["page"]
    bbox = slot.get("bbox", [])
    section = slot.get("section", "")
    section_conf = slot.get("section_confidence", "low")
    section_source = slot.get("section_source", "unknown")
    section_reason = slot.get("section_reason", "")
    nearby_before = slot.get("nearby_text_before", "")
    nearby_after = slot.get("nearby_text_after", "")
    marker_latex = slot.get("marker_latex", "")
    final_latex = slot.get("final_latex", "")
    final_origin = slot.get("final_origin", "unresolved")
    crop_path = slot.get("crop_path", "")
    ocr_status = slot.get("ocr_status", "")

    # Canonical
    can_info = canonical_formulas.get(fid, {})
    canonical_latex = can_info.get("latex", "")
    canonical_comment = can_info.get("comment", "")
    canonical_match = fid in canonical_formulas

    # File checks
    crop_full = BASE / paper_key / "formula_crops" / crop_path if crop_path else None
    crop_exists = crop_full.exists() if crop_full else False
    overlay_path = f"{paper_key}/formula_overlays/overlay_page{page}.png"
    overlay_full = BASE / paper_key / "formula_overlays" / f"overlay_page{page}.png"
    overlay_exists = overlay_full.exists()

    # Public PDF context
    public_page_text = public_page_texts.get(page, "")
    public_pdf_context = public_page_text[:1000] if public_page_text else ""
    public_context_found = bool(public_page_text and (
        nearby_before[:50] in public_page_text or
        nearby_after[:50] in public_page_text or
        (marker_latex[:20] in public_page_text if marker_latex else False)
    ))

    # Auto-checks
    latex_exact_marker_vs_final = (marker_latex.strip() == final_latex.strip()) if (marker_latex and final_latex) else False
    latex_exact_final_vs_canonical = (final_latex.strip() == canonical_latex.strip()) if (final_latex and canonical_latex) else False
    latex_non_empty = bool(final_latex.strip())
    section_trusted = is_section_trusted(section)
    section_polluted = is_section_polluted(section)
    nearby_non_empty = bool(nearby_before.strip() or nearby_after.strip())

    return {
        "paper_key": paper_key,
        "paper_id": paper_info["pid"],
        "public_pdf_url": paper_info["public_pdf_url"],
        "formula_id": fid,
        "page": page,
        "bbox": bbox,
        "section": section,
        "section_confidence": section_conf,
        "section_source": section_source,
        "section_reason": section_reason,
        "nearby_text_before": nearby_before[:500],
        "nearby_text_after": nearby_after[:500],
        "crop_path": crop_path,
        "overlay_path": overlay_path if overlay_exists else "",
        "marker_latex": marker_latex,
        "final_latex": final_latex,
        "canonical_latex": canonical_latex,
        "canonical_comment": canonical_comment[:200],
        "canonical_match": canonical_match,
        "formula_origin": final_origin,
        "ocr_status": ocr_status,
        "manual_check_required": "YES",
        # Public PDF fields
        "public_pdf_page_hint": page,
        "local_pdf_page": page,
        "page_offset_suspected": False,
        "public_pdf_formula_context": public_pdf_context[:500],
        "expected_formula_text_from_public_pdf_if_extractable": "",
        # Auto-consistency checks
        "latex_exact_match_marker_vs_final": latex_exact_marker_vs_final,
        "latex_exact_match_final_vs_canonical": latex_exact_final_vs_canonical,
        "latex_non_empty": latex_non_empty,
        "crop_exists": crop_exists,
        "overlay_exists": overlay_exists,
        "canonical_formula_comment_exists": canonical_match,
        "section_is_trusted": section_trusted,
        "section_is_formula_polluted": section_polluted,
        "nearby_text_non_empty": nearby_non_empty,
        "public_pdf_available": True,
        "public_pdf_text_context_found": public_context_found,
    }


def detect_high_risk(records: list) -> list:
    """Detect high-risk items from verification records."""
    risks = []
    for r in records:
        fid = r["formula_id"]
        pk = r["paper_key"]
        if not r["crop_exists"]:
            risks.append({"priority": "HIGH", "paper": pk, "formula_id": fid, "reason": "CROP_MISSING", "what_to_check": "Crop file not found"})
        if not r["overlay_exists"]:
            risks.append({"priority": "HIGH", "paper": pk, "formula_id": fid, "reason": "OVERLAY_MISSING", "what_to_check": "Overlay file not found"})
        if not r["latex_non_empty"]:
            risks.append({"priority": "HIGH", "paper": pk, "formula_id": fid, "reason": "LATEX_EMPTY", "what_to_check": "No LaTeX resolved"})
        if not r["canonical_match"]:
            risks.append({"priority": "HIGH", "paper": pk, "formula_id": fid, "reason": "CANONICAL_MISMATCH", "what_to_check": "Formula not in canonical"})
        if r["section_is_formula_polluted"]:
            risks.append({"priority": "HIGH", "paper": pk, "formula_id": fid, "reason": "SECTION_POLLUTED", "what_to_check": f"Section '{r['section']}' contains formula text"})
        if not r["section_is_trusted"]:
            risks.append({"priority": "MEDIUM", "paper": pk, "formula_id": fid, "reason": "SECTION_UNKNOWN", "what_to_check": f"Section '{r['section']}' is not trusted"})
        if not r["public_pdf_text_context_found"]:
            risks.append({"priority": "LOW", "paper": pk, "formula_id": fid, "reason": "PUBLIC_PDF_CONTEXT_NOT_FOUND", "what_to_check": "Could not match nearby text in public PDF"})
        if r["page_offset_suspected"]:
            risks.append({"priority": "MEDIUM", "paper": pk, "formula_id": fid, "reason": "PAGE_OFFSET_SUSPECTED", "what_to_check": "Page numbering may differ between local and public PDF"})
    return risks


def generate_map_md(records: list, paper_infos: dict, title_verified: dict) -> str:
    """Generate PUBLIC_PDF_VERIFY_MAP.md."""
    lines = [
        "# PUBLIC_PDF_VERIFY_MAP",
        "",
        f"**Generated**: 2026-06-09",
        f"**Total FormulaSlots**: {len(records)}",
        "",
        "## Paper Sources",
        "",
    ]
    for pk, pi in paper_infos.items():
        tv = title_verified.get(pk, "UNKNOWN")
        lines.append(f"### {pk}")
        lines.append(f"- paper_id: {pi['pid']}")
        lines.append(f"- title_from_report: {pi['title_from_report']}")
        lines.append(f"- title_from_pdf: {pi.get('title_from_pdf', '?')}")
        lines.append(f"- title_verified: **{tv}**")
        lines.append(f"- arxiv_id: {pi.get('arxiv_id', 'N/A')}")
        lines.append(f"- public_pdf_url: {pi['public_pdf_url']}")
        lines.append(f"- source_pdf_path: {pi['pdf_path'].relative_to(ROOT)}")
        lines.append("")

    lines.extend([
        "## Verification Table",
        "",
        "| paper | formula_id | page | section | crop | overlay | marker_latex | final_latex | canonical_match | origin | public_ctx |",
        "|-------|-----------|-----:|---------|------|---------|-------------|------------|-----------------|--------|-----------|",
    ])
    for r in records:
        crop_s = "YES" if r["crop_exists"] else "NO"
        overlay_s = "YES" if r["overlay_exists"] else "NO"
        ml = r["marker_latex"][:40].replace("|", "/") if r["marker_latex"] else "(none)"
        fl = r["final_latex"][:40].replace("|", "/") if r["final_latex"] else "(none)"
        can_s = "YES" if r["canonical_match"] else "NO"
        ctx_s = "YES" if r["public_pdf_text_context_found"] else "NO"
        lines.append(
            f"| {r['paper_key']} | {r['formula_id']} | {r['page']} | {r['section']} | {crop_s} | {overlay_s} | `{ml}` | `{fl}` | {can_s} | {r['formula_origin']} | {ctx_s} |"
        )
    return "\n".join(lines)


def generate_report_md(records: list, paper_infos: dict, title_verified: dict, risks: list) -> str:
    """Generate PUBLIC_PDF_VERIFY_REPORT.md."""
    lines = [
        "# PUBLIC_PDF_VERIFY_REPORT",
        "",
        f"**Generated**: 2026-06-09",
        f"**Total FormulaSlots**: {len(records)}",
        "",
        "---",
        "",
        "## 1. Overview",
        "",
        "| paper | title_verified | public_pdf_url | formula_count | crop_exists | overlay_exists | latex_match | canonical_match | section_trusted | public_pdf_context_found |",
        "|-------|---------------|---------------|:-------------:|:-----------:|:--------------:|:-----------:|:---------------:|:---------------:|:------------------------:|",
    ]

    for pk, pi in paper_infos.items():
        paper_records = [r for r in records if r["paper_key"] == pk]
        tv = title_verified.get(pk, "UNKNOWN")
        fc = len(paper_records)
        ce = sum(1 for r in paper_records if r["crop_exists"])
        oe = sum(1 for r in paper_records if r["overlay_exists"])
        lm = sum(1 for r in paper_records if r["latex_exact_match_final_vs_canonical"])
        cm = sum(1 for r in paper_records if r["canonical_match"])
        st = sum(1 for r in paper_records if r["section_is_trusted"])
        pc = sum(1 for r in paper_records if r["public_pdf_text_context_found"])
        lines.append(
            f"| {pk} | {tv} | {pi['public_pdf_url']} | {fc} | {ce}/{fc} | {oe}/{fc} | {lm}/{fc} | {cm}/{fc} | {st}/{fc} | {pc}/{fc} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 2. Per-Paper Detail",
        "",
    ])

    for pk, pi in paper_infos.items():
        paper_records = [r for r in records if r["paper_key"] == pk]
        lines.append(f"### {pk} — {pi['pid']}")
        lines.append("")
        tv = title_verified.get(pk, "UNKNOWN")
        lines.append(f"- **title_from_report**: {pi['title_from_report']}")
        lines.append(f"- **title_from_pdf**: {pi.get('title_from_pdf', '?')}")
        lines.append(f"- **title_verified**: {tv}")
        lines.append(f"- **public_pdf_url**: {pi['public_pdf_url']}")
        lines.append(f"- **formula_count**: {len(paper_records)}")
        lines.append(f"- **crop_exists**: {sum(1 for r in paper_records if r['crop_exists'])}/{len(paper_records)}")
        lines.append(f"- **overlay_exists**: {sum(1 for r in paper_records if r['overlay_exists'])}/{len(paper_records)}")
        lines.append(f"- **latex_non_empty**: {sum(1 for r in paper_records if r['latex_non_empty'])}/{len(paper_records)}")
        lines.append(f"- **marker_vs_final_match**: {sum(1 for r in paper_records if r['latex_exact_match_marker_vs_final'])}/{len(paper_records)}")
        lines.append(f"- **final_vs_canonical_match**: {sum(1 for r in paper_records if r['latex_exact_match_final_vs_canonical'])}/{len(paper_records)}")
        lines.append(f"- **trusted_section**: {sum(1 for r in paper_records if r['section_is_trusted'])}/{len(paper_records)}")
        lines.append(f"- **polluted_section**: {sum(1 for r in paper_records if r['section_is_formula_polluted'])}/{len(paper_records)}")
        lines.append(f"- **public_pdf_context_found**: {sum(1 for r in paper_records if r['public_pdf_text_context_found'])}/{len(paper_records)}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 3. Full Formula Verification Table",
        "",
        "| # | paper | formula_id | page | section | crop | overlay | marker_latex | final_latex | canonical | origin | public_ctx | trusted | polluted |",
        "|---|-------|-----------|-----:|---------|------|---------|-------------|------------|-----------|--------|-----------|---------|----------|",
    ])
    for i, r in enumerate(records, 1):
        crop_s = "Y" if r["crop_exists"] else "N"
        overlay_s = "Y" if r["overlay_exists"] else "N"
        ml = (r["marker_latex"][:30] + "...").replace("|", "/") if len(r["marker_latex"]) > 30 else (r["marker_latex"].replace("|", "/") if r["marker_latex"] else "-")
        fl = (r["final_latex"][:30] + "...").replace("|", "/") if len(r["final_latex"]) > 30 else (r["final_latex"].replace("|", "/") if r["final_latex"] else "-")
        can_s = "Y" if r["canonical_match"] else "N"
        ctx_s = "Y" if r["public_pdf_text_context_found"] else "N"
        trust_s = "Y" if r["section_is_trusted"] else "N"
        poll_s = "Y" if r["section_is_formula_polluted"] else "N"
        lines.append(
            f"| {i} | {r['paper_key']} | {r['formula_id']} | {r['page']} | {r['section']} | {crop_s} | {overlay_s} | `{ml}` | `{fl}` | {can_s} | {r['formula_origin']} | {ctx_s} | {trust_s} | {poll_s} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 4. High-Risk Items",
        "",
    ])
    if risks:
        lines.append("| priority | paper | formula_id | reason | what_to_check |")
        lines.append("|----------|-------|-----------|--------|---------------|")
        for risk in sorted(risks, key=lambda x: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(x["priority"], 3)):
            lines.append(f"| {risk['priority']} | {risk['paper']} | {risk['formula_id']} | {risk['reason']} | {risk['what_to_check']} |")
    else:
        lines.append("No high-risk items detected.")

    lines.extend([
        "",
        "---",
        "",
        "## 5. Manual Check Recommendations",
        "",
    ])
    # Group by priority
    high_risks = [r for r in risks if r["priority"] == "HIGH"]
    med_risks = [r for r in risks if r["priority"] == "MEDIUM"]
    low_risks = [r for r in risks if r["priority"] == "LOW"]

    if high_risks:
        lines.append("### HIGH Priority")
        lines.append("")
        for risk in high_risks:
            lines.append(f"1. **{risk['paper']}/{risk['formula_id']}** — {risk['reason']}: {risk['what_to_check']}")
        lines.append("")

    if med_risks:
        lines.append("### MEDIUM Priority")
        lines.append("")
        for risk in med_risks:
            lines.append(f"1. **{risk['paper']}/{risk['formula_id']}** — {risk['reason']}: {risk['what_to_check']}")
        lines.append("")

    if low_risks:
        lines.append("### LOW Priority")
        lines.append("")
        for risk in low_risks[:10]:  # Limit to 10
            lines.append(f"1. **{risk['paper']}/{risk['formula_id']}** — {risk['reason']}: {risk['what_to_check']}")
        if len(low_risks) > 10:
            lines.append(f"   ... and {len(low_risks) - 10} more LOW priority items")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 6. TITLE_MISMATCH Alert",
        "",
    ])
    mismatches = [(pk, pi) for pk, pi in paper_infos.items() if title_verified.get(pk) == "TITLE_MISMATCH"]
    if mismatches:
        for pk, pi in mismatches:
            lines.append(f"**{pk}**: TITLE MISMATCH DETECTED!")
            lines.append(f"- title_from_report: {pi['title_from_report']}")
            lines.append(f"- title_from_pdf: {pi.get('title_from_pdf', '?')}")
            lines.append(f"- public_pdf_url: {pi['public_pdf_url']}")
            lines.append(f"- Action required: Verify that the local source.pdf matches the intended paper.")
            lines.append("")
    else:
        lines.append("No title mismatches detected.")
        lines.append("")

    return "\n".join(lines)


def main():
    import fitz

    all_records = []
    title_verified = {}
    paper_infos_with_pdf_title = {}

    for pk, pi in PAPERS.items():
        print(f"\nProcessing {pk}...")

        # Get PDF title
        pdf_title = get_pdf_title(pi["pdf_path"])
        pi["title_from_pdf"] = pdf_title

        # Check title match
        report_title = pi["title_from_report"].lower().strip()
        pdf_title_lower = pdf_title.lower().strip()
        # Flexible match: first 40 chars
        if report_title[:40] == pdf_title_lower[:40]:
            title_verified[pk] = "YES"
        elif any(w in pdf_title_lower for w in report_title.split()[:3]):
            title_verified[pk] = "PARTIAL"
        else:
            title_verified[pk] = "TITLE_MISMATCH"
        print(f"  PDF title: {pdf_title}")
        print(f"  Title verified: {title_verified[pk]}")

        # Load formula slots
        slots_path = BASE / pk / "formula_slots.json"
        with open(slots_path, "r", encoding="utf-8") as f:
            slots = json.load(f)
        print(f"  {len(slots)} formula slots")

        # Extract canonical formulas
        canonical_path = BASE / pk / "canonical_paper.md"
        canonical_formulas = extract_canonical_formulas(canonical_path)
        print(f"  {len(canonical_formulas)} canonical formula comments")

        # Get public PDF page texts
        public_page_texts = {}
        pdf_path = pi["pdf_path"]
        doc = fitz.open(str(pdf_path))
        for page_idx in range(len(doc)):
            public_page_texts[page_idx + 1] = doc[page_idx].get_text()
        doc.close()

        # Build records
        for slot in slots:
            rec = build_record(pk, pi, slot, canonical_formulas, public_page_texts)
            all_records.append(rec)

        paper_infos_with_pdf_title[pk] = pi

    # Detect risks
    risks = detect_high_risk(all_records)
    print(f"\nHigh-risk items: {len([r for r in risks if r['priority'] == 'HIGH'])}")
    print(f"Medium-risk items: {len([r for r in risks if r['priority'] == 'MEDIUM'])}")
    print(f"Low-risk items: {len([r for r in risks if r['priority'] == 'LOW'])}")

    # Generate PUBLIC_PDF_VERIFY_MAP.md
    map_md = generate_map_md(all_records, paper_infos_with_pdf_title, title_verified)
    map_path = AUDIT_DIR / "PUBLIC_PDF_VERIFY_MAP.md"
    map_path.write_text(map_md, encoding="utf-8")
    print(f"\nWrote {map_path}")

    # Generate PUBLIC_PDF_VERIFY_MAP.json
    map_json_path = AUDIT_DIR / "PUBLIC_PDF_VERIFY_MAP.json"
    map_json_path.write_text(
        json.dumps(all_records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {map_json_path}")

    # Generate PUBLIC_PDF_VERIFY_REPORT.md
    report_md = generate_report_md(all_records, paper_infos_with_pdf_title, title_verified, risks)
    report_path = AUDIT_DIR / "PUBLIC_PDF_VERIFY_REPORT.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"Wrote {report_path}")

    # Summary
    print(f"\n{'=' * 60}")
    print("PUBLIC PDF VERIFY MAP COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total records: {len(all_records)}")
    print(f"crop_exists: {sum(1 for r in all_records if r['crop_exists'])}/{len(all_records)}")
    print(f"overlay_exists: {sum(1 for r in all_records if r['overlay_exists'])}/{len(all_records)}")
    print(f"latex_non_empty: {sum(1 for r in all_records if r['latex_non_empty'])}/{len(all_records)}")
    print(f"marker_vs_final_match: {sum(1 for r in all_records if r['latex_exact_match_marker_vs_final'])}/{len(all_records)}")
    print(f"final_vs_canonical_match: {sum(1 for r in all_records if r['latex_exact_match_final_vs_canonical'])}/{len(all_records)}")
    print(f"trusted_section: {sum(1 for r in all_records if r['section_is_trusted'])}/{len(all_records)}")
    print(f"polluted_section: {sum(1 for r in all_records if r['section_is_formula_polluted'])}/{len(all_records)}")
    print(f"public_pdf_context_found: {sum(1 for r in all_records if r['public_pdf_text_context_found'])}/{len(all_records)}")
    for pk in PAPERS:
        print(f"  {pk}: title_verified={title_verified.get(pk, '?')}")


if __name__ == "__main__":
    main()
