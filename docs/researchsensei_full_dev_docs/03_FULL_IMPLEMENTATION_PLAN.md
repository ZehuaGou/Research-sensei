# 03_FULL_IMPLEMENTATION_PLAN

> **2026-06-03 更新**：Phase 1-11 完成作为 baseline infrastructure。Phase 12 冻结。
> 新增 Phase 11.5-11.9 子阶段，用于升级论文理解核心。
> 详见 `docs/RESEARCHSENSEI_TECH_ROUTE_REVIEW.md` 和 `docs/PHASE_MAPPING.md`。
>
> 原始 Phase 12（工程可靠性）推迟到后续。当前 Phase 12 = patterns + drill。

## 总前置规则：Phase 复用评估门禁

ResearchSensei 的每个 Phase 在执行代码任务前，必须先完成复用评估，并更新 `docs/REUSE_REPORT.md`。

执行顺序：

1. 明确本 Phase 要解决的问题和模块边界。
2. 列出候选开源项目、GitHub 项目、官方 API、SDK 或可复用库。
3. 按 `docs/REUSE_REPORT.md` 的评估表检查 license、维护活跃度、recent commits、issues、安装复杂度、Windows 支持、本地部署、GPU/付费 API、中文适配、安全性、替代方案和复用风险。
4. 决定每个候选的使用方式：`DIRECT_DEPENDENCY` / `OPTIONAL_ADAPTER` / `REFERENCE_ONLY` / `NOT_USE`。
5. 明确是否需要新增依赖、是否需要 Adapter、是否允许进入代码开发。

门禁：

- 复用评估未完成，不允许执行本 Phase 的业务代码任务。
- 不允许为了快而写低质量替代实现。
- 不允许把第三方库深度耦合进核心逻辑；必须通过 Adapter 封装。
- 不允许引入未评估 license 的依赖。
- 不允许把真实网络测试放入默认 pytest。
- Phase 计划中的每个后续阶段都默认受此规则约束，不需要在每个 Phase 条目中重复书写。

这是完整项目分解。文档覆盖所有阶段，但代码执行必须阶段化。

## 总阶段概览

| Phase | 名称 | 目标 | 是否可夜间自动跑 |
|---|---|---|---|
| 0 | 文档与复用评估 | 建立规则、评估依赖 | 是 |
| 1 | 项目骨架 | 建立可运行空项目 | 是 |
| 2 | Schema 与示例数据 | 固定数据契约 | 是 |
| 3 | LLM 层与 Prompt 基建 | 模型调用可控、可 mock | 是 |
| 4 | 单篇论文输入与解析 | markdown/txt/PDF 基础解析 | 是 |
| 5 | 证据定位与论文骨架 | grounding + skeleton | 部分可自动 |
| 6 | 学习卡片生成 | paper/formula/concept/pattern/drill cards | 部分可自动 |
| 7 | HTML 渲染与页面 | 静态卡片 + HTMX 追问入口 | 是 |
| 8 | 交互追问与上下文 | context pack + memory + advisor mode | 部分可自动 |
| 9 | 方向学习核心 | query/acquisition/selection/reading plan | 部分可自动 |
| 10 | 多论文方向脉络 | direction map + 多论文聚合 | 需人工验收 |
| 11 | 复习与用户模型 | feedback、review、error attribution | 部分可自动 |
| 12 | 工程可靠性 | 缓存、断点续跑、日志、安全 | 是 |
| 13 | 真实样例与评估集 | 用真实论文做端到端评估 | 需人工验收 |
| 14 | 打包与部署 | CLI/Web/API 文档与启动脚本 | 是 |

---

# Phase 0：文档与复用评估

## 目标
先定技术边界，不写业务代码。

## 任务

### Task 0.1 创建文档目录
授权文件：
- `docs/REUSE_REPORT.md`
- `docs/MODULE_CONTRACTS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/REVIEW_CHECKLIST.md`
- `docs/GLOSSARY.md`
- `docs/OPEN_QUESTIONS.md`

