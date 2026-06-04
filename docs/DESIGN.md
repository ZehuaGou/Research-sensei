# ResearchSensei Design

---

## 1. 项目定位

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

### reuse before build

能复用成熟项目就先评估复用，不重复造轮子。外部项目必须通过 adapter 或独立模块接入。

### adapter-first

外部 parser / retrieval / audit 能力必须通过 adapter 接入，不能深度耦合。

### mock-first testing

默认测试不联网、不真实调用 LLM。HTTP 测试用 MockTransport，LLM 测试用 MockLLMClient。

---

## 3. 为什么不是 ARIS

ARIS 做的是自动科研：idea discovery → experiment → paper writing → rebuttal。目标是帮研究者做科研。

ResearchSensei 做的是教人读懂论文：解析 → 证据 → 理解 → 卡片 → 追问。目标是帮学生建立科研思维。

两者目标完全不同。只参考 ARIS 的：
- audit chain（5 层审计）
- reviewer independence（审计者独立于生成者）
- claim audit（零上下文验证）

不整包迁移 ARIS。

---

## 4. 为什么保留 Vue / FastAPI / Pydantic

- Vue 3 前端已有基础，重写成本高收益低
- FastAPI 适合 API、schema 校验、mock 测试
- Pydantic 适合 artifact JSON 驱动链路
- 旧 `backend/` 冻结，新功能只走 `src/researchsensei/`

---

## 5. 系统架构

```
Product Layer       → Vue / FastAPI / workspace / job / artifact / Pydantic
Parser Layer        → ParserAdapter interface, LightweightParser fallback
Evidence Layer      → PassageIndex, ClaimExtractor, ClaimEvidence, EvidenceRetriever
Paper Understanding → paper_card, formula_cards, teaching_cards, evidence-constrained LLM
Literature Search   → QueryPlanner, adapters, SelectionService, DirectionRunner
Audit / Quality     → explanation audit, formula audit, evidence audit, reviewer independence
```

---

## 6. 用户流程

用户上传论文 PDF → 系统解析为结构化文档 → 构建 passage 和 claim evidence → 生成 evidence pack → LLM 生成卡片 → 审计 → 前端根据状态展示结果。

不同状态用户看到什么：

| status | 用户看到 |
|--------|---------|
| SUCCESS | 完整论文卡片、公式卡片、教学讲解 |
| DEGRADED_STRUCTURAL | 部分卡片 + "部分讲解暂不可用" 提示 |
| BASELINE_ONLY | "当前为基线解析结果，不是最终导师级理解"，不展示卡片 |
| BLOCKED_UNDERSTANDING | 阻断原因 + 警告，不展示卡片 |
| FAILED | 系统错误 |

BASELINE_ONLY 不是最终导师级理解。DEGRADED_STRUCTURAL 不是完整导师级解释。

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

每个 artifact 有明确的生成者和消费者，JSON 可序列化/反序列化，失败时阻断而非编造。

---

## 8. 产品边界

- v1 主链路已阶段性封版
- 不是最终产品
- Real LLM smoke、Docling parser、evidence_ref 跳转、debug/admin 鉴权、Phase 12 都是后续能力
- Phase 12（patterns / drill / advisor questions）当前冻结
