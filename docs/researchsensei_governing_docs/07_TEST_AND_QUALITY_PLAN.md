# ResearchSensei Test and Quality Plan

---

## Test Layers

| Layer | What | Default pytest | Example |
|-------|------|----------------|---------|
| L1 | Schema validity | YES | model_dump_json → model_validate_json |
| L2 | Structural integrity | YES | evidence_ref exists, artifact chain complete |
| L3 | Artifact round-trip | YES | write JSON → read → validate |
| L4 | Mock LLM | YES | MockLLMClient, no real API |
| L5 | Quality hard-fail | YES | no fabrication, no formula-as-explanation |
| L6 | Live smoke | NO (separate mark) | real network, real LLM, optional |

---

## Current Test Status (281 tests)

| Category | Count | Files |
|----------|-------|-------|
| Schema tests | ~40 | test_schemas_core, test_*_schema |
| Builder tests | ~60 | test_*_builder |
| Pipeline tests | ~20 | test_*_runner, test_*_pipeline |
| API tests | ~25 | test_api_* |
| LLM tests | ~50 | test_llm_*, test_prompt_* |
| Quality tests | ~32 | test_quality_*, test_deep_audit_* |
| Selection tests | ~16 | test_selection_*, test_direction_* |
| Other | ~38 | config, workspace, jobs, etc. |

---

## Quality Hard-Fail Conditions

These conditions must NEVER pass quality tests:

| ID | Condition | Check |
|----|-----------|-------|
| HF-1 | Core claim has no evidence_ref and is not degraded | evidence_ref exists or evidence_type is degraded |
| HF-2 | human_explanation is formula text | formula character ratio < 0.3 |
| HF-3 | Formula symbol explanation contradicts paper | symbol meaning from paper context, not generic dict |
| HF-4 | core_idea/problem missing evidence_ref | must have evidence_ref or INSUFFICIENT_EVIDENCE |
| HF-5 | Output has no paper-specific terms | title/method/dataset keywords present |
| HF-6 | Output contradicts paper | claim text matches paper content |

---

## Future Test Directions (Phase 11.6-11.9)

### ParserAdapter Contract Tests (Phase 11.6)

- ParserAdapter interface compliance
- LightweightParserAdapter produces same output as original parser
- Optional adapter fallback behavior
- parsed_document.json backward compatibility

### PassageIndex Tests (Phase 11.7)

- Passage-level indexing correctness
- Claim extraction from passages
- ClaimEvidence v2 semantic support
- EvidenceRetriever returns relevant passages

### Evidence-constrained LLM Tests (Phase 11.8)

- LLM output has valid evidence_ref
- Hallucinated evidence_ref rejected
- LLM failure falls back to rule-based
- All card types tested

### Explanation Audit Tests (Phase 11.9)

- Explanation is faithful to paper
- Formula explanation is accurate
- Teaching card is not copied from paper
- Uncertainty is properly handled

---

## Test Rules

1. **Default pytest must not use real network.** All HTTP calls use MockTransport.
2. **Default pytest must not use real LLM.** All LLM calls use MockLLMClient.
3. **Live tests must use separate mark.** `@pytest.mark.live` for real network/LLM.
4. **Quality tests must check content, not just fields.** "Field exists" is not enough.
5. **"Good" must be testable.** At minimum:
   - No copied text as explanation
   - core_idea ≠ method_overview
   - Formula symbols from context or degraded
   - evidence_ref semantically supports claim
   - Uncertainty triggers degradation

---

## Fixture Papers

| Fixture | Purpose | Characteristics |
|---------|---------|-----------------|
| fixture_method_paper.md | Paper card + teaching card testing | Has abstract, method, experiments, limitations |
| fixture_formula_heavy.md | Formula card + formula fallback testing | Multiple formulas and symbols |
| fixture_minimal.md | Degradation + no-fabrication testing | Abstract only, no method/experiments |
