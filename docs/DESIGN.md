# ResearchSensei Design

---

## 1. 产品定位

ResearchSensei / 读博模拟器 是一个多能力科研学习与训练系统，帮助研究生和初级研究者建立研究方向框架、真正读懂论文、理解公式和方法机制、形成学习卡片、比较多篇论文关系、接受导师式追问训练，并沉淀长期记忆。

**是**：科研学习与训练系统、读博模拟器、evidence-constrained paper understanding system。

**不是**：普通摘要器、自动写论文系统、自动做科研系统、RAG 问答机器人、ARIS clone。

ResearchSensei 有 6 层能力（见下文 Product Capability Layers），不是单一篇论文卡片系统，也不是纯方向地图系统。方向框架是核心能力之一，单篇论文精读也是核心能力之一，两者并列，不可互相替代。

---

## 2. 设计原则

### evidence-constrained

LLM 容易编造。每个解释必须可追踪到论文中的具体证据（evidence_ref）。没有证据的解释不能输出。

### fail-closed

宁可不输出，也不输出低可信解释。论文理解失败时标记 BLOCKED_UNDERSTANDING，不生成垃圾卡片。

### baseline is not final

规则 baseline（rule-based builders）是诊断工具，不是最终导师级理解。不能冒充高质量解释。

### 不重复造轮子

ResearchSensei 不优先自研所有能力。每个模块在设计和实现前，都要优先调研 GitHub 开源项目、论文工具、成熟库和外部 API。能稳定复用的优先复用；不能直接复用的，也要学习其接口设计、数据结构、失败处理和测试方式。

### adapter-first

外部 parser / retrieval / audit 能力必须通过 adapter 接入，不能深度耦合。

### real-validation-first

mock/fake/skip 不作为模块验收依据。涉及 LLM、联网搜索、PDF 下载、PDF 解析、前后端联调的模块，验收时必须跑真实链路。缺 key、缺网络、API 限流、PDF 下载失败、LLM JSON 解析失败，不能汇报为真实验收通过。允许 mock/fake 用于快速回归，但不作为模块完成依据。

---

## 3. Product Capability Layers

ResearchSensei 有 6 层能力。M1-M5 是模块划分，不等于能力层划分。一个模块可以支撑多个能力层，一个能力层也可能跨多个模块。

### C1 Direction Framework

建立研究方向整体框架：梳理技术演进阶段、识别方法族、找代表论文/方向锚点/推荐阅读顺序。给定宽 query（如"时间序列异常检测"），生成 `direction_landscape.json`。

### C2 Paper Acquisition

多源搜索论文、验证论文真实性、区分 landscape anchor 和可进入 M2 的 deep-read paper、下载可精读 PDF。给定窄 query（如"时间序列异常检测 transformer 方法"），生成 `reading_plan.json` 和 `A_READ_FOR_M2`。

### C3 Single Paper Deep Reading

解析单篇论文、构建 evidence_ref、生成 paper_card / formula_card / teaching_card、解释公式/符号/方法机制。这是 evidence-constrained 的核心能力，不能被方向综述或摘要替代。

### C4 Cross-paper Understanding

比较多篇论文之间的关系、理解某篇论文解决了前一阶段什么问题、理解后续论文如何改进它、识别技术路线、局限和开放问题。

### C5 Interactive Learning / Advisor Training

选中内容解释、上下文追问、导师式追问、研究训练。必须能围绕单篇论文和研究方向两种层级进行。公式/符号解释仍是核心能力，不能被方向追问替代。

### C6 Long-term Memory

保存论文记忆、方向记忆、方法族记忆、用户学习过程。支持 memory-first retrieval。

---

## 4. 用户核心流程

```
用户输入研究方向 → M1 搜索论文 → 生成阅读计划
                                    ↓
用户上传论文 PDF  → M2 解析论文 → 证据链路 → 讲解生成 → 质量审计 → 状态门控
                                    ↓
                            M3 前端根据状态展示结果
                                    ↓
                            M4 用户追问 / 训练 / 长期记忆
                                    ↓
                            M5 全程保障可靠、安全、可测试
```

---

## 5. 一级模块体系

| 编号 | 模块 | 职责 |
|------|------|------|
| M1 | 论文搜索、获取与阅读计划 | 搜索、下载、筛选、排序、生成阅读计划 |
| M2 | 单篇论文解析、精读与可信讲解 | 解析、证据链路、讲解生成、质量审计、状态门控 |
| M3 | 接口与前端展示 | 后端 API、前端状态展示、debug 入口 |
| M4 | 互动式学习与长期记忆 | 选中解释、追问、训练、知识库、记忆检索 |
| M5 | 工程可靠性与测试保障 | 测试、安全、缓存、debug/admin、CI、成本控制 |

---

## 6. 子模块索引

### M1 论文搜索、获取与阅读计划

| 子模块 | 职责 |
|--------|------|
| M1.1 用户问题与搜索规划 | QueryPlanner |
| M1.2 多源论文检索 | Search Adapters / Acquisition |
| M1.3 论文下载与原始材料获取 | Paper Download / Source Fetch |
| M1.4 候选论文去重与评分 | Candidate Selection |
| M1.5 阅读计划生成 | Reading Plan / DirectionRunner |