完成标准：文档存在，包含 TODO 和初步结论。

### Task 0.2 复用评估
评估：
- PyMuPDF
- Marker/MinerU/GROBID
- arXiv API
- Semantic Scholar / OpenAlex / Crossref
- Jinja2 / HTMX
- Chroma/Qdrant 或本地轻量检索
- Pydantic / FastAPI

完成标准：每个依赖说明用途、license、是否必须、替代方案、风险。

### Task 0.3 决定第一轮最小依赖
推荐第一轮只引入：
- fastapi
- uvicorn
- pydantic
- python-dotenv
- jinja2
- pytest
- pymupdf（可选）
- markdown/beautifulsoup4（可选）

---

# Phase 1：项目骨架

## 目标
创建可运行、可测试、可导入的项目。

## 任务

### Task 1.1 创建目录结构
授权创建：
- `src/researchsensei/`
- `tests/`
- `configs/`
- `templates/`
- `outputs/sample/`
- `scripts/`

完成标准：`python -m researchsensei --help` 或基础 CLI 能运行。

### Task 1.2 配置与日志
实现：
- `.env.example`
- `configs/default.yaml`
- `src/researchsensei/config.py`
- `src/researchsensei/logging_utils.py`

完成标准：配置可加载，日志不输出 API key。

### Task 1.3 基础 CLI
实现命令：

```bash
researchsensei healthcheck
researchsensei parse --input examples/sample.md
researchsensei render --paper-id sample
```

完成标准：healthcheck 通过，parse/render 可返回合理错误。

---

# Phase 2：Schema 与示例数据

## 目标
先固定 JSON/Pydantic 契约，防止后续模块互相乱接。

## 任务

### Task 2.1 定义通用模型
文件：
- `src/researchsensei/schemas/common.py`

包含：
- StatusEnvelope
- WarningItem
- ErrorItem
- EvidenceStatus
- DegradationStatus
- GeneratedMetadata

### Task 2.2 定义论文解析模型
文件：
- `src/researchsensei/schemas/paper.py`

包含：
- PaperMetadata
- PaperSection
- Block
- FormulaBlock
- FigureBlock
- TableBlock
- SourceStatus

### Task 2.3 定义卡片模型
文件：
- `src/researchsensei/schemas/cards.py`

包含：
- PaperSkeleton
- PaperCard
- FormulaCard
- PatternCard
- DrillCard
- ConceptCard

### Task 2.4 示例 fixture
文件：
- `tests/fixtures/sample_paper.md`
- `tests/fixtures/sample_blocks.json`
- `tests/fixtures/sample_paper_skeleton.json`

完成标准：所有 schema 可序列化/反序列化，pytest 通过。

---

# Phase 3：LLM 层与 Prompt 基建

## 目标
所有模型调用统一走 llm 模块，支持 mock，避免业务模块直接请求 API。

## 任务

### Task 3.1 LLM Client
文件：
- `src/researchsensei/llm/client.py`
- `src/researchsensei/llm/types.py`
- `src/researchsensei/llm/model_config.py`

要求：
- OpenAI-compatible API
- timeout/retry
- mock mode
- 不记录 API key

### Task 3.2 Prompt Builder
文件：
- `src/researchsensei/llm/prompt_builder.py`

要求：
- system/user/context/evidence 分区
- 用户问题指令隔离
- prompt_version

### Task 3.3 Token Budget
文件：
- `src/researchsensei/llm/token_budget.py`

要求：
- 估算输入长度
- 超预算时裁剪 evidence/history

### Task 3.4 Response Cache
文件：
- `src/researchsensei/context/response_cache.py`

要求：
- key 包含 prompt_version/model_name/model_config/content_hash
- 支持手动清除

完成标准：无 API key 时 mock 测试全通过。

---

# Phase 4：单篇论文输入与解析

## 目标
跑通本地论文输入 -> blocks。

## 任务

### Task 4.1 source_resolver 本地输入
支持：
- `.md`
- `.txt`
- `.pdf` 基础解析

