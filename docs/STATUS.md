# ResearchSensei Status

---

## 1. 当前状态

- Phase 1-11 baseline complete
- 281 tests passing
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

- 第三批（Frontend/API + Engineering Reliability + Full Pipeline）同步完成
- 全部模块开发文档同步完成
- 尚未进入代码开发
- 尚未进入 Phase 12
- 下一步：整体检查正式开发文档一致性，确认无冲突后再考虑第一个代码任务

---

## 4. 测试和 commit

- pytest: 281 passed
- commit: 以 `git rev-parse --short HEAD` 为准，不在 STATUS.md 固化记录

---

## 5. 当前禁止事项

- 不进入 Phase 12
- 不新增依赖
- 不真实联网测试
- 不真实调用 LLM 测试
