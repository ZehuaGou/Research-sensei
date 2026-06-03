# Phase 11.9 Playbook Draft: Paper Understanding Quality Benchmark

> **Status**: DRAFT — not authorized for code.
> **Detail level**: L3 (Playbook Draft)
> **Must be upgraded to L2 (Detailed Playbook) before code begins.**

---

## 1. Goal

Establish quality benchmark with fixtures, audits, and hard-fail tests.

**What this phase does**:
- Extend fixture papers for quality testing
- Implement explanation audit tests
- Implement formula audit tests
- Implement evidence audit tests
- Generate audit reports

**What this phase does NOT do**:
- No real LLM in default tests
- No new dependencies
- No changes to card builders
- No changes to pipeline

---

## 2. Non-Goals

- No real LLM API calls
- No new card types
- No changes to existing artifacts
- No subjective scoring (only automated heuristics)

---

## 3. File Plan

### Allowed to CREATE

| File | Purpose |
|------|---------|
| `tests/test_explanation_audit.py` | Explanation quality audit |
| `tests/test_formula_audit.py` | Formula quality audit |
| `tests/test_evidence_audit.py` | Evidence binding audit |
| `tests/fixtures/quality/` (extend) | Additional fixture papers |

### Allowed to MODIFY

| File | Changes |
|------|---------|
| `docs/QUALITY_EVALUATION_SPEC.md` | Update with benchmark results |
| `docs/` | Progress, questions |

### FORBIDDEN

- `src/researchsensei/ingestion/**`
- `src/researchsensei/paper_card.py`, `formula_card.py`, `teaching_card.py`
- `frontend/`, `backend/`, `pyproject.toml`

---

## 4. Benchmark Fixtures

### Existing Fixtures

| Fixture | Purpose | Status |
|---------|---------|--------|
| `fixture_method_paper.md` | Paper card + teaching card | exists |
| `fixture_formula_heavy.md` | Formula card + fallback | exists |
| `fixture_minimal.md` | Degradation + no-fabrication | exists |

### Possible Additional Fixtures

| Fixture | Purpose | Priority |
|---------|---------|----------|
| `fixture_experiment_only.md` | Experiments without method | LOW |
| `fixture_chinese_paper.md` | Chinese language handling | LOW |
| `fixture_multi_formula.md` | Multiple formulas | LOW |

---

## 5. Audit Tests

### Explanation Audit (`test_explanation_audit.py`)

| Test | Check |
|------|-------|
| `test_core_idea_not_copied_from_abstract` | core_idea text ≠ abstract text |
| `test_method_overview_not_copied_from_method` | method_overview text ≠ method section text |
| `test_human_explanation_not_formula_text` | formula char ratio < 0.3 |
| `test_paper_role_explanation_not_generic` | contains paper-specific terms |
| `test_explanation_has_paper_keywords` | title/method terms present |

### Formula Audit (`test_formula_audit.py`)

| Test | Check |
|------|-------|
| `test_formula_symbols_not_all_generic` | at least one symbol from paper context |
| `test_formula_purpose_not_unknown_when_context` | purpose set when section context exists |
| `test_formula_heavy_triggers_conservative` | confidence ≤ 0.5 for formula-heavy |
| `test_formula_evidence_ref_valid` | evidence_ref exists in evidence_index |

### Evidence Audit (`test_evidence_audit.py`)

| Test | Check |
|------|-------|
| `test_all_card_evidence_refs_exist` | every ref in cards exists in evidence_index |
| `test_core_claims_have_evidence_ref` | core_idea, problem have ref or degrade |
| `test_no_fabricated_results_in_minimal` | minimal paper has no accuracy/SOTA |
| `test_no_fabricated_datasets_in_minimal` | minimal paper has no ImageNet/CIFAR |
| `test_confidence_degrades_when_no_evidence` | confidence ≤ 0.5 when evidence missing |

---

## 6. Audit Report Format

### JSON Report

```json
{
  "paper_id": "test-paper",
  "audit_type": "explanation|formula|evidence",
  "verdict": "PASS|WARN|FAIL",
  "checks": [
    {
      "name": "core_idea_not_copied",
      "passed": true,
      "detail": ""
    }
  ],
  "hard_fail_triggered": false,
  "generated_at": "ISO-8601"
}
```

### Human-readable Summary

```
Paper: test-paper
Audit: explanation
Verdict: PASS
Checks: 5/5 passed
Hard-fail: none
```

---

## 7. Hard-Fail Conditions

| ID | Condition | Trigger |
|----|-----------|---------|
| HF-1 | Core claim has no evidence_ref and not degraded | evidence_ref missing + not INSUFFICIENT_EVIDENCE |
| HF-2 | human_explanation is formula text | formula char ratio ≥ 0.3 |
| HF-3 | Formula symbol explanation contradicts paper | generic dict meaning ≠ paper context |
| HF-4 | core_idea/problem missing evidence_ref | no ref + not degraded |
| HF-5 | Output has no paper-specific terms | no title/method keywords |
| HF-6 | Output contradicts paper | claim text ≠ paper content |

---

## 8. Test Checklist

- [ ] Explanation audit covers all hard-fail conditions
- [ ] Formula audit covers all hard-fail conditions
- [ ] Evidence audit covers all hard-fail conditions
- [ ] Audit reports generated in JSON format
- [ ] All 281+ existing tests still pass
- [ ] No real network/LLM in default tests

---

## 9. Gate Condition

**Phase 12 unfreezes only when**:
- All hard-fail tests pass
- Audit reports show PASS for all fixture papers
- User confirms quality is acceptable

---

## 10. Unresolved Decisions

- Whether to add more fixture papers
- Whether audit should be a separate module or just tests
- Whether to generate audit reports as artifacts (written to workspace)
- How to handle partial passes (some checks fail, others pass)
