# 07_NIGHT_RUN_PLAYBOOK

本文件用于无人值守长任务。目标是让 Agent 晚上可以连续做事，但不能失控。

## 重要判断

不要让 Agent “整晚自由开发完整系统”。正确方式是：

```text
按阶段任务队列执行。
每个 task 完成后运行测试。
测试失败就停。
不得越级开发。
不得生成无关文件。
```

## 夜间允许执行的阶段

建议夜间只执行这些阶段：

- Phase 0 文档与复用评估
- Phase 1 项目骨架
- Phase 2 Schema 与示例数据
- Phase 3 LLM mock 层与 Prompt 基建
- Phase 4 markdown/txt 解析基础版
- Phase 7 静态 HTML 渲染基础版
- Phase 12 日志/缓存/断点续跑基础设施

不建议夜间无人值守完整推进：

- Phase 5 深度论文理解
- Phase 6 公式/模式/训练卡生成
- Phase 8 交互追问
- Phase 9 搜索筛选
- Phase 10 方向地图
- Phase 13 真实论文评估

这些阶段更容易出现“看起来对，其实胡编”。需要人工验收。

## 夜间任务边界

一次夜间最多执行：

```text
Phase 0 -> Phase 4
```

或者：

```text
从当前 Phase 开始，最多连续执行 3 个 Phase。
```

不要让它从 0 干到 14。风险太高。

## 夜间执行前准备

Agent 必须先做：

```bash
git status
python --version
pip list
pytest -q
```

如果项目没有 git 仓库，应先提示用户初始化，或至少写入 `BASELINE_FILE_LIST.txt`。

## 夜间执行输出文件

必须维护：

```text
PROGRESS.md
CHANGELOG_AGENT.md
OPEN_QUESTIONS.md
TEST_RESULTS.md
```

### PROGRESS.md 格式

```markdown
# PROGRESS

## Current Phase
Phase X - xxx

## Completed Tasks
- [x] Task X.1 ...

## Failed Tasks
- [ ] Task X.2 ...
  - failure reason:
  - attempted fix:
  - next action:

## Next Safe Task
Task X.3 ...
```

### CHANGELOG_AGENT.md 格式

```markdown
# CHANGELOG_AGENT

## YYYY-MM-DD HH:mm
- Modified:
  - path
- Added:
  - path
- Tests:
  - command: result
- Notes:
  - xxx
```

## 夜间失败停止条件

遇到以下任一情况必须停止：

1. pytest 失败且修复一次后仍失败。
2. 需要真实 API key 才能继续。
3. 需要用户选择技术方案。
4. 发现原项目已有代码结构和文档冲突。
5. 某个依赖安装失败。
6. 需要联网但当前环境不可联网。
7. 解析器/依赖存在许可证或安全不确定。
8. 需要删除或覆盖已有用户结果。

## 夜间可复制 Prompt

见：`prompts/night_run_prompt.md`
