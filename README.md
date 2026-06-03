# ResearchSensei / 研读导师

科研论文理解与思维框架训练系统。不是论文摘要器，而是帮助用户真正读懂论文、理解公式、形成科研思维、回答导师追问的学习工作台。

## 主要文档

- [docs/DESIGN.md](docs/DESIGN.md) — 产品定位、架构、技术路线
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — 开发规则、入口
- [docs/development/PAPER_UNDERSTANDING.md](docs/development/PAPER_UNDERSTANDING.md) — ParserAdapter / Evidence / LLM / Quality
- [docs/development/LITERATURE_SEARCH.md](docs/development/LITERATURE_SEARCH.md) — Query / Acquisition / Selection / Reading Plan

## 当前状态

- Phase 1-11 baseline complete (281 tests)
- Phase 12 (patterns + drill) frozen
- 下一步：Paper Understanding 升级

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

backend/         — 旧版代码（冻结）
frontend/        — Vue 3 前端（保留）
tests/           — 测试
```
