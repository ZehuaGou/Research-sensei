# ResearchSensei Implementation Plan

> **Canonical docs**: See `docs/DESIGN.md`, `docs/STATUS.md`, `docs/DEVELOPMENT.md`.

## Completed Phases

- Phase 1: Project skeleton, CLI, FastAPI health
- Phase 2: Config, logging, errors, schemas
- Phase 3: Workspace, job store, artifact writing
- Phase 4: Single document lightweight parsing
- Phase 5: Source resolver, parse API, job/artifact query
- Phase 6: Grounding, evidence index, paper skeleton
- Phase 7: LLM infrastructure (client, prompt, cache, token budget)
- Phase 8: Paper card JSON v1
- Phase 9: Formula cards JSON v1
- Phase 10: Teaching cards JSON v1
- Phase 11: Query / Acquisition / Selection / Reading Plan v1

## v2 Chain Completed (Post Phase 11)

- ParserAdapter interface + LightweightParserAdapter
- PassageIndex builder + passage_index.json artifact
- ClaimEvidenceV2 + ClaimEvidenceBundle + claim_evidence.json artifact
- BM25 EvidenceRetriever (runtime only)
- EvidencePack runtime builder
- Isolated LLM v2 builders (fail-closed, no fallback)
- Pipeline v2 path (SUCCESS / DEGRADED_STRUCTURAL / BLOCKED_UNDERSTANDING)
- UnderstandingStatus + DownstreamGates + EvidencePackSummary
- QualityAuditor (F-1 to F-6 structural rules)
- quality_report.json artifact
- API gating (/understanding_status + /cards + /artifacts debug-only)
- Frontend API alignment (UploadView + LearningWorkspaceView)
- StatusBanner component + tests (Vitest)
- Main chain v1 freeze documented

## Current Phase

- Documentation consolidation before further feature development
- No new code until P0 docs are consistent

## Frozen

Phase 12: Patterns + Drill + Advisor Questions

**Phase 12 unfreezes only when:**
- Real LLM smoke passes
- Frontend status gating tests complete
- Audit quality rules enhanced
- DownstreamGates stable
- User confirms unfreeze

## Future

Phase 13-18: Direction Map, Frontend, Advisor, Reliability, Benchmark, Deployment

## Execution Rule

Every phase must have its detailed playbook written and confirmed by user before code begins.
