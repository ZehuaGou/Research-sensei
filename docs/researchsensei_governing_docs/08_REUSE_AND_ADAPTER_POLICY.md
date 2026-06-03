# ResearchSensei Reuse and Adapter Policy

---

## Principles

1. **Not for reuse's sake.** Only reuse when it genuinely solves a problem.
2. **Not whole-package migration.** ARIS is not imported wholesale.
3. **Not default heavy dependencies.** Optional adapters only.
4. **Useful capabilities absorbed via adapter / workflow / prompt / audit contract.**
5. **Every dependency needs reuse gate.**

---

## Decision Categories

| Category | Meaning |
|----------|---------|
| DIRECT_DEPENDENCY | Install as project dependency (default) |
| DIRECT_ADAPTER | Wrap as adapter, default available |
| OPTIONAL_ADAPTER | Wrap as adapter, user must install |
| REFERENCE_ONLY | Learn from design, do not import code |
| NOT_USE | Explicitly not used |

---

## External Project Decisions

### ARIS

| Aspect | Decision |
|--------|----------|
| What it does | 77 composable skills for ML research lifecycle |
| What we learn | Audit chain, reviewer independence, assurance contract |
| What we do NOT learn | Skills architecture, idea discovery, experiment bridge |
| Category | REFERENCE_ONLY |
| Risk | Whole-package import would pollute architecture |

**Specific ARIS concepts we reference**:
- `reviewer-independence.md` — explanation and audit should be separate
- `assurance-contract.md` — 6-state verdict (PASS/WARN/FAIL/BLOCKED/ERROR/NOT_APPLICABLE)
- `paper-claim-audit` — zero-context verification prevents confirmation bias
- `citation-audit` — three-layer verification (existence, metadata, context)

### PaperQA

| Aspect | Decision |
|--------|----------|
| What it does | Scientific literature QA with passage retrieval |
| What we learn | Passage retrieval, citation-backed answers |
| What we do NOT learn | QA system architecture |
| Category | OPTIONAL_ADAPTER |
| Risk | QA system ≠ teaching system |

### OpenScholar

| Aspect | Decision |
|--------|----------|
| What it does | Passage-level retrieval, citation accuracy benchmark |
| What we learn | Citation accuracy evaluation methods |
| Category | REFERENCE_ONLY |

### ResearchPilot

| Aspect | Decision |
|--------|----------|
| What it does | Research question → retrieval → structured findings |
| What we learn | Structured findings design |
| Category | REFERENCE_ONLY |

### STORM

| Aspect | Decision |
|--------|----------|
| What it does | Outline-guided synthesis, multi-perspective questions |
| What we learn | Outline-guided design for cross-paper synthesis |
| Category | REFERENCE_ONLY |
| Note | STORM writes surveys; we teach reading |

### Docling

| Aspect | Decision |
|--------|----------|
| What it does | PDF parsing with layout/table/formula support |
| Category | OPTIONAL_ADAPTER |
| Risk | Heavy dependency, requires installation |

### Nougat

| Aspect | Decision |
|--------|----------|
| What it does | PDF → Markdown with formula conversion |
| Category | OPTIONAL_ADAPTER |
| Risk | Requires GPU, heavy dependency |

### Marker

| Aspect | Decision |
|--------|----------|
| What it does | PDF → Markdown, fast |
| Category | OPTIONAL_ADAPTER |
| Risk | Lighter than Docling/Nougat |

### MinerU

| Aspect | Decision |
|--------|----------|
| What it does | PDF parsing with layout analysis |
| Category | OPTIONAL_ADAPTER |
| Risk | Heavy dependency |

### Unstructured

| Aspect | Decision |
|--------|----------|
| What it does | General document parsing |
| Category | NOT_USE |
| Reason | Too generic, not academic-focused |

---

## Current Dependencies (pyproject.toml)

| Dependency | Role | Category |
|------------|------|----------|
| fastapi | Backend API | DIRECT_DEPENDENCY |
| httpx | HTTP client + mock tests | DIRECT_DEPENDENCY |
| httpx-sse | LLM streaming | DIRECT_DEPENDENCY |
| jinja2 | Template rendering | DIRECT_DEPENDENCY |
| pymupdf | PDF fallback parsing | DIRECT_DEPENDENCY |
| python-multipart | FastAPI upload | DIRECT_DEPENDENCY |
| python-dotenv | Environment loading | DIRECT_DEPENDENCY |
| pydantic | Schema validation | DIRECT_DEPENDENCY |
| uvicorn | ASGI server | DIRECT_DEPENDENCY |
| aiosqlite | Async SQLite (unused) | DIRECT_DEPENDENCY (review later) |

---

## Adapter Design Rules

1. **Accept httpx.Client via dependency injection.** Enables MockTransport in tests.
2. **Accept LLMClient | MockLLMClient.** Enables mock testing.
3. **Return typed Pydantic models.** Enables schema validation.
4. **Log failures, do not swallow.** Exceptions propagate to caller.
5. **Provide fallback.** If adapter fails, degrade gracefully.
