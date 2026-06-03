# Phase 11.6 Detailed Playbook: ParserAdapter Design

> **Status**: Ready for detailed planning, NOT authorized for code.
> **Code development is NOT authorized until**:
> 1. This playbook is reviewed.
> 2. Execution template (`06_PHASE_EXECUTION_TEMPLATE.md`) is filled.
> 3. User explicitly confirms.
> 4. Then code may begin.

---

## 1. Final Goal

Design a `ParserAdapter` interface and wrap the existing `LightweightIngestionService` as a `LightweightParserAdapter`.

**What this phase does**:
- Define `ParserAdapter` ABC
- Implement `LightweightParserAdapter` wrapper
- Write contract tests

**What this phase does NOT do**:
- Does NOT change existing parser behavior
- Does NOT add new dependencies
- Does NOT integrate Docling/Nougat/Marker
- Does NOT modify pipeline, web API, frontend, or old backend
- Does NOT enter Phase 12

---

## 2. Current Code Facts

### LightweightIngestionService

- **Location**: `src/researchsensei/ingestion/lightweight.py`
- **Class**: `LightweightIngestionService`
- **Entry method**: `ingest_path(self, path: str | Path, paper_id: str | None = None) -> DocumentIngestion`
- **Return schema**: `DocumentIngestion` (from `src/researchsensei/schemas/document.py`)
- **Supported file types**: `.md`, `.txt`, `.pdf`
- **Unsupported file types**: Any other suffix → `degraded=True`, warning `UNSUPPORTED_FILE_TYPE`
- **PDF handling**: Uses PyMuPDF (`fitz`) if installed; if not, returns `degraded=True` with `PYMUPDF_MISSING` warning
- **Empty text**: Returns `degraded=True` with `NO_TEXT_EXTRACTED` warning, empty blocks
- **Warnings generated**: `UNSUPPORTED_FILE_TYPE`, `NO_TEXT_EXTRACTED`, `PYMUPDF_MISSING`, `PDF_PARSE_FAILED`, `PDF_TEXT_EMPTY`, `FORMULA_UNAVAILABLE`, `METHOD_SECTION_MISSING`, `EXPERIMENT_SECTION_MISSING`

### DocumentIngestion Schema

```python
class DocumentIngestion(SenseiModel):
    paper_id: str
    detected_language: str = "unknown"
    source_path: str = ""
    parser_name: str = "lightweight"
    degraded: bool = False
    warnings: list[WarningItem] = Field(default_factory=list)
    blocks: list[DocumentBlock] = Field(default_factory=list)
```

### WarningItem Schema

```python
class WarningItem(SenseiModel):
    code: str
    message: str
    detail: str = ""
```

### DocumentBlock Schema

```python
class DocumentBlock(SenseiModel):
    block_id: str
    type: BlockType
    text: str
    evidence_ref: str
    section: str = ""
    page: int | None = None
    normalized_text: str = ""
    offset_start: int = 0
    offset_end: int = 0
    raw_latex: str = ""
```

### Existing Tests

- **File**: `tests/test_lightweight_ingestion.py`
- **Tests**: 4 tests
  - `test_ingests_markdown_into_heading_paragraph_and_formula_blocks` — .md parsing
  - `test_ingests_txt_and_detects_chinese_language` — .txt + language detection
  - `test_invalid_pdf_degrades_without_crashing` — broken PDF degradation
  - `test_valid_pdf_extracts_text_when_pymupdf_is_available` — valid PDF (skips if no fitz)

---

## 3. File-Level Modification Plan

### Allowed to CREATE

| File | Purpose |
|------|---------|
| `src/researchsensei/parser/__init__.py` | Barrel export |
| `src/researchsensei/parser/adapter.py` | ParserAdapter ABC |
| `src/researchsensei/parser/lightweight_adapter.py` | LightweightParserAdapter wrapper |
| `tests/test_parser_adapter.py` | Contract tests |

### Allowed to MODIFY

| File | Changes |
|------|---------|
| `docs/PROGRESS.md` | Mark Phase 11.6 complete |
| `docs/OPEN_QUESTIONS.md` | Update if new questions |

### FORBIDDEN to modify

- `src/researchsensei/ingestion/**` (existing parser)
- `src/researchsensei/web/**` (API)
- `src/researchsensei/paper_card.py`, `formula_card.py`, `teaching_card.py` (card builders)
- `src/researchsensei/ingestion/pipeline.py` (pipeline)
- `frontend/**`
- `backend/**`
- `pyproject.toml`

