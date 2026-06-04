# ResearchSensei Status

---

## 1. 当前状态

- Phase 1-11 baseline complete
- 447 tests passing
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

- Isolated QualityAuditor 已完成：
  - AuditFinding / ComponentAuditResult / QualityReport / ArtifactBundle schema 已完成
  - isolated QualityAuditor 已完成
  - 初版结构性 audit 规则 F-1 到 F-6 已完成
  - Audit 当前不接 pipeline
  - Audit 当前不写 quality_report.json
  - Audit 当前不改变 UnderstandingStatus
  - 447 tests passing（427 existing + 20 new）
- 尚未完成：
  - pipeline audit 接入尚未实现
  - quality_report.json artifact 尚未实现
  - formula-heavy / raw-copy / generic-output audit 尚未实现
  - Frontend/API gating 尚未实现
  - formula_is_core 判断尚未实现
  - real LLM integration 尚未验证
- Phase 12 仍冻结
- 下一步：讨论是否将 QualityAuditor 接入 pipeline

---

## 4. 测试和 commit

- pytest: 447 passed
- commit: 以 `git rev-parse --short HEAD` 为准，不在 STATUS.md 固化记录

---

## 5. 当前禁止事项

- 不进入 Phase 12
- 不新增依赖
- 不真实联网测试
- 不真实调用 LLM 测试
