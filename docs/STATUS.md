# ResearchSensei Status

---

## 1. 当前状态

- Phase 1-11 baseline complete
- 410 tests passing
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

- UnderstandingStatus + BASELINE_ONLY pipeline 写入已完成：
  - UnderstandingStatus / DownstreamGates / EvidencePackSummary schema 已完成
  - pipeline baseline 模式写入 understanding_status.json
  - baseline status 为 BASELINE_ONLY，blocking_reason=NO_LLM_CLIENT
  - allowed_for_user_display=False，allowed_downstream 全 False
  - artifact 数量从 9 变 10
  - old baseline card artifacts 仍写入
  - pipeline 尚未接 v2 builders
  - 410 tests passing（400 existing + 10 new）
- 尚未完成：
  - pipeline v2 path 尚未实现
  - SUCCESS / DEGRADED_STRUCTURAL / BLOCKED_UNDERSTADING runtime mapping 尚未实现
  - Audit / QualityReport 尚未实现
  - Frontend/API gating 尚未实现
- Phase 12 仍冻结
- 下一步：讨论 pipeline v2 path：llm_client 参数、EvidencePack 构建、v2 builder 调用、BLOCKED / DEGRADED 状态映射

---

## 4. 测试和 commit

- pytest: 410 passed
- commit: 以 `git rev-parse --short HEAD` 为准，不在 STATUS.md 固化记录

---

## 5. 当前禁止事项

- 不进入 Phase 12
- 不新增依赖
- 不真实联网测试
- 不真实调用 LLM 测试