输出 `source_status.json`。

### Task 4.2 ingestion: markdown/txt parser
输出：
- sections
- blocks
- detected_language
- extraction_warnings

### Task 4.3 ingestion: PDF fallback
使用 PyMuPDF 做基础文本抽取。

要求：
- 解析失败给 warning
- 不做 OCR
- 不假装公式解析成功

### Task 4.4 block index
生成：
- `blocks.json`
- `paper_sections.json`

完成标准：sample markdown 能生成结构化 blocks。

---

# Phase 5：证据定位与论文骨架

## 目标
从 blocks 生成有证据状态的 paper_skeleton。

## 任务

### Task 5.1 grounding 基础版
输入 blocks，输出 evidence_index。

初期可先支持：
- section-level evidence
- paragraph evidence
- formula nearby evidence

### Task 5.2 understanding skeleton generator
基于 LLM mock/真实模型生成：
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

### Task 5.3 evidence checker
检查 skeleton 中关键字段是否有 evidence。

完成标准：没有证据的 claim 标为 `UNVERIFIED` 或 `INSUFFICIENT_EVIDENCE`。

---

# Phase 6：学习卡片生成

## 目标
把 skeleton 转成可学习卡片。

## 任务

### Task 6.1 paper_card
包含：
- 30 秒看懂
- 5 分钟讲懂
- 核心问题
- 旧方法瓶颈
- 新机制
- 实验证据
- 局限
- 迁移思路

### Task 6.2 formula_card
包含：
- purpose
- symbols
- terms
- numeric_example
- what_if_removed
- weight_sensitivity
- evidence_status

### Task 6.3 concept_card
识别难点概念，生成：
- 人话版
- 类比版
- 最小公式版
- 数字例子
- 论文作用版

### Task 6.4 pattern_card
归类科研模式：
- Representation
- Objective
- Structure
- Generation
- Retrieval/Memory
- Reasoning/Planning
- Causal/Counterfactual
- Evaluation
- System Pipeline

### Task 6.5 drill_card
生成：
- immediate_recall
- next_day_review
- one_week_transfer
- advisor_questions
- weakness_checks

完成标准：cards JSON 通过 schema 校验。

---

# Phase 7：HTML 渲染与页面

## 目标
把 cards 渲染成可读页面。

## 任务

### Task 7.1 Jinja2 模板
文件：
- `templates/base.html`
- `templates/paper_card.html`
- `templates/formula_card.html`
- `templates/drill_card.html`

### Task 7.2 页面布局
要求：
- 大屏三栏：目录 / 学习区 / 追问区
- 小屏纵向：学习区 / 追问区
- 卡片不横向挤压
- 公式渲染 KaTeX/MathJax

### Task 7.3 FastAPI 基础服务
路由：
- `/`
- `/papers/{paper_id}`
- `/papers/{paper_id}/cards/{card_id}`
- `/api/ask`

完成标准：sample paper 可打开 HTML。

---

# Phase 8：交互追问与上下文

## 目标
用户在卡片上追问，系统知道当前论文/卡片/公式/证据。

## 任务

### Task 8.1 context pack builder
输入：session_id, card_id, selected_text, user_question
输出：context_pack.json

必须包含：
- current card
- selected text
- evidence chunks
- recent chat history
- user profile
- instruction-isolated user question

### Task 8.2 interactive answer
支持模式：
- Explain Simpler
- Numeric Example
- Step-by-Step Derivation
- Advisor Mode
- Quiz Me

### Task 8.3 memory_store
记录：
- understood_items
- confusing_items
- asked_questions
- weak_concepts
- review_cards
- feedback

### Task 8.4 Advisor 状态机
状态：
- INITIATE
- LISTEN
- ASSESS
- PROBE
- HINT
- REVEAL_AND_CONTRAST
- SUMMARIZE

完成标准：追问不是孤立问答，而是带上下文和证据。

---

# Phase 9：方向学习核心

