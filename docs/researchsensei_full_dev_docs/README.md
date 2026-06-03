# ResearchSensei Full Development Docs

本文件夹用于把 `RS设计文档` 转成 Agent/Codex/Web Coding 可执行的开发规格。

## 使用方式

把整个文件夹复制到项目根目录：

```text
researchsensei/
  docs/dev_plan/   <- 放本文件夹内容
  src/
  tests/
```

然后让 AI 先读：

1. `00_AGENT_START_HERE.md`
2. `01_ARCHITECTURE.md`
3. `02_MODULE_CONTRACTS.md`
4. `03_FULL_IMPLEMENTATION_PLAN.md`
5. `04_ACCEPTANCE_CRITERIA.md`
6. `05_TEST_PLAN.md`
7. `06_AGENT_RULES.md`
8. `07_NIGHT_RUN_PLAYBOOK.md`

## 核心原则

- 文档可以完整，代码必须分阶段实现。
- 每阶段必须可运行、可测试、可回滚。
- 测试不过，不允许进入下一阶段。
- Agent 不得一口气实现全系统。
- 每次只允许在当前阶段授权范围内修改文件。
- 任何“不确定”必须写入 `OPEN_QUESTIONS.md`，不得脑补。

## 推荐执行

白天人工确认方向，晚上可让 Agent 按 `07_NIGHT_RUN_PLAYBOOK.md` 执行。

但夜间长任务必须满足：

- 每个阶段结束后运行测试。
- 失败即停。
- 写入 `PROGRESS.md`。
- 写入 `CHANGELOG_AGENT.md`。
- 不允许跳过测试继续开发。
