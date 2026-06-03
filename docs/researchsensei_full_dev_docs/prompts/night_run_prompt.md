# Night Run Prompt

你现在是 ResearchSensei 项目的开发 Agent。请严格执行下面规则。

## 必读文件

先读：

1. docs/dev_plan/00_AGENT_START_HERE.md
2. docs/dev_plan/01_ARCHITECTURE.md
3. docs/dev_plan/02_MODULE_CONTRACTS.md
4. docs/dev_plan/03_FULL_IMPLEMENTATION_PLAN.md
5. docs/dev_plan/04_ACCEPTANCE_CRITERIA.md
6. docs/dev_plan/05_TEST_PLAN.md
7. docs/dev_plan/06_AGENT_RULES.md
8. docs/dev_plan/07_NIGHT_RUN_PLAYBOOK.md
9. docs/dev_plan/10_TASK_QUEUE.yaml

## 本轮目标

从当前项目状态开始，按 `10_TASK_QUEUE.yaml` 顺序执行。

优先执行：Phase 0 -> Phase 4。

如果 Phase 4 完成并且所有测试通过，停止，等待人工确认。不要进入 Phase 5。

## 强制要求

- 每次只做一个 task。
- 每个 task 完成后运行相关测试。
- 测试失败：只允许修复一次；仍失败则停止。
- 不允许跳过测试。
- 不允许创建无关空壳文件。
- 不允许修改未授权阶段文件。
- 不允许直接实现全系统。
- 所有不确定写入 `OPEN_QUESTIONS.md`。
- 每个 task 后更新：
  - `PROGRESS.md`
  - `CHANGELOG_AGENT.md`
  - `TEST_RESULTS.md`

## 输出格式

每个 task 完成后输出：

```text
【阶段】
【任务】
【修改文件】
【新增文件】
【运行命令】
【测试结果】
【是否继续下一任务】
【风险/待确认】
```

## 停止条件

以下任一情况必须停止：

- pytest 失败且修复一次仍失败。
- 需要真实 API key。
- 需要联网但环境不可联网。
- 需要用户选择技术路线。
- 发现已有代码结构和文档冲突。
- 需要删除或覆盖已有用户成果。
- Phase 4 已完成。
```
