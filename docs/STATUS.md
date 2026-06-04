# ResearchSensei Status

---

## 1. 当前状态

- Phase 1-11 baseline complete
- 481 tests passing
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
- Frontend UI 尚未适配新 endpoint
- 外部项目已完成 GitHub README 级调研，正式接入前仍需本地安装验证和样例对比
- Paper Understanding 质量仍未达到导师级
- Phase 12 仍冻结

---

## 3. 当前任务

- API gating 第一批已完成：
  - /understanding_status endpoint 已完成
  - /cards endpoint 已完成（status gating + card artifact 一致性校验）
  - SUCCESS 缺 cards 返回 409
  - DEGRADED 缺 paper_card/formula_cards 返回 409
  - DEGRADED 缺 teaching_cards 返回 200 + degraded 标记
  - /artifacts 默认 403，SENSEI_DEBUG=1 时返回 raw artifacts
  - quality_report 不通过普通 /artifacts 暴露
  - BASELINE_ONLY cards 不通过普通 /artifacts 暴露
  - API gating 基础测试已覆盖 SUCCESS / DEGRADED / BLOCKED
  - Frontend UI 尚未适配新 endpoint
  - 481 tests passing（476 existing + 5 new）
- 尚未完成：
  - /quality_report debug/admin endpoint 尚未实现
  - 正式鉴权系统尚未实现
  - formula-heavy / raw-copy / generic-output audit 尚未实现
  - Phase 12 仍冻结
- 下一步：讨论 frontend UI 适配或继续补 audit 规则

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
