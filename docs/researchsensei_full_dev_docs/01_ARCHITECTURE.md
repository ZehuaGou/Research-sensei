# 01_ARCHITECTURE

## 1. 总目标

ResearchSensei 不做普通摘要。核心是：

```text
论文/方向输入
  -> 可靠解析与证据定位
  -> 论文骨架理解
  -> 教学化讲解
  -> 公式/概念/模式/训练卡片
  -> 页面阅读
  -> 交互追问
  -> 用户薄弱点记忆与复习
```

## 2. 两条主流程

### 2.1 单篇论文精读流程：优先实现

```text
输入 PDF/Markdown/LaTeX/文本
  -> source_resolver
  -> ingestion
  -> grounding
  -> understanding
  -> teaching/formula/patterns/drill
  -> render
  -> interactive/context
```

这是最先要跑通的闭环。方向搜索、多论文脉络必须排在后面。

### 2.2 方向学习流程：后续实现

```text
输入研究方向
  -> query
  -> acquisition
  -> selection
  -> source_resolver(A_READ papers)
  -> 单篇论文精读流程
  -> direction map
  -> reading plan
```

方向学习依赖单篇精读闭环，不得先做方向学习。

## 3. 总模块

```text
src/researchsensei/
  query/             # 方向理解和 query 扩展
  acquisition/       # 搜索和资料收集
  selection/         # 论文筛选和排序
  source_resolver/   # LaTeX/PDF/HTML 获取与来源状态
  ingestion/         # 论文解析、语言检测、blocks 生成
  grounding/         # 证据定位、claim-evidence 绑定
  understanding/     # paper_skeleton 生成
  teaching/          # 讲懂引擎
  formula/           # 公式教学卡
  direction/         # 方向脉络
  patterns/          # 科研模式卡
  drill/             # 复述、复习、导师追问
  interactive/       # 追问层、Advisor 状态机
  context/           # 上下文、记忆、缓存
  llm/               # LLM 客户端、prompt、token budget
  render/            # HTML/Markdown/JSON 输出
```

### 架构层次 (2026-06-03 更新)

```text
A. Product Layer       — Vue frontend, FastAPI API, workspace/job store, artifact JSON, Pydantic schemas, mock-first tests
B. Parser Layer        — ParserAdapter interface, LightweightParser as fallback, optional Docling/Nougat/Marker
C. Evidence Layer      — PassageIndex, ClaimExtractor, ClaimEvidence v2, EvidenceRetriever
D. Paper Understanding — paper_skeleton/card/formula/teaching v2, evidence-constrained LLM explainer, uncertainty handling
E. Direction/Literature— query planner, acquisition adapters, reading plan, cross-paper synthesis (later)
F. Audit Layer         — explanation audit, formula audit, citation/evidence audit, reviewer independence
```

详见 `docs/RESEARCHSENSEI_TECH_ROUTE_REVIEW.md`。
  integrations/      # 外部工具 adapter
  templates/         # Jinja2/HTMX 模板
```

## 4. 数据流与文件输出

每篇论文生成一个工作目录：

```text
outputs/{paper_id}/
  metadata.json
  source_status.json
  paper_sections.json
  blocks.json
  evidence_index.json
  paper_skeleton.json
  cards/
    paper_card.json
    formula_cards.json
    concept_cards.json
    pattern_cards.json
    drill_cards.json
  html/
    paper_card.html
    formula_cards.html
    drill_cards.html
  session/
    memory_store.json
    chat_history.json
```

方向学习输出：

```text
outputs/directions/{direction_id}/
  query_plan.json
  candidate_pool.json
  reading_plan.json
  direction_map.json
  direction_map.html
```

## 5. 证据状态原则

所有重要结论必须带 evidence status：

- `SUPPORTED_BY_TEXT`
- `SUPPORTED_BY_FORMULA`
- `SUPPORTED_BY_EXPERIMENT`
- `REASONABLE_INFERENCE`
- `UNVERIFIED`
- `NEEDS_HUMAN_CHECK`
- `INSUFFICIENT_EVIDENCE`

如果证据不足，只能降级输出，不能强行深度讲解。

## 6. 降级机制

任何模块失败时必须返回结构化状态，不得假装成功。

典型降级：

- `ABSTRACT_ONLY`
- `FULL_TEXT_MISSING`
- `FORMULA_UNAVAILABLE`
- `METHOD_SECTION_MISSING`
- `EXPERIMENT_SECTION_MISSING`
- `BASIC_SUMMARY_ONLY`
- `NO_FORMULA_DEEP_DIVE`
- `LOW_CONFIDENCE_ANALYSIS`

## 7. 安全边界

- LaTeX 不得执行，仅做文本/公式提取。
- PDF 解析不得执行脚本。
- HTML 需要清洗，避免 XSS。
- 用户自由追问必须做指令隔离。
- API key 只从 `.env` 读取，不得写入日志。

## 8. 推荐技术路线

第一阶段优先：

- Python 3.11+
- FastAPI
- Jinja2 + HTMX
- TailwindCSS 或普通 CSS
- Pydantic
- pytest
- PyMuPDF 作为 PDF 兜底
- Markdown/纯文本输入优先支持
- LLM 使用 OpenAI-compatible 接口封装

后续再逐步加入：

- arXiv/Semantic Scholar/OpenAlex
- Marker/MinerU/GROBID adapter
- 向量索引
- Vue/React 前端
- 更复杂的多 Agent 调度
