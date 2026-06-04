# ResearchSensei 主链路 v1 封版记录 — 历史归档

> **本文档是历史封版记录，不作为当前开发依据。**
> 当前正式开发依据是 M1-M5 模块体系，见 DESIGN.md 和 STATUS.md。

---

## 1. 当前阶段结论

- 主链路 v1 可以阶段性封版。
- 不是产品最终完成。
- Phase 12 仍冻结。
- 后续功能必须在当前链路稳定基础上继续。

---

## 2. 已完成能力

### Pipeline

- ParserAdapter 已接入 SinglePaperIngestionRunner
- PassageIndex 已生成并写入 passage_index.json
- ClaimEvidenceV2 / claim_evidence.json 已生成
- EvidencePack runtime builder 已实现
- baseline path：BASELINE_ONLY（无 llm_client）
- v2 path：SUCCESS / DEGRADED_STRUCTURAL / BLOCKED_UNDERSTANDING
- quality_report.json 已接入所有非 FAILED run
- understanding_status.json 已接入所有非 FAILED run
- audit BLOCK 可覆盖 v2 SUCCESS/DEGRADED 为 BLOCKED_UNDERSTANDING
- audit WARNING 可写入 UnderstandingStatus.warnings
- _run_async_builder 处理 sync pipeline 调用 async v2 builders

### API

- /understanding_status 已实现
- /cards 已实现（status gating + card artifact 一致性校验）
- /artifacts 默认 403，SENSEI_DEBUG=1 时返回 raw artifacts
- BASELINE_ONLY / BLOCKED 不返回 cards
- SUCCESS / DEGRADED 按 status 返回 cards
- SUCCESS 缺 cards 返回 409
- DEGRADED 缺 required cards 返回 409
- DEGRADED 缺 teaching_cards 返回 200 + degraded 标记

### Frontend

- UploadView 改用 /api/v1/documents/parse
- LearningWorkspaceView 改用 /understanding_status + /cards
- BASELINE_ONLY / BLOCKED 不展示 cards，显示 StatusBanner
- DEGRADED 显示降级提示
- Phase 12 tabs 显示"未开放"
- FormulaCard 字段兼容后端 schema（formula_raw/purpose/location 映射）
- frontend npm run build 成功

### Audit

- QualityAuditor 已实现
- F-1 到 F-6 结构性规则已实现
- candidate audit 语义已写清（AUDIT_QUALITY.md）
- formula-heavy / raw-copy / generic-output 未实现

### Evidence

- passage_index.json / claim_evidence.json / evidence_index.json 职责清晰
- v1 evidence_index.json 兼容保留
- EvidencePack 不持久化（runtime only）
- EvidencePackSummary 写入 UnderstandingStatus
- BM25 EvidenceRetriever 已实现
- evidence_ref 跳转尚未实现

---

## 3. 当前验证结果

- backend pytest：481 passed
- frontend npm install：成功
- frontend npm run build：成功（300ms）
- 静态 grep：无 /api/papers/upload，无 /api/learn
- API baseline flow 验证通过（parse → understanding_status → cards 403 → artifacts 403）
- SUCCESS / DEGRADED / BLOCKED API gating 测试通过（15 个测试）
- 未跑 Playwright / Cypress
- 当前没有前端自动化测试
- 页面级验证主要是 build + 代码审查 + API 测试

---

## 4. 已知限制

- 未接真实 LLM smoke
- 未实现前端自动化测试（Vitest / Vue Test Utils）
- 未实现 e2e 测试（Playwright / Cypress）
- 未实现 Docling parser adapter
- 未实现 evidence_ref 原文跳转
- 未实现 formula-heavy / raw-copy / generic audit 规则
- 未实现 /quality_report debug endpoint
- 未实现正式 debug/admin 鉴权
- Phase 12 未解冻
- old with_llm builders 仍存在 fallback，但 pipeline v2 不使用它们

---

## 5. 下一阶段建议优先级

### P0：必须先做

1. **前端自动化测试**：Vitest + Vue Test Utils，覆盖 status gating 逻辑
2. **real LLM smoke 方案讨论**：先定 env、模型、成本、失败处理，不直接跑

### P1：建议近期做

1. real LLM smoke 实现
2. Docling parser adapter
3. Audit 质量规则增强（formula-heavy / raw-copy / generic-output）
4. /quality_report debug endpoint
5. debug/admin 鉴权

### P2：可以后置

1. evidence_ref 跳转
2. e2e 测试
3. Phase 12 解冻准备

---

## 6. 禁止误解

- BASELINE_ONLY 不是最终导师级理解，只是无 LLM 时的结构化骨架
- DEGRADED_STRUCTURAL 不是完整导师级解释，teaching 层已降级
- quality_report 审的是 candidate artifacts（pipeline 写盘前的内存对象），不是 final written artifacts
- /artifacts 不是普通前端数据入口，是 debug-only raw API
- Phase 12 不可使用，patterns/drill 标记为"未开放"
- v2 builders fail-closed，不 fallback
- old with_llm builders 仍存在 fallback，但 pipeline v2 path 不使用它们
