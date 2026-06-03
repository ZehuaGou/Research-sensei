# 06_AGENT_RULES

## 全局复用门禁 / No Rebuilding Rule

ResearchSensei 严禁重复造轮子。任何新的大 Phase 开始前，必须先检查是否有成熟开源项目、GitHub 项目、官方 API、SDK 或可复用库可以复用、封装或适配。

强制规则：

- 每个新 Phase 开始前，必须先更新 `docs/REUSE_REPORT.md`。
- `docs/REUSE_REPORT.md` 必须列出本 Phase 的候选开源项目/API/SDK，以及每个候选的用途、license、维护活跃度、安装复杂度、Windows 支持、本地部署、GPU/付费 API 需求、安全性、替代方案和最终决策。
- 复用评估未完成前，不得写本 Phase 的业务代码。
- 未核验 license 或维护风险的第三方依赖，不得作为硬依赖引入。
- 第三方工具必须通过 Adapter 封装，不能深度耦合进核心业务逻辑。
- 默认 pytest 不得包含真实网络测试；外部 API、下载、搜索、RAG、LLM 测试必须 mock。
- 引入任何新依赖时，必须同步更新 `pyproject.toml` 和安装/运行说明。

允许自研的范围仅限 ResearchSensei 独有能力，例如 Teach-Me Engine、Formula Tutor、PhD Thinking Scaffold、Learning Card Schema、科研模式归纳和交互式导师追问；即便如此，也必须先完成复用评估并说明为什么现有项目不能直接满足需求。

## 总规则

你必须按阶段开发，不得自由发挥。

## 允许行为

- 根据当前阶段创建必要文件。
- 写最小但真实可运行的实现。
- 为当前任务补充测试。
- 发现文档矛盾时写入 `OPEN_QUESTIONS.md`。
- 使用 mock 代替外部 API。

## 禁止行为

- 不得一次性实现全系统。
- 不得创建大批空壳模块。
- 不得修改未授权阶段的文件。
- 不得删除用户已有代码。
- 不得覆盖已有结果。
- 不得编造测试通过。
- 不得跳过测试。
- 不得写死路径/API key。
- 不得把项目做成摘要器。
- 不得把 reasonable inference 标成事实。
- 不得绕过 grounding。

## 文件修改规则

每个 task 必须先声明授权修改范围。

示例：

```text
本轮只允许修改：
- src/researchsensei/schemas/**
- tests/test_schemas.py
不允许修改：
- src/researchsensei/interactive/**
- templates/**
```

## 代码质量规则

- 函数必须有清晰输入输出。
- 复杂逻辑必须拆函数。
- Pydantic schema 放 schemas 目录。
- 外部依赖通过 adapter 包装。
- LLM 调用必须经过 llm/client.py。
- 任何输出 JSON 必须可 validate。

## 提交前自查

每轮完成前回答：

```text
1. 我是否只做了当前任务？
2. 是否有无关文件改动？
3. 是否新增空壳文件？
4. 是否运行了相关测试？
5. 是否有失败测试？
6. 是否有未确认需求？
7. 是否存在 API key/隐私泄露？
```

## 不确定处理

如果不确定，不得猜。必须写：

```markdown
# OPEN_QUESTIONS

- [ ] 问题：xxx
  - 影响：xxx
  - 当前临时处理：xxx
  - 需要用户确认：xxx
```

## 新增规则 (2026-06-03)

1. **不允许把 block-level evidence 称为 claim-level grounding**。当前 evidence_index 是 block-level，不是 claim-level。升级到 passage-level 后才能称为 claim-level grounding。

2. **不允许把 rule-based baseline 称为导师级讲解**。Phase 8-10 的 rule-based builder 是 baseline，不是最终产品。LLM-enhanced 路径需要 evidence constraint 才能接入主 pipeline。

3. **不允许未经 reuse gate 引入重依赖**。每个新 Phase 开始前必须完成 reuse gate。optional adapter 也需要评估。

4. **不允许默认 pytest 真实联网或真实 LLM**。所有外部 API 和 LLM 调用必须 mock。

5. **不允许 Phase 12 在 route reset 未完成前继续开发**。Phase 12 (patterns + drill) 冻结，等待 Phase 11.5-11.9 完成。
