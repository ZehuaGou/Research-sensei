# ResearchSensei Technology Route Review

审计日期: 2026-06-03
状态: Pre-Phase12 route reset
结论: 当前技术路线基本正确，但论文理解核心需要升级

---

## 1. 当前技术路线是否错了？

**不完全错，但需要升级。**

### 正确的部分

| 决策 | 评估 |
|------|------|
| Python/FastAPI/Pydantic 作为产品底座 | 正确。成熟、可测试、Windows 兼容 |
| Vue 前端保留 | 正确。不需要重写 |
| 旧 backend/ 冻结 | 正确。迁移路线有效 |
| artifact JSON 驱动链路 | 正确。每个步骤可审计、可测试 |
| mock-first 测试策略 | 正确。默认测试不联网不调 LLM |
| evidence-constrained 设计 | 正确。每个 claim 绑定 evidence_ref |

### 需要升级的部分

| 当前状态 | 问题 | 升级方向 |
|----------|------|----------|
| Phase 4 ingestion 用 PyMuPDF 做 fallback | PDF 解析质量低，公式/表格/布局丢失 | 引入 ParserAdapter，可选 Docling/Nougat |
| Phase 6 grounding 用 block-level evidence | 只能定位到段落，不能定位到具体 claim | 升级为 passage-level + claim extraction |
| Phase 8-10 card builder 是 rule-based baseline | 输出质量不够"导师级" | 引入 evidence-constrained LLM explainer |
| Phase 11 direction pipeline 只做搜索+评分 | 没有 cross-paper synthesis | 后续可引入 STORM-style outline guidance |

### 不需要改的部分

| 项目 | 理由 |
|------|------|
| 不需要引入 ARIS-style skills 作为核心架构 | ResearchSensei 是产品，不是研究工具链 |
| 不需要引入 PaperQA 作为默认依赖 | PaperQA 是 QA 系统，不是教学系统 |
| 不需要改成 ARIS-style 项目 | ARIS 做的是"自动做科研"，ResearchSensei 做的是"教你读懂论文" |

---

## 2. ResearchSensei 的新定位

### ResearchSensei 不是

- 普通论文摘要器（不只提取摘要）
- 自动写论文系统（不做 paper writing）
- 自动做科研系统（不做 idea discovery / experiment）
- 单纯 RAG 问答机器人（不只回答问题，要教用户理解）

### ResearchSensei 是

- **论文研读导师**：帮助用户真正读懂一篇论文
- **公式解释器**：把公式拆成符号、项、作用、数字例子
- **科研思维训练系统**：训练用户理解假设、创新点、代价、适用边界
- **导师追问准备系统**：帮用户准备回答导师的追问
- **evidence-constrained paper understanding system**：所有解释必须有证据支撑

### 核心差异化

ResearchSensei 的核心价值不在于"找到论文"或"总结论文"，而在于：

1. **evidence-constrained explanation**：每个解释必须绑定 evidence_ref
2. **formula teaching**：符号→项→作用→数字例子→去除影响
3. **five-layer teaching**：人话版→类比版→最小公式版→数字例子→论文作用版
4. **uncertainty handling**：不确定时降级，不编造
5. **advisor preparation**：帮用户准备导师追问

---

## 3. 新推荐架构

### A. Product Layer（保留，不改）

- Vue frontend
- FastAPI API
- workspace / job store
- artifact JSON
- Pydantic schemas
- mock-first tests

### B. Parser Layer（升级）

- **ParserAdapter interface**：统一的文档解析接口
- **LightweightParser as fallback only**：当前 PyMuPDF/Markdown 解析器作为兜底
- **optional adapters**：Docling / Nougat / Marker / MinerU（不默认安装，用户可选）

### C. Evidence Layer（升级）

- **PassageIndex**：passage-level 索引，不只是 block-level
- **ClaimExtractor**：从文本中提取可验证的 claim
- **ClaimEvidence v2**：支持 semantic support，不只是 block location
- **EvidenceRetriever**：根据 claim 检索相关 evidence passage

### D. Paper Understanding Layer（升级）

- paper skeleton v2：更准确的问题/方法/实验提取
- paper card v2：evidence-constrained LLM explainer
- formula card v2：symbol grounding from paper context
- teaching card v2：five-layer with evidence binding
- uncertainty / degraded mode：不确定时降级

### E. Direction / Literature Layer（保留，后续扩展）

- query planner（已有）
- acquisition adapters（已有）
- literature retrieval（已有）
- reading plan（已有）
- cross-paper synthesis（后续，可参考 STORM）

