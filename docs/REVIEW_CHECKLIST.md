# ResearchSensei Review Checklist

> **Canonical docs**: See `docs/DEVELOPMENT.md`, `docs/STATUS.md`, `docs/development/`.

## Pre-Commit Checklist

1. Did I only modify authorized files?
2. Did I run `python -m pytest -q`?
3. Are all tests passing?
4. Did I avoid modifying forbidden files?
5. Did I avoid new dependencies without reuse gate?
6. Did I avoid real network/LLM in default tests?
7. Is there any API key or secret in the changes?
8. Did I update documentation if needed?

## Phase Completion Checklist

1. All new tests pass
2. All existing tests still pass
3. No forbidden files modified
4. No new dependencies (or reuse gate completed)
5. Documentation updated
6. Artifacts backward compatible (if applicable)
7. No real network/LLM in default tests
8. Hard-fail conditions tested

## ResearchSensei Quality Standards

- Every claim must have evidence_ref or degrade
- No formula text as human explanation
- No template-based generic output
- No fabrication of results or datasets
