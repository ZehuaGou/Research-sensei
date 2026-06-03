# ResearchSensei Design Document

---

## 1. 项目定位

ResearchSensei 是一个**论文研读导师系统**，帮助研究生和初级研究者真正读懂论文，而不是只做摘要。

### ResearchSensei 是

- 论文研读导师 — 引导用户逐步理解论文
- 公式解释器 — 拆解符号、项、作用、数字例子
- 科研思维训练系统 — 训练理解假设、创新点、代价、边界
- 导师追问准备系统 — 帮用户准备回答导师问题
- evidence-constrained paper understanding system — 所有解释必须有证据支撑

### ResearchSensei 不是

- 普通摘要器
- 自动写论文系统
- 自动做科研系统
- 单纯 RAG 问答机器人
- ARIS clone

---

## 2. 技术路线

### 保留

- Vue 3 + Vite + TypeScript 前端
- Python / FastAPI 后端
- Pydantic schema 驱动
- workspace (文件系统) + job store (SQLite)
- JSON artifact 链路
- mock-first 测试策略

### 冻结

- `backend/` — 旧代码，只作迁移参考，不接收新功能
- 新功能只走 `src/researchsensei/`

---

## 3. 架构

六层架构：

```
A. Product Layer     — Vue / FastAPI / workspace / job / artifact / Pydantic / mock tests
B. Parser Layer      — ParserAdapter interface, LightweightParser fallback, optional Docling/Nougat/Marker
C. Evidence Layer    — PassageIndex, ClaimExtractor, ClaimEvidence v2, EvidenceRetriever
D. Paper Understanding — paper_card / formula_cards / teaching_cards, evidence-constrained LLM
E. Direction Layer   — query_plan, candidate_pool, filtered_candidates, reading_plan
F. Audit Layer       — explanation audit, formula audit, evidence audit, reviewer independence
```

---

## 4. Artifact 链路

### 单篇论文链路

```
source_status.json → parsed_document.json → evidence_index.json
→ paper_skeleton.json → paper_card.json → formula_cards.json → teaching_cards.json
```

| Artifact | 作用 | 当前限制 | 后续升级 | 阻塞 Phase 12 |
|----------|------|----------|----------|---------------|
| source_status.json | 来源状态 | 无 | 无 | 否 |
| parsed_document.json | 文档 blocks | PyMuPDF fallback 质量低 | Phase 11.6 ParserAdapter | 是 |
| evidence_index.json | 证据绑定 | block-level，不是 claim-level | Phase 11.7 PassageIndex + ClaimEvidence v2 | 是 |
| paper_skeleton.json | 论文骨架 | rule-based 提取保守 | Phase 11.8 LLM-enhanced | 是 |
| paper_card.json | 论文学习卡 | rule-based baseline | Phase 11.8 evidence-constrained LLM | 是 |
| formula_cards.json | 公式讲解卡 | generic symbol dictionary | Phase 11.8 paper-context grounding | 是 |
| teaching_cards.json | 五层教学卡 | rule-based baseline | Phase 11.8 evidence-constrained LLM | 是 |

### 方向链路

```
query_plan.json → candidate_pool.json → filtered_candidates.json → reading_plan.json
```

| Artifact | 作用 | 阻塞 Phase 12 |
|----------|------|---------------|
| query_plan.json | 查询计划 | 否 |
| candidate_pool.json | 原始候选池 | 否 |
| filtered_candidates.json | 去重后候选 | 否 |
| reading_plan.json | 阅读计划 | 否 |

---

## 5. 当前真实状态

- **Phase 1-11 = baseline infrastructure complete**，不是最终论文理解质量。
- **Phase 6 evidence 是 block-level**，不是 claim-level grounding。
- **Phase 8-10 是 rule-based baseline**，不是导师级讲解。LLM-enhanced 未接入主 pipeline。
- **Phase 11 是 direction pipeline v1**，不是完整 literature review system。
- **Phase 12 继续冻结**。

---

## 6. 外部项目复用原则

### 原则

- 不为了复用而复用。
- 不整包迁移 ARIS。
- 不默认接入重依赖。
- 能复用核心能力就复用，不能复用就参考。
- 引入任何外部项目前必须先做 reuse gate。
- 默认 pytest 不允许真实联网、不允许真实 LLM。

### 当前判断

| 项目 | 决策 | 理由 |
|------|------|------|
| ARIS | REFERENCE_ONLY | 参考 audit chain / reviewer independence / claim audit，不整包接入 |
| PaperQA | OPTIONAL_ADAPTER | 参考 passage retrieval / citation-backed answer |
| OpenScholar | REFERENCE_ONLY | 参考 citation accuracy |
| ResearchPilot | REFERENCE_ONLY | 参考 structured findings |
| STORM | REFERENCE_ONLY | 参考 outline / multi-perspective questioning |
| Docling / Nougat / Marker / MinerU | OPTIONAL_ADAPTER | 可选 parser adapter |
| Unstructured | NOT_USE | 通用不够学术 |

---

## 7. 阶段路线

| 阶段 | 状态 | 内容 |
|------|------|------|
| Phase 1-11 | baseline complete | 基础设施完成，281 tests |
| Phase 11.6 | 待确认 | ParserAdapter 设计 |
| Phase 11.7 | 草案 | PassageIndex + ClaimEvidence v2 |
| Phase 11.8 | 草案 | Evidence-constrained LLM Paper Understanding |
| Phase 11.9 | 草案 | Paper Understanding Quality Benchmark |
| Phase 12 | 冻结 | Patterns + Drill |
| Phase 13+ | 路线 | Direction Map / Frontend / Advisor / Reliability / Benchmark / Deploy |

---

## 8. 不允许事项

1. 不允许直接进入 Phase 12。
2. 不允许把 rule-based baseline 称为导师级讲解。
3. 不允许把 block-level evidence 称为 claim-level grounding。
4. 不允许无 evidence 生成解释。
5. 不允许默认测试真实联网或真实 LLM。
6. 不允许未经 reuse gate 新增依赖。