### F. Audit Layer（新增，参考 ARIS）

- explanation audit：检查解释是否忠实原文
- formula audit：检查公式解释是否准确
- citation/evidence audit：检查 evidence_ref 是否有效
- advisor / kill-argument audit：检查追问质量
- reviewer independence：参考 ARIS，解释和审计分离

---

## 4. 外部项目复用矩阵

| 项目 | 核心能力 | 对应 ResearchSensei 模块 | 迁移方式 | 当前是否引入 | 风险 | 结论 |
|------|----------|--------------------------|----------|-------------|------|------|
| ARIS | 77 skills, cross-model review, audit chain, reviewer independence | Audit Layer, reviewer independence concept | REFERENCE_ONLY | 否 | ARIS 是研究工具链，不是产品；整包接入会污染架构 | 参考其 audit chain 和 reviewer independence 设计，不整包接入 |
| PaperQA | scientific QA, passage retrieval, citation-backed answer | Evidence Layer, EvidenceRetriever | OPTIONAL_ADAPTER | 否 | PaperQA 是 QA 系统，不是教学系统；依赖过重 | 参考其 passage retrieval 和 citation-backed answer 设计，可选 adapter |
| OpenScholar | passage-level retrieval, citation accuracy, ScholarQABench | Evidence Layer evaluation | REFERENCE_ONLY | 否 | 主要贡献是 benchmark，不是工具 | 参考其 citation accuracy 评估方法 |
| ResearchPilot | research question → retrieval → structured findings | Direction Layer | REFERENCE_ONLY | 否 | 与 Phase 11 方向类似，但更偏 agent | 参考其 structured findings 设计 |
| STORM | outline-guided synthesis, multi-perspective questions | Direction Layer, cross-paper synthesis | REFERENCE_ONLY | 否 | STORM 做的是"写综述"，不是"教读论文" | 参考其 outline-guided 设计，不直接引入 |
| Docling | PDF parsing, layout/table/formula/markdown conversion | Parser Layer | OPTIONAL_ADAPTER | 否 | 依赖较重（需要安装），但质量高 | 作为 optional ParserAdapter，不默认安装 |
| Nougat | PDF → Markdown, formula conversion | Parser Layer | OPTIONAL_ADAPTER | 否 | 需要 GPU，依赖重 | 作为 optional ParserAdapter，不默认安装 |
| Marker | PDF → Markdown, fast | Parser Layer | OPTIONAL_ADAPTER | 否 | 较轻量 | 作为 optional ParserAdapter |
| MinerU | PDF parsing, layout analysis | Parser Layer | OPTIONAL_ADAPTER | 否 | 依赖重 | 作为 optional ParserAdapter |
| Unstructured | document parsing, multiple formats | Parser Layer | NOT_USE | 否 | 通用文档解析，不够学术专用 | 不引入 |

### 迁移方式说明

- **DIRECT_DEPENDENCY**：直接安装为项目依赖（本次无）
- **DIRECT_ADAPTER**：封装为 adapter，默认可用（arXiv, OpenAlex 已有）
- **OPTIONAL_ADAPTER**：封装为 adapter，用户可选安装
- **REFERENCE_ONLY**：参考设计，不直接引入代码
- **NOT_USE**：明确不使用

---

## 5. 当前 Artifact 保留/升级判断

### 单篇论文链路

| Artifact | 判断 | 当前问题 | 未来职责 | 阻塞 Phase 12 |
|----------|------|----------|----------|---------------|
| source_status.json | 保留 | 无 | 来源状态 | 否 |
| parsed_document.json | v2 升级 | PyMuPDF fallback 质量低 | ParserAdapter 统一接口 | 是 (Phase 11.6) |
| evidence_index.json | v2 升级 | block-level evidence | passage-level + claim extraction | 是 (Phase 11.7) |
| paper_skeleton.json | v2 升级 | rule-based 提取保守 | LLM-enhanced extraction | 是 (Phase 11.8) |
| paper_card.json | v2 升级 | rule-based baseline | evidence-constrained LLM explainer | 是 (Phase 11.8) |
| formula_cards.json | v2 升级 | generic symbol dictionary | paper-context symbol grounding | 是 (Phase 11.8) |
| teaching_cards.json | v2 升级 | rule-based baseline | evidence-constrained five-layer | 是 (Phase 11.8) |

### 方向链路