---

## 4. Interface Definition

### ParserAdapter ABC

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from researchsensei.schemas.document import DocumentIngestion


class ParserAdapter(ABC):
    """Abstract interface for document parsers.

    Every parser adapter must:
    1. Accept a source file path and paper_id
    2. Return a DocumentIngestion
    3. Not write artifacts or update jobs
    4. Not generate paper_id (caller provides it)
    """

    @abstractmethod
    def supports(self, source: Path) -> bool:
        """Check if this adapter can handle the source file.

        Args:
            source: Path to the source file.

        Returns:
            True if this adapter can parse the file, False otherwise.
        """
        ...

    @abstractmethod
    def parse(self, source: Path, paper_id: str) -> DocumentIngestion:
        """Parse a source file into a DocumentIngestion.

        Args:
            source: Path to the source file.
            paper_id: Paper identifier (must be provided by caller).

        Returns:
            DocumentIngestion with parsed blocks.

        Raises:
            FileNotFoundError: If source does not exist (optional — adapter may degrade instead).
        """
        ...
```

**Rules**:
- `source` must be `Path`
- `paper_id` must be provided by caller — adapter must NOT generate it
- adapter must NOT write artifacts
- adapter must NOT update jobs
- adapter only returns `DocumentIngestion`

---

## 5. LightweightParserAdapter Implementation Requirements

### Constructor

```python
class LightweightParserAdapter(ParserAdapter):
    def __init__(self, ingestion: LightweightIngestionService | None = None) -> None:
        self._ingestion = ingestion or LightweightIngestionService()
```

- Accepts optional `LightweightIngestionService` for dependency injection
- Default creates `LightweightIngestionService()`

### supports() Method

```python
def supports(self, source: Path) -> bool:
    return source.suffix.lower() in {".md", ".txt", ".pdf"}
```

- Only supports `.md`, `.txt`, `.pdf`
- Suffix must be lower-cased before comparison
- `.markdown` is NOT supported (explicit decision)
- `.MD`, `.TXT`, `.PDF` are supported (case-insensitive)

### parse() Method

```python
def parse(self, source: Path, paper_id: str) -> DocumentIngestion:
    return self._ingestion.ingest_path(source, paper_id=paper_id)
```

- Directly delegates to `ingest_path(source, paper_id=paper_id)`
- Does NOT copy parser logic
- Does NOT change block generation rules
- Does NOT change warning rules
- Does NOT add any processing

---

## 6. Error and Degradation Strategy

| Error | Behavior |
|-------|----------|
| Unsupported file type | `supports()` returns False; caller should not call `parse()` |
| Source does not exist | Delegates to `LightweightIngestionService` — may raise `FileNotFoundError` or degrade |
| Empty file | Delegates to `LightweightIngestionService` — returns `degraded=True`, `NO_TEXT_EXTRACTED` |
| PDF parse failure | Delegates to `LightweightIngestionService` — returns `degraded=True`, `PDF_PARSE_FAILED` |
| PyMuPDF not installed | Delegates to `LightweightIngestionService` — returns `degraded=True`, `PYMUPDF_MISSING` |

**Rules**:
- Adapter does NOT introduce new exception types
- Adapter does NOT swallow exceptions (unless original parser already degrades)
- All degradation behavior is inherited from `LightweightIngestionService`

---

## 7. Backward Compatibility Definition

The `LightweightParserAdapter` output must be identical to calling `LightweightIngestionService.ingest_path()` directly.

**Comparison fields** (must match):

| Field | Location |
|-------|----------|
| `paper_id` | DocumentIngestion |
| `detected_language` | DocumentIngestion |
| `degraded` | DocumentIngestion |
| `warnings` | DocumentIngestion (compare code + message for each WarningItem) |
| `blocks` length | DocumentIngestion |
| `blocks[i].block_id` | DocumentBlock |
| `blocks[i].type` | DocumentBlock |
| `blocks[i].section` | DocumentBlock |
| `blocks[i].text` | DocumentBlock |
| `blocks[i].evidence_ref` | DocumentBlock |

**Note**: `source_path` and `parser_name` may differ (adapter may set different values). These are metadata, not content.

---

## 8. Tests — Exact Specifications

### test_parser_adapter_is_abstract

```
Arrange: import ParserAdapter
Act: try to instantiate ParserAdapter()
Assert: raises TypeError (cannot instantiate abstract class)
```

### test_lightweight_adapter_supports_md_txt_pdf_case_insensitive

```
Arrange: create LightweightParserAdapter
Act: call supports() for .md, .txt, .pdf, .MD, .TXT, .PDF, .markdown, .docx
Assert:
  - .md → True
  - .txt → True
  - .pdf → True
  - .MD → True
  - .TXT → True
  - .PDF → True
  - .markdown → False
  - .docx → False