### M2 单篇论文解析、精读与可信讲解

| 子模块 | 职责 |
|--------|------|
| M2.1 论文解析与结构化 | Parser / Ingestion |
| M2.2 证据链路构建 | Evidence / Grounding |
| M2.3 论文理解与讲解生成 | Paper Understanding / Teaching |
| M2.4 质量审计与可信控制 | Audit / Quality |
| M2.5 理解状态与结果门控 | UnderstandingStatus / Gates |

### M3 接口与前端展示

| 子模块 | 职责 |
|--------|------|
| M3.1 后端 API | API endpoints |
| M3.2 上传与任务页面 | Upload / Job UI |
| M3.3 论文学习工作区 | Learning Workspace |
| M3.4 状态提示与卡片展示 | StatusBanner / Cards |
| M3.5 调试入口与 raw artifact 限制 | Debug / Artifacts Gating |

### M4 互动式学习与长期记忆

| 子模块 | 职责 |
|--------|------|
| M4.1 选中内容解释 | Selection Explain |
| M4.2 符号与公式解释 | Symbol / Formula Explain |
| M4.3 上下文追问 | Interactive Q&A |
| M4.4 导师式追问与研究训练 | Advisor-style Questioning / Research Drill |
| M4.5 论文知识库与长期记忆 | PaperMemory / SessionContext |
| M4.6 记忆优先检索与 token 节省 | Memory-first Retrieval |

### M5 工程可靠性与测试保障

| 子模块 | 职责 |
|--------|------|
| M5.1 后端测试 | pytest |
| M5.2 前端测试 | Vitest |
| M5.3 真实 LLM smoke 与成本控制 | LLM Smoke / Cost |
| M5.4 缓存与复用 | Cache |
| M5.5 安全与密钥扫描 | Secret Scan |
| M5.6 Debug/admin 权限 | Debug/Admin |
| M5.7 CI 与发布检查 | CI / Release Check |

---

## 7. 模块流转

```
M1 找论文 → M2 读懂论文 → M3 展示结果 → M4 互动学习与长期记忆 → M5 保障系统可靠
```

---

## 8. Artifact 链路

### 单篇论文（v2）

```
source_status.json
→ parsed_document.json
→ passage_index.json
→ claim_evidence.json
→ evidence_index.json (v1 兼容)
→ paper_skeleton.json
→ paper_card.json / formula_cards.json / teaching_cards.json
→ understanding_status.json
→ quality_report.json
```

不同状态 artifact 数量：

| 状态 | artifact 数量 |
|------|--------------|
| BASELINE_ONLY | 11 |
| SUCCESS | 11 |
| DEGRADED_STRUCTURAL | 10 |
| BLOCKED_UNDERSTANDING | 8 |
| FAILED | 不保证完整 |

### 研究方向（Focused Acquisition）

```
query_plan.json → candidate_pool.json → filtered_candidates.json → source_resolution.json → reading_plan.json
```

`reading_plan.json` 中的 `A_READ_FOR_M2` 服务单篇精读入口（C3）。

### 方向框架（Direction Framework）

```
query_plan.json → candidate_pool.json → filtered_candidates.json → direction_landscape.json
```

`direction_landscape.json` 包含 chronology_stage / method_family / landscape_anchor / representative_papers / recommended_reading_order / gaps_or_open_questions。服务方向理解（C1），不替代 `reading_plan.json`。

---

## 9. 当前未实现能力归属

| 能力 | 归属模块 | 当前状态 |
|------|---------|---------|
| Docling parser adapter | M2.1 | 文档有，代码未实现 |
| Real LLM smoke | M5.3 | 文档有，代码未实现 |
| evidence_ref 原文跳转 | M2.2 | 文档有，代码未实现 |
| formula-heavy / raw-copy / generic audit | M2.4 | 文档有，代码未实现 |
| Debug/admin 鉴权 | M5.6 | 文档有，代码未实现 |
| /quality_report endpoint | M3.1 | 文档有，代码未实现 |
| Frontend 页面级测试 | M5.2 | 部分完成 |
| 互动式学习 | M4 | 文档待设计，代码未实现 |
| 长期记忆 | M4.5 | 文档待设计，代码未实现 |
| 导师式追问 | M4.4 | 文档待设计，代码未实现 |
| 成本控制 | M5.3 | 文档待设计，代码未实现 |

---

## 10. 为什么不是 ARIS

ARIS 做的是自动科研：idea discovery → experiment → paper writing → rebuttal。目标是帮研究者做科研。

ResearchSensei 做的是教人读懂论文：解析 → 证据 → 理解 → 卡片 → 追问。目标是帮学生建立科研思维。

两者目标完全不同。只参考 ARIS 的：
- audit chain（5 层审计）
- reviewer independence（审计者独立于生成者）
- claim audit（零上下文验证）

不整包迁移 ARIS。

---

## 11. 为什么保留 Vue / FastAPI / Pydantic

- Vue 3 前端已有基础，重写成本高收益低
- FastAPI 适合 API、schema 校验、mock 测试
- Pydantic 适合 artifact JSON 驱动链路
- 旧 `backend/` 冻结，新功能只走 `src/researchsensei/`
