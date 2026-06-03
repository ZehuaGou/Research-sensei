# Phase 11.8 Playbook Draft: Evidence-constrained LLM Paper Understanding

> **Status**: DRAFT — not authorized for code.
> **Detail level**: L3 (Playbook Draft)
> **Must be upgraded to L2 (Detailed Playbook) before code begins.**

---

## 1. Goal

Wire LLM-enhanced card builders into the main pipeline with evidence constraints.

**What this phase does**:
- Connect `build_paper_card_with_llm` to `SinglePaperIngestionRunner`
- Connect `build_formula_cards_with_llm` to `SinglePaperIngestionRunner`
- Connect `build_teaching_cards_with_llm` to `SinglePaperIngestionRunner`
- Strengthen evidence_ref validation
- Ensure LLM failure falls back to rule-based

**What this phase does NOT do**:
- No real LLM in default tests
- No new dependencies
- No frontend changes
- No changes to schema (same schema, better content)

---

## 2. Non-Goals

- No real LLM API calls in default pytest
- No new card types
- No changes to artifact format
- No changes to web API

---

## 3. File Plan

### Allowed to MODIFY

| File | Changes |
|------|---------|
| `src/researchsensei/ingestion/pipeline.py` | Add LLM path (accept optional LLM client) |
| `src/researchsensei/paper_card.py` | Strengthen evidence_ref validation |
| `src/researchsensei/formula_card.py` | Strengthen evidence_ref validation |
| `src/researchsensei/teaching_card.py` | Strengthen evidence_ref validation |
| `tests/test_llm_paper_understanding.py` (new) | LLM-enhanced tests |

### FORBIDDEN

- `src/researchsensei/ingestion/lightweight.py`
- `src/researchsensei/web/**`
- `frontend/`, `backend/`, `pyproject.toml`

---

## 4. Key Design Decisions

### Pipeline Integration

```python
class SinglePaperIngestionRunner:
    def __init__(
        self,
        workspace: WorkspaceStore,
        jobs: JobStore,
        ingestion: LightweightIngestionService | None = None,
        llm_client: LLMClient | MockLLMClient | None = None,  # NEW
    ) -> None:
        self.llm_client = llm_client
        ...

    def run(self, ...):
        ...
        if self.llm_client is not None:
            try:
                paper_card = await build_paper_card_with_llm(skeleton, evidence_index, self.llm_client)
            except Exception:
                paper_card = build_paper_card(skeleton, evidence_index)  # fallback
        else:
            paper_card = build_paper_card(skeleton, evidence_index)
        ...
```

### Evidence Constraint Enforcement

Every LLM-generated claim must:
1. Have a valid `evidence_ref` that exists in `evidence_index`
2. Have `evidence_type` matching the referenced evidence
3. If evidence_ref is invalid → reject claim, use rule-based fallback

### Fallback Strategy

| LLM Step | Fallback |
|----------|----------|
| `build_paper_card_with_llm` fails | Use `build_paper_card` (rule-based) |
| `build_formula_cards_with_llm` fails | Use `build_formula_cards` (rule-based) |
| `build_teaching_cards_with_llm` fails | Use `build_teaching_cards` (rule-based) |
| LLM returns invalid JSON | Use `parse_llm_json` repair, then validate |
| LLM returns hallucinated evidence_ref | Reject claim, log warning |

---

## 5. v2 Quality Gates

### paper_card v2

- `core_idea` must differ from `method_overview`
- `core_idea` must have `evidence_ref`
- `problem` must have `evidence_ref`
- No claim text should be "UNKNOWN" if evidence exists

### formula_cards v2

- Symbols must come from paper context, not just generic dictionary
- `purpose` must not be "UNKNOWN" for formulas with context
- Generic dictionary symbols → `REASONABLE_INFERENCE` (not `SUPPORTED_BY_FORMULA`)

### teaching_cards v2

- `human_explanation` must not be formula text
- `human_explanation` must differ from `minimal_formula_explanation`
- `paper_role_explanation` must reference paper-specific content
- Confidence must degrade when evidence is insufficient

---

## 6. Test Checklist

- [ ] Pipeline accepts optional LLM client
- [ ] Pipeline with MockLLMClient produces v2 cards
- [ ] Pipeline without LLM client produces v1 cards (rule-based)
- [ ] LLM failure falls back to rule-based
- [ ] Hallucinated evidence_ref rejected
- [ ] All LLM output has valid evidence_ref
- [ ] core_idea ≠ method_overview
- [ ] Symbols from paper context (not just generic dict)
- [ ] human_explanation not formula text
- [ ] Existing 281 tests still pass
- [ ] No real LLM in default tests

---

## 7. Hard-Fail Conditions

- Real LLM in default tests
- Invalid evidence_ref accepted
- No fallback on LLM failure
- Existing tests break
- New dependency introduced
- Formula text as human_explanation

---

## 8. Unresolved Decisions

- How to handle `run()` as sync vs async (LLM calls are async)
- Whether to add `llm_client` parameter to existing `run()` or create `run_with_llm()`
- How strict evidence_ref validation should be (exact match vs prefix match)
- Whether to add quality assertion tests (content-level) or only structural tests
