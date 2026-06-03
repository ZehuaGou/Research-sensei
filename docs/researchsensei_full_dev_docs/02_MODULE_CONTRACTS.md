# 02_MODULE_CONTRACTS

本文档定义模块边界。Agent 实现时必须遵守：一个模块只做一件事，输入输出用结构化 JSON/Pydantic 模型连接。

## 通用输出 Envelope

所有模块建议返回：

```json
{
  "ok": true,
  "data": {},
  "warnings": [],
  "errors": [],
  "metadata": {
    "generated_at": "ISO-8601",
    "generator_version": "v0.1.0",
    "content_hash": "sha256:..."
  }
}
```

## 1. query

### 职责
理解用户输入方向，生成中英文查询计划、同义词、排除词、搜索意图。

### 输入
`user_query`, `language`

### 输出
`query_plan.json`

### 禁止
- 不得搜索论文。
- 不得生成阅读计划。
- 不得直接生成卡片。

### 测试点
- 中文方向能生成英文术语。
- `search_intents` 必须是封闭枚举。
- 跨领域方向能拆分 `domain_components`。

## 2. acquisition

### 职责
调用搜索 adapter，生成候选池。

### 输入
`query_plan.json`

### 输出
`candidate_pool.json`

### 禁止
- 不得筛选 A_READ。
- 不得做论文精读。
- 不得把搜索结果直接渲染成最终学习卡片。

### 测试点
- 能合并多源候选。
- 每条候选包含 title/year/source/url/abstract 等基础字段。
- 单一搜索源失败不影响其他源。

## 3. selection

### 职责
去重、过滤、分类、评分、生成阅读计划。

### 输入
`candidate_pool.json`

### 输出
`deduped_candidates.json`, `filtered_candidates.json`, `reading_plan.json`

### 禁止
- 不得下载全文。
- 不得生成论文卡片。

### 测试点
- DOI/arXiv/title fuzzy 去重。
- 每篇论文必须有 `scoring_breakdown`。
- `A_READ` 默认不超过 12 篇。

## 4. source_resolver

### 职责
根据阅读计划获取全文来源或本地输入，并记录来源状态。

### 输入
`paper metadata`, `input_path/url`

### 输出
`source_status.json`, `paper.pdf/source.tex/raw.md`

### 禁止
- 不得解析正文。
- 不得生成理解结论。

### 测试点
- 文件不存在时返回 `SOURCE_NOT_FOUND`。
- 只有摘要时返回 `ABSTRACT_ONLY`。
- API/下载失败时可降级。

## 5. ingestion

### 职责
把 PDF/LaTeX/Markdown/纯文本解析成 sections 和 blocks。

### 输入
`source_status.json`, source file

### 输出
`paper_sections.json`, `blocks.json`, `extraction_warnings.json`

### block 类型
`title`, `abstract`, `heading`, `paragraph`, `formula`, `figure`, `table`, `algorithm`, `reference`, `appendix`

### 禁止
- 不得解释论文。
- 不得生成 paper_skeleton。
- 不得调用 LLM 编造缺失内容。

### 测试点
- 至少能解析 markdown/txt。
- PDF 解析失败时有 warning。
- 每个 block 必须有 `block_id`, `type`, `section`, `evidence_ref`。

## 6. grounding

### 职责
把关键 claim 和原文 blocks 绑定。

### 输入
`blocks.json`, draft claims 或 skeleton candidates

### 输出
`evidence_index.json`

### 禁止
- 不得把 `REASONABLE_INFERENCE` 写成 `SUPPORTED_BY_TEXT`。
- 不得在没有 evidence_ref 时标注强证据。

### 测试点
- claim 有 evidence_type。
- evidence_ref 能定位到 block。
- 证据缺失时标 `INSUFFICIENT_EVIDENCE`。

## 7. understanding

### 职责
生成论文骨架：问题、旧方法、瓶颈、新假设、机制、目标、实验、局限、迁移点。

### 输入
`paper_sections.json`, `blocks.json`, `evidence_index.json`

### 输出
`paper_skeleton.json`

### 禁止
- 不得照抄 abstract 当理解。
- 不得无证据生成强结论。

