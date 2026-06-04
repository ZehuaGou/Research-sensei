# ResearchSensei Module Contracts

> **Canonical docs**: See `docs/DEVELOPMENT.md` and `docs/development/*.md`.

---

## M1 — Literature Search

**测试边界**: 每个 search/download/selection 子模块必须有 mock external tests。adapter 默认用 MockTransport。

### query

Input: user_query
Output: query_plan.json
Boundary: Does not search papers. Does not generate reading plans.

### acquisition

Input: query_plan.json
Output: candidate_pool.json
Boundary: Does not filter A_READ. Does not do paper reading.

### selection

Input: candidate_pool.json
Output: filtered_candidates.json, reading_plan.json
Boundary: Does not download full text. Does not generate paper cards.

---

## M2 — Single Paper Understanding

**测试边界**: 每个 parser/evidence/understanding/audit/gating 子模块必须有 schema/artifact/failure tests。LLM 默认用 fake/mock client。

### source_resolver (M2.0)

Input: paper metadata, input_path/url
Output: source_status.json, source file
Boundary: Does not parse content. Does not generate understanding.

### ingestion / parser (M2.1)

Input: source file
Output: parsed_document.json (ParserResult)
Boundary: Does not explain papers. Does not generate paper_skeleton.

### passage_index (M2.2)

Input: parsed_document.json
Output: passage_index.json
Boundary: Only builds passages. Does not judge claims.

### claim_evidence (M2.2)

Input: passage_index.json
Output: claim_evidence.json
Boundary: Only extracts claim evidence. Does not generate final explanations.

### grounding (M2.2, v1 compatibility)

Input: parsed_document.json
Output: evidence_index.json
Boundary: Block-level evidence (v1). Does not generate teaching text.

### evidence_retriever (M2.2)

Input: claim_evidence.json + passage_index.json
Output: EvidenceRetrievalResult (runtime, not persisted)
Boundary: BM25 retrieval only. Does not generate cards.

### evidence_pack (M2.2)

Input: claim_evidence.json + passage_index.json + optional retriever
Output: EvidencePack + EvidencePackSummary (runtime, not persisted)
Boundary: Filters and prioritizes evidence for LLM. Not persisted.

### paper_understanding (M2.3)

Input: EvidencePack + paper_skeleton.json
Output: paper_card.json / formula_cards.json / teaching_cards.json / understanding_status.json
Boundary: Fail-closed. Unreliable → BLOCKED_UNDERSTANDING.

### audit (M2.4)

Input: candidate artifacts (in-memory dicts)
Output: quality_report.json
Boundary: Reads candidate artifacts, does not regenerate cards. Does not write artifacts. Pure logic.

### full_pipeline (M2.5)

Input: source file → all M2.1-M2.4
Output: 10 artifacts (baseline/success), fewer on degraded/blocked
Boundary: Orchestration only. Does not contain business logic.

---

## M3 — API / Frontend

**测试边界**: API 和前端子模块必须有 endpoint / component tests。前端 fetch 默认用 mock。

### api (M3.1)

Input: job_id
Output: /understanding_status, /cards
Boundary: /artifacts debug-only. Normal frontend must not use /artifacts.

### upload_page (M3.2)

Input: user file upload
Output: parse job creation
Boundary: Does not parse content itself. Delegates to api.

### learning_workspace (M3.3)

Input: /understanding_status + /cards
Output: User page display
Boundary: Does not read /artifacts directly. Does not display BASELINE/BLOCKED cards.

### status_banner (M3.4)

Input: understanding_status
Output: Status banner UI
Boundary: Displays status, does not modify data.

### debug_entry (M3.5)

Input: debug signal (SENSEI_DEBUG)
Output: raw artifact access
Boundary: Debug/admin only. Production must have auth.

---

## M4 — Interactive Learning

**测试边界**: 互动和记忆子模块必须有 context / memory / no-duplicate-LLM-call tests。

### direction / selection_explanation (M4.1)

Input: selected text, paper context
Output: explanation for selected content
Boundary: Must use paper context, not generic knowledge.

### patterns / symbol_formula_explanation (M4.2)

Input: formula/symbol, paper context
Output: symbol/formula breakdown
Boundary: Must bind to paper evidence, not fabricate meanings.

### interactive / context_qa (M4.3)

Input: user question, session context, cards
Output: interactive_answer.json
Boundary: Must not send entire paper to prompt.

### drill / advisor_drill (M4.4)

Input: paper_card, formula_cards, pattern_cards
Output: advisor questions and evaluations
Boundary: Questions must be paper-specific, not generic.

### context / paper_memory (M4.5)

Input: reading sessions, user interactions
Output: PaperMemory / SessionContext
Boundary: Memory is structured, not raw chat history.

### memory_first_retrieval (M4.6)

Input: user question, PaperMemory, paper context
Output: retrieved context for answer
Boundary: Must check memory before calling LLM. No duplicate LLM calls for same question.

---

## M5 — Engineering Reliability

> M5 是**横切工程保障模块**，负责测试基础设施、CI、安全、smoke、成本控制和发布门槛。
> M1-M4 的业务测试必须在各自模块内完成，M5 不替代模块验收。

**测试边界**: M5 负责测试基础设施和全局回归，不替代 M1-M4 子模块测试。

### backend_tests (M5.1)

Input: tests/, src/, pytest config
Output: pytest result
Boundary: 默认不联网。默认不真实调用 LLM。不依赖外部 API。

### frontend_tests (M5.2)

Input: frontend/src/, Vitest specs
Output: npm test result
Boundary: 不启动真实后端。fetch 使用 mock。组件测试不代替 e2e。

### llm_smoke_and_cost (M5.3)

Input: explicit env flags, model config, smoke prompt
Output: live smoke report
Boundary: 默认不执行。必须显式开启。必须控制 token 和成本。不进入普通 pytest。所有 LLM 调用通过 llm/client.py。

### cache (M5.4)

Input: prompt hash, model config, schema version
Output: cached LLM response
Boundary: cache 不进 Git。测试默认关闭。cache 不等于长期记忆。

### secret_scan (M5.5)

Input: repo files, commit diff
Output: secret scan result
Boundary: 不允许提交 .env、API key、cache、大文件。不在日志打印 key。

### debug_admin (M5.6)

Input: admin/debug auth signal, request path
Output: allow/deny debug API access
Boundary: /artifacts 是 debug/admin raw API。/quality_report 是 debug/admin API。SENSEI_DEBUG 只适合本地开发。生产环境必须有正式鉴权。

### ci_release_check (M5.7)

Input: test commands, build commands, secret scan
Output: release readiness result
Boundary: 不真实联网。不真实调用 LLM。失败时不得发布。

### render

Input: cards JSON
Output: HTML/Markdown (future)
Boundary: Must not call LLM in render.
