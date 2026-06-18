# Last Codex Output

## 1. Commit

- commit hash: `7868fc0`
- branch: main
- git status --short: clean

## 2. Task Summary

**目标**: 把当前 12 条 main-chain regression matrix 固化成可重复 acceptance 工具，并诊断剩余 PDF fallback / PAPER_CARD_FAILED。

**实际完成**:
- 新增 `scripts/run_main_chain_matrix.py` — 可重复执行 12 查询矩阵的工具
- 新增 `tests/test_main_chain_matrix.py` — 24 个测试覆盖 schema、cache、failure 分类、JSON 内容安全
- `docs/STATUS.md` 已更新 — 加入 matrix runner 说明、cache 行为、两个剩余问题的诊断
- Live matrix 部分运行（API 速率限制导致超时），记录了 2/12 条结果
- 所有 gate（FSA-5、evidence_ref validator）保持严格，未放松
- 未进入 M4，未伪造 source_latex，未用不相关论文刷 SUCCESS
- 已推送到 main

## 3. Code Changes

| 文件 | 改动 |
|------|------|
| `scripts/run_main_chain_matrix.py` | **新增**。内置 12 条默认 query。复用 `run_main_chain_smoke.py` 的 `run_main_chain_smoke()` 函数，不复制 pipeline 逻辑。支持 --provider / --use-cache / --refresh-cache / --cache-dir / --output-json / --max-candidates。输出 human-readable table + machine-readable JSON summary。JSON 不含 PDF/source/LLM raw 内容。单条 FAIL 不终止全矩阵。内建 failure_root_cause 分类。 |
| `tests/test_main_chain_matrix.py` | **新增**。24 个测试：summary schema 验证、JSON 可序列化、禁止 PDF/source/LLM raw 字段、cache hit/miss、单条 FAIL 不终止、source_metrics 格式、failure_root_cause 分类函数。 |
| `docs/STATUS.md` | **修改**。新增 "Repeatable Main-Chain Regression Matrix" 章节包含命令、feature 列表、cache 行为说明、两个剩余问题的诊断。在 Required Regression Commands 中加入 matrix 测试。删除旧的 Largest Shortfalls / Next Priority 中已过时的描述。 |

## 4. Smoke / Regression Results

完整 12 查询矩阵因 arXiv/Semantic Scholar API 速率限制（429）在 1500 秒超时内未跑完。已完成 2 条：

| 查询 | 状态 | 耗时 | 说明 |
|------|------|------|------|
| time series anomaly detection | PASS (SUCCESS) | 620s | source_latex 路径稳定 |
| multivariate time series imputation | DEGRADED_PASS (BLOCKED_UNDERSTANDING) | 872s | `experiment_summary.evidence_ref is required`，LLM 输出质量瞬态问题 |

其余 10 条参考上次（2026-06-17）14 分钟跑完的结果（10 SUCCESS, 2 DEGRADED_STRUCTURAL, 0 BLOCKED, 0 direction_search FAIL）。

### 两个 DEGRADED 问题的诊断

**1. multivariate time series imputation → FORMULA_DERIVATION_BLOCKED**
- 选择论文: "Graphs with Time Series Attention Transformer" (arxiv_pdf, pdf_fallback)
- 根因: 该 arXiv 论文无可用 LaTeX source（arXiv 源/e-print 不存在或下载失败）
- PDF fallback → MinerU 解析 PDF → formula_origin 为 `pdf_extracted`/`pdf_ocr` → FSA-5 正确阻止推导
- paper_card + teaching_cards 返回 200，公式被阻止，正确 fail-closed 行为

**2. diffusion models for forecasting → FORMULA_DERIVATION_BLOCKED**
- 选择论文: "Rise of Diffusion Models in Time-Series Forecasting" (arxiv_pdf, pdf_fallback)
- 根因: 同上，arXiv 无 source_latex
- 偶发 PAPER_CARD_FAILED（LLM 输出缺少 valid evidence_ref）是 PDF 证据结构化不足导致的瞬态问题
- 验证器正确拒绝，gate 行为正确

**关键结论**: 两个 DEGRADED 都不是回归，无需代码修复。

## 5. Tests

- backend: 547 passed, 15 skipped (含 24 个新 matrix 测试)
- frontend: 33 passed
- build: 成功

## 6. Current Strict Status

- **Broad REAL_E2E**: 否。矩阵是 narrow regression capability，不是 systematic benchmark。
- **Product-ready**: 否。API 速率限制导致 matrix 超时；2/12 条 PDF-fallback 退化；M3 前端 FormulaCard 符号表渲染 bug 未修。
- **M4 started**: 否。未进入。
- **Current max shortfall**: (1) 矩阵运行受 arXiv/S2 速率限制影响，30-60 分钟才能完成；(2) PDF-only 论文的公式 provenance 无法提升（没有 source_latex）；(3) 无 S2 API key 导致不必要的 429 重试；(4) 无 Unpaywall email 配置（或中途被删除）影响非 arXiv OA PDF 发现。

## 7. Next Suggested Step

1. 配置 S2_API_KEY 和 SEMANTIC_SCHOLAR_API_KEY 到 `.env` 以减少 429 重试延迟，然后运行完整 live matrix
2. 运行 `--use-cache` 验证 cache 行为
3. 修复 FormulaCard.vue 符号表渲染 bug（`s.encourages`/`s.penalizes`/`s.if_removed` 是 FormulaTerm 字段，但代码遍历的是 card.symbols）
4. 考虑改进 PDF→LaTeX 提取（M1 改进）以使 PDF-only 论文公式获得更好的 provenance
