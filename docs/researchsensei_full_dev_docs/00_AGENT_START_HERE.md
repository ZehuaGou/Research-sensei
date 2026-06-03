# 00_AGENT_START_HERE

> **HISTORICAL DOCUMENT — DO NOT EXECUTE DIRECTLY**
>
> This original full dev docs package is historical reference only.
> The canonical execution entry is now:
> **`docs/researchsensei_governing_docs/00_START_HERE.md`**
>
> Do not execute old phase numbers directly. See governing docs for current route.

---

## 启动必读：复用门禁

每次开始工作前，除本开发文档包外，必须先读取项目根目录下的 `docs/REUSE_REPORT.md`。

新大 Phase 开始前必须执行 reuse gate：

1. 明确本 Phase 要解决的问题。
2. 检查成熟开源项目、GitHub 项目、官方 API、SDK 或可复用库。
3. 更新 `docs/REUSE_REPORT.md`，记录候选工具、license、维护活跃度、安装复杂度、安全性、替代方案和最终决策。
4. 未完成复用评估前，不允许写本 Phase 的业务代码。
5. 第三方能力必须通过 Adapter 封装，不能深度耦合进核心流程。

此规则优先级高于具体 Phase 任务描述。若用户要求直接进入代码开发，但该 Phase 的复用评估尚未完成，必须先完成 `docs/REUSE_REPORT.md` 更新。

你是 ResearchSensei 项目的开发 Agent。你的任务不是自由发挥，而是严格按照本文档包逐阶段实现系统。

## 项目一句话定义

ResearchSensei 是一个“科研论文理解与思维框架训练系统”。用户输入方向或单篇论文，系统通过搜索、精读、讲解、追问、训练，帮助用户真正看懂论文，建立科研思维，并能回答导师追问。

## 绝对禁止

1. 禁止直接根据原始需求文档一口气实现完整系统。
2. 禁止创建大量没有逻辑的空壳文件。
3. 禁止把系统做成普通摘要器。
4. 禁止只处理标题/摘要就输出深度论文理解。
5. 禁止每次追问都把整篇论文塞进 LLM。
6. 禁止绕过 evidence/grounding 机制直接生成结论。
7. 禁止把合理推测写成论文事实。
8. 禁止写死 API key、模型 key、路径、用户私有信息。
9. 禁止引入许可证不明或难以替换的强依赖。
10. 禁止测试未通过还继续下一阶段。

## 执行顺序

必须按以下文件执行：

1. `01_ARCHITECTURE.md`：理解总架构。
2. `02_MODULE_CONTRACTS.md`：理解模块边界和输入输出。
3. `03_FULL_IMPLEMENTATION_PLAN.md`：选择当前阶段。
4. `04_ACCEPTANCE_CRITERIA.md`：确认完成标准。
5. `05_TEST_PLAN.md`：写测试和运行测试。
6. `06_AGENT_RULES.md`：遵守开发纪律。
7. `07_NIGHT_RUN_PLAYBOOK.md`：如果是无人值守长任务，必须遵守。

## 每轮任务输出格式

每完成一个任务，必须在回复中输出：

```text
【阶段】Phase X - xxx
【任务】Task X.Y - xxx
【修改文件】
- path/to/file
【新增文件】
- path/to/file
【运行命令】
- command
【测试结果】
- pass/fail
【未完成项】
- xxx
【风险/待确认】
- xxx
【下一步建议】
- Task X.Y+1
```

## 失败处理

如果任何测试、导入、启动、静态检查失败：

1. 停止进入后续任务。
2. 尝试在当前任务范围内修复一次。
3. 修复仍失败，写入 `PROGRESS.md` 和 `OPEN_QUESTIONS.md`。
4. 不得继续推进下一阶段。
