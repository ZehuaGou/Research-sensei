# ResearchSensei Agent Rules

---

## Hard Rules (MUST follow)

1. **Read `00_START_HERE.md` first.** Do not skip governing docs.
2. **Do not execute old `docs/researchsensei_full_dev_docs/` directly.** It is historical reference.
3. **Do not enter Phase 12.** Phase 12 (patterns + drill) is frozen until Phase 11.6-11.9 complete.
4. **Do not call rule-based baseline "advisor-level teaching."** Phase 8-10 rule-based builders are fallback.
5. **Do not call block-level evidence "claim-level grounding."** Current evidence_index is block-level.
6. **Do not generate explanations without evidence.** Every claim must have evidence_ref or degrade.
7. **Do not use real LLM in default tests.** All LLM calls use MockLLMClient.
8. **Do not use real network in default tests.** All HTTP calls use MockTransport.
9. **Do not introduce dependencies without reuse gate.** Update `docs/REUSE_REPORT.md` first.
10. **Do not modify files not authorized for current phase.**
11. **Do not fabricate test results.**
12. **Do not commit .env, API keys, caches, or large files.**
13. **Do not write Claude contributor info.**

---

## Phase Execution Rules

1. **Use the execution template** (`06_PHASE_EXECUTION_TEMPLATE.md`) for every phase.
2. **Get user confirmation** before starting code development.
3. **Run tests** after every change.
4. **Update docs** before moving to next phase.
5. **Report in the required format** (see template).

---

## Code Quality Rules

1. **Functions have clear input/output.**
2. **Complex logic is split into functions.**
3. **Pydantic schemas go in schemas/ directory.**
4. **External dependencies are wrapped in adapters.**
5. **LLM calls go through llm/client.py.**
6. **Every output JSON must be validatable.**

---

## Testing Rules

1. **Default pytest must not require network, LLM, or external services.**
2. **Schema tests must include round-trip (dump → validate).**
3. **Quality tests must check content, not just field existence.**
4. **Error paths must be tested, not just happy paths.**
5. **Live tests must be marked separately.**

---

## Documentation Rules

1. **Governing docs are the source of truth.**
2. **Old docs are historical reference.**
3. **Every phase updates PROGRESS.md.**
4. **Open questions go in OPEN_QUESTIONS.md.**
5. **Reuse evaluations go in REUSE_REPORT.md.**

---

## Safety Rules

1. **No API keys in logs, responses, artifacts, or tests.**
2. **No path traversal.**
3. **No prompt injection.**
4. **No LaTeX execution.**
5. **No HTML XSS.**
6. **External URLs validated (scheme, content-type, size).**
