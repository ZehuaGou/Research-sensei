from __future__ import annotations

from pathlib import Path

from researchsensei.canonical import MaterialNormalizer
from researchsensei.canonical.parser_quality import (
    extract_formula_candidates,
    formula_text_matches,
)
from researchsensei.schemas import CandidatePaper, ResolvedPaperSource
from researchsensei.schemas.enums import (
    CanonicalQualityStatus,
    CanonicalizationStatus,
    FormulaOrigin,
    PaperSourceStatus,
    PaperSourceType,
)


def _paper(**overrides) -> CandidatePaper:
    data = {
        "paper_id": "paper-x",
        "title": "A Parser Test Paper",
        "authors": ["A. Author"],
        "year": 2026,
        "venue": "TestConf",
        "source_confidence": "high",
        "metadata_confidence": "high",
        "pdf_downloaded": True,
        "pdf_available": True,
    }
    data.update(overrides)
    return CandidatePaper(**data)


def _source(path: Path) -> ResolvedPaperSource:
    return ResolvedPaperSource(
        paper_id="paper-x",
        title="A Parser Test Paper",
        status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,
        source_type=PaperSourceType.PDF,
        local_path=str(path),
        sha256="abc123",
        file_size=path.stat().st_size if path.exists() else 0,
    )


def test_section_parser_keeps_references_from_overwriting_introduction() -> None:
    text = """
Abstract
This is the abstract.
I. INTRODUCTION
Real introduction text about the method, sensors, and motivation.
III. METHODOLOGY
Real method text before any result table.
Table III: Results
Method
EDAD
IV. EXPERIMENTS
Real experiments text.
REFERENCES
[43] G. Moody and R. Mark, "The impact of the MIT-BIH arrhythmia database," 2001.
I. INTRODUCTION TO AUTOENCODERS
CoRR, vol. abs/2201.03898, 2022.
# <span id="page-9-0"></span>References
[44] HTML anchored reference entry.
"""
    sections = MaterialNormalizer()._parse_text_sections(text, "A Parser Test Paper")

    assert "Real introduction text" in sections["Introduction"]
    assert "[43]" not in sections["Introduction"]
    assert "INTRODUCTION TO AUTOENCODERS" in sections["References"]
    assert "HTML anchored reference entry" in sections["References"]
    assert "EDAD" in sections["Method"]


def test_contaminated_introduction_fails_quality_and_blocks_m2(tmp_path, monkeypatch) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%fake but not parsed in this test\n")
    sections = {
        "Abstract": "This paper proposes a real method.",
        "Introduction": "\n".join(
            f"[{i}] A. Author, \"Reference title,\" Conf., 20{i:02d}."
            for i in range(43, 52)
        ),
        "Method": "The method is only a stub here.",
        "Experiments": "The experiments are only a stub here.",
        "Conclusion": "The conclusion is only a stub here.",
        "References": "[1] Existing reference.",
    }

    def fake_extract_content(*args, **kwargs):
        return sections, [], "pymupdf", []

    normalizer = MaterialNormalizer()
    monkeypatch.setattr(normalizer, "_extract_content", fake_extract_content)

    result = normalizer.normalize(_paper(), _source(pdf_path), output_dir=tmp_path)

    assert result.canonical_quality_status == CanonicalQualityStatus.FAIL
    assert result.canonicalization_status == CanonicalizationStatus.FAILED
    assert result.m2_ready is False
    assert "Introduction contaminated by reference entries" in result.degradation_reason
    assert "canonical_quality_status: FAIL" in Path(result.canonical_paper_path).read_text(encoding="utf-8")


def test_marker_policy_defaults_are_visible_and_disabled() -> None:
    normalizer = MaterialNormalizer()

    assert normalizer.marker_enabled is False
    assert normalizer.marker_trigger_mode == "never"
    assert normalizer.marker_timeout_seconds > 0


