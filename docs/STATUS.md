# ResearchSensei Status

---

## 1. 当前状态

- Phase 1-11 baseline complete
- 281 tests passing
- 当前重点：Paper Understanding 核心升级
- Phase 12 暂不开发

---

## 2. 当前下一步

Paper Understanding 核心升级，按以下顺序：

1. ParserAdapter — 设计 interface，包装现有 parser
2. PassageIndex + ClaimEvidence — 升级 evidence 到 passage/claim-level
3. Evidence-constrained LLM — LLM card builder 接入主 pipeline
4. Quality Benchmark — 质量审计和 hard-fail 测试

---

## 3. 当前限制

- Phase 6 evidence 仍是 block-level，不是 claim-level
- Phase 8-10 仍是 rule-based baseline，不是导师级讲解
- Phase 11 是 direction pipeline v1，不是完整 literature review
- 这些限制会影响最终"讲得好"

---

## 4. 当前测试结果

- pytest: 281 passed
- 最近 commit: `c4c6ae6 organize development docs by major modules`

---

## 5. 当前禁止事项

- 不进入 Phase 12
- 不新增依赖
- 不真实联网测试
- 不真实调用 LLM 测试
