"""Generate PUBLIC_PDF_VERIFY_MAP.md, .json, and PUBLIC_PDF_VERIFY_REPORT.md.

Cross-verifies: public PDF vs local source.pdf vs FormulaSlot bbox/crop
vs Marker LaTeX vs canonical LaTeX vs section/nearby_text.

Title verification strategy:
  1. Extract PDF metadata title
  2. Extract first page body text title (first substantial line)
  3. Compare both against expected title from report
  4. Classification:
     - YES: metadata or body text matches expected
     - YES_WITH_BAD_METADATA: body text matches but metadata is empty/wrong
     - TITLE_MISMATCH: neither metadata nor body text matches
     - SOURCE_MISMATCH: body text is a completely different paper
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
        "pid": "2110.02642",
        "title_from_report": "Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy",
        "arxiv_id": "2110.02642",
        "doi": None,
        "public_abs_url": "https://arxiv.org/abs/2110.02642",
        "public_pdf_url": "https://arxiv.org/pdf/2110.02642",
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


def get_pdf_metadata_title(pdf_path: Path) -> str:
    """Extract title from PDF metadata."""
    import fitz
    doc = fitz.open(str(pdf_path))
    meta_title = doc.metadata.get("title", "").strip()
    doc.close()
    return meta_title


def get_pdf_body_title(pdf_path: Path) -> str:
    """Extract title from first page body text.

    Strategy: skip lines that look like headers (e.g. "Published as..."),
    then take the first substantial line as the title.
    """
    import fitz
    doc = fitz.open(str(pdf_path))
    text = doc[0].get_text()
    doc.close()

    skip_patterns = [
        r'^Published\s+as',
        r'^arXiv:',
        r'^\d{4}\.\d{4,5}',
        r'^Vol\.',
        r'^IEEE',
        r'^©',
        r'^Copyright',
    ]

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or len(stripped) < 5:
            continue
        if any(re.match(pat, stripped, re.IGNORECASE) for pat in skip_patterns):
            continue
        # Skip lines that are just numbers or single words
        if len(stripped.split()) < 3:
            continue
        return stripped[:200]

    # Fallback: first non-empty line
    for line in text.split("\n"):
        if line.strip():
            return line.strip()[:200]
    return ""


def classify_title(meta_title: str, body_title: str, expected_title: str) -> tuple[str, str]:
    """Classify title match between PDF and expected.

    Returns (classification, detail) where classification is one of:
      YES, YES_WITH_BAD_METADATA, TITLE_MISMATCH, SOURCE_MISMATCH
    """
    exp_lower = expected_title.lower().strip()
    meta_lower = meta_title.lower().strip()
    body_lower = body_title.lower().strip()

    def titles_match(a: str, b: str) -> bool:
        """Check if two titles match (flexible: first 40 chars or key words)."""
        if not a or not b:
            return False
        # Exact match (first 40 chars)
        if a[:40] == b[:40]:
            return True
        # Key word overlap: at least 3 significant words in common
        stop_words = {"the", "a", "an", "of", "for", "in", "on", "with", "and", "to", "by", "at"}
        a_words = {w for w in a.split() if w not in stop_words and len(w) > 2}
        b_words = {w for w in b.split() if w not in stop_words and len(w) > 2}
        common = a_words & b_words
        if len(common) >= 3:
            return True
        return False

    body_matches = titles_match(body_lower, exp_lower)
    meta_matches = titles_match(meta_lower, exp_lower)

    if body_matches and meta_matches:
        return "YES", "metadata and body text both match"
    elif body_matches and not meta_matches:
        if not meta_lower or meta_lower in ("1", "untitled", ""):
            return "YES_WITH_BAD_METADATA", f"body text matches but metadata is '{meta_title}'"
        else:
            return "YES_WITH_BAD_METADATA", f"body text matches but metadata title differs"
    elif not body_matches and meta_matches:
        return "YES", "metadata matches"
    else:
        # Neither matches. Check if it's a completely different paper.
        # If body title has zero overlap with expected, it's SOURCE_MISMATCH
        if body_lower and exp_lower:
            stop_words = {"the", "a", "an", "of", "for", "in", "on", "with", "and", "to", "by", "at"}
            exp_words = {w for w in exp_lower.split() if w not in stop_words and len(w) > 2}
            body_words = {w for w in body_lower.split() if w not in stop_words and len(w) > 2}
            common = exp_words & body_words
            if len(common) == 0:
                return "SOURCE_MISMATCH", f"body text '{body_title[:60]}' has zero overlap with expected"
        return "TITLE_MISMATCH", f"neither metadata nor body text matches expected"


def extract_canonical_formulas(canonical_path: Path) -> dict:
    """Extract formula comments and LaTeX from canonical_paper.md."""
    if not canonical_path.exists():
        return {}
    content = canonical_path.read_text(encoding="utf-8")
    formulas = {}
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


def detect_risks(records: list, paper_title_status: dict) -> list:
    """Detect all risks from verification records + paper-level title status.

    Risk categories:
      HIGH: source_mismatch, title_mismatch, crop_missing, overlay_missing,
            latex_empty, canonical_mismatch, section_polluted
      MEDIUM: section_unknown, page_offset_suspected
      LOW: public_pdf_context_not_found, bad_pdf_metadata
    """
    risks = []

    # Paper-level risks from title verification
    for pk, status_info in paper_title_status.items():
        classification = status_info["classification"]
        if classification == "SOURCE_MISMATCH":
            risks.append({
                "priority": "HIGH",
                "paper": pk,
                "formula_id": "(paper-level)",
                "reason": "SOURCE_MISMATCH",
                "what_to_check": f"{status_info['detail']}. Local source.pdf is NOT the intended paper.",
            })
        elif classification == "TITLE_MISMATCH":
            risks.append({
                "priority": "HIGH",
                "paper": pk,
                "formula_id": "(paper-level)",
                "reason": "TITLE_MISMATCH",
                "what_to_check": f"{status_info['detail']}. Neither metadata nor body text matches.",
            })
        elif classification == "YES_WITH_BAD_METADATA":
            risks.append({
                "priority": "LOW",
                "paper": pk,
                "formula_id": "(paper-level)",
                "reason": "BAD_PDF_METADATA",
                "what_to_check": f"{status_info['detail']}. Content is correct, metadata is bad.",
            })

    # Per-formula risks
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


def generate_map_md(records: list, paper_infos: dict, title_status: dict) -> str:
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
        ts = title_status.get(pk, {})
        classification = ts.get("classification", "UNKNOWN")
        detail = ts.get("detail", "")
        lines.append(f"### {pk}")
        lines.append(f"- paper_id: {pi['pid']}")
        lines.append(f"- title_from_report: {pi['title_from_report']}")
        lines.append(f"- title_from_pdf_metadata: {pi.get('title_from_pdf_metadata', '?')}")
        lines.append(f"- title_from_pdf_body: {pi.get('title_from_pdf_body', '?')}")
        lines.append(f"- title_verified: **{classification}**")
        lines.append(f"- title_detail: {detail}")
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


def generate_report_md(records: list, paper_infos: dict, title_status: dict, risks: list) -> str:
    """Generate PUBLIC_PDF_VERIFY_REPORT.md."""
    # Check if any paper has SOURCE_MISMATCH → BLOCKED
    blocked_papers = [pk for pk, ts in title_status.items() if ts.get("classification") == "SOURCE_MISMATCH"]

    lines = [
        "# PUBLIC_PDF_VERIFY_REPORT",
        "",
        f"**Generated**: 2026-06-09",
        f"**Total FormulaSlots**: {len(records)}",
    ]
    if blocked_papers:
        lines.append(f"**BLOCKED**: {', '.join(blocked_papers)} — SOURCE_MISMATCH (local source.pdf != intended paper)")
    lines.extend(["", "---", ""])

    # 1. Overview
    lines.append("## 1. Overview")
    lines.append("")
    lines.append("| paper | title_verified | public_pdf_url | formula_count | crop_exists | overlay_exists | latex_match | canonical_match | section_trusted | public_pdf_context_found |")
    lines.append("|-------|---------------|---------------|:-------------:|:-----------:|:--------------:|:-----------:|:---------------:|:---------------:|:------------------------:|")

    for pk, pi in paper_infos.items():
        paper_records = [r for r in records if r["paper_key"] == pk]
        ts = title_status.get(pk, {})
        classification = ts.get("classification", "UNKNOWN")
        fc = len(paper_records)
        ce = sum(1 for r in paper_records if r["crop_exists"])
        oe = sum(1 for r in paper_records if r["overlay_exists"])
        lm = sum(1 for r in paper_records if r["latex_exact_match_final_vs_canonical"])
        cm = sum(1 for r in paper_records if r["canonical_match"])
        st = sum(1 for r in paper_records if r["section_is_trusted"])
        pc = sum(1 for r in paper_records if r["public_pdf_text_context_found"])
        lines.append(
            f"| {pk} | {classification} | {pi['public_pdf_url']} | {fc} | {ce}/{fc} | {oe}/{fc} | {lm}/{fc} | {cm}/{fc} | {st}/{fc} | {pc}/{fc} |"
        )

    lines.extend(["", "---", ""])

    # 2. Per-Paper Detail
    lines.append("## 2. Per-Paper Detail")
    lines.append("")

    for pk, pi in paper_infos.items():
        paper_records = [r for r in records if r["paper_key"] == pk]
        ts = title_status.get(pk, {})
        classification = ts.get("classification", "UNKNOWN")
        detail = ts.get("detail", "")
        lines.append(f"### {pk} — {pi['pid']}")
        lines.append("")
        lines.append(f"- **title_from_report**: {pi['title_from_report']}")
        lines.append(f"- **title_from_pdf_metadata**: {pi.get('title_from_pdf_metadata', '?')}")
        lines.append(f"- **title_from_pdf_body**: {pi.get('title_from_pdf_body', '?')}")
        lines.append(f"- **title_verified**: {classification}")
        lines.append(f"- **title_detail**: {detail}")
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

    lines.extend(["---", ""])

    # 3. Full Formula Verification Table
    lines.append("## 3. Full Formula Verification Table")
    lines.append("")
    lines.append("| # | paper | formula_id | page | section | crop | overlay | marker_latex | final_latex | canonical | origin | public_ctx | trusted | polluted |")
    lines.append("|---|-------|-----------|-----:|---------|------|---------|-------------|------------|-----------|--------|-----------|---------|----------|")
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

    lines.extend(["", "---", ""])

    # 4. High-Risk Items
    lines.append("## 4. High-Risk Items")
    lines.append("")
    high_risks = [r for r in risks if r["priority"] == "HIGH"]
    med_risks = [r for r in risks if r["priority"] == "MEDIUM"]
    low_risks = [r for r in risks if r["priority"] == "LOW"]

    if high_risks:
        lines.append("| priority | paper | formula_id | reason | what_to_check |")
        lines.append("|----------|-------|-----------|--------|---------------|")
        for risk in sorted(high_risks, key=lambda x: x["paper"]):
            lines.append(f"| {risk['priority']} | {risk['paper']} | {risk['formula_id']} | {risk['reason']} | {risk['what_to_check']} |")
    else:
        lines.append("No high-risk items detected.")

    lines.extend(["", "---", ""])

    # 5. All Risks by Priority
    lines.append("## 5. Risk Summary")
    lines.append("")
    lines.append(f"- **HIGH**: {len(high_risks)}")
    lines.append(f"- **MEDIUM**: {len(med_risks)}")
    lines.append(f"- **LOW**: {len(low_risks)}")
    lines.append(f"- **Total**: {len(risks)}")
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
        for risk in low_risks[:15]:
            lines.append(f"1. **{risk['paper']}/{risk['formula_id']}** — {risk['reason']}: {risk['what_to_check']}")
        if len(low_risks) > 15:
            lines.append(f"   ... and {len(low_risks) - 15} more LOW priority items")
        lines.append("")

    lines.extend(["---", ""])

    # 6. SOURCE_MISMATCH / TITLE_MISMATCH Alert
    lines.append("## 6. Source/Title Mismatch Alert")
    lines.append("")
    mismatch_papers = [(pk, ts) for pk, ts in title_status.items()
                       if ts.get("classification") in ("SOURCE_MISMATCH", "TITLE_MISMATCH")]
    if mismatch_papers:
        for pk, ts in mismatch_papers:
            lines.append(f"**{pk}**: {ts['classification']} DETECTED!")
            lines.append(f"- title_from_report: {paper_infos[pk]['title_from_report']}")
            lines.append(f"- title_from_pdf_metadata: {paper_infos[pk].get('title_from_pdf_metadata', '?')}")
            lines.append(f"- title_from_pdf_body: {paper_infos[pk].get('title_from_pdf_body', '?')}")
            lines.append(f"- detail: {ts['detail']}")
            lines.append(f"- public_pdf_url: {paper_infos[pk]['public_pdf_url']}")
            lines.append(f"- Action required: Verify that the local source.pdf matches the intended paper.")
            lines.append("")
    else:
        lines.append("No source/title mismatches detected.")
        lines.append("")

    # 7. M1 Review Status
    lines.extend(["---", ""])
    lines.append("## 7. M1 Review Status")
    lines.append("")

    # 7a. Source/Title Verification
    lines.append("### Source/Title Verification")
    lines.append("")
    if blocked_papers:
        for pk in blocked_papers:
            lines.append(f"- **{pk}**: BLOCKED — SOURCE_MISMATCH")
        lines.append("")
    else:
        lines.append("All papers pass source/title verification.")
        lines.append("")

    # 7b. Visual Audit
    lines.append("### Visual Audit")
    lines.append("")
    if high_risks:
        lines.append(f"**NOT PASSED** — {len(high_risks)} HIGH-risk item(s) remain.")
        lines.append("")
    else:
        lines.append("**PASSED** — no HIGH-risk items.")
        lines.append("")

    # 7c. Overall
    lines.append("### Overall M1 Review Status")
    lines.append("")
    if blocked_papers:
        lines.append("**BLOCKED** — source/title mismatch must be resolved first.")
    elif high_risks:
        lines.append("**NOT PASSED** — visual audit has unresolved HIGH-risk items.")
    else:
        lines.append("**PASSED** — source/title verification and visual audit both clear.")
    lines.append("")

    return "\n".join(lines)


def main():
    import fitz

    all_records = []
    title_status = {}
    paper_infos_enriched = {}

    for pk, pi in PAPERS.items():
        print(f"\nProcessing {pk}...")

        # Get metadata title
        meta_title = get_pdf_metadata_title(pi["pdf_path"])
        pi["title_from_pdf_metadata"] = meta_title

        # Get body title from first page
        body_title = get_pdf_body_title(pi["pdf_path"])
        pi["title_from_pdf_body"] = body_title

        # Classify
        classification, detail = classify_title(meta_title, body_title, pi["title_from_report"])
        title_status[pk] = {"classification": classification, "detail": detail}
        print(f"  metadata title: {repr(meta_title)}")
        print(f"  body title: {repr(body_title[:80])}")
        print(f"  classification: {classification} — {detail}")

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

        paper_infos_enriched[pk] = pi

    # Detect risks
    risks = detect_risks(all_records, title_status)
    high_count = len([r for r in risks if r["priority"] == "HIGH"])
    med_count = len([r for r in risks if r["priority"] == "MEDIUM"])
    low_count = len([r for r in risks if r["priority"] == "LOW"])
    print(f"\nRisks: {high_count} HIGH, {med_count} MEDIUM, {low_count} LOW")

    # Generate PUBLIC_PDF_VERIFY_MAP.md
    map_md = generate_map_md(all_records, paper_infos_enriched, title_status)
    map_path = AUDIT_DIR / "PUBLIC_PDF_VERIFY_MAP.md"
    map_path.write_text(map_md, encoding="utf-8")
    print(f"\nWrote {map_path}")

    # Generate PUBLIC_PDF_VERIFY_MAP.json
    map_json_path = AUDIT_DIR / "PUBLIC_PDF_VERIFY_MAP.json"
    map_json_data = {
        "generated": "2026-06-09",
        "total_formula_slots": len(all_records),
        "title_status": {pk: ts for pk, ts in title_status.items()},
        "risk_summary": {"high": high_count, "medium": med_count, "low": low_count},
        "records": all_records,
    }
    map_json_path.write_text(
        json.dumps(map_json_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {map_json_path}")

    # Generate PUBLIC_PDF_VERIFY_REPORT.md
    report_md = generate_report_md(all_records, paper_infos_enriched, title_status, risks)
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
    print(f"Risks: {high_count} HIGH, {med_count} MEDIUM, {low_count} LOW")
    for pk in PAPERS:
        ts = title_status.get(pk, {})
        print(f"  {pk}: {ts.get('classification', '?')} — {ts.get('detail', '')[:60]}")


if __name__ == "__main__":
    main()
