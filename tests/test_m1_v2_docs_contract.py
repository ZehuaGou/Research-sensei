from __future__ import annotations

from pathlib import Path


DOCS = [
    "docs/development/M1_LITERATURE_SEARCH.md",
    "docs/MODULE_CONTRACTS.md",
    "docs/DESIGN.md",
    "docs/STATUS.md",
    "docs/DEVELOPMENT.md",
    "docs/development/M2_1_PARSER.md",
    "docs/development/M5_ENGINEERING_RELIABILITY.md",
]


def test_m1_v2_docs_state_primary_parser_and_boundaries() -> None:
    combined = "\n".join(Path(path).read_text(encoding="utf-8") for path in DOCS)

    required = [
        "MinerU2.5-Pro via mineru-vl-utils is the primary M1 parser",
        "magic_pdf/do_parse is not an equivalent implementation",
        "Marker is fallback/audit baseline",
        "Ollama is an optional structured refiner",
        "Ollama must not modify latex, bbox, page, or source identity",
        "M1 gate blocks all-formulas-in-Abstract",
        "M1 gate blocks section contradiction",
        "M1 gate blocks source mismatch",
        "M1 gate blocks missing latex/crop/overlay",
    ]
    for phrase in required:
        assert phrase in combined


def test_status_doc_no_longer_marks_m1_v2_core_as_not_implemented() -> None:
    status = Path("docs/STATUS.md").read_text(encoding="utf-8")

    forbidden_rows = [
        "MinerU25ProAdapter (v2 PRIMARY) | not implemented",
        "LlamaSectionRefiner | not implemented",
        "StructureRefiner | not implemented",
        "M1 Quality Gate (v2) | not implemented",
    ]
    for row in forbidden_rows:
        assert row not in status
