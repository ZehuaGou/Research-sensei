# ResearchSensei Status

---

## 1. 当前状态

- Phase 1-11 baseline complete
- 298 tests passing
- 当前代码仍不是最终论文理解系统
- Phase 6 evidence 是 block-level，不是 claim-level
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

- ParserAdapter 已完成并接入 pipeline：
  - ParserAdapter 抽象接口（supports / parse）
  - LightweightParserAdapter（包装 LightweightIngestionService）
  - ParseMetadata / ParserResult schema
  - DocumentBlock Optional 结构化字段（bbox / table_html / figure_caption / reference_entries）
  - ParserAdapter 已接入 SinglePaperIngestionRunner
  - parser_adapter=None 时仍走 LightweightIngestionService
  - 注入 parser_adapter 时使用 ParserResult.document
  - parsed_document.json 仍是 DocumentIngestion shape
  - 298 tests passing（292 existing + 6 new）
- 尚未完成：
  - PassageIndex / passage_index.json 尚未实现
  - ClaimEvidence v2 / claim_evidence.json 尚未实现
  - evidence_index.json v1 wrapper 尚未升级
  - Paper Understanding v2 尚未实现
  - Audit / QualityReport / UnderstandingStatus 尚未实现
  - Frontend/API gating 尚未实现
- Phase 12 仍冻结
- 下一步：规划 PassageIndex + ClaimEvidence v2，不要直接大改

---

## 4. 测试和 commit

- pytest: 298 passed
- commit: 以 `git rev-parse --short HEAD` 为准，不在 STATUS.md 固化记录

---

## 5. 当前禁止事项

- 不进入 Phase 12
- 不新增依赖
- 不真实联网测试
- 不真实调用 LLM 测试
