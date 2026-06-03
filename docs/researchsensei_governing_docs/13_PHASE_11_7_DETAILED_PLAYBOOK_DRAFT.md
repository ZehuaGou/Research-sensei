# Phase 11.7 Playbook Draft: PassageIndex + ClaimEvidence v2

> **Status**: DRAFT — not authorized for code.
> **Detail level**: L3 (Playbook Draft)
> **Must be upgraded to L2 (Detailed Playbook) before code begins.**

---

## 1. Goal

Upgrade evidence from block-level to passage-level with claim extraction.

**What this phase does**:
- Implement `PassageIndex` (passage-level text indexing)
- Implement `ClaimExtractor` (rule-based claim extraction from passages)
- Upgrade `ClaimEvidence` to v2 (semantic support)
- Implement `EvidenceRetriever` (claim → passage retrieval)

**What this phase does NOT do**:
- No LLM-based claim extraction
- No vector database
- No new dependencies
- No changes to parser or pipeline

---

## 2. Non-Goals

- No real LLM in default tests
- No vector embeddings
- No semantic search (just keyword/heuristic matching)
- No changes to existing `evidence_index.json` format (backward compatible)

---

## 3. File Plan

### Allowed to CREATE

| File | Purpose |
|------|---------|
| `src/researchsensei/evidence/__init__.py` | Barrel export |
| `src/researchsensei/evidence/passage_index.py` | PassageIndex |
| `src/researchsensei/evidence/claim_extractor.py` | ClaimExtractor |
| `src/researchsensei/evidence/retriever.py` | EvidenceRetriever |
| `tests/test_passage_index.py` | PassageIndex tests |
| `tests/test_claim_extractor.py` | ClaimExtractor tests |
| `tests/test_evidence_retriever.py` | EvidenceRetriever tests |

### Allowed to MODIFY

| File | Changes |
|------|---------|
| `src/researchsensei/schemas/evidence.py` | Add optional v2 fields to ClaimEvidence |
| `docs/` | Progress, questions |

### FORBIDDEN

- `src/researchsensei/ingestion/**`
- `src/researchsensei/paper_card.py`, `formula_card.py`, `teaching_card.py`
- `src/researchsensei/ingestion/pipeline.py`
- `frontend/`, `backend/`, `pyproject.toml`

---

## 4. Schema Plan

### PassageIndex (new)

```python
class Passage(SenseiModel):
    passage_id: str          # e.g. "p001"
    block_ids: list[str]     # source block IDs
    section: str             # section name
    text: str                # passage text
    normalized_text: str     # lowercased, cleaned

class PassageIndex(SenseiModel):
    paper_id: str
    passages: list[Passage]
```

### ClaimEvidence v2 (modify existing)

Add optional fields (backward compatible):

```python
class ClaimEvidence(SenseiModel):
    # existing v1 fields (unchanged)
    claim_id: str
    block_id: str
    evidence_type: EvidenceType
    evidence_ref: str
    quote_or_summary: str
    confidence: float

    # new v2 fields (optional)
    passage_id: str = ""           # link to PassageIndex
    claim_type: str = ""           # HYPOTHESIS, METHOD, RESULT, LIMITATION, CONTRIBUTION, DEFINITION
    semantic_support: str = ""     # "direct_quote", "paraphrase", "inference"
```

### ClaimExtractor (new)

```python
class ClaimExtractor:
    def extract(self, passages: list[Passage]) -> list[ClaimEvidence]:
        """Extract claims from passages using rule-based heuristics."""
        ...
```

### EvidenceRetriever (new)

```python
class EvidenceRetriever:
    def retrieve(self, claim: str, index: PassageIndex) -> list[Passage]:
        """Retrieve passages relevant to a claim."""
        ...
```

---

## 5. Warning / Degraded Rules

| Situation | Behavior |
|-----------|----------|
| No passages extracted | `warnings.append("NO_PASSAGES")` |
| No claims extracted | `warnings.append("NO_CLAIMS")` |
| Claim has no matching passage | `evidence_type = INSUFFICIENT_EVIDENCE` |
| Passage too short (< 50 chars) | Skip passage |

---

## 6. Test Checklist

- [ ] PassageIndex correctly segments blocks into passages
- [ ] PassageIndex groups consecutive blocks in same section
- [ ] ClaimExtractor extracts claims from method sections
- [ ] ClaimExtractor extracts claims from abstract
- [ ] ClaimExtractor does NOT extract claims from headings
- [ ] ClaimExtractor assigns claim_type correctly
- [ ] EvidenceRetriever finds relevant passage for a claim
- [ ] EvidenceRetriever returns empty for unrelated claim
- [ ] ClaimEvidence v2 backward compatible (v1 fields unchanged)
- [ ] ClaimEvidence v2 optional fields default to empty
- [ ] Existing evidence_index tests still pass

---

## 7. Hard-Fail Conditions

- Block-level only (no passage-level)
- No claim extraction
- Modify parser or pipeline
- Real network/LLM in default tests
- Existing tests break

---

## 8. Unresolved Decisions

- How to segment blocks into passages (by section? by paragraph count?)
- How to determine claim_type (keyword matching? position heuristic?)
- How to define semantic_support (exact match vs paraphrase detection)
- Whether EvidenceRetriever should use TF-IDF or simpler keyword matching
