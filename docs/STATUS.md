# ResearchSensei Status

---

## 1. 当前状态

- Phase 1-11 baseline complete
- 313 tests passing
- 当前代码仍不是最终论文理解系统
- Phase 6 evidence 已有 PassageIndex，但 ClaimEvidence 仍是 block-level
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

- PassageIndex 第一小批已完成：
  - Passage / PassageIndex / PassageIndexBuildConfig / PassageIndexStats schema
  - build_passage_index(document) builder
  - pipeline 写入 passage_index.json
  - artifact 数量从 7 变为 8
  - 旧 evidence_index.json 仍保留，build_evidence_index / ClaimEvidence / EvidenceIndex v1 未修改
  - 313 tests passing（298 existing + 15 new）
- 尚未完成：
  - ClaimEvidence v2 字段尚未实现
  - ClaimEvidenceBundle 尚未实现
  - claim_evidence.json 尚未实现
  - BM25 / EvidenceRetriever 尚未实现
  - Paper Understanding v2 尚未实现
  - Audit / QualityReport / UnderstandingStatus 尚未实现
  - Frontend/API gating 尚未实现
- Phase 12 仍冻结
- 下一步：规划 ClaimEvidence v2 + claim_evidence.json，不要直接大改

---

## 4. 测试和 commit

- pytest: 313 passed
- commit: 以 `git rev-parse --short HEAD` 为准，不在 STATUS.md 固化记录

---

## 5. 当前禁止事项

- 不进入 Phase 12
- 不新增依赖
- 不真实联网测试
- 不真实调用 LLM 测试
