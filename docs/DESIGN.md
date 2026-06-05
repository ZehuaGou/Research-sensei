# ResearchSensei Design

---

## 1. 产品定位

ResearchSensei / 读博模拟器 是一个多能力科研学习与训练系统。

它不是普通论文摘要器，不是单篇论文卡片生成器，不是单纯方向地图工具，不是自动写论文系统，也不是 ARIS clone。

它的目标是帮助用户在科研学习过程中：

- 建立研究方向框架；
- 找到综述、代表论文和可精读论文；
- 可信精读单篇论文；
- 理解公式、符号和方法机制；
- 理解多篇论文之间的演进关系；
- 通过前端形成方向页和论文页；
- 进行论文级、方向级和上下游扩展互动；
- 接受导师式追问和研究训练；
- 沉淀长期记忆。

正式模块体系为 M1 → M2 → M3 → M4 → M5。产品能力可以跨模块，但不另设编号。

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

涉及 LLM、联网搜索、PDF 下载、PDF 解析、前后端联调的模块，验收必须跑真实链路。mock/fake/skip 不作为模块完成依据。缺 key、缺网络、API 限流、PDF 下载失败、LLM JSON 解析失败，不能汇报为真实验收通过。

---

## 3. 三个产品入口

### 入口 1：Direction Exploration Page

用户输入研究方向，例如：

- 时间序列异常检测
- 图异常检测
- 多模态大模型
- 扩散模型

系统默认行为：

1. 优先搜索高质量综述；
2. 如果找不到合格综述，再执行 staged multi-source search；
3. 生成方向框架、方法族、技术阶段、代表论文、推荐阅读顺序。

输出：survey_candidates, direction_landscape, method_families, chronology_stages, landscape_anchors, recommended_reading_order, papers that can be sent to M2。

### 入口 2：Paper Deep Reading Page

用户可以：

- 上传 PDF
- 输入论文标题
- 输入 DOI
- 输入 arXiv ID
- 输入 arXiv URL
- 输入 PDF URL
- 输入 publisher URL

系统默认行为：

1. 定位论文；
2. 下载或接收 PDF；
3. 验证是否同一篇论文；
4. 进入 M2 单篇精读。

输出：paper_card, formula_cards, teaching_cards, evidence_refs, quality_report, understanding_status。

### 入口 3：Seed Paper Expansion

用户在论文精读页点击"查找这篇论文的上下游 / 相关综述 / 后续改进"。

系统默认行为：

1. 围绕当前论文调用 M1；
2. 查找引用论文、被引论文、相关综述、同路线论文、后续改进论文；
3. 形成局部论文关系图。

输出：seed_expansion_result, upstream_papers, downstream_papers, related_surveys, follow_up_papers, paper_relation_graph。

---

## 4. M1-M5 模块职责

| 编号 | 模块 | 职责 |
|------|------|------|
| M1 | 论文搜索、综述优先、方向探索、论文获取、阅读计划、seed paper expansion | 搜索、验证、下载、筛选、排序、生成阅读计划和方向框架 |
| M2 | 单篇论文精读、综述论文精读、证据链、公式/符号/方法机制讲解 | 解析、证据链路、讲解生成、质量审计、状态门控 |
| M3 | 前端展示，包括 DirectionWorkspace、PaperWorkspace、SeedExpansionPanel | 后端 API、前端状态展示、debug 入口 |
| M4 | 互动学习，包括 paper-level、direction-level、seed-expansion interaction，以及导师式追问和长期记忆 | 选中解释、追问、训练、知识库、记忆检索 |
| M5 | 真实测试、CI、安全、密钥、成本、工程可靠性 | 测试、安全、缓存、debug/admin、CI、成本控制 |

---

## 5. M1-M5 不是单向流水线

- M1 可以独立从方向入口启动。
- M2 可以独立从上传 / 标题 / DOI / URL 启动。
- M1 可以把论文送入 M2 精读。
- M2 也可以反向触发 M1 做 seed paper expansion。
- M3 负责展示 M1 / M2 / M4 的结果。
- M4 同时支持 paper-level interaction、direction-level interaction、seed-expansion interaction。
- M5 负责真实测试、安全、成本和工程可靠性，不替代 M1-M4 的业务验收。

---

## 6. 子模块索引

### M1

