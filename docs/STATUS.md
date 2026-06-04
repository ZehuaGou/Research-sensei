# ResearchSensei Status

---

## 1. 当前状态

- Phase 1-11 baseline complete
- 481 backend tests passing + 7 frontend tests passing
- 当前代码仍不是最终论文理解系统
- Phase 6 evidence 已有 PassageIndex + ClaimEvidenceV2 + BM25 EvidenceRetriever + EvidencePack
- Phase 8-10 是 rule-based baseline，不是导师级讲解
- Phase 11 是 direction pipeline v1，不是完整 literature review

---

## 2. 当前主要差距

- old builders / old with_llm builders 仍保留 rule-based fallback；pipeline baseline path 使用 old rule-based builders
- pipeline v2 path 使用 isolated v2 builders，fail-closed，不 fallback
- QualityReport debug/admin endpoint 尚未实现
- formula-heavy / raw-copy / generic-output audit 尚未实现
- LearningWorkspaceView / UploadView 测试尚未实现
- 外部项目已完成 GitHub README 级调研，正式接入前仍需本地安装验证和样例对比
- Paper Understanding 质量仍未达到导师级
- Phase 12 仍冻结

---

## 3. 当前任务

- 前端测试基础已引入：
  - Vitest + Vue Test Utils + jsdom 已安装
  - StatusBanner 组件测试已覆盖 BASELINE_ONLY / BLOCKED / DEGRADED / FAILED / SUCCESS
  - npm test 通过（7 tests）
  - npm run build 通过
  - 481 backend tests + 7 frontend tests
- 尚未完成：
  - LearningWorkspaceView / UploadView 测试尚未实现
  - real LLM smoke 方案尚未讨论
  - Phase 12 仍冻结
- 下一步：第二批前端测试（LearningWorkspaceView status gating）或 real LLM smoke 方案讨论

---

## 4. 测试和 commit

- pytest: 481 passed
- commit: 以 `git rev-parse --short HEAD` 为准，不在 STATUS.md 固化记录

---

## 5. 当前禁止事项

- 不进入 Phase 12
- 不新增依赖
- 不真实联网测试
- 不真实调用 LLM 测试
