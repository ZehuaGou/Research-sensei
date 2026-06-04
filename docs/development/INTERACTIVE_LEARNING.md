# 互动式学习与长期记忆模块（M4）

---

## 1. 模块目标

在 M2 单篇论文理解完成后，提供互动式学习能力：让用户通过选中内容、追问、训练、长期记忆，真正掌握论文，而非只看一遍卡片。

---

## 2. 非目标

- 不重复 M2 的论文解析和卡片生成
- 不替代 M1 的论文搜索
- 不实现自动写论文

---

## 3. 产品流程位置

```
M1 找论文 → M2 读懂论文 → M3 展示结果 → M4 互动学习与长期记忆 → M5 保障系统可靠
```

M4 在 M3 之后：用户已经看到论文卡片，开始互动学习。

---

## 4. 用户场景

### 选中一段文字解释

用户在论文原文中选中一段文字，系统解释这段文字在论文中的含义和作用。

### 选中一个公式解释

用户选中一个公式，系统解释公式的每一项、符号含义、直觉、数值例子。

### 选中一个符号解释

用户选中公式中的一个符号，系统解释这个符号的含义、来源、在论文中的作用。

### 联系当前段落

用户追问"这段话和前面的方法有什么关系"，系统结合当前段落和论文上下文回答。

### 联系整篇论文

用户追问"这个公式在整篇论文中起什么作用"，系统结合全文理解回答。

### 联系已读过的论文

用户追问"这篇论文和之前读的 XX 论文有什么区别"，系统结合长期记忆回答。

### 追问

用户对卡片内容追问，系统根据论文证据回答。

### 训练题

系统生成训练题（单题追问、连续追问），用户回答后系统评分和追问。

### 导师式追问与研究训练

系统模拟博士生导师 / 论文导师的追问方式，训练用户真正理解论文。追问重点包括：

- 论文核心假设
- 方法为什么有效
- 公式机制
- 实验设计是否合理
- 消融实验是否支撑结论
- 和已有工作的区别
- 创新点是否站得住
- 方法失败场景
- 可扩展方向
- 研究价值
- 用户是否能用自己的话讲清论文

交互形式：

- 单题追问
- 连续追问
- 组会模拟
- 开题 / 答辩式追问
- 根据用户回答继续追问

需要结合：

- 当前选中内容
- 当前论文全文理解
- 证据链
- 已读论文知识库
- 用户历史回答

---

## 5. 子模块

| 子模块 | 职责 | 当前状态 |
|--------|------|---------|
| M4.1 选中内容解释 | 用户选中文字/公式/符号，系统解释 | 文档待设计，代码未实现 |
| M4.2 符号与公式解释 | 公式每一项、符号含义、直觉、数值例子 | 文档待设计，代码未实现 |
| M4.3 上下文追问 | 联系当前段落 / 整篇论文 / 已读论文 | 文档待设计，代码未实现 |
| M4.4 导师式追问与研究训练 | 模拟导师追问，训练用户真正理解论文 | 文档待设计，代码未实现 |
| M4.5 论文知识库与长期记忆 | PaperMemory / PassageMemory / FormulaMemory / SessionContext | 文档待设计，代码未实现 |
| M4.6 记忆优先检索与 token 节省 | 记忆优先检索，减少重复 LLM 调用 | 文档待设计，代码未实现 |

---

## 6. 输入输出

| 子模块 | 输入 | 输出 |
|--------|------|------|
| M4.1 | 选中内容 + 论文上下文 | 解释文本 |
| M4.2 | 公式 / 符号 + 论文上下文 | 符号解释 / 公式讲解 |
| M4.3 | 用户追问 + 论文上下文 + 已读论文 | 回答文本 |
| M4.4 | 用户回答 + 论文理解 + 已读论文 | 追问文本 + 评分 |
| M4.5 | 论文理解 + 用户交互 | 记忆条目 |
| M4.6 | 用户问题 + 记忆库 | 优先检索结果 |

---

## 7. 候选 Schema

```python
class PaperMemory(SenseiModel):
    paper_id: str
    core_claims: list[str] = Field(default_factory=list)
    key_formulas: list[str] = Field(default_factory=list)
    user_understanding_level: str = "unknown"
    last_interaction: str = ""

class PassageMemory(SenseiModel):
    passage_id: str
    paper_id: str
    key_concepts: list[str] = Field(default_factory=list)
    user_explanation: str = ""
    understanding_score: float = 0.0

class FormulaMemory(SenseiModel):
    formula_id: str
    paper_id: str
    symbol_explanations: dict[str, str] = Field(default_factory=dict)
    user_explanation: str = ""

class SymbolMemory(SenseiModel):
    symbol: str
    paper_id: str
    meaning: str = ""
    user_explanation: str = ""

class SessionContext(SenseiModel):
    session_id: str
    paper_id: str
    current_focus: str = ""
    question_history: list[dict] = Field(default_factory=list)
    token_budget_used: int = 0

class UserQuestionMemory(SenseiModel):
    question_id: str
    paper_id: str
    question: str = ""
    answer: str = ""
    follow_ups: list[str] = Field(default_factory=list)
```

---

## 8. 记忆优先检索策略

- 用户追问时，先查 PaperMemory / PassageMemory / FormulaMemory
- 如果记忆中有相关解释，直接使用，不调用 LLM
- 如果记忆中没有，再调用 LLM
- LLM 回答后，写入记忆

---

## 9. token 节省策略

- 重复问题不重复调用 LLM
- 记忆中的解释可以作为 LLM prompt 的 context
- SessionContext 记录 token_budget_used，避免超限

---

## 10. 可复用开源项目 / 外部服务调研表

| 项目 | 用途 | GitHub / 官网 | 接入方式 | 是否默认依赖 | 风险 | 当前结论 |
|------|------|---------------|----------|--------------|------|----------|
| LangChain Memory | 长期记忆框架 | github.com/langchain-ai/langchain | 参考设计 | 否 | 过重 | 参考 memory 模块设计 |
| MemGPT / Letta | 会话记忆管理 | github.com/cpacker/MemGPT | 参考设计 | 否 | 过重 | 参考 session memory 设计 |
| STORM | 多视角追问 | github.com/stanford-oval/storm | 参考设计 | 否 | — | 参考 multi-perspective questioning |

---

## 11. API 候选

- `POST /api/v1/jobs/{job_id}/explain` — 选中内容解释
- `POST /api/v1/jobs/{job_id}/ask` — 上下文追问
- `POST /api/v1/jobs/{job_id}/drill` — 训练题
- `GET /api/v1/jobs/{job_id}/memory` — 获取记忆

---

## 12. 前端交互候选

- 选中文字 → 弹出解释面板
- 公式 hover → 显示符号解释
- 追问输入框 → 发送问题
- 训练题卡片 → 用户回答 + 系统评分

---

## 13. 测试要求

- 选中内容解释必须绑定 evidence_ref
- 追问回答必须基于论文证据
- 记忆检索必须优先于 LLM 调用
- token budget 必须受控
- 默认测试不真实调用 LLM

---

## 14. 当前状态

- 文档设计中
- 代码未实现
- 当前不进入代码开发
- 后续需要先完成开发文档

---

## 15. 未决问题

- PaperMemory 和 PassageMemory 的粒度
- 记忆优先检索的具体策略
- token 节省的量化指标
- 导师式追问的评分标准
- 训练题的生成策略
- 和 M2 understanding_status 的关系
