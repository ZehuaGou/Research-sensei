# ResearchSensei Development

---

## 1. 当前开发状态

- Phase 1-11 baseline complete，281 tests passing
- Phase 12 frozen
- 当前优先开发大模块：Paper Understanding 升级

---

## 2. 开发文档入口

| 文档 | 内容 |
|------|------|
| [development/PAPER_UNDERSTANDING.md](development/PAPER_UNDERSTANDING.md) | ParserAdapter / Evidence / LLM / Quality Benchmark |
| [development/LITERATURE_SEARCH.md](development/LITERATURE_SEARCH.md) | Query / Acquisition / Selection / Reading Plan |

---

## 3. 通用开发规则

- 只改授权文件
- 不改旧 `backend/`
- 不改 `frontend/`，除非阶段明确授权
- 不新增依赖，除非先做 reuse gate
- 默认 pytest 不联网、不调用真实 LLM
- HTTP 测试用 `httpx.MockTransport`
- LLM 测试用 `MockLLMClient`
- 不提交 `.env` / API key / 缓存 / 大文件
- 不写 Claude 贡献者信息

---

## 4. 开发文档粒度要求

每个开发模块文档必须写到：

- 文件路径
- 类名
- 方法签名
- 输入 / 输出
- 错误 / 降级策略
- artifact 变化
- 测试计划（每个关键测试的断言）
- hard-fail 条件

---

## 5. Phase 1-11 Baseline Contract

| Phase | 核心文件 | 能力 | Artifact | 限制 |
|-------|----------|------|----------|------|
| 1 | `__init__.py`, `__main__.py` | CLI healthcheck | — | 只有 healthcheck |
| 2 | `core/`, `schemas/` | Config, logging, schemas | — | — |
| 3 | `workspace/`, `jobs/` | Workspace, SQLite jobs | workspace 结构 | — |
| 4 | `ingestion/lightweight.py` | .md/.txt/.pdf 解析 | parsed_document.json | PyMuPDF fallback 质量低 |
| 5 | `source_resolver.py`, `web/app.py` | Source resolver, API | source_status.json | — |
| 6 | `grounding.py`, `paper_skeleton.py` | Evidence, skeleton | evidence_index.json, paper_skeleton.json | **block-level evidence** |
| 7 | `llm/` (6 files) | LLM client, prompt, cache | — | — |
| 8 | `paper_card.py` | Paper card | paper_card.json | **rule-based baseline** |
| 9 | `formula_card.py` | Formula cards | formula_cards.json | **generic symbol dict** |
| 10 | `teaching_card.py` | Teaching cards | teaching_cards.json | **rule-based baseline** |
| 11 | `query/`, `acquisition/`, `selection/`, `direction/` | Direction pipeline | 4 artifacts | **v1, not full lit review** |
