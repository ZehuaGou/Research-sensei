# ResearchSensei / 研读导师

科研论文理解与思维框架训练系统。不是论文摘要器，而是帮助用户真正读懂论文、理解公式、形成科研思维、回答导师追问的学习工作台。

## 当前状态

- Phase 1-11 完成 (269 tests passing)
- Phase 12 (patterns + drill) 未开始
- interactive / render / frontend 对接未实现

## 已实现功能

### 单篇论文精读

输入 PDF / Markdown / 纯文本，生成 7 个结构化 artifact：

1. `source_status.json` — 来源状态
2. `parsed_document.json` — 文档解析 blocks
3. `evidence_index.json` — 证据定位
4. `paper_skeleton.json` — 论文骨架
5. `paper_card.json` — 论文学习卡
6. `formula_cards.json` — 公式讲解卡
7. `teaching_cards.json` — 五层教学卡

### 研究方向学习

输入研究方向（中/英文），生成 4 个 artifact：

1. `query_plan.json` — 查询计划
2. `candidate_pool.json` — 候选论文池
3. `filtered_candidates.json` — 去重后候选
4. `reading_plan.json` — 阅读计划

## 安装

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e ".[dev]"
```

## 测试

```bash
python -m pytest -q
```

默认测试不联网、不调 LLM、不依赖外部服务。

## 项目结构

```
src/researchsensei/
  core/          — 配置、日志、错误类型
  schemas/       — Pydantic 数据契约
  llm/           — LLM 客户端、prompt builder、缓存
  ingestion/     — 文档解析
  workspace/     — 工作目录管理
  jobs/          — SQLite job 持久化
  web/           — FastAPI API
  acquisition/   — arXiv / OpenAlex adapter
  selection/     — 去重、评分、阅读计划
  query/         — 查询规划
  direction/     — 方向分析编排
  grounding.py   — 证据定位
  paper_skeleton.py — 论文骨架
  paper_card.py  — 论文卡
  formula_card.py — 公式卡
  teaching_card.py — 教学卡
  source_resolver.py — 来源解析

backend/         — 旧版代码（冻结，仅作迁移参考）
frontend/        — Vue 3 前端（保留，未重写）
tests/           — 测试
legacy_tests/    — 旧测试（已排除）
tests_e2e/       — E2E 测试（已排除）
```

## 配置

复制 `.env.example` 为 `.env`，填入 API key：

```bash
cp .env.example .env
```

支持 DeepSeek、MiMo 和任意 OpenAI-compatible provider。

## 复用边界

不自研：论文搜索、PDF 解析、RAG、向量检索、间隔复习算法。

自研：Teach-Me Engine、Formula Tutor、Research Pattern Library、Learning Card Schema、交互追问协议。