def test_formula_candidate_extraction_keeps_latex_and_raw_text_separate() -> None:
    marker_text = r"""
$$p(\mathbf{x}|z) = \begin{cases}p^+(\mathbf{x}) & \text{if } z=0\end{cases}$$
The transition is $p(z_{t+1}|z_t)$ and the emission is \(p(\mathbf{x}_t|z_t=0)\).
\[
\operatorname{ELBO} = \mathbb{E}_q[\log p(x,z)]
\]
\begin{align}
p(\mathbf{x}_t|z_t=1) &= p^-(\mathbf{x}_t) \tag{3}
\end{align}
Attention(Q, K, V)
Prior-Association
Series-Association
AnomalyScore
"""

    candidates = extract_formula_candidates("marker_pdf", "", "", marker_text)
    latex_values = [c["latex"] for c in candidates if c["origin"] == FormulaOrigin.PARSER_LATEX.value]
    raw_values = [c for c in candidates if c["origin"] == FormulaOrigin.RAW_FORMULA_TEXT.value]

    assert any("p(\\mathbf{x}|z)" in value for value in latex_values)
    assert any("p(z_{t+1}|z_t)" in value for value in latex_values)
    assert any("ELBO" in value for value in latex_values)
    assert any("\\tag{3}" in value for value in latex_values)
    assert raw_values
    assert all(c["latex"] == "" and c["is_latex"] is False for c in raw_values)
    assert any(c["raw_formula_text"] == "Prior-Association" for c in raw_values)
    assert any(c["raw_formula_text"] == "Series-Association" for c in raw_values)
    assert any(c["raw_formula_text"] == "AnomalyScore" for c in raw_values)


def test_formula_coverage_matching_normalizes_spacing_symbols_and_case() -> None:
    assert formula_text_matches("Attention(Q,K,V)", "Attention(Q, K, V)")
    assert formula_text_matches("MultiHead(Q,K,V)", "multihead ( q , k , v )")
    assert formula_text_matches("AssDis(P,S;X)", "AssDis(P, S ; X)")
    assert formula_text_matches("sqrt(x) * y - z", "sqrt ( x ) * y - z")


def test_formula_dense_pages_scan_uses_pdf_page_fields(tmp_path) -> None:
    import fitz

    pdf_path = tmp_path / "math.pdf"
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Plain prose without many math tokens.")
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Attention(Q, K, V) = Softmax(QKT / sqrt(dk)); AssDis(P,S;X)")
    doc.save(str(pdf_path))
    doc.close()

    pages = MaterialNormalizer().find_formula_dense_pages_from_pdf(pdf_path)

    assert pages
    top = pages[0]
    assert top["page"] == 2
    assert top["math_token_count"] > 0
    assert top["density"] > 0
    assert top["sample_lines"]


def test_page_header_footer_blocks_marked_with_risk_flags() -> None:
    """Repeated page header titles should be marked with PAGE_HEADER_REPEATED risk flag."""
    from researchsensei.canonical.document_blocks import CanonicalDocumentBlock
    from researchsensei.canonical.structure_refiner import RuleBasedStructureRefiner

    blocks = [
        CanonicalDocumentBlock(
            block_id="title0", page=1, bbox=[10, 10, 100, 30],
            block_type="title", text="EdgeConvFormer Paper",
        ),
    ]
    # Simulate 20 pages with the same "EdgeConvFormer" header
    for i in range(1, 21):
        blocks.append(CanonicalDocumentBlock(
            block_id=f"header{i}", page=i + 1, bbox=[10, 10, 100, 30],
            block_type="title", text="EdgeConvFormer",
        ))
        blocks.append(CanonicalDocumentBlock(
            block_id=f"footer{i}", page=i + 1, bbox=[10, 750, 100, 770],
            block_type="text", text=f"Page {i} of 20",
        ))
        blocks.append(CanonicalDocumentBlock(
            block_id=f"author{i}", page=i + 1, bbox=[10, 780, 100, 800],
            block_type="text", text="Jie Liu et al.: Preprint submitted to Elsevier",
        ))
    blocks.append(CanonicalDocumentBlock(
        block_id="f001", page=5, bbox=[10, 100, 100, 120],
        block_type="formula", latex="x_t=f(h_t)",
    ))

    refiner = RuleBasedStructureRefiner()
    refiner.refine(blocks)

    # Repeated title blocks should be marked
    header_flags = [
        b.risk_flags for b in blocks
        if b.block_id.startswith("header") and "PAGE_HEADER_REPEATED" in b.risk_flags
    ]
    assert len(header_flags) == 20

    # Footer blocks should be marked
    footer_flags = [
        b.risk_flags for b in blocks
        if b.block_id.startswith("footer") and "PAGE_NUMBER_FOOTER" in b.risk_flags
    ]
    assert len(footer_flags) == 20

    # Author blocks should be marked
    author_flags = [
        b.risk_flags for b in blocks
        if b.block_id.startswith("author") and "AUTHOR_FOOTER" in b.risk_flags
    ]
    assert len(author_flags) == 20