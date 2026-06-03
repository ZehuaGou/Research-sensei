# ResearchSensei Status

---

## 1. 当前状态

- Phase 1-11 baseline complete
- 335 tests passing
- 当前代码仍不是最终论文理解系统
- Phase 6 evidence 已有 PassageIndex + ClaimEvidenceV2
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

- ClaimEvidenceV2 + claim_evidence.json 已完成：
  - ParserAdapter 已接入 pipeline
  - PassageIndex 已完成并写入 passage_index.json
  - ClaimEvidenceV2 独立 schema（不污染 v1）
  - ClaimEvidenceBundle 已完成
  - build_claim_evidence(document, passage_index) 已完成
  - pipeline 写入 claim_evidence.json
  - artifact 数量从 8 变 9
  - METHOD / RESULT claim sentence selection 已修正，使用关键词匹配，命中时 DIRECT_QUOTE，未命中时 PARAPHRASE
  - 旧 evidence_index.json 仍保留，build_evidence_index / ClaimEvidence v1 / EvidenceIndex v1 未修改
  - 335 tests passing（313 existing + 22 new）
- 尚未完成：
  - BM25 / EvidenceRetriever 尚未实现
  - Paper Understanding v2 尚未实现
  - Audit / QualityReport / UnderstandingStatus 尚未实现
  - Frontend/API gating 尚未实现
- Phase 12 仍冻结
- 下一步：讨论 BM25 / EvidenceRetriever，不要直接进入 Paper Understanding

---

## 4. 测试和 commit

- pytest: 335 passed
- commit: 以 `git rev-parse --short HEAD` 为准，不在 STATUS.md 固化记录

---

## 5. 当前禁止事项

- 不进入 Phase 12
- 不新增依赖
- 不真实联网测试
- 不真实调用 LLM 测试