## 目标
支持用户输入方向，生成搜索计划和阅读计划。

## 任务

### Task 9.1 query planner
生成：
- direction_zh
- direction_en
- core_terms
- related_terms
- exclude_terms
- search_intents
- sub_directions

### Task 9.2 acquisition adapters
初期支持 mock + arXiv/OpenAlex/Semantic Scholar 中至少一个真实 adapter。

### Task 9.3 selection scoring
实现：
- 去重
- role classification
- scoring_breakdown
- A_READ/B_SKIM/C_REFERENCE/D_IGNORE

完成标准：输入“时间序列异常检测”能生成 reading_plan.json。

---

# Phase 10：多论文方向脉络

## 目标
把多篇 paper_skeleton 组织成问题驱动的方向地图。

## 任务

### Task 10.1 direction map generator
输出：
- direction_core_problem
- evolution_chain
- representative_papers
- unresolved_problems
- recommended_learning_order

### Task 10.2 direction_map.html
渲染：
- 方向概览
- 阶段演化
- 每阶段代表论文
- 下一步学习顺序

完成标准：不能只是论文列表，必须是问题驱动演化链。

---

# Phase 11：复习与用户模型

## 目标
让系统能根据用户反馈调整讲解和复习。

## 任务

### Task 11.1 feedback API
反馈类型：
- TOO_HARD
- TOO_SHALLOW
- TOO_VERBOSE
- TOO_SHORT
- NEEDS_EXAMPLE
- FORMULA_UNCLEAR
- EVIDENCE_WEAK
- HELPFUL

### Task 11.2 error attribution
错误类型：
- CONCEPT_CONFUSION
- FORMULA_SYMBOL_CONFUSION
- MECHANISM_GAP
- EVIDENCE_MISSING
- TRANSFER_FAILURE
- MEMORY_DECAY
- MATH_DERIVATION_ERROR
- OVERGENERALIZATION

### Task 11.3 review scheduler
支持：
- 立即复述
- 隔天复习
- 一周迁移

完成标准：用户答题后能生成诊断和下一步训练。

---

# Phase 12：工程可靠性

## 目标
保证系统可长期运行和可调试。

## 任务

### Task 12.1 断点续跑
每个 pipeline step 写状态文件：
- pending
- running
- success
- failed
- skipped

### Task 12.2 日志与成本统计
记录：
- 每步耗时
- 模型名
- token 估算
- 缓存命中
- 降级原因
- 输出路径

不得记录：
- API key
- 完整敏感论文原文

### Task 12.3 缓存失效
支持：
- prompt_version
- schema_version
- model_name
- content_hash
- TTL
- 手动清除

### Task 12.4 安全测试
测试：
- prompt injection
- LaTeX dangerous command
- HTML XSS
- path traversal

完成标准：安全测试通过。

---

# Phase 13：真实样例与评估集

## 目标
用真实论文验证系统是否真的有用。

## 任务

### Task 13.1 sample paper set
准备：
- 一篇英文 ML 论文
- 一篇中文论文/讲义
- 一篇公式较多论文
- 一篇只有摘要/解析质量低的材料

### Task 13.2 golden outputs
人工检查：
- paper_skeleton 是否准确
- formula_card 是否不胡编
- drill 是否有深度
- direction map 是否不是论文列表

### Task 13.3 evaluation report
生成：
- `outputs/evaluation/EVAL_REPORT.md`

完成标准：至少一篇论文完整端到端跑通并人工确认。

---

# Phase 14：打包与部署

## 目标
让用户能稳定启动和使用。

## 任务

### Task 14.1 启动脚本
- `scripts/dev_server.sh`
- `scripts/dev_server.ps1`
- `scripts/run_sample.sh`

### Task 14.2 CLI 文档
支持：
- parse
- generate-cards
- render
- serve
- direction-plan

### Task 14.3 部署文档
说明：
- Windows/Conda
- Linux
- .env
- 常见错误

完成标准：新机器按 README 能跑 sample。