```

### test_lightweight_adapter_rejects_unsupported_suffix

```
Arrange: create LightweightParserAdapter, create tmp file "test.docx"
Act: call supports(Path("test.docx"))
Assert: returns False
```

### test_lightweight_adapter_matches_original_markdown_output

```
Arrange:
  - create tmp markdown file with known content
  - create LightweightIngestionService (original)
  - create LightweightParserAdapter (wrapper)
Act:
  - original_doc = service.ingest_path(path, paper_id="test")
  - adapter_doc = adapter.parse(path, paper_id="test")
Assert:
  - adapter_doc.paper_id == original_doc.paper_id
  - adapter_doc.detected_language == original_doc.detected_language
  - adapter_doc.degraded == original_doc.degraded
  - len(adapter_doc.warnings) == len(original_doc.warnings)
  - for each warning: code and message match
  - len(adapter_doc.blocks) == len(original_doc.blocks)
  - for each block: block_id, type, section, text, evidence_ref match
```

### test_lightweight_adapter_matches_original_txt_output

```
Same as markdown test but with .txt file.
```

### test_lightweight_adapter_parse_returns_document_ingestion

```
Arrange: create LightweightParserAdapter, create tmp .md file
Act: result = adapter.parse(path, paper_id="test")
Assert:
  - isinstance(result, DocumentIngestion)
  - result.paper_id == "test"
  - result.blocks is a list
```

### test_lightweight_adapter_json_round_trip

```
Arrange: create LightweightParserAdapter, create tmp .md file
Act:
  - doc = adapter.parse(path, paper_id="test")
  - json_str = doc.model_dump_json()
  - restored = DocumentIngestion.model_validate_json(json_str)
Assert:
  - restored.paper_id == doc.paper_id
  - len(restored.blocks) == len(doc.blocks)
  - restored.detected_language == doc.detected_language
```

### test_lightweight_adapter_does_not_write_artifacts

```
Arrange: create LightweightParserAdapter, create tmp .md file in tmp_path
Act: adapter.parse(path, paper_id="test")
Assert:
  - no *.json artifact files are created in tmp_path
  - no workspace/run artifact directory is created
  - adapter only returns DocumentIngestion and does not write artifacts
```

### test_lightweight_adapter_uses_injected_service

```
Arrange:
  - create mock LightweightIngestionService (or real one)
  - create LightweightParserAdapter(ingestion=mock_service)
Act: adapter.parse(path, paper_id="test")
Assert:
  - mock_service.ingest_path was called with (path, paper_id="test")
  (If using real service: output matches direct call)
```

### test_lightweight_adapter_propagates_or_preserves_degraded_behavior

```
Arrange:
  - create tmp file "broken.pdf" with invalid PDF bytes
  - create LightweightParserAdapter
Act: result = adapter.parse(path, paper_id="test")
Assert:
  - result.degraded is True
  - any warning.code == "PDF_PARSE_FAILED" for warning in result.warnings
```

---

## 9. Completion Criteria

- [ ] `src/researchsensei/parser/` package can be imported
- [ ] `ParserAdapter` ABC cannot be instantiated (abstract)
- [ ] `LightweightParserAdapter` wrapper output matches original parser
- [ ] All 10 new tests pass
- [ ] Full pytest passes (281+ tests)
- [ ] No new dependencies
- [ ] No forbidden files modified
- [ ] No parser behavior changed
- [ ] No real network in tests
- [ ] No real LLM in tests
- [ ] No Phase 12 content

---

## 10. Hard-Fail Conditions

Any of these means the phase fails:

- New dependency introduced
- Existing `ingestion/lightweight.py` modified
- `ingestion/pipeline.py` modified
- `web/` modified
- `frontend/` modified
- `backend/` modified
- Adapter output incompatible with original parser
- Tests only check field existence, not content comparison
- Default pytest uses real network or real LLM
- Phase 12 content included
