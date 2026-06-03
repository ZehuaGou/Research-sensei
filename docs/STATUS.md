# ResearchSensei Status

---

## 1. 当前状态

- Phase 1-11 baseline complete
- 368 tests passing
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

- EvidencePack runtime builder 已完成：
  - EvidencePackItem / EvidencePack schema
  - build_evidence_pack(claim_bundle, passage_index, retriever) builder
  - 过滤 INSUFFICIENT_EVIDENCE / low confidence / empty claim_type
  - claim_type 优先级排序（METHOD > RESULT > FORMULA_CONTEXT > ...）
  - retriever 集成（命中用 top result，无命中 fallback 到 claim.passage_id）
  - token budget 控制 + passage_text 截断
  - EvidencePack 是 runtime object，未接 pipeline，未写 artifact
  - EvidencePackSummary 尚未实现
  - 368 tests passing（350 existing + 18 new）
- 尚未完成：
  - LLM v2 card builder 尚未实现
  - fail-closed runtime status 尚未实现
  - Audit / QualityReport / UnderstandingStatus 尚未实现
  - Frontend/API gating 尚未实现
- Phase 12 仍冻结
- 下一步：讨论 LLM v2 card builder + fail-closed，不要直接进入 Audit 或 Frontend

---

## 4. 测试和 commit

- pytest: 368 passed
- commit: 以 `git rev-parse --short HEAD` 为准，不在 STATUS.md 固化记录

---

## 5. 当前禁止事项

- 不进入 Phase 12
- 不新增依赖
- 不真实联网测试
- 不真实调用 LLM 测试