| 子模块 | 职责 |
|--------|------|
| M1.1 用户问题与搜索规划 | QueryPlanner |
| M1.2 多源论文检索 | Search Adapters / Acquisition |
| M1.3 论文下载与原始材料获取 | Paper Download / Source Fetch |
| M1.4 候选论文去重与评分 | Candidate Selection / Verification / Relevance |
| M1.5 阅读计划与方向框架 | Reading Plan / Direction Landscape |

### M2

| 子模块 | 职责 |
|--------|------|
| M2.1 论文解析与结构化 | Parser / Ingestion |
| M2.2 证据链路构建 | Evidence / Grounding |
| M2.3 论文理解与讲解生成 | Paper Understanding / Teaching |
| M2.4 质量审计与可信控制 | Audit / Quality |
| M2.5 理解状态与结果门控 | UnderstandingStatus / Gates |

### M3

| 子模块 | 职责 |
|--------|------|
| M3.1 后端 API | API endpoints |
| M3.2 上传与任务页面 | Upload / Job UI |
| M3.3 学习工作区 | Learning Workspace |
| M3.4 状态提示与卡片展示 | StatusBanner / Cards |
| M3.5 调试入口与 raw artifact 限制 | Debug / Artifacts Gating |

### M4

| 子模块 | 职责 |
|--------|------|
| M4.1 选中内容解释 | Selection Explain |
| M4.2 符号与公式解释 | Symbol / Formula Explain |
| M4.3 上下文追问 | Interactive Q&A |
| M4.4 导师式追问与研究训练 | Advisor-style Questioning / Research Drill |
| M4.5 论文知识库与长期记忆 | PaperMemory / SessionContext |
| M4.6 记忆优先检索与 token 节省 | Memory-first Retrieval |

### M5

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

## 7. Artifact 链路

### 单篇论文精读（M2）

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

### 方向探索（M1 Direction Exploration）

```
query_plan.json → survey_candidates.json → direction_landscape.json → reading_plan.json
```

### 聚焦获取（M1 Focused Acquisition）

```
query_plan.json → candidate_pool.json → filtered_candidates.json → source_resolution.json → reading_plan.json
```

### Seed Paper Expansion（M1）

```
seed_paper_metadata → paper_relation_graph.json → seed_expansion_result.json
```

---

## 8. 当前未实现能力归属

| 能力 | 归属模块 | 当前状态 |
|------|---------|---------|
| Direction Exploration Mode | M1 | NOT_IMPLEMENTED |
| Seed Paper Expansion Mode | M1 | NOT_IMPLEMENTED |
| Survey Deep Reading | M2 | NOT_IMPLEMENTED |
| Docling parser adapter | M2.1 | 文档有，代码未实现 |
| Real LLM smoke | M5.3 | 文档有，代码未实现 |
| evidence_ref 原文跳转 | M2.2 | 文档有，代码未实现 |
| Debug/admin 鉴权 | M5.6 | 文档有，代码未实现 |
| /quality_report endpoint | M3.1 | 文档有，代码未实现 |
| DirectionWorkspace | M3 | NOT_IMPLEMENTED |
| SeedExpansionPanel | M3 | NOT_IMPLEMENTED |
| 互动式学习 | M4 | 文档待设计，代码未实现 |
| 长期记忆 | M4.5 | 文档待设计，代码未实现 |
| 导师式追问 | M4.4 | 文档待设计，代码未实现 |
| 成本控制 | M5.3 | 文档待设计，代码未实现 |

---

## 9. 为什么不是 ARIS

ARIS 做的是自动科研：idea discovery → experiment → paper writing → rebuttal。目标是帮研究者做科研。

ResearchSensei 做的是教人读懂论文、理解方向、训练科研思维。目标是帮学生建立科研能力。

两者目标完全不同。只参考 ARIS 的：
- audit chain（5 层审计）
- reviewer independence（审计者独立于生成者）
- claim audit（零上下文验证）

不整包迁移 ARIS。

---

## 10. 为什么保留 Vue / FastAPI / Pydantic

- Vue 3 前端已有基础，重写成本高收益低
- FastAPI 适合 API、schema 校验
- Pydantic 适合 artifact JSON 驱动链路
- 旧 `backend/` 冻结，新功能只走 `src/researchsensei/`
