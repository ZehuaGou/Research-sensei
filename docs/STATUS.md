# ResearchSensei Status

---

## 1. 当前状态

- Phase 1-11 baseline complete
- 466 tests passing
- 当前代码仍不是最终论文理解系统
- Phase 6 evidence 已有 PassageIndex + ClaimEvidenceV2 + BM25 EvidenceRetriever + EvidencePack
- Phase 8-10 是 rule-based baseline，不是导师级讲解
- Phase 11 是 direction pipeline v1，不是完整 literature review

---

## 2. 当前主要差距

- old builders / old with_llm builders 仍保留 rule-based fallback；pipeline baseline path 使用 old rule-based builders
- pipeline v2 path 使用 isolated v2 builders，fail-closed，不 fallback
- Frontend/API gating 尚未实现
- QualityReport debug/admin 权限尚未实现
- formula-heavy / raw-copy / generic-output audit 尚未实现
- 外部项目已完成 GitHub README 级调研，正式接入前仍需本地安装验证和样例对比
- Paper Understanding 质量仍未达到导师级
- Phase 12 仍冻结

---

## 3. 当前任务

- QualityAuditor 已接入 pipeline：
  - QualityAuditor 已接入 pipeline
  - quality_report.json 已写入所有非 FAILED run
  - BASELINE_ONLY artifact 数量 11
  - SUCCESS artifact 数量 11
  - DEGRADED artifact 数量 10
  - BLOCKED artifact 数量 8
  - audit BLOCK 可覆盖 v2 SUCCESS/DEGRADED 为 BLOCKED_UNDERSTANDING
  - audit WARNING 可写入 UnderstandingStatus.warnings
  - baseline 正常保持 BASELINE_ONLY
  - blocked 正常保持 BLOCKED_UNDERSTANDING
  - 466 tests passing（447 existing + 19 new）
- 尚未完成：
  - Frontend/API gating 尚未实现
  - QualityReport debug/admin 权限尚未实现
  - formula-heavy / raw-copy / generic-output audit 尚未实现
  - Phase 12 仍冻结
- 下一步：讨论 Frontend/API gating

---

## 4. 测试和 commit

- pytest: 466 passed
- commit: 以 `git rev-parse --short HEAD` 为准，不在 STATUS.md 固化记录

---

## 5. 当前禁止事项

- 不进入 Phase 12
- 不新增依赖
- 不真实联网测试
- 不真实调用 LLM 测试
