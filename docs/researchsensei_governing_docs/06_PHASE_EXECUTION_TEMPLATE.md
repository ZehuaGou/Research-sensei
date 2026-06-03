# ResearchSensei Phase Execution Template

> **Every agent must copy and fill this template before starting any new phase.**
> The user must confirm before code development begins.

---

## Phase [NUMBER]: [NAME]

### Problem Solved

[What problem does this phase solve?]

### Non-Goals

[What is explicitly out of scope?]

### Reuse Gate

| Candidate | Decision | Reason |
|-----------|----------|--------|
| [project/tool] | DIRECT_DEPENDENCY / DIRECT_ADAPTER / OPTIONAL_ADAPTER / REFERENCE_ONLY / NOT_USE | [reason] |

New dependencies: [NONE / list]
Code development authorized: [YES / NO]

### Authorized Files

Files this phase MAY create or modify:
- `src/researchsensei/[module]/[file].py`
- `tests/test_[name].py`
- `docs/[file].md`

### Forbidden Files

Files this phase MUST NOT touch:
- `src/researchsensei/[other_module]/`
- `frontend/`
- `backend/`
- `.env`

### Input Artifacts

| Artifact | Format | Source |
|----------|--------|--------|
| [artifact.json] | [schema] | [generator module] |

### Output Artifacts

| Artifact | Format | Generator |
|----------|--------|-----------|
| [artifact.json] | [schema] | [this module] |

### Schema Changes

- [ ] New schema classes: [list]
- [ ] Modified schema classes: [list]
- [ ] Backward compatible: [YES / NO]

### Adapter Decisions

- [ ] New adapters: [list]
- [ ] Optional adapters: [list]
- [ ] Default adapters: [list]

### LLM Policy

- [ ] Uses LLM: [YES / NO]
- [ ] LLM via: [llm/client.py / direct / N/A]
- [ ] Default test uses: [MockLLMClient / no LLM]
- [ ] Real LLM in default tests: [NO — always NO]

### Network Policy

- [ ] Uses network: [YES / NO]
- [ ] Default test uses: [MockTransport / no network]
- [ ] Real network in default tests: [NO — always NO]

### Error / Degraded Behavior

| Error | Behavior |
|-------|----------|
| [error type] | [degraded output + warning] |

### Test Plan

| Test File | Tests | Covers |
|-----------|-------|--------|
| [test_file.py] | [count] | [what it tests] |

### Quality Gate

- [ ] All existing tests pass
- [ ] New tests pass
- [ ] No real network in default tests
- [ ] No real LLM in default tests
- [ ] Hard-fail conditions tested
- [ ] Schema round-trip tested

### Documentation Updates

- [ ] PROGRESS.md updated
- [ ] PHASE_MAPPING.md updated (if needed)
- [ ] OPEN_QUESTIONS.md updated (if needed)
- [ ] REUSE_REPORT.md updated (if new dependencies)

### Final Report Format

```
【Phase】[NUMBER] - [NAME]
【Modified Files】- list
【New Files】- list
【Tests】- count passed
【Quality Gate】- pass/fail
【Unfinished Items】- list
【Risks/Confirmations】- list
【Next Phase Suggestion】- Phase [N+1]
```

### Completion Criteria

[What must be true before this phase is considered complete?]

### Hard-Fail Conditions

[What conditions would make this phase fail regardless of other progress?]
