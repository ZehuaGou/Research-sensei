# ResearchSensei Acceptance Criteria

> **Canonical docs**: See `docs/DESIGN.md`, `docs/DEVELOPMENT.md`, and `docs/STATUS.md`.

## Global Criteria

Every phase must satisfy:
1. Related files exist and code can import.
2. Tests can run and pass.
3. Output conforms to schema.
4. Failures produce structured errors.
5. Logs do not leak API keys.
6. Unfinished items recorded in development docs.

## Paper Understanding Quality

- Every claim must have evidence_ref or degrade to INSUFFICIENT_EVIDENCE.
- human_explanation must not be formula text.
- Formula symbols from generic dictionary must be REASONABLE_INFERENCE.
- Output must contain paper-specific terms (not generic templates).
- Confidence must degrade when evidence is insufficient.
- LLM output must be evidence-constrained.

## Phase 12 Gate

Phase 12 unfreezes only when:
- Phase 11.6-11.9 complete.
- Quality benchmarks pass.
- All hard-fail conditions tested.
- User confirms.

## Detailed Criteria

See `docs/DEVELOPMENT.md` for per-phase completion criteria and hard-fail conditions.
