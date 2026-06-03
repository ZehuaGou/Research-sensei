# ResearchSensei Design

---

## 1. 项目定位

ResearchSensei 是论文研读导师系统，帮助研究生和初级研究者真正读懂论文。

**是**：论文研读导师、公式解释器、科研思维训练系统、导师追问准备系统、evidence-constrained paper understanding system。

**不是**：普通摘要器、自动写论文系统、自动做科研系统、RAG 问答机器人、ARIS clone。

---

## 2. 用户和核心价值

**用户**：研究生、初级研究者、需要深入理解论文的科研人员。

**用户问题**：读论文时看不懂公式、不理解方法创新点、无法回答导师追问、不知道论文的核心假设和局限。

**系统解决**：
- 把论文拆解成可学习的结构（骨架、卡片、公式讲解）
- 每个解释绑定证据，不编造
- 五层讲解法：人话 → 类比 → 最小公式 → 数字例子 → 论文作用
- 帮用户准备导师追问

**"讲得好"意味着**：解释有证据支撑、忠实原文、不是模板化输出、公式讲解有符号依据、不确定时诚实降级。

---

## 3. 总体技术路线

- Vue 3 前端保留，不重写
- Python / FastAPI / Pydantic 后端
- `backend/` 冻结，只作迁移参考
- 新功能只走 `src/researchsensei/`
- JSON artifact 驱动链路
- mock-first 测试策略

---

## 4. 系统架构

### Product Layer

负责：用户界面、API、持久化、artifact 存储。

- Vue frontend
- FastAPI backend
- Pydantic schemas
- workspace (文件系统) + job store (SQLite)
- artifact JSON

不负责：论文解析、证据绑定、卡片生成。

### Parser Layer

负责：将 PDF/Markdown/文本解析为结构化 blocks。

- ParserAdapter interface
- LightweightParser fallback（现有 PyMuPDF/Markdown parser）
- optional 外部 parser adapter（Docling/Nougat/Marker/MinerU）

不负责：证据绑定、卡片生成、LLM 调用。

交互：接收源文件 → 输出 `DocumentIngestion` → 传给 Evidence Layer。

### Evidence Layer

负责：将文档 blocks 关联到 passage-level 证据，提取 claim。

- PassageIndex
- ClaimExtractor
- ClaimEvidence
- EvidenceRetriever

不负责：生成解释、生成卡片。

交互：接收 `DocumentIngestion` → 输出 `evidence_index.json` → 传给 Paper Understanding Layer。

### Paper Understanding Layer

负责：基于证据生成学习卡片。

- paper_card（论文学习卡）
- formula_cards（公式讲解卡）
- teaching_cards（五层教学卡）
- evidence-constrained LLM explainer

不负责：搜索论文、解析文档。

交互：接收 skeleton + evidence → 输出 card JSON → 传给 Audit Layer 和用户。

### Literature Search Layer

负责：搜索、筛选、排序论文。

- QueryPlanner
- ArxivAdapter / OpenAlexAdapter
- SelectionService（去重、评分）
- DirectionRunner（编排）

不负责：单篇论文理解。

交互：接收用户方向 → 输出 `reading_plan.json` → A_READ 论文进入 Paper Understanding。

### Audit Layer

负责：检查解释质量，独立于生成者。

- explanation audit
- formula audit
- evidence audit
- advisor / kill-argument audit
- reviewer independence（参考 ARIS）

不负责：生成解释。

交互：接收 card JSON + evidence → 输出 audit report。

---

## 5. Artifact 链路

### 单篇论文

```
source_status.json → parsed_document.json → evidence_index.json
→ paper_skeleton.json → paper_card.json → formula_cards.json → teaching_cards.json
```

每个 artifact 有明确的生成者和消费者，JSON 可序列化/反序列化，失败时降级而非编造。

### 研究方向

```
query_plan.json → candidate_pool.json → filtered_candidates.json → reading_plan.json
```

A_READ 论文进入单篇论文链路做精读。

---

## 6. 外部项目复用原则

- 不为了复用而复用
- 能复用成熟项目就评估复用，不重复造轮子
- 外部项目必须先做 reuse gate
- 默认测试不能真实联网，不能真实调用 LLM
- ARIS 只参考 audit / reviewer independence / claim audit 思想，不整包迁移
- PaperQA / OpenScholar 参考 evidence / citation 思路
- Docling / Nougat / Marker / MinerU 可作为 parser adapter 候选
- 不默认引入重依赖
