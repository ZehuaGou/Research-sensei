# Last Codex Output

## 1. Commit

- commit hash: `bf2ea17`
- branch: main
- git status --short: clean (after commit)

## 2. Task Summary

**目标**:
1. 检查 .env 中 `UNPAYWALL_EMAIL` / `RESEARCHSENSEI_CONTACT_EMAIL` / `SEMANTIC_SCHOLAR_API_KEY` / `S2_API_KEY`
2. 验证 `run_main_chain_matrix.py --use-cache` 行为
3. 修复 FormulaCard.vue 符号表渲染 bug
4. 补充前端测试
5. 后端 + 前端测试 + build 全跑

**实际完成**:
- `.env` 检查: `UNPAYWALL_EMAIL` 和 `RESEARCHSENSEI_CONTACT_EMAIL` 存在于 `.env`（含完整邮箱），`SEMANTIC_SCHOLAR_API_KEY` 和 `S2_API_KEY` 缺失
- Cache 行为验证: 通过 `_verify_cache.py` 程序化验证缓存读写、TTL、内容安全（无 PDF/source/LLM），确认 12 个缓存文件中过期/有效状态
- FormulaCard.vue bug 修复: 符号表从 `card.symbols`（FormulaSymbol: 4字段）改为 `card.terms`（FormulaTerm: 7字段），正确渲染 `encourages`/`penalizes`/`if_removed`
- 新增 9 个 FormulaCard 前端测试
- 全量测试通过: backend 547 + 15 skip, frontend 42 pass, build 成功

## 3. Code Changes

| 文件 | 改动 |
|------|------|
| `frontend/src/components/cards/FormulaCard.vue` | **修复 bug**。符号表从迭代 `card.symbols` 改为 `card.terms`。FormulaTerm 有 `term`/`meaning`/`encourages`/`penalizes`/`if_removed` 7 字段，FormulaSymbol 只有 `symbol`/`meaning`/`evidence_status`/`confidence` 4 字段。原代码访问不存在的 `s.encourages`/`s.penalizes`/`s.if_removed`，导致这些列始终显示 `-`。 |
| `frontend/src/components/tests/FormulaCard.spec.ts` | **新增**。9 个测试覆盖: 核心字段渲染、origin 标签、OCR 标签、term 表完整字段、空字段回退 `-`、空 terms 不渲染、无 terms 不崩溃、KaTeX 错误处理、展开/收起交互。 |

## 4. Smoke / Regression Results

未运行完整矩阵（上轮已确认 10/12 SUCCESS, 2/12 DEGRADED）。本次仅验证 cache 行为:

**Cache 验证结果**:
- 12 个缓存文件存在于 `.cache/researchsensei/`
- 5/12 为有效期内的 VALID 条目（由本次 partial `--use-cache` 运行刷新）
- 7/12 为过期条目（>6h TTL）
- 程序化测试: cache 读写正确，TTL 检查正确，缓存不含 PDF/source/LLM 内容
- 限制: cache 只缓存 direction search 结果；seed expansion、deep_read、M2/M3 永远不缓存

**`--use-cache` 矩阵运行**（1800s 超时）:
- 5/12 queries 使用了缓存（cache_hit=True），direction search 阶段未调用外部 API
- 7/12 queries 缓存过期，fall through 到 live API，因 arXiv/Semantic Scholar 429 超时
- Matrix 对单条 FAIL 正确处理（不终止），但因网络不可靠无法完成全部 12 条

## 5. Tests

- backend: 547 passed, 15 skipped
- frontend: **42 passed**（新增 9 个 FormulaCard 测试）
- build: 成功

## 6. .env Key Status

| Key | 在 .env 中 | 运行时可见 |
|-----|-----------|-----------|
| `UNPAYWALL_EMAIL` | 是 | 否（未 export 到环境变量） |
| `RESEARCHSENSEI_CONTACT_EMAIL` | 是 | 否（未 export 到环境变量） |
| `SEMANTIC_SCHOLAR_API_KEY` | **缺失** | 缺失 |
| `S2_API_KEY` | **缺失** | 缺失 |

缺少 S2 API key 是 Semantic Scholar 持续 429 的根本原因。Unpaywall email 在 `.env` 中但未注入到 Python 进程环境变量，需显式 `$env:UNPAYWALL_EMAIL=...` 或通过 `dotenv` 加载。

## 7. Current Strict Status

- **Broad REAL_E2E**: 否。narrow regression matrix。
- **Product-ready**: 否。API 速率限制导致矩阵无法完整运行；2/12 PDF-fallback 退化。
- **M4 started**: 否。
- **Current max shortfall**: (1) 缺少 S2_API_KEY 导致 Semantic Scholar 持续 429；(2) Unpaywall email 未注入运行环境；(3) 矩阵运行时需 ~60+ 外部 API 调用，依赖 API 健康状态；(4) PDF-only 论文公式 provenance 无法提升。

## 8. Next Suggested Step

1. 将 `.env` 中的 `MIMO_API_KEY`、`UNPAYWALL_EMAIL` 注入环境变量（通过 dotenv 或 shell export）
2. 添加 `SEMANTIC_SCHOLAR_API_KEY` 和 `S2_API_KEY` 到 `.env` 减少 429
3. 运行完整 live matrix: `--provider mimo --refresh-cache`
4. 运行 cached matrix: `--provider mimo --use-cache`
5. 确认 cache hit 数 = 12，direction search 阶段外部 API 调用为零
