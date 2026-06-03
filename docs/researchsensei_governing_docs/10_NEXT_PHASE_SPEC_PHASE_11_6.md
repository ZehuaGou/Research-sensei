# Phase 11.6: ParserAdapter Design — Executable Spec

> **Status**: Ready for detailed planning, NOT authorized for code.
> This is the only phase currently ready for planning.
>
> **Code development is NOT authorized until**:
> 1. The detailed playbook (`12_PHASE_11_6_DETAILED_PLAYBOOK.md`) is reviewed.
> 2. The agent fills `06_PHASE_EXECUTION_TEMPLATE.md` specifically for Phase 11.6.
> 3. The filled execution plan is shown to the user.
> 4. The user explicitly confirms.
> 5. Then code may begin.
>
> This document is the next-phase **specification**, not a code authorization.
> For executable details, see `12_PHASE_11_6_DETAILED_PLAYBOOK.md`.

---

## Problem Solved

Current PDF parsing uses PyMuPDF as a fallback with low quality. We need a ParserAdapter interface so that better parsers (Docling, Nougat, Marker) can be plugged in later without changing the pipeline.

---

## Non-Goals

- No real Docling/Nougat/Marker integration
- No new dependencies
- No changes to existing parser behavior
- No frontend changes
- No old backend changes
- No Phase 12

---

## Reuse Gate

| Candidate | Decision | Reason |
|-----------|----------|--------|
| Docling | OPTIONAL_ADAPTER (future) | Not this phase — only design interface |
| Nougat | OPTIONAL_ADAPTER (future) | Not this phase |
| Marker | OPTIONAL_ADAPTER (future) | Not this phase |
| MinerU | OPTIONAL_ADAPTER (future) | Not this phase |

New dependencies: NONE
Code development authorized: NO — only after agent fills execution template and user confirms

---

## Authorized Files

**May create**:
- `src/researchsensei/parser/__init__.py`
- `src/researchsensei/parser/adapter.py` (ParserAdapter interface)
- `src/researchsensei/parser/lightweight_adapter.py` (wraps existing parser)
- `tests/test_parser_adapter.py`

**May modify**:
- `docs/PROGRESS.md`
- `docs/PHASE_MAPPING.md` (if needed)
- `docs/OPEN_QUESTIONS.md` (if needed)

---

## Forbidden Files

- `src/researchsensei/ingestion/` (do not modify existing parser)
- `src/researchsensei/web/` (do not modify API)
- `src/researchsensei/paper_card.py` etc. (do not modify card builders)
- `frontend/` (do not touch)
- `backend/` (do not touch)
- `.env` (do not touch)

---

## Input Artifacts

| Artifact | Format | Source |
|----------|--------|--------|
| Source file (PDF/MD/TXT) | file | user upload |

---

## Output Artifacts

| Artifact | Format | Generator |
|----------|--------|-----------|
| parsed_document.json | DocumentIngestion | ParserAdapter |

**Critical**: Output must be backward compatible with existing parsed_document.json format.

---

## Schema Changes

None. ParserAdapter produces the same DocumentIngestion schema.

---

## Business Logic

### ParserAdapter Interface

```python
class ParserAdapter(ABC):
    @abstractmethod
    def parse(self, source: Path, paper_id: str) -> DocumentIngestion:
        """Parse a source file into a DocumentIngestion."""
        ...

    @abstractmethod
    def supports(self, source: Path) -> bool:
        """Check if this adapter can handle the source."""
        ...
```

### LightweightParserAdapter

- Wraps existing `LightweightIngestionService`
- `parse()` delegates to `ingestion.ingest_path()`
- `supports()` returns True for .md, .txt, .pdf

### Future Optional Adapters

- `DoclingAdapter` — wraps docling library
- `NougatAdapter` — wraps nougat library
- `MarkerAdapter` — wraps marker library

These are NOT built in this phase. Only the interface is designed.

---

## Test Plan

| Test File | Tests | Covers |
|-----------|-------|--------|
| test_parser_adapter.py | ~8 | Interface compliance, wrapper behavior, fallback |

Specific tests:
1. LightweightParserAdapter produces same output as original parser
2. ParserAdapter interface is abstract (cannot instantiate)
3. LightweightParserAdapter supports .md, .txt, .pdf
4. LightweightParserAdapter rejects unsupported files
5. Parse result is valid DocumentIngestion
6. Parse result serializes to valid JSON
7. Degraded PDF produces degraded result with warning
8. Empty file produces degraded result

---

## Quality Gate

- [ ] All 281 existing tests still pass
- [ ] New parser adapter tests pass
- [ ] No new dependencies
- [ ] Output backward compatible with existing parsed_document.json
- [ ] No real network in tests
- [ ] No real LLM in tests

---

## Documentation Updates

- [ ] PROGRESS.md — mark Phase 11.6 complete
- [ ] OPEN_QUESTIONS.md — update if any new questions

---

## Completion Criteria

1. ParserAdapter ABC defined with `parse()` and `supports()` methods
2. LightweightParserAdapter wraps existing LightweightIngestionService
3. Contract tests prove interface works
4. Output backward compatible
5. All tests pass

---

## Hard-Fail Conditions

- ParserAdapter output is not backward compatible
- Existing tests break
- New dependency introduced
- Real network/LLM in default tests

---

## After Completion

After Phase 11.6 completes and user confirms, proceed to Phase 11.7 (PassageIndex + ClaimEvidence v2).
