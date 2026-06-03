# ResearchSensei Status

---

## 1. 当前状态

- Phase 1-11 baseline complete
- 427 tests passing
- 当前代码仍不是最终论文理解系统
- Phase 6 evidence 已有 PassageIndex + ClaimEvidenceV2 + BM25 EvidenceRetriever + EvidencePack
- Phase 8-10 是 rule-based baseline，不是导师级讲解
- Phase 11 是 direction pipeline v1，不是完整 literature review

---

## 2. 当前主要差距

- fail-closed 策略已写入 DEVELOPMENT，但当前代码还未完全实现
- understanding_status.json 还未实现
- 当前 card builders 仍使用 rule-based baseline 作为 fallback
- 外部项目已完成 GitHub README 级调研，正式接入前仍需本地安装验证和样例对比
- Paper Understanding 质量仍未达到导师级

---

## 3. 当前任务

- Pipeline v2 path 已接入：
  - pipeline 新增 llm_client 可选参数
  - baseline path 仍为 BASELINE_ONLY
  - v2 path 构建 EvidencePack 并调用 isolated v2 builders
  - v2 SUCCESS / DEGRADED_STRUCTURAL / BLOCKED_UNDERSTADING 状态映射已实现
  - BLOCKED 不写 card artifacts
  - DEGRADED 不写 failed teaching artifact
  - job.status 区分 FAILED（系统异常）和 BLOCKED（理解失败）
  - EvidencePackSummary 写入 UnderstandingStatus
  - _run_async_builder 处理 sync pipeline 调用 async v2 builders
  - 427 tests passing（410 existing + 17 new）
- 尚未完成：
  - Audit / QualityReport 尚未实现
  - Frontend/API gating 尚未实现
  - formula_is_core 判断尚未实现
  - real LLM integration 尚未验证
- Phase 12 仍冻结
- 下一步：讨论 Audit / QualityReport

---

## 4. 测试和 commit

- pytest: 427 passed
- commit: 以 `git rev-parse --short HEAD` 为准，不在 STATUS.md 固化记录

---

## 5. 当前禁止事项

- 不进入 Phase 12
- 不新增依赖
- 不真实联网测试
- 不真实调用 LLM 测试
