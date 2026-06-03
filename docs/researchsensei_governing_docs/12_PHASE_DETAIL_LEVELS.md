# ResearchSensei Phase Detail Levels

> **This document defines how detailed documentation must be for each phase type.**
> It prevents two failure modes: over-specifying far-future phases (fake precision) and under-specifying imminent phases (agent free-forming).

---

## Detail Level Definitions

| Level | Name | What it contains | When to write |
|-------|------|------------------|---------------|
| L1 | Retrospective Contract | Current files, capabilities, invariants, known limits | After phase completes |
| L2 | Detailed Playbook | Function signatures, implementation rules, test assertions, error strategy | Before code begins |
| L3 | Playbook Draft | Goals, file plan, schema direction, key classes, test checklist | When planning future phases |
| L4 | Design-level Spec | Goals, non-goals, input/output artifacts, constraints, open questions | When defining near-future phases |
| L5 | Roadmap-level Spec | Goals, dependencies, expected outputs, constraints | When defining far-future phases |

---

## Phase Type → Detail Level Mapping

| Phase Type | Required Level | Example |
|------------|---------------|---------|
| Completed baseline (1-11) | L1 Retrospective Contract | Phase 8 paper_card |
| Immediate next phase | L2 Detailed Playbook | Phase 11.6 ParserAdapter |
| Near-future phase (next 2-3) | L3 Playbook Draft | Phase 11.7-11.9 |
| Frozen phase | L4 Design-level Spec | Phase 12 Patterns + Drill |
| Far-future phase (3+) | L5 Roadmap-level Spec | Phase 13-18 |

---

## What Each Level Requires

### L1: Retrospective Contract

For completed phases only. Documents what exists, not what to build.

Required fields:
- Current status (complete/baseline/partial)
- Core files (actual file paths)
- Artifacts produced
- Tests (file names + count)
- Invariants (what must not break)
- Known limitations
- Future upgrade path
- Phase 12 blocker (yes/no)

**Do NOT include**: implementation steps, function signatures, test code.

### L2: Detailed Playbook

For the immediate next phase. Agent must be able to implement without free-forming.

Required fields (beyond L1):
- Exact function signatures
- Implementation rules (what to do, what not to do)
- Error and degradation strategy
- Backward compatibility definition (exact field comparison)
- Test specifications with arrange/act/assert
- Completion criteria checklist
- Hard-fail conditions

**Must be reviewed and confirmed by user before code begins.**

### L3: Playbook Draft

For near-future phases (next 2-3). Provides direction but is NOT code authorization.

Required fields:
- Goals and non-goals
- File plan (allowed/forbidden)
- Schema plan (new fields, direction)
- Key classes/functions (candidates, not final)
- Input/output artifacts
- Warning/degraded rules
- Test checklist (categories, not individual tests)
- Hard-fail conditions
- Unresolved decisions

**Must be upgraded to L2 before code begins.**

### L4: Design-level Spec

For frozen or near-future phases. Defines the design space.

Required fields:
- Goals and non-goals
- Unfreeze conditions (if frozen)
- Input/output artifacts
- Constraints
- Possible approaches
- Open questions

**Must be upgraded to L3 → L2 before code begins.**

### L5: Roadmap-level Spec

For far-future phases (3+ away). Only direction.

Required fields:
- Goals
- Dependencies on prior phases
- Expected outputs
- Key constraints

**Must be upgraded to L4 → L3 → L2 before code begins.**

---

## Current Phase Detail Levels

| Phase | Current Level | Required Level | Gap |
|-------|--------------|----------------|-----|
| 1-11 | L1 | L1 | None |
| 11.6 | L2 | L2 | None — playbook complete |
| 11.7 | L3 | L3 | None — draft exists |
| 11.8 | L3 | L3 | None — draft exists |
| 11.9 | L3 | L3 | None — draft exists |
| 12 | L4 | L4 | None — design spec exists |
| 13-18 | L5 | L5 | None — roadmap exists |

---

## Upgrade Rules

1. **L5 → L4**: When phase becomes "next 3-4 phases away." Add design details.
2. **L4 → L3**: When phase becomes "next 2-3 phases away." Add playbook draft.
3. **L3 → L2**: When phase becomes "immediate next." Write detailed playbook.
4. **L2 → User Confirmation**: Before code begins.
5. **No skipping**: Cannot go from L5 directly to L2.

---

## Anti-Patterns

| Anti-Pattern | Why it fails |
|--------------|-------------|
| Writing L2 for Phase 18 now | Fake precision — details will be wrong by then |
| Writing only L5 for Phase 11.6 | Agent free-forms implementation |
| Skipping L3 for Phase 11.7-11.9 | No design direction when those phases start |
| Using L1 for a new phase | No implementation guidance |
