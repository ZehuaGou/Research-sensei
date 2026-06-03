# ResearchSensei Module Contracts

---

## source_resolver

| Aspect | Rule |
|--------|------|
| Responsible for | Resolving paper source (upload, local, URL, arXiv) |
| NOT responsible for | Parsing, understanding, teaching |
| Input | user input (path/url/id) |
| Output | source_status.json + source file copy |
| Allowed deps | httpx, pathlib |
| Forbidden deps | LLM, PDF parser |
| Can call | httpx (for downloads) |
| Cannot call | ingestion, grounding, cards |
| Failure mode | status="failed", warning added |

---

## ingestion / parser

| Aspect | Rule |
|--------|------|
| Responsible for | Parsing document into blocks |
| NOT responsible for | Understanding, explaining, teaching |
| Input | source file |
| Output | parsed_document.json |
| Allowed deps | PyMuPDF (optional) |
| Forbidden deps | LLM |
| Can call | nothing downstream |
| Cannot call | grounding, cards, LLM |
| Failure mode | degraded=true, warning added |

**Critical**: Parser does NOT generate explanations. It only extracts structure.

---

## grounding / evidence

| Aspect | Rule |
|--------|------|
| Responsible for | Binding claims to evidence |
| NOT responsible for | Generating explanations or teaching text |
| Input | parsed_document.json |
| Output | evidence_index.json |
| Allowed deps | none |
| Forbidden deps | LLM, network |
| Can call | nothing |
| Cannot call | cards, LLM |
| Failure mode | INSUFFICIENT_EVIDENCE / NEEDS_HUMAN_CHECK |

**Critical**: Evidence layer does NOT generate teaching text. It only binds claims to blocks.

---

## paper_skeleton

| Aspect | Rule |
|--------|------|
| Responsible for | Extracting paper structure |
| NOT responsible for | Teaching, explaining |
| Input | parsed_document.json + evidence_index.json |
| Output | paper_skeleton.json |
| Allowed deps | none (v1), LLM (v2) |
| Forbidden deps | network |
| Can call | evidence_index |
| Cannot call | cards |
| Failure mode | UNKNOWN / INSUFFICIENT_EVIDENCE |

---

## paper_card / formula_card / teaching_card

| Aspect | Rule |
|--------|------|
| Responsible for | Generating learning cards |
| NOT responsible for | Parsing, evidence binding |
| Input | skeleton + evidence |
| Output | card JSON |
| Allowed deps | LLM (via llm/client.py) |
| Forbidden deps | network (direct) |
| Can call | llm/client.py |
| Cannot call | source_resolver, parser |
| Failure mode | fallback to rule-based, degraded confidence |

**Critical**: Card builders do NOT directly call network. All LLM calls go through llm/client.py.

---

## query / acquisition / selection / direction

| Aspect | Rule |
|--------|------|
| Responsible for | Direction analysis pipeline |
| NOT responsible for | Single paper understanding |
| Input | user query |
| Output | query_plan → candidate_pool → filtered_candidates → reading_plan |
| Allowed deps | httpx (via adapters) |
| Forbidden deps | LLM (for acquisition) |
| Can call | arXiv/OpenAlex adapters |
| Cannot call | paper_card, teaching_card |
| Failure mode | warning in bundle |

---

## llm

| Aspect | Rule |
|--------|------|
| Responsible for | LLM communication, prompt building, caching |
| NOT responsible for | Business logic, card generation |
| Input | messages |
| Output | response |
| Allowed deps | httpx |
| Forbidden deps | none |
| Can call | LLM API |
| Cannot call | nothing business-level |
| Failure mode | LLMClientError / fallback to mock |

---

## audit (Phase 11.9 — new)

| Aspect | Rule |
|--------|------|
| Responsible for | Checking explanation quality |
| NOT responsible for | Generating explanations |
| Input | card JSON + evidence_index |
| Output | audit report |
| Allowed deps | LLM (for cross-model review) |
| Forbidden deps | none |
| Can call | llm/client.py |
| Cannot call | card builders (must be independent) |

**Critical**: Audit must be independent. The generator must NOT audit itself.

---

## workspace / jobs

| Aspect | Rule |
|--------|------|
| Responsible for | File system and job persistence |
| NOT responsible for | Business logic |
| Input | job data |
| Output | files + SQLite records |
| Allowed deps | sqlite3, pathlib |
| Forbidden deps | LLM, network |
| Can call | nothing |
| Cannot call | nothing |
| Failure mode | JobNotFoundError |

---

## web API

| Aspect | Rule |
|--------|------|
| Responsible for | HTTP endpoints |
| NOT responsible for | Business logic |
| Input | HTTP requests |
| Output | HTTP responses |
| Allowed deps | FastAPI |
| Forbidden deps | direct network calls |
| Can call | source_resolver, jobs, workspace |
| Cannot call | LLM directly |
| Failure mode | structured error response |