| Artifact | 判断 | 当前问题 | 未来职责 | 阻塞 Phase 12 |
|----------|------|----------|----------|---------------|
| query_plan.json | 保留 | 中文 fallback 降级 | 查询规划 | 否 |
| candidate_pool.json | 保留 | 无 | 候选池 | 否 |
| filtered_candidates.json | 保留 | 无 | 去重后候选 | 否 |
| reading_plan.json | 保留 | selection_reason 偏模板 | 阅读计划 | 否 |

**结论**：artifact 名称和链路保留，但 v2 升级是 Phase 12 代码开发的前置条件。Phase 12 remains frozen until Phase 11.6-11.9 complete.

---

## 6. 与 ARIS 的关系

### ARIS 做什么

ARIS 是一个**研究工具链**（research harness），包含 77 个 composable skills，覆盖：
- Workflow 1: idea discovery（找 idea）
- Workflow 1.5: experiment bridge（跑实验）
- Workflow 2: auto review loop（自动审稿）
- Workflow 3: paper writing（写论文）
- Workflow 4: rebuttal（回复审稿）
- 5-layer audit chain（实验审计→结果→声明→引用→反驳）

### ARIS 不做什么

ARIS 不做"教用户读懂论文"。它的目标是**自动化科研流程**，不是**教学**。

### ResearchSensei 从 ARIS 学什么

| ARIS 能力 | 对 ResearchSensei 的价值 | 如何吸收 |
|-----------|--------------------------|----------|
| reviewer independence（审计者独立） | 高。解释者和审计者应该分离 | 参考设计，在 Audit Layer 中实现 |
| assurance contract（6-state verdict） | 中。PASS/WARN/FAIL 状态机可用于质量门禁 | 参考设计，用于 explanation audit |
| zero-context audit（零上下文审计） | 高。防止 confirmation bias | 参考 paper-claim-audit 的设计理念 |
| artifact contracts（artifact 契约） | 中。ResearchSensei 已有类似设计 | 已有，无需引入 |
| cross-model review | 低。ResearchSensei 当前用 mock LLM | 后续可参考，不紧急 |

### ResearchSensei 不从 ARIS 学什么

| ARIS 能力 | 不引入的理由 |
|-----------|-------------|
| 77 skills 架构 | ResearchSensei 是产品，不需要 composable skills |
| idea discovery workflow | ResearchSensei 不做"找 idea" |
| experiment bridge | ResearchSensei 不做"跑实验" |
| paper writing workflow | ResearchSensei 不做"写论文" |
| rebuttal workflow | ResearchSensei 不做"回复审稿" |

---

## 7. 实施路线建议

### Phase 11.5: Technology Route Review（当前）

- 完成技术路线重审
- 更新设计文档
- 不写业务代码

### Phase 11.6: ParserAdapter Design

- 定义 ParserAdapter interface
- 保留 LightweightParser 作为 default
- 设计 optional adapter 插槽（Docling/Nougat/Marker）
- 不新增依赖，只设计接口

### Phase 11.7: PassageIndex + ClaimEvidence v2

- 升级 evidence_index 为 passage-level
- 实现 claim extraction（规则版）
- 升级 ClaimEvidence 支持 semantic support
- 不新增依赖

### Phase 11.8: Evidence-constrained LLM Paper Understanding

- 升级 paper_card/formula_card/teaching_card 的 LLM-enhanced 路径
- 接入 SinglePaperIngestionRunner 主 pipeline
- 所有 LLM 输出必须绑定 evidence_ref
- 使用 MockLLMClient 测试

### Phase 11.9: Paper Understanding Quality Benchmark

- 实现 explanation audit
- 实现 formula audit
- 建立 quality benchmark fixtures
- 覆盖 hard-fail 条件

### Phase 12: Patterns + Drill

- PatternCard schema + builder
- DrillCard schema + builder
- 集成到主 pipeline
- 质量测试

---

## 8. 关键决策记录

| # | 决策 | 理由 |
|---|------|------|
| D1 | 保留 Python/FastAPI/Pydantic 架构 | 成熟、可测试、Windows 兼容 |
| D2 | 不引入 ARIS-style skills 架构 | ResearchSensei 是产品，不是工具链 |
| D3 | 不引入 PaperQA 作为默认依赖 | PaperQA 是 QA 系统，不是教学系统 |
| D4 | ParserAdapter 为 optional | 不强制用户安装重依赖 |
| D5 | Evidence Layer 升级为 passage-level | block-level 不够精确 |
| D6 | 参考 ARIS reviewer independence | 解释和审计应该分离 |
| D7 | Phase 8-10 rule-based 保留为 fallback | LLM-enhanced 需要 evidence constraint |
| D8 | Phase 12 冻结，等待 route reset 完成 | 避免在错误方向上继续投入 |
