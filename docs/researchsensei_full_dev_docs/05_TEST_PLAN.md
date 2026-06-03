# 05_TEST_PLAN

## 测试原则

- 先写 schema 测试，再写业务测试。
- 外部 API 全部 mock。
- LLM 默认 mock，真实模型测试单独标记。
- 解析失败必须可测试。
- 不追求一开始覆盖全部真实论文，先保证 pipeline 不乱。

## 测试目录建议

```text
tests/
  fixtures/
  test_config.py
  test_schemas.py
  test_llm_client.py
  test_prompt_builder.py
  test_source_resolver.py
  test_ingestion_markdown.py
  test_ingestion_pdf.py
  test_grounding.py
  test_understanding.py
  test_formula_card.py
  test_pattern_card.py
  test_drill_card.py
  test_render_html.py
  test_context_pack.py
  test_interactive_followup.py
  test_query_planner.py
  test_selection.py
  test_direction_map.py
  test_response_cache.py
  test_pipeline_resume.py
  test_security.py
```

## 必须测试的错误场景

### 输入错误
- 文件不存在
- 空文件
- 只有标题
- 只有摘要
- PDF 解析失败
- 乱码文本

### 证据错误
- claim 没有 evidence_ref
- evidence_ref 不存在
- 公式附近文本缺失
- 实验 section 缺失

### LLM 错误
- API timeout
- 返回非 JSON
- 返回缺字段 JSON
- token 超预算

### 交互错误
- 用户问题包含 prompt injection
- session 不存在
- card_id 不存在
- selected_text 不属于当前卡片

### 缓存错误
- prompt_version 改变后缓存失效
- content_hash 改变后缓存失效
- model_name 改变后缓存失效

### 安全错误
- LaTeX 包含 `\write18`
- HTML 包含 `<script>`
- 文件路径包含 `../`
- API key 出现在日志中

## 每阶段测试命令

```bash
pytest tests/test_schemas.py
pytest tests/test_llm_client.py tests/test_prompt_builder.py
pytest tests/test_source_resolver.py tests/test_ingestion_markdown.py
pytest tests/test_grounding.py tests/test_understanding.py
pytest tests/test_formula_card.py tests/test_drill_card.py
pytest tests/test_render_html.py
pytest tests/test_context_pack.py tests/test_interactive_followup.py
pytest tests/test_query_planner.py tests/test_selection.py tests/test_direction_map.py
pytest tests/test_pipeline_resume.py tests/test_security.py
```

## 夜间任务测试规则

Agent 每完成一个 task 必须运行相关测试。若失败：

1. 在当前 task 范围内修复一次。
2. 再失败，停止后续任务。
3. 写 `PROGRESS.md`。
4. 写 `OPEN_QUESTIONS.md`。

## 新增测试方向 (2026-06-03)

以下测试方向在 Phase 11.6-11.9 中逐步补充：

### Parser Adapter Contract Tests
- ParserAdapter interface 定义
- LightweightParser 作为 default
- optional adapter 的 fallback 行为

### Passage Index Tests
- passage-level 索引正确性
- claim extraction 从 passage 中提取
- ClaimEvidence v2 的 semantic support

### Evidence Retriever Tests
- 根据 claim 检索相关 passage
- evidence_ref 有效性验证
- 降级行为（无相关 passage 时）

### Evidence-constrained LLM Mock Tests
- LLM 输出必须绑定 evidence_ref
- 幻觉 ref 拒绝
- LLM 失败时 fallback 到 rule-based

### Explanation Audit Tests
- 解释忠实原文检查
- 公式解释准确性检查
- 非模板化检查
- 不确定性处理检查

### Paper Understanding Benchmark Fixtures
- 普通方法论文 fixture
- 公式密集论文 fixture
- 信息不足论文 fixture

详见 `docs/QUALITY_EVALUATION_SPEC.md` 和 `docs/RESEARCHSENSEI_TECH_ROUTE_REVIEW.md`。