### 测试点
- 输出包含 problem/bottleneck/mechanism/objective/experiments/limitations。
- 每个关键字段带 evidence 或 evidence_status。

## 8. teaching

### 职责
把 skeleton 和 concepts 讲成适合基础较弱用户的中文学习内容。

### 输入
`paper_skeleton.json`, `user_profile`

### 输出
`paper_card.json`, `concept_cards.json`

### 禁止
- 不得输出空话：“提升性能”“优化效果”但不解释机制。
- 不得过度长篇堆砌。

### 测试点
- 包含人话版、机制版、论文作用版。
- 不确定内容标注。

## 9. formula

### 职责
对公式进行符号、项、作用、去除影响、数字例子讲解。

### 输入
`formula blocks`, `nearby_text`, `paper_skeleton.json`

### 输出
`formula_cards.json`

### 禁止
- 附近文本不足时禁止深度推断。
- 不得只写“该公式用于优化模型”。

### 测试点
- 每张公式卡包含 purpose/symbols/terms/numeric_example/what_if_removed/evidence_status。

## 10. patterns

### 职责
归类科研创新模式。

### 输入
`paper_skeleton.json`

### 输出
`pattern_cards.json`

### 禁止
- 不得把所有论文都归为泛泛“方法创新”。

### 测试点
- 每个模式包含 why_this_pattern/how_paper_uses_it/transfer_guidance。

## 11. drill

### 职责
生成复述题、复习题、迁移题、导师追问，并支持错误归因。

### 输入
`paper_card.json`, `formula_cards.json`, `pattern_cards.json`, `memory_store.json`

### 输出
`drill_cards.json`, `error_attribution.json`

### 禁止
- 不得只问“论文提出了什么方法”。

### 测试点
- 包含 immediate_recall/next_day_review/one_week_transfer/advisor_questions。
- 错误归因包含 error_types 和 next_action。

## 12. render

### 职责
把 JSON 卡片渲染成 HTML/Markdown。

### 输入
cards JSON

### 输出
HTML/Markdown

### 禁止
- 不得在 render 中调用 LLM。
- 不得把多个复杂卡片横向挤压成小字。

### 测试点
- HTML 包含 30 秒看懂、5 分钟讲懂、深挖推导、证据状态、追问入口。
- KaTeX/MathJax 能渲染公式。

## 13. interactive

### 职责
用户在卡片中追问，系统构造上下文包，调用 LLM，生成回答，并更新 memory。

### 输入
`user_question`, `card_id`, `selected_text`, `session_id`

### 输出
`interactive_answer.json`, 更新 `memory_store.json`

### 禁止
- 不得只把用户一句话发给 LLM。
- 不得把整篇论文塞进 prompt。

### 测试点
- prompt 包含 current_card/evidence/recent_history/user_question 隔离区。
- 支持快捷问题：再讲简单点、数字例子、导师追问、测我懂没懂。

## 14. context

### 职责
管理当前卡片、检索证据、压缩历史、缓存、用户画像。

### 输入
session 状态、用户追问、cards、blocks

### 输出
context_pack.json, memory_store.json, cache hits/misses

### 禁止
- 不得无上限增长 prompt。

### 测试点
- 最近对话超长时能压缩。
- 缓存基于 content_hash/prompt_version/model_name 失效。

## 15. llm

### 职责
统一封装模型 API、重试、超时、streaming、token budget、response cache。

### 输入
PromptRequest

### 输出
LLMResponse

### 禁止
- 不得在业务模块中散落直接 API 调用。
- 不得记录 API key。

### 测试点
- mock 模式能无 API key 跑通测试。
- 超时/重试/缓存可配置。

## 16. direction

### 职责
基于多篇 paper_skeleton 生成问题驱动的方向脉络，而不是论文列表。

### 输入
`reading_plan.json`, 多个 `paper_skeleton.json`

### 输出
`direction_map.json`, `direction_map.html`

### 禁止
- 不得把 direction map 做成普通 bibliography。

### 测试点
- 输出包含核心问题、演化阶段、代表论文、新问题、学习顺序。
