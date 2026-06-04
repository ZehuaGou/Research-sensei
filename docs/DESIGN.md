# ResearchSensei Design

---

## 1. 产品定位

ResearchSensei 是论文研读导师系统，帮助研究生和初级研究者真正读懂论文。

**是**：论文研读导师、公式解释器、科研思维训练系统、导师追问准备系统、evidence-constrained paper understanding system。

**不是**：普通摘要器、自动写论文系统、自动做科研系统、RAG 问答机器人、ARIS clone。

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

### mock-first testing

默认测试不联网、不真实调用 LLM。HTTP 测试用 MockTransport，LLM 测试用 MockLLMClient。

---

## 3. 用户核心流程

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

## 4. 一级模块体系

| 编号 | 模块 | 职责 |
|------|------|------|
| M1 | 论文搜索、获取与阅读计划 | 搜索、下载、筛选、排序、生成阅读计划 |
| M2 | 单篇论文解析、精读与可信讲解 | 解析、证据链路、讲解生成、质量审计、状态门控 |
| M3 | 接口与前端展示 | 后端 API、前端状态展示、debug 入口 |
| M4 | 互动式学习与长期记忆 | 选中解释、追问、训练、知识库、记忆检索 |
| M5 | 工程可靠性与测试保障 | 测试、安全、缓存、debug/admin、CI、成本控制 |

---

## 5. 子模块索引

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

## 6. 模块流转

```
M1 找论文 → M2 读懂论文 → M3 展示结果 → M4 互动学习与长期记忆 → M5 保障系统可靠
```

---

## 7. Artifact 链路

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

### 研究方向

```
query_plan.json → candidate_pool.json → filtered_candidates.json → reading_plan.json
```

---

## 8. 当前未实现能力归属

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

## 9. 为什么不是 ARIS

ARIS 做的是自动科研：idea discovery → experiment → paper writing → rebuttal。目标是帮研究者做科研。

ResearchSensei 做的是教人读懂论文：解析 → 证据 → 理解 → 卡片 → 追问。目标是帮学生建立科研思维。

两者目标完全不同。只参考 ARIS 的：
- audit chain（5 层审计）
- reviewer independence（审计者独立于生成者）
- claim audit（零上下文验证）

不整包迁移 ARIS。

---

## 10. 为什么保留 Vue / FastAPI / Pydantic

- Vue 3 前端已有基础，重写成本高收益低
- FastAPI 适合 API、schema 校验、mock 测试
- Pydantic 适合 artifact JSON 驱动链路
- 旧 `backend/` 冻结，新功能只走 `src/researchsensei/`
