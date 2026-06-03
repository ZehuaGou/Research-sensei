# 04_ACCEPTANCE_CRITERIA

本文件定义“完成”的标准。Agent 不能用“已实现基本功能”糊弄。

## 全局完成标准

每个阶段必须满足：

1. 相关文件存在。
2. 代码能导入。
3. 测试能运行。
4. 输出符合 schema。
5. 失败有结构化错误。
6. 日志不泄露 key。
7. 未完成项写入 `OPEN_QUESTIONS.md`。

## Phase 1 骨架验收

- `src/researchsensei` 可导入。
- `pytest` 可运行。
- `researchsensei healthcheck` 可执行。
- `.env.example` 存在。
- `configs/default.yaml` 存在。

## Phase 2 Schema 验收

- common/paper/cards/session schema 存在。
- 示例 JSON 可 validate。
- 缺少必填字段时测试失败。
- 枚举值封闭，不允许任意字符串。

## Phase 3 LLM 验收

- 业务模块不能直接调用第三方 API。
- mock LLM 可用于测试。
- prompt 有版本号。
- 用户问题有指令隔离。
- response cache 可命中/失效。

## Phase 4 解析验收

- markdown/txt 能生成 blocks。
- PDF 解析失败有 warning。
- 每个 block 有 `evidence_ref`。
- 只有摘要时标记 `ABSTRACT_ONLY`。
- 不得用 LLM 编造正文。

## Phase 5 骨架验收

paper_skeleton 必须包含：

- problem
- old_methods
- bottleneck
- assumption
- representation
- mechanism
- objective
- experiments
- limitations
- transfer
- pattern_candidates

每个关键 claim 必须有 evidence status。

## Phase 6 卡片验收

paper_card 必须包含：

- 30 秒看懂
- 5 分钟讲懂
- 旧方法瓶颈
- 机制解释
- 证据状态
- 局限
- 迁移点

formula_card 必须包含：

- purpose
- symbols
- terms
- numeric_example
- what_if_removed
- weight_sensitivity
- evidence_status

drill_card 必须包含：

- immediate_recall
- next_day_review
- one_week_transfer
- advisor_questions
- weakness_checks

## Phase 7 页面验收

- 页面能打开。
- 大屏三栏，小屏纵向。
- 公式能渲染。
- 每个关键段落有追问入口。
- 不得多个卡片横向挤成小字。

## Phase 8 交互验收

- 追问时构造 context_pack。
- context_pack 包含当前卡片、选中文本、证据、历史、用户问题。
- 不把整篇论文塞进 prompt。
- memory_store 更新用户薄弱点。
- Advisor Mode 有状态机。

## Phase 9 方向学习验收

- query_plan 有中英文术语、同义词、排除词。
- search_intents 是枚举。
- reading_plan 有 scoring_breakdown。
- A_READ 篇数受限。
- survey 不能当 baseline。

## Phase 10 方向地图验收

- direction_map 是问题驱动演化链。
- 包含每阶段解决的问题和引出的新问题。
- 包含代表论文和学习顺序。
- 不得只是论文列表。

## Phase 11 用户模型验收

- 能保存反馈。
- 能根据错误回答生成 error_attribution。
- 能生成下一步补救动作。

## 内容质量验收 (2026-06-03 新增)

以下标准适用于 Phase 8-11 的所有 card/plan 输出：

- 解释必须由 evidence 支撑（evidence_ref 存在且可回指）
- citation/evidence audit 必须通过（无幻觉 ref，无编造证据）
- formula explanation 需要 symbol grounding（符号从论文上下文推断，不是通用字典）
- teaching card 不能只是原文复制（human_explanation 不能是公式文本）
- LLM 输出必须可追踪 evidence（LLM-enhanced 路径的 evidence_ref 必须有效）
- 不确定内容必须降级（INSUFFICIENT_EVIDENCE / NEEDS_HUMAN_CHECK / UNKNOWN）
- 输出必须包含论文特有术语（不能全是通用模板）

详见 `docs/QUALITY_EVALUATION_SPEC.md`。

## Phase 12 可靠性验收

- 支持断点续跑。
- 失败不重跑全部流程。
- 日志记录耗时/模型/缓存/失败原因。
- 安全测试通过。

## Phase 13 评估验收

- 至少一篇真实论文端到端跑通。
- 有人工检查报告。
- 标注不确定与错误案例。

## Phase 14 部署验收

- README 能指导新环境启动。
- Windows PowerShell 有命令。
- 常见错误有说明。
