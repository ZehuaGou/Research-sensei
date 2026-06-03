# ResearchSensei Status

---

## 1. 当前状态

- Phase 1-11 baseline complete
- 400 tests passing
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

- Isolated LLM v2 card builders 已完成：
  - LLM output schemas（PaperCardLLMOutput / FormulaCardsLLMOutput / TeachingCardsLLMOutput）
  - LLM output validator（evidence_ref 校验）
  - isolated PaperCard v2 builder（fail-closed，不 fallback）
  - isolated FormulaCards v2 builder（fail-closed，不 fallback）
  - isolated TeachingCards v2 builder（fail-closed，不 fallback）
  - v2 builders 未接 pipeline
  - 未改旧 rule-based builders
  - 未改旧 with_llm builders
  - 400 tests passing（369 existing + 31 new）
- 尚未完成：
  - EvidencePackSummary 尚未实现
  - UnderstandingStatus 尚未实现
  - BASELINE_ONLY 尚未实现
  - pipeline v2 path 尚未实现
  - Audit / QualityReport 尚未实现
  - Frontend/API gating 尚未实现
- Phase 12 仍冻结
- 下一步：讨论 UnderstandingStatus + BASELINE_ONLY + pipeline v2 gating

---

## 4. 测试和 commit

- pytest: 400 passed
- commit: 以 `git rev-parse --short HEAD` 为准，不在 STATUS.md 固化记录

---

## 5. 当前禁止事项

- 不进入 Phase 12
- 不新增依赖
- 不真实联网测试
- 不真实调用 LLM 测试
