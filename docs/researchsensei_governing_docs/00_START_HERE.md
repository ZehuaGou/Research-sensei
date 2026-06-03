# ResearchSensei Governing Docs — Start Here

> **This is the canonical execution entry for all agents.**
> If you are reading `docs/researchsensei_full_dev_docs/` — stop. That package is historical reference only.
> If you are reading any other docs file — check it against this file first.

---

## Current State (2026-06-03)

| Phase | Status | Meaning |
|-------|--------|---------|
| Phase 1-11 | **baseline infrastructure complete** | Working code, 281 tests passing, but rule-based baseline only |
| Phase 11.5 | **route review complete** | External projects evaluated, architecture confirmed |
| Phase 11.6-11.9 | **must complete first** | Upgrade paper understanding core before Phase 12 |
| Phase 12 | **frozen** | Patterns + Drill code NOT authorized |

**Next allowed task**: Phase 11.6 ParserAdapter Design — planning only. Code requires filling execution template + user confirmation.

---

## What You Must NOT Do

1. **Do not enter Phase 12.** Phase 12 (patterns + drill) is frozen until Phase 11.6-11.9 complete.
2. **Do not call rule-based baseline "advisor-level teaching."** Phase 8-10 rule-based builders are fallback, not final product.
3. **Do not call block-level evidence "claim-level grounding."** Current evidence_index is block-level. PassageIndex (Phase 11.7) upgrades this.
4. **Do not introduce dependencies without reuse gate.** Every new dependency must go through `docs/REUSE_REPORT.md`.
5. **Do not use real network or real LLM in default pytest.** All external calls must be mocked.
6. **Do not execute old phase numbers directly.** Actual execution order is in `05_IMPLEMENTATION_ROADMAP.md`.
7. **Do not modify files not authorized for current phase.**
8. **Do not fabricate test results.**
9. **Do not commit .env, API keys, caches, or large files.**
10. **Do not write Claude contributor info.**

---

## What You Must Do

1. Read this file first.
2. Read `01_PRODUCT_SPEC.md` to understand what ResearchSensei is.
3. Read `02_ARCHITECTURE_V2.md` to understand the architecture.
4. Read `03_ARTIFACT_CONTRACTS.md` to understand artifact obligations.
5. Read `04_MODULE_CONTRACTS.md` to understand module boundaries.
6. Read `05_IMPLEMENTATION_ROADMAP.md` to understand what to build next.
7. Read `06_PHASE_EXECUTION_TEMPLATE.md` before starting any phase.
8. Read `07_TEST_AND_QUALITY_PLAN.md` to understand testing requirements.
9. Read `08_REUSE_AND_ADAPTER_POLICY.md` before introducing any dependency.
10. Read `09_AGENT_RULES.md` for hard rules.
11. Read `10_NEXT_PHASE_SPEC_PHASE_11_6.md` if you are about to start Phase 11.6.

---

## Document Index

| File | Purpose |
|------|---------|
| `00_START_HERE.md` | This file — routing index |
| `01_PRODUCT_SPEC.md` | What ResearchSensei is and is not |
| `02_ARCHITECTURE_V2.md` | Six-layer architecture |
| `03_ARTIFACT_CONTRACTS.md` | Artifact definitions and obligations |
| `04_MODULE_CONTRACTS.md` | Module boundaries and responsibilities |
| `05_IMPLEMENTATION_ROADMAP.md` | Phase 11.6 → 12 execution plan |
| `06_PHASE_EXECUTION_TEMPLATE.md` | Template for every phase |
| `07_TEST_AND_QUALITY_PLAN.md` | Testing layers and quality gates |
| `08_REUSE_AND_ADAPTER_POLICY.md` | External project reuse decisions |
| `09_AGENT_RULES.md` | Hard rules |
| `10_NEXT_PHASE_SPEC_PHASE_11_6.md` | Phase 11.6 executable spec |

---

## Superseded Documents

The following documents are **historical reference only**. Do not execute them directly.

| Document | Status |
|----------|--------|
| `docs/researchsensei_full_dev_docs/` (entire directory) | Historical — original product planning |
| `docs/PROGRESS.md` | Still maintained but not the execution entry |
| `docs/PHASE_MAPPING.md` | Still maintained for phase numbering reference |
| `docs/REUSE_REPORT.md` | Still maintained for reuse evaluations |
| `docs/OPEN_QUESTIONS.md` | Still maintained for open decisions |
| `docs/MIGRATION_PLAN.md` | Historical — migration Phase 1-6 is complete |
| `docs/FULL_PROJECT_REVIEW.md` | Historical — pre-route-reset audit |
| `docs/PRE_PHASE12_PROJECT_AUDIT.md` | Historical — pre-route-reset audit |
