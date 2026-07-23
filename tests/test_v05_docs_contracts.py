from pathlib import Path


REQUIRED_DOCS = [
    "REUSE_REPORT.md",
    "MODULE_CONTRACTS.md",
    "REVIEW_CHECKLIST.md",
    "GLOSSARY.md",
]


def test_required_engineering_docs_exist_and_have_core_sections():
    docs_dir = Path("docs")
    for name in REQUIRED_DOCS:
        path = docs_dir / name
        assert path.exists(), f"missing {path}"
        text = path.read_text(encoding="utf-8")
        assert "ResearchSensei" in text
        assert len(text) > 600


def test_module_contracts_cover_every_required_module():
    text = Path("docs/MODULE_CONTRACTS.md").read_text(encoding="utf-8")
    for module in [
        "query",
        "acquisition",
        "selection",
        "source_resolver",
        "ingestion",
        "grounding",
        "understanding",
        "teaching",
        "formula",
        "direction",
        "patterns",
        "learning",
        "interactive",
        "context",
        "llm",
        "render",
    ]:
        assert module in text, f"module '{module}' not found in MODULE_CONTRACTS.md"
    assert "Input" in text
    assert "Output" in text
    assert "Boundary" in text


def test_reuse_report_marks_external_tools_as_replaceable():
    text = Path("docs/REUSE_REPORT.md").read_text(encoding="utf-8")
    for tool in ["paper-search-mcp", "OpenCode Server", "OpenCode Go", "PyMuPDF"]:
        assert tool in text
    assert "OPTIONAL_ADAPTER" in text
    assert "替换" in text


def test_current_architecture_documents_single_pdf_agent_path():
    text = Path("docs/ARCHITECTURE.md").read_text(encoding="utf-8").lower()
    for phrase in [
        "literature discovery and acquisition",
        "paper analysis: one paper agent, two models",
        "reader workspace",
        "paper tutor: session-first full-paper tutoring",
        "never hidden by parser fallback",
    ]:
        assert phrase in text
