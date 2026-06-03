# ResearchSensei Architecture v2

---

## Six-Layer Architecture

```
A. Product Layer
B. Parser Layer
C. Evidence Layer
D. Paper Understanding Layer
E. Direction Layer
F. Audit Layer
```

---

## A. Product Layer (keep, do not rewrite)

| Component | Technology | Status |
|-----------|------------|--------|
| Frontend | Vue 3 + Vite + TypeScript + Pinia + TailwindCSS + KaTeX | Preserved |
| Backend | Python + FastAPI + Pydantic | Phase 1-11 complete |
| Persistence | workspace (filesystem) + jobs (SQLite) | Phase 3 complete |
| Artifacts | JSON files in workspace runs | Phase 4-11 complete |
| Testing | pytest, mock-first | 281 tests passing |
| Config | .env + TOML + ConfigService | Phase 2 complete |

**Decision**: Keep Python/FastAPI/Pydantic. Do not introduce ARIS-style skills architecture.

---

## B. Parser Layer (Phase 11.6 — upgrade)

| Component | Current | Future |
|-----------|---------|--------|
| ParserAdapter interface | does not exist | Phase 11.6 |
| LightweightParser | ingestion/lightweight.py (default) | wrapped as default adapter |
| Docling adapter | does not exist | optional |
| Nougat adapter | does not exist | optional |
| Marker adapter | does not exist | optional |
| MinerU adapter | does not exist | optional |

**Decision**: ParserAdapter interface + optional adapters. Do NOT install heavy dependencies by default.

---

## C. Evidence Layer (Phase 11.7 — upgrade)

| Component | Current | Future |
|-----------|---------|--------|
| evidence_index | block-level, rule-based | preserved as fallback |
| PassageIndex | does not exist | Phase 11.7 |
| ClaimExtractor | does not exist | Phase 11.7 (rule-based) |
| ClaimEvidence v2 | block_id only | semantic support |
| EvidenceRetriever | does not exist | Phase 11.7 |

**Decision**: Upgrade from block-level to passage-level. Keep block-level as fallback.

---

## D. Paper Understanding Layer (Phase 11.8 — upgrade)

| Component | Current | Future |
|-----------|---------|--------|
| paper_skeleton | rule-based extraction | v2 with LLM-enhanced |
| paper_card | rule-based baseline | v2 with evidence-constrained LLM |
| formula_cards | generic symbol dictionary | v2 with paper-context grounding |
| teaching_cards | rule-based baseline | v2 with evidence-constrained five-layer |
| uncertainty handling | UNKNOWN/NEEDS_HUMAN_CHECK | same, but better detection |

**Decision**: LLM-enhanced builders must be evidence-constrained. Keep rule-based as fallback.

---

## E. Direction Layer (Phase 11 complete, extend later)

| Component | Status |
|-----------|--------|
| query planner | Phase 11 complete |
| acquisition adapters (arXiv, OpenAlex) | Phase 11 complete |
| candidate pool + dedup | Phase 11 complete |
| reading plan | Phase 11 complete |
| cross-paper synthesis | later (reference STORM) |

---

## F. Audit Layer (Phase 11.9 — new)

| Component | Status | Inspiration |
|-----------|--------|-------------|
| explanation audit | Phase 11.9 | ARIS paper-claim-audit |
| formula audit | Phase 11.9 | ARIS citation-audit concept |
| evidence/citation audit | Phase 11.9 | ARIS reviewer-independence |
| advisor/kill-argument audit | later | ARIS kill-argument |

**Decision**: Reference ARIS audit chain design. Do NOT import ARIS code.

---

## Key Architectural Decisions

1. **Python/FastAPI/Pydantic preserved.** No ARIS-style skills.
2. **ARIS is REFERENCE_ONLY.** We learn from its audit chain and reviewer independence, not its architecture.
3. **PaperQA is OPTIONAL_ADAPTER.** We learn from its passage retrieval, not its QA system.
4. **Docling/Nougat/Marker are OPTIONAL_ADAPTER.** Users can install if they want better PDF parsing.
5. **Rule-based builders are fallback.** LLM-enhanced builders need evidence constraint.
6. **All LLM output must be evidence-constrained.** No explanation without evidence_ref.
7. **Audit must be independent.** The generator must not audit itself.

See `docs/ARCHITECTURE_DECISION.md` for ADR-001 and ADR-002.
